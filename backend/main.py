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
    "dieharder": 104857600,
    "testu01": 16000000,
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

def process_file_content(content: bytes) -> np.ndarray:
    try:
        content[:1000].decode('utf-8')
        arr = np.frombuffer(content, dtype=np.uint8)
        mask = (arr == 48) | (arr == 49)
        valid = arr[mask]
        if len(valid) == 0:
            raise ValueError("No valid text bits found, fallback to binary")
        return (valid - 48).astype(np.int8)
    except Exception:
        return np.unpackbits(np.frombuffer(content, dtype=np.uint8)).astype(np.int8)

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
        
    if "testu01" in selected_tests:
        tu01 = get_skipped_payload("testu01", MIN_BITS_MAP["testu01"]) if ext_len < MIN_BITS_MAP["testu01"] else run_testu01_suite(extracted)
    else:
        tu01 = {"pass": 0, "fail": 0, "error": True}
        
    if "dieharder" in selected_tests:
        dh = get_skipped_payload("dieharder", MIN_BITS_MAP["dieharder"]) if ext_len < MIN_BITS_MAP["dieharder"] else run_dieharder_suite(extracted)
    else:
        dh = {"pass": 0, "weak": 0, "fail": 0, "error": True}
    
    chart_item = {
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

def run_analysis_job(job_id: str, content: bytes, selected_method_names: list, selected_tests: list):
    try:
        jobs[job_id]["logs"].append("Processing file content...")
        input_bits = process_file_content(content)
        total_bits = len(input_bits)
        
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
            
        if "testu01" in selected_tests:
            raw_tu01 = get_skipped_payload("testu01", MIN_BITS_MAP["testu01"]) if total_bits < MIN_BITS_MAP["testu01"] else run_testu01_suite(input_bits)
        else:
            raw_tu01 = {"pass": 0, "fail": 0, "error": True}
            
        if "dieharder" in selected_tests:
            raw_dh = get_skipped_payload("dieharder", MIN_BITS_MAP["dieharder"]) if total_bits < MIN_BITS_MAP["dieharder"] else run_dieharder_suite(input_bits)
        else:
            raw_dh = {"pass": 0, "weak": 0, "fail": 0, "error": True}
        
        chart_data = [{
            "method": "Raw (Baseline)",
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
        
        with ProcessPoolExecutor(max_workers=min(os.cpu_count() or 4, 8)) as pool:
            futures = {
                pool.submit(analyze_single_method, name, input_bits, selected_tests, total_bits, MAX_STAT_BITS): name
                for name in selected_method_names
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    res_name, chart_item = future.result()
                    if chart_item:
                        chart_data.append(chart_item)
                        jobs[job_id]["logs"].append(f"Completed tests for {name}.")
                except Exception as e:
                    jobs[job_id]["logs"].append(f"Error in {name}: {e}")
        

        jobs[job_id]["logs"].append("Ranking methods and finalizing results...")
        ranked_methods = []
        for d in chart_data:
            if d["method"] != "Raw (Baseline)":
                nist_rate = d["passCount"] / max(1, d.get("totalCount", 16))
                nist_score = nist_rate * 35
                ent_score = min(1.0, d["minEntropy"]) * 20
                bias_score = max(0, (0.5 - d["bias"]) / 0.5) * 10
                
                comp = d.get("compression", {})
                comp_rate = comp.get("pass_count", 0) / 4.0
                comp_score = comp_rate * 10
                
                tu01 = d.get("testu01", {})
                tu01_rate = tu01.get("pass_rate", 0.0)
                tu01_score = tu01_rate * 15
                
                dh = d.get("dieharder", {})
                dh_rate = dh.get("pass_rate", 0.0)
                dh_score = dh_rate * 10
                
                score = nist_score + ent_score + bias_score + comp_score + tu01_score + dh_score
                
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
                    "dieharderPass": dh.get("pass", 0) if not (dh.get("error") or dh.get("insufficient")) else 0
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

@app.post("/api/analyze/start")
async def start_analyze(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    methods: str = Form(...),
    tests: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    selected_tests = json.loads(tests)
    content = await file.read()
    
    job_id = f"analysis-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    jobs[job_id] = {
        "status": "processing",
        "logs": ["Job queued..."],
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_analysis_job, job_id, content, selected_method_names, selected_tests)
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
    content = await file.read()
    input_bits = process_file_content(content)
    
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

