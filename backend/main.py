from fastapi import FastAPI, UploadFile, File, Form, Body
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
    raw_comp = run_compression_test(input_bits)
    raw_tu01 = run_testu01_suite(input_bits)
    raw_dh = run_dieharder_suite(input_bits)
    
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
    
    for name in selected_method_names:
        func = METHODS_DICT.get(name)
        if func:
            try:
                start = time.time()
                extracted = func(input_bits)
                exec_time = time.time() - start
                
                metrics = calculate_metrics(extracted, total_bits, exec_time)
                nist = run_nist_suite(extracted)
                comp = run_compression_test(extracted)
                tu01 = run_testu01_suite(extracted)
                dh = run_dieharder_suite(extracted)
                
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
                    "totalCount": nist.get("total", 16),
                    "details": nist.get("details", []),
                    "compression": comp,
                    "testu01": tu01,
                    "dieharder": dh
                })
            except Exception as e:
                print(f"Error in {name}: {e}")
                
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
        "id": "analysis-" + str(int(time.time())),
        "bestMethod": best_method,
        "bestMethodExplanation": best_explanation,
        "totalBits": total_bits,
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

class PDFRequest(BaseModel):
    chartData: List[Dict[str, Any]]
    rankedMethods: List[Dict[str, Any]]
    totalBits: int

@app.post("/api/download/pdf")
async def download_pdf(request: PDFRequest):
    data_points = []
    for d in request.chartData:
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
    
    pdf_buffer = generate_pdf_report(data_points, request.totalBits, request.rankedMethods)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=RNG_Report.pdf"}
    )

