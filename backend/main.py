from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import math
import numpy as np
import io
import zipfile
import json
import sys
import os

from core_logic import calculate_metrics, run_nist_suite, Extractors

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

METHODS = Extractors.get_all_extractors()
METHODS_DICT = {name: func for name, func in METHODS}

SLOW_METHODS = [
    "2. Leftover Hash Lemma (LHL)",
    "10. Goldreich–Levin Extractor",
    "11. Chor–Goldreich 2-Source",
    "15. Trevisan Extractor",
    "17. Quantum-Proof Strong Extractor"
]
MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
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

def process_file_content(content: bytes) -> np.ndarray:
    try:
        text = content.decode('utf-8')
        return np.array([int(c) for c in text if c in '01'], dtype=np.int8)
    except Exception:
        return np.unpackbits(np.frombuffer(content, dtype=np.uint8)).astype(np.int8)

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    methods: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    content = await file.read()
    input_bits = process_file_content(content)
    
    total_bits = len(input_bits)
    
    raw_start = time.time()
    raw_elapsed = max(0.001, time.time() - raw_start)
    raw_metrics = calculate_metrics(input_bits, total_bits, raw_elapsed)
    raw_nist = run_nist_suite(input_bits)
    
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
        "details": raw_nist.get("details", [])
    }]
    
    for name in selected_method_names:
        func = METHODS_DICT.get(name)
        if func:
            try:
                start = time.time()
                extracted = func(input_bits)
                exec_time = time.time() - start
                
                metrics = calculate_metrics(extracted, total_bits, exec_time)
                nist = run_nist_suite(extracted)
                
                chart_data.append({
                    "method": name,
                    "shannonEntropy": metrics["shannon"],
                    "minEntropy": metrics["min_entropy"],
                    "bitRate": metrics["bit_rate"],
                    "bias": metrics["bias"],
                    "executionTime": metrics["time_sec"] * 1000,
                    "passCount": nist["pass"],
                    "failCount": nist["fail"],
                    "invalidCount": nist["invalid"],
                    "details": nist.get("details", [])
                })
            except Exception as e:
                print(f"Error in {name}: {e}")
                
    ranked_methods = []
    for d in chart_data:
        if d["method"] != "Raw (Baseline)":
            score = (d["passCount"] * 5) + (d["minEntropy"] * 20) - (d["bias"] * 10)
            ranked_methods.append({
                "method": d["method"],
                "score": round(score, 2),
                "nistPass": d["passCount"],
                "shannon": d["shannonEntropy"],
                "minEntropy": d["minEntropy"],
                "bias": d["bias"],
                "bitRate": d["bitRate"]
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
        "id": "analysis-" + str(int(time.time())),
        "bestMethod": best_method,
        "bestMethodExplanation": best_explanation,
        "chartData": chart_data,
        "rankedMethods": ranked_methods
    }
    
    return sanitize_nan(response_data)

@app.post("/api/download/bits")
async def download_bits(
    file: UploadFile = File(...),
    methods: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    content = await file.read()
    input_bits = process_file_content(content)
    total_bits = len(input_bits)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("Raw_Baseline.txt", "".join(map(str, input_bits.tolist())))
        for name in selected_method_names:
            if name in SLOW_METHODS and total_bits > FAST_TIER_THRESHOLD:
                continue
            func = METHODS_DICT.get(name)
            if func:
                try:
                    extracted = func(input_bits)
                    clean_name = "".join(c if c.isalnum() else "_" for c in name)
                    zip_file.writestr(f"{clean_name}.txt", "".join(map(str, extracted.tolist())))
                except Exception:
                    pass
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=extracted_bits.zip"}
    )

from pdf_report import generate_pdf_report

@app.post("/api/download/pdf")
async def download_pdf(
    file: UploadFile = File(...),
    methods: str = Form(...) 
):
    selected_method_names = json.loads(methods)
    content = await file.read()
    input_bits = process_file_content(content)
    total_bits = len(input_bits)
    
    # Quick analysis run
    raw_start = time.time()
    raw_elapsed = max(0.001, time.time() - raw_start)
    raw_metrics = calculate_metrics(input_bits, total_bits, raw_elapsed)
    raw_nist = run_nist_suite(input_bits)
    
    data_points = [{
        "method": "Raw (Baseline)",
        "shannon": raw_metrics["shannon"],
        "minEntropy": raw_metrics["min_entropy"],
        "bitRate": raw_metrics["bit_rate"],
        "bias": raw_metrics["bias"],
        "executionTime": raw_metrics["time_sec"] * 1000,
        "pass": raw_nist["pass"],
        "fail": raw_nist["fail"],
        "invalid": raw_nist["invalid"],
        "total": raw_nist["total"]
    }]
    
    for name in selected_method_names:
        if name in SLOW_METHODS and total_bits > FAST_TIER_THRESHOLD: continue
        func = METHODS_DICT.get(name)
        if func:
            try:
                start = time.time()
                extracted = func(input_bits)
                exec_time = time.time() - start
                m = calculate_metrics(extracted, total_bits, exec_time)
                n = run_nist_suite(extracted)
                data_points.append({
                    "method": name, "shannon": m["shannon"], "minEntropy": m["min_entropy"],
                    "bitRate": m["bit_rate"], "bias": m["bias"], "executionTime": m["time_sec"] * 1000,
                    "pass": n["pass"], "fail": n["fail"], "invalid": n["invalid"], "total": n["total"]
                })
            except: pass

    ranked_methods = []
    for d in data_points:
        if d["method"] != "Raw (Baseline)":
            score = (d["pass"] * 5) + (d["minEntropy"] * 20) - (d["bias"] * 10)
            ranked_methods.append({
                "method": d["method"],
                "score": round(score, 2),
                "nistPass": d["pass"],
                "shannon": d["shannon"],
                "minEntropy": d["minEntropy"],
                "bias": d["bias"],
                "bitRate": d["bitRate"]
            })
            
    ranked_methods.sort(key=lambda x: x["score"], reverse=True)
            
    pdf_buffer = generate_pdf_report(data_points, total_bits, ranked_methods)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=RNG_Report.pdf"}
    )

