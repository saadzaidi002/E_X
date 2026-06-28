import sys
from pdf_report import generate_pdf_report

data_points = [{
    "method": "Raw (Baseline)",
    "shannon": 0.99,
    "minEntropy": 0.8,
    "bitRate": 1000000,
    "bias": 0.001,
    "pass": 15,
    "fail": 1,
    "invalid": 0,
    "total": 16,
    "executionTime": 0
}, {
    "method": "Test Method",
    "shannon": 0.999,
    "minEntropy": 0.99,
    "bitRate": 500000,
    "bias": 0.0001,
    "pass": 16,
    "fail": 0,
    "invalid": 0,
    "total": 16,
    "executionTime": 15
}]

ranked_methods = [{
    "method": "Test Method",
    "score": 100.5,
    "nistPass": 16,
    "shannon": 0.999,
    "minEntropy": 0.99,
    "bias": 0.0001,
    "bitRate": 500000
}]

total_bits = 100000

try:
    buf = generate_pdf_report(data_points, total_bits, ranked_methods)
    with open("test.pdf", "wb") as f:
        f.write(buf.read())
    print("PDF generated successfully")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
