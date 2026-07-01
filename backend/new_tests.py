import zlib
import bz2
import lzma
import gzip
import tempfile
import subprocess
import os
import numpy as np

def run_compression_test(bits):
    """
    Runs compression using zlib, lzma, bz2, and gzip.
    Computes compression ratio = compressed_size / original_size.
    Pass threshold is >= 0.999.
    """
    bits_array = np.asarray(bits, dtype=np.int8)
    byte_data = np.packbits(bits_array).tobytes()
    original_size = len(byte_data)

    if original_size < 1000:
        return {
            "algorithms": [],
            "overall_status": "INVALID",
            "message": "Insufficient data to accurately measure compression. Compression overhead dominates at this size.",
            "pass_count": 0,
            "invalid": True
        }

    results = []
    
    # 1. zlib (Deflate)
    compressed_zlib = zlib.compress(byte_data)
    results.append({
        "name": "Deflate",
        "original_bytes": original_size,
        "compressed_bytes": len(compressed_zlib),
        "ratio": round(len(compressed_zlib) / original_size, 4),
        "status": "PASS" if (len(compressed_zlib) / original_size) >= 0.999 else "FAIL"
    })
    
    # 2. lzma
    compressed_lzma = lzma.compress(byte_data)
    results.append({
        "name": "LZMA",
        "original_bytes": original_size,
        "compressed_bytes": len(compressed_lzma),
        "ratio": round(len(compressed_lzma) / original_size, 4),
        "status": "PASS" if (len(compressed_lzma) / original_size) >= 0.999 else "FAIL"
    })
    
    # 3. bz2
    compressed_bz2 = bz2.compress(byte_data)
    results.append({
        "name": "Bzip2",
        "original_bytes": original_size,
        "compressed_bytes": len(compressed_bz2),
        "ratio": round(len(compressed_bz2) / original_size, 4),
        "status": "PASS" if (len(compressed_bz2) / original_size) >= 0.999 else "FAIL"
    })
    
    # 4. gzip
    compressed_gzip = gzip.compress(byte_data)
    results.append({
        "name": "Gzip",
        "original_bytes": original_size,
        "compressed_bytes": len(compressed_gzip),
        "ratio": round(len(compressed_gzip) / original_size, 4),
        "status": "PASS" if (len(compressed_gzip) / original_size) >= 0.999 else "FAIL"
    })

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    overall_status = "PASS" if pass_count == 4 else "FAIL"

    return {
        "algorithms": results,
        "overall_status": overall_status,
        "pass_count": pass_count
    }

def run_testu01_suite(bits):
    """
    Runs TestU01 SmallCrush using the pytestu01 library.
    """
    try:
        import pytestu01
    except ImportError:
        return {
            "error": "pytestu01 library is not installed or failed to import."
        }
    
    bits_array = np.asarray(bits, dtype=np.int8)
    
    # Pack to 32-bit uints for TestU01
    padding = (32 - len(bits_array) % 32) % 32
    if padding > 0:
        bits_array = np.concatenate((bits_array, np.zeros(padding, dtype=np.int8)))
    
    uint32_array = np.packbits(bits_array.reshape(-1, 8)).view(np.uint32)

    try:
        res = pytestu01.run_smallcrush(uint32_array.tolist())
        
        tests = []
        pass_count = 0
        total_count = 0
        
        for name, p_val in res.items():
            val = p_val if isinstance(p_val, (int, float)) else p_val[0]
            status = "PASS" if 0.001 < val < 0.999 else "FAIL"
            if status == "PASS":
                pass_count += 1
            total_count += 1
            
            tests.append({
                "name": name,
                "p_value": round(val, 5),
                "status": status
            })
            
        pass_rate = pass_count / total_count if total_count > 0 else 0.0
        
        return {
            "battery": "SmallCrush",
            "tests": tests,
            "pass": pass_count,
            "fail": total_count - pass_count,
            "total": total_count,
            "pass_rate": round(pass_rate, 3)
        }

    except Exception as e:
        return {
            "error": f"Failed to execute TestU01: {str(e)}"
        }

def run_dieharder_suite(bits):
    """
    Runs the Dieharder test suite via subprocess.
    """
    bits_array = np.asarray(bits, dtype=np.int8)
    
    MIN_BITS = 1_000_000
    if len(bits_array) < MIN_BITS:
        return {
            "error": f"Insufficient data. Dieharder requires a substantial dataset (at least {MIN_BITS} bits) to produce meaningful results.",
            "insufficient": True
        }
        
    byte_data = np.packbits(bits_array).tobytes()
    
    fd, temp_path = tempfile.mkstemp(suffix=".bin")
    with os.fdopen(fd, 'wb') as f:
        f.write(byte_data)
        
    try:
        result = subprocess.run(
            ['dieharder', '-a', '-g', '201', '-f', temp_path],
            capture_output=True,
            text=True,
            timeout=180
        )
        
        output = result.stdout
        
        tests = []
        pass_count = 0
        fail_count = 0
        weak_count = 0
        
        for line in output.split('\n'):
            if '|' in line and not line.startswith('#'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    name = parts[0]
                    p_val_str = parts[4]
                    res_str = parts[5]
                    
                    try:
                        p_val = float(p_val_str)
                    except ValueError:
                        continue
                        
                    tests.append({
                        "name": name,
                        "p_value": round(p_val, 5),
                        "result": res_str
                    })
                    
                    if res_str == "PASSED":
                        pass_count += 1
                    elif res_str == "FAILED":
                        fail_count += 1
                    elif res_str == "WEAK":
                        weak_count += 1
                        
        total_count = pass_count + fail_count + weak_count
        pass_rate = pass_count / total_count if total_count > 0 else 0.0
        
        if total_count == 0:
            if "command not found" in result.stderr or not result.stdout.strip():
                return {
                    "error": "Dieharder not available in this environment. It is fully supported in the deployed Linux environment."
                }
            return {
                "error": "Dieharder executed but returned no recognizable results."
            }
            
        return {
            "tests": tests,
            "pass": pass_count,
            "fail": fail_count,
            "weak": weak_count,
            "total": total_count,
            "pass_rate": round(pass_rate, 3)
        }
        
    except FileNotFoundError:
        return {
            "error": "Dieharder not available in this environment. It is fully supported in the deployed Linux environment."
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "Dieharder execution timed out after 3 minutes."
        }
    except Exception as e:
        return {
            "error": f"Failed to execute Dieharder: {str(e)}"
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
