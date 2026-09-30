from fastapi import FastAPI, UploadFile, File, Form, Body, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import time
import math
import numpy as np
import io
import zipfile
import json
import sys
import os
import uuid
import gc
import shutil
import tempfile
from starlette.concurrency import run_in_threadpool

jobs = {}

from core_logic import calculate_metrics, run_nist_suite, Extractors
from new_tests import run_compression_test, run_testu01_suite, run_dieharder_suite

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "running", "message": "RNG Extractors Backend API is live"}

METHODS = Extractors.get_all_extractors()
METHODS_DICT = {name: func for name, func in METHODS}

SLOW_METHODS = [
    "2. Leftover Hash Lemma (LHL)",
    "10. Goldreich–Levin Extractor",
    "11. Chor–Goldreich 2-Source",
    "15. Trevisan Extractor",
    "17. Quantum-Proof Strong Extractor"
]
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024 # 5GB
FAST_TIER_THRESHOLD = 50000
# Bits are held as one int8 per bit and copied into each worker process, so a
# 500 MB upload would need >4 GB per copy. Analysis runs on the first
# MAX_ANALYSIS_BITS bits: statistical suites only consume 1M-16M bits anyway.
MAX_ANALYSIS_BITS = int(os.environ.get("RNG_MAX_ANALYSIS_BITS", 64 * 1024 * 1024))
MAX_WORKERS = int(os.environ.get("RNG_MAX_WORKERS", min(os.cpu_count() or 4, 4)))
# TestU01 and Dieharder need far more data than the analysis window (Dieharder
# reads hundreds of MB per test), so they run on the whole uploaded file: each
# extractor is streamed over it in STREAM_CHUNK_BITS segments into a temp file.
# The segment size is a multiple of every extractor's block size.
DEEP_SUITES = ("testu01", "dieharder")
STREAM_CHUNK_BITS = 2 ** 24
RAW_METHOD = "Raw (Baseline)"

@app.get("/api/methods")
def get_methods():
    return [
        {"id": name, "name": name, "isFast": name not in SLOW_METHODS}
        for name, _ in METHODS
    ]

@app.get("/api/limits")
def get_limits():
    return {
        "maxFileSize": MAX_FILE_SIZE,
        "fastTierThreshold": FAST_TIER_THRESHOLD,
        "message": f"Warning: Executing the 5 O(n²) methods (LHL, Goldreich-Levin, Chor-Goldreich, Trevisan, Quantum-Proof) on files > {FAST_TIER_THRESHOLD} bits will result in extreme analysis times. User assumes full responsibility for long waits."
    }

MIN_BITS_MAP = {
    "dieharder": 16000,
    "testu01": 2 ** 20,
    "nist": 1000000,
    "compression": 512000,
    "performance": 16384
}

def get_skipped_payload(suite: str, min_bits: int):
    reason = f"Insufficient bit length for {suite} (< {min_bits} bits required)"
    if suite == "nist":
        return {"status": "skipped", "reason": reason, "pass": 0, "fail": 0, "invalid": 0, "total": 15, "details": []}
    if suite == "testu01":
        return {"status": "skipped", "reason": reason, "pass": 0, "fail": 0, "error": True}
    if suite == "dieharder":
        return {"status": "skipped", "reason": reason, "pass": 0, "weak": 0, "fail": 0, "error": True}
    if suite == "compression":
        return {"status": "skipped", "reason": reason, "pass_count": 0, "fail_count": 0, "invalid": 0, "details": []}
    if suite == "performance":
        return {"status": "skipped", "reason": reason, "shannon": 0, "min_entropy": 0, "bit_rate": 0, "bias": 0, "time_sec": 0}
    return {}

TEXT_BIT_CHARS = frozenset(b"01 \t\r\n,")

def is_text_bits(head: bytes) -> bool:
    """A file is an ASCII '0'/'1' bit file only if its head contains nothing else.
    (Previously any UTF-8-decodable head was treated as text, which silently
    discarded all non-'0'/'1' bytes of binary files that happen to start with ASCII.)"""
    return len(head) > 0 and set(head) <= TEXT_BIT_CHARS and (48 in head or 49 in head)

def process_file_content(content: bytes, max_bits: int = None) -> np.ndarray:
    arr = np.frombuffer(content, dtype=np.uint8)
    if is_text_bits(content[:4096]):
        bits = (arr[(arr == 48) | (arr == 49)] - 48).astype(np.int8)
    else:
        if max_bits is not None:
            arr = arr[:(max_bits + 7) // 8]
        bits = np.unpackbits(arr).astype(np.int8)
    return bits[:max_bits] if max_bits is not None else bits

def iter_file_bits(path: str, is_text: bool, chunk_bits: int = STREAM_CHUNK_BITS):
    """Yield the file's bits in chunk_bits-long int8 arrays (the last may be shorter)."""
    carry = np.empty(0, dtype=np.int8)
    with open(path, "rb") as f:
        while True:
            raw = f.read(chunk_bits if is_text else chunk_bits // 8)
            if not raw:
                break
            arr = np.frombuffer(raw, dtype=np.uint8)
            bits = (arr[(arr == 48) | (arr == 49)] - 48).astype(np.int8) if is_text else np.unpackbits(arr).astype(np.int8)
            carry = np.concatenate((carry, bits)) if len(carry) else bits
            while len(carry) >= chunk_bits:
                yield carry[:chunk_bits]
                carry = carry[chunk_bits:]
    if len(carry):
        yield carry

def stream_to_packed_file(src_path: str, is_text: bool, func=None):
    """Apply func segment by segment over the whole file (or copy the raw bits when
    func is None) into a packed binary temp file. Returns (path, bits_written)."""
    fd, out_path = tempfile.mkstemp(suffix=".bin")
    pending = np.empty(0, dtype=np.int8)
    written = 0
    with os.fdopen(fd, "wb") as out:
        for chunk in iter_file_bits(src_path, is_text):
            bits = func(chunk) if func else chunk
            bits = np.concatenate((pending, np.asarray(bits, dtype=np.int8))) if len(pending) else np.asarray(bits, dtype=np.int8)
            n = len(bits) // 8 * 8
            out.write(np.packbits(bits[:n]).tobytes())
            pending = bits[n:]
            written += n
    return out_path, written

def run_deep_suites(name: str, src_path: str, is_text: bool, selected_tests: list):
    """TestU01 and Dieharder on the named extractor's output over the whole file."""
    start = time.time()
    if name == RAW_METHOD and not is_text:
        path, owned = src_path, False
    else:
        path, _ = stream_to_packed_file(src_path, is_text, None if name == RAW_METHOD else METHODS_DICT[name])
        owned = True
    try:
        tu01 = run_testu01_suite(path=path) if "testu01" in selected_tests else {"pass": 0, "fail": 0, "error": True}
        dh = run_dieharder_suite(path=path) if "dieharder" in selected_tests else {"pass": 0, "weak": 0, "fail": 0, "error": True}
    finally:
        if owned:
            try:
                os.unlink(path)
            except OSError:
                pass
    return name, tu01, dh, time.time() - start

async def read_upload(file: UploadFile, max_bits: int):
    """Read only as many bytes as the analysis will use. Returns (content, file_size_bytes)."""
    head = await file.read(4096)
    need = max_bits + max_bits // 4 if is_text_bits(head) else (max_bits + 7) // 8
    rest = await file.read(max(0, need - len(head)))
    size = file.size if file.size is not None else len(head) + len(rest)
    return head + rest, size

def analyze_single_method(name, input_bits, selected_tests, total_bits, MAX_STAT_BITS):
    func = METHODS_DICT.get(name)
    if not func:
        return None, None
        
    start = time.time()
    extracted = func(input_bits)
    exec_time = time.time() - start
    
    stat_bits_ext = extracted[:MAX_STAT_BITS] if len(extracted) > MAX_STAT_BITS else extracted
    ext_len = len(extracted)
    
    if "performance" in selected_tests:
        if ext_len < MIN_BITS_MAP["performance"]:
            metrics = get_skipped_payload("performance", MIN_BITS_MAP["performance"])
            metrics["time_sec"] = exec_time
        else:
            metrics = calculate_metrics(extracted, total_bits, exec_time)
    else:
        metrics = {"shannon": 0, "min_entropy": 0, "bit_rate": 0, "bias": 0, "time_sec": exec_time}

    if "nist" in selected_tests:
        nist = get_skipped_payload("nist", MIN_BITS_MAP["nist"]) if ext_len < MIN_BITS_MAP["nist"] else run_nist_suite(stat_bits_ext)
    else:
        nist = {"pass": 0, "fail": 0, "invalid": 0, "total": 15, "details": []}
        
    if "compression" in selected_tests:
        comp = get_skipped_payload("compression", MIN_BITS_MAP["compression"]) if ext_len < MIN_BITS_MAP["compression"] else run_compression_test(stat_bits_ext)
    else:
        comp = {"pass_count": 0, "fail_count": 0, "invalid": 0, "details": []}
        
    # TestU01 / Dieharder results are filled in by run_deep_suites.
    tu01 = {"pass": 0, "fail": 0, "error": True}
    dh = {"pass": 0, "weak": 0, "fail": 0, "error": True}

    chart_item= {
        "method": name,
        "shannonEntropy": metrics["shannon"],
        "minEntropy": metrics["min_entropy"],
        "bitRate": metrics["bit_rate"],
        "bias": metrics["bias"],
        "executionTime": metrics["time_sec"] * 1000,
        "passCount": nist["pass"],
        "failCount": nist["fail"],
        "invalidCount": nist["invalid"],
        "totalCount": nist.get("total", 16),
        "details": nist.get("details", []),
        "compression": comp,
        "testu01": tu01,
        "dieharder": dh
    }
    
    return name, chart_item

def run_analysis_job(job_id: str, upload_path: str, selected_method_names: list, selected_tests: list):
    try:
        jobs[job_id]["logs"].append("Processing file content...")
        file_size = os.path.getsize(upload_path)
        with open(upload_path, "rb") as f:
            head = f.read(4096)
            is_text = is_text_bits(head)
            need = MAX_ANALYSIS_BITS + MAX_ANALYSIS_BITS // 4 if is_text else (MAX_ANALYSIS_BITS + 7) // 8
            content = head + f.read(max(0, need - len(head)))
        input_bits = process_file_content(content, MAX_ANALYSIS_BITS)
        del content
        total_bits = len(input_bits)
        if file_size and total_bits >= MAX_ANALYSIS_BITS:
            jobs[job_id]["logs"].append(
                f"File is {file_size:,} bytes; analyzing the first {total_bits:,} bits "
                f"(limit RNG_MAX_ANALYSIS_BITS={MAX_ANALYSIS_BITS:,})."
            )
        
        jobs[job_id]["logs"].append(f"Running baseline Raw tests on {total_bits} bits...")
        raw_start = time.time()
        raw_elapsed = max(0.001, time.time() - raw_start)
        
        # NIST SP 800-22 recommends ~1M bit sequences for statistical tests.
        # Running 42M bits through O(n^2) tests like Serial/ApproximateEntropy takes hours.
        # We sample 1M bits for stat tests but use ALL bits for entropy/throughput metrics.
        MAX_STAT_BITS = 1_000_000
        stat_bits_raw = input_bits[:MAX_STAT_BITS] if total_bits > MAX_STAT_BITS else input_bits
        if total_bits > MAX_STAT_BITS:
            jobs[job_id]["logs"].append(f"Statistical tests will use {MAX_STAT_BITS:,} bit sample (NIST recommended). Metrics use all {total_bits:,} bits.")
        
        if "performance" in selected_tests:
            if total_bits < MIN_BITS_MAP["performance"]:
                raw_metrics = get_skipped_payload("performance", MIN_BITS_MAP["performance"])
                raw_metrics["time_sec"] = raw_elapsed
            else:
                raw_metrics = calculate_metrics(input_bits, total_bits, raw_elapsed)
        else:
            raw_metrics = {"shannon": 0, "min_entropy": 0, "bit_rate": 0, "bias": 0, "time_sec": raw_elapsed}

        if "nist" in selected_tests:
            raw_nist = get_skipped_payload("nist", MIN_BITS_MAP["nist"]) if total_bits < MIN_BITS_MAP["nist"] else run_nist_suite(stat_bits_raw)
        else:
            raw_nist = {"pass": 0, "fail": 0, "invalid": 0, "total": 15, "details": []}
            
        if "compression" in selected_tests:
            raw_comp = get_skipped_payload("compression", MIN_BITS_MAP["compression"]) if total_bits < MIN_BITS_MAP["compression"] else run_compression_test(stat_bits_raw)
        else:
            raw_comp = {"pass_count": 0, "fail_count": 0, "invalid": 0, "details": []}
            
        raw_tu01 = {"pass": 0, "fail": 0, "error": True}
        raw_dh = {"pass": 0, "weak": 0, "fail": 0, "error": True}

        chart_data = [{
            "method": RAW_METHOD,
            "shannonEntropy": raw_metrics["shannon"],
            "minEntropy": raw_metrics["min_entropy"],
            "bitRate": raw_metrics["bit_rate"],
            "bias": raw_metrics["bias"],
            "executionTime": raw_metrics["time_sec"] * 1000,
            "passCount": raw_nist["pass"],
            "failCount": raw_nist["fail"],
            "invalidCount": raw_nist["invalid"],
            "totalCount": raw_nist.get("total", 16),
            "details": raw_nist.get("details", []),
            "compression": raw_comp,
            "testu01": raw_tu01,
            "dieharder": raw_dh
        }]
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        deep = [t for t in selected_tests if t in DEEP_SUITES]
        if deep:
            jobs[job_id]["logs"].append(
                f"Running {' + '.join(d.capitalize() if d == 'dieharder' else 'TestU01' for d in deep)} on the whole "
                f"{file_size:,}-byte file for the baseline and every extractor. This takes several minutes per method."
            )
        deep_results = {}
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(analyze_single_method, name, input_bits, selected_tests, total_bits, MAX_STAT_BITS): ("fast", name)
                for name in selected_method_names
            }
            if deep:
                for name in [RAW_METHOD] + [n for n in selected_method_names if n in METHODS_DICT]:
                    futures[pool.submit(run_deep_suites, name, upload_path, is_text, deep)] = ("deep", name)
            for future in as_completed(futures):
                kind, name = futures[future]
                try:
                    if kind == "fast":
                        res_name, chart_item = future.result()
                        if chart_item:
                            chart_data.append(chart_item)
                            jobs[job_id]["logs"].append(f"Completed tests for {name}.")
                    else:
                        _, tu01, dh, secs = future.result()
                        deep_results[name] = (tu01, dh)
                        summary = []
                        if "testu01" in deep:
                            summary.append(f"TestU01 {tu01['pass']}/{tu01['total']}" if tu01.get("total") else f"TestU01: {tu01.get('error')}")
                        if "dieharder" in deep:
                            summary.append(f"Dieharder {dh['pass']}/{dh['total']}" if dh.get("total") else f"Dieharder: {dh.get('error')}")
                        jobs[job_id]["logs"].append(f"Deep tests for {name} ({secs:.0f}s): {'; '.join(summary)}")
                except Exception as e:
                    jobs[job_id]["logs"].append(f"Error in {name}: {e}")
        for d in chart_data:
            if d["method"] in deep_results:
                d["testu01"], d["dieharder"] = deep_results[d["method"]]


        jobs[job_id]["logs"].append("Ranking methods and finalizing results...")
        ranked_methods = []
        for d in chart_data:
            if d["method"] != "Raw (Baseline)":
                # Tests NIST marks not applicable (e.g. Random Excursions with J < 500
                # cycles) are neither passes nor failures, so they don't count against a method.
                nist_decided = d["passCount"] + d["failCount"]
                nist_rate = d["passCount"] / nist_decided if nist_decided else None
                ent_rate = min(1.0, d["minEntropy"])
                bias_rate = max(0, (0.5 - d["bias"]) / 0.5)

                comp = d.get("compression", {})
                comp_rate = comp["pass_count"] / 4.0 if "algorithms" in comp and not comp.get("invalid") else None

                tu01 = d.get("testu01", {})
                tu01_rate = tu01.get("pass_rate")

                dh = d.get("dieharder", {})
                dh_rate = dh.get("pass_rate")

                # Suites that were not selected, skipped, or unavailable (e.g. TestU01/Dieharder
                # on Windows) are left out and the remaining weights rescaled to 100, instead of
                # scoring 0 for every method and flattening the ranking into ties.
                components = [(35, nist_rate), (20, ent_rate), (10, bias_rate),
                              (10, comp_rate), (15, tu01_rate), (10, dh_rate)]
                used = [(w, r) for w, r in components if r is not None]
                score = 100 * sum(w * r for w, r in used) / sum(w for w, _ in used)
                
                ranked_methods.append({
                    "method": d["method"],
                    "score": round(score, 2),
                    "nistPass": d["passCount"],
                    "shannon": d["shannonEntropy"],
                    "minEntropy": d["minEntropy"],
                    "bias": d["bias"],
                    "bitRate": d["bitRate"],
                    "compressionPass": comp.get("pass_count", 0) if not comp.get("invalid") else 0,
                    "testu01Pass": tu01.get("pass", 0) if not tu01.get("error") else 0,
                    "testu01Total": tu01.get("total", 0) if not tu01.get("error") else 0,
                    "dieharderPass": dh.get("pass", 0) if not (dh.get("error") or dh.get("insufficient")) else 0,
                    "dieharderTotal": dh.get("total", 0) if not (dh.get("error") or dh.get("insufficient")) else 0
                })
                
        ranked_methods.sort(key=lambda x: x["score"], reverse=True)
        
        best_method = ""
        best_explanation = ""
        if len(ranked_methods) > 1:
            best_method = ranked_methods[0]["method"]
            best_explanation = f"{best_method} achieved the highest combined score, passing {ranked_methods[0]['nistPass']} NIST statistical tests while maintaining an entropy level of {ranked_methods[0]['minEntropy']:.4f} per bit."
            
        def sanitize_nan(obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            elif isinstance(obj, dict):
                return {k: sanitize_nan(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_nan(item) for item in obj]
            return obj

        response_data = {
            "id": job_id,
            "bestMethod": best_method,
            "bestMethodExplanation": best_explanation,
            "totalBits": total_bits,
            "fileSizeBytes": file_size,
            "chartData": chart_data,
            "rankedMethods": ranked_methods
        }
        
        jobs[job_id]["result"] = sanitize_nan(response_data)
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["logs"].append("Analysis complete.")
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["logs"].append(f"Fatal error: {e}")
    finally:
        try:
            os.unlink(upload_path)
        except OSError:
            pass

@app.post("/api/analyze/start")
async def start_analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    methods: str = Form(...),
    tests: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    selected_tests = json.loads(tests)
    # Stream the upload to disk: the deep suites read the whole file, which may
    # be far larger than memory.
    fd, upload_path = tempfile.mkstemp(suffix=".upload")
    with os.fdopen(fd, "wb") as out:
        await run_in_threadpool(shutil.copyfileobj, file.file, out, 1 << 20)
    
    job_id = f"analysis-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "processing",
        "logs": ["Job queued..."],
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_analysis_job, job_id, upload_path, selected_method_names, selected_tests)
    return {"job_id": job_id}

@app.get("/api/analyze/status/{job_id}")
def get_analyze_status(job_id: str):
    if job_id not in jobs:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return jobs[job_id]

import tempfile
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

@app.post("/api/download/bits")
async def download_bits(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    methods: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    content, _ = await read_upload(file, MAX_ANALYSIS_BITS)
    input_bits = process_file_content(content, MAX_ANALYSIS_BITS)
    
    fd, temp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    
    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("Raw_Baseline.txt", "".join(map(str, input_bits.tolist())))
        for name in selected_method_names:
            func = METHODS_DICT.get(name)
            if func:
                try:
                    extracted = func(input_bits)
                    clean_name = "".join(c if c.isalnum() else "_" for c in name)
                    zip_file.writestr(f"{clean_name}.txt", "".join(map(str, extracted.tolist())))
                    del extracted
                    gc.collect()
                except Exception:
                    pass
    
    del input_bits
    gc.collect()
    
    def cleanup():
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    background_tasks.add_task(cleanup)
    
    return FileResponse(
        path=temp_path,
        media_type="application/zip",
        filename="extracted_bits.zip"
    )

from pdf_report import generate_pdf_report

class PDFRequest(BaseModel):
    chartData: List[Dict[str, Any]]
    rankedMethods: List[Dict[str, Any]]
    totalBits: int
    selectedTests: List[str] = []

@app.post("/api/download/pdf")
async def download_pdf(request: PDFRequest):
    def replace_none(obj):
        if isinstance(obj, dict):
            return {k: replace_none(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_none(v) for v in obj]
        elif obj is None:
            return 0
        return obj
    print("DEBUG DOWNLOAD PDF SELECTED TESTS:", request.selectedTests)

    safe_chart = replace_none(request.chartData)
    safe_ranked = replace_none(request.rankedMethods)

    data_points = []
    for d in safe_chart:
        data_points.append({
            "method": d["method"],
            "shannon": d.get("shannonEntropy", 0),
            "minEntropy": d.get("minEntropy", 0),
            "bitRate": d.get("bitRate", 0),
            "bias": d.get("bias", 0),
            "executionTime": d.get("executionTime", 0),
            "pass": d.get("passCount", 0),
            "fail": d.get("failCount", 0),
            "invalid": d.get("invalidCount", 0),
            "total": d.get("totalCount", 16),
            "compression": d.get("compression", {}),
            "testu01": d.get("testu01", {}),
            "dieharder": d.get("dieharder", {})
        })
    
    pdf_buffer = generate_pdf_report(data_points, request.totalBits, safe_ranked, request.selectedTests)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=RNG_Report.pdf"}
    )

