import zlib
import bz2
import lzma
import gzip
import tempfile
import subprocess
import os
import re
import shlex
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

# ---------------------------------------------------------------------------
# TestU01 and Dieharder run as the official Linux builds: natively on Linux
# (Docker / Hugging Face) and through WSL on Windows. Neither tool is allowed
# to rewind its input file: a result computed on reused data is reported as
# insufficient instead of being counted.
# ---------------------------------------------------------------------------

WSL_DISTRO = os.environ.get("RNG_WSL_DISTRO", "Ubuntu")
TU01_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testu01", "tu01_file")

# Rabbit/Alphabit are TestU01's batteries for finite bit files. Rabbit's run
# time grows with the length (~20 s at 2^25 bits), so longer inputs are truncated.
TU01_MIN_BITS = 2 ** 20
TU01_MAX_BITS = 2 ** 25
# SmallCrush reads 227,097,303 32-bit words (measured); smaller files would be rewound.
SMALLCRUSH_MIN_BYTES = 227_097_303 * 4

# Dieharder tests rated "Good" by `dieharder -l` (5, 6, 7 are "Suspect", 14 is
# "Do Not Use"; 200 prints nothing without -n; 201 run on its own fails even
# Dieharder's built-in AES_OFB and mt19937 generators), run at standard settings.
# Values: a lower bound on the bytes each test reads, measured from how often it
# rewound an 8 MiB file (rewinds x 8 MiB). Inputs below the bound are skipped
# without running; anything else still has to finish without rewinding.
_MIB8 = 8 * 1024 * 1024
DIEHARDER_TESTS = {
    0: 6 * _MIB8, 1: 52 * _MIB8, 2: 65 * _MIB8, 3: 33 * _MIB8, 4: 17 * _MIB8,
    8: 7 * _MIB8, 9: 65 * _MIB8, 10: 5 * _MIB8, 11: 5 * _MIB8, 12: 5 * _MIB8,
    13: 114 * _MIB8, 15: 9 * _MIB8, 16: 68 * _MIB8, 17: 958 * _MIB8,
    100: 9 * _MIB8, 101: 9 * _MIB8, 102: 9 * _MIB8, 202: 28 * _MIB8, 203: 52 * _MIB8,
    204: 9 * _MIB8, 205: 78 * _MIB8, 206: 10 * _MIB8, 207: 58 * _MIB8, 208: 18 * _MIB8,
    209: 35 * _MIB8,
}


def _to_linux_path(path):
    if os.name != "nt":
        return path
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    return f"/mnt/{drive[0].lower()}{rest.replace(os.sep, '/')}"


def _run_linux(script, timeout):
    """Run a bash script on Linux, or inside WSL on Windows. Returns stdout text."""
    cmd = ["bash", "-s"] if os.name != "nt" else ["wsl.exe", "-d", WSL_DISTRO, "--", "bash", "-s"]
    # Bytes, not text: text-mode stdin on Windows would turn \n into \r\n and break bash.
    res = subprocess.run(cmd, input=script.encode(), capture_output=True, timeout=timeout)
    out = res.stdout.decode("utf-8", errors="replace")
    if res.returncode == 3:
        raise RuntimeError(out.strip().splitlines()[-1] if out.strip() else "tool missing")
    return out


def _write_bits_file(bits):
    fd, path = tempfile.mkstemp(suffix=".bin")
    with os.fdopen(fd, "wb") as f:
        f.write(np.packbits(np.asarray(bits, dtype=np.int8)).tobytes())
    return path


def _bits_or_path(bits, path):
    """Returns (path, size_bytes, owned). Suites accept an in-memory bit array or
    a packed binary file; files let them test far more data than fits in RAM."""
    if path is not None:
        return path, os.path.getsize(path), False
    path = _write_bits_file(bits)
    return path, os.path.getsize(path), True


def _sections(output):
    """Split output on '=== <label>' marker lines."""
    sections, label = {}, None
    for line in output.splitlines():
        if line.startswith("=== "):
            label = line[4:].strip()
            sections[label] = []
        elif label is not None:
            sections[label].append(line)
    return sections


def _tu01_status(p):
    # TestU01 flags p outside [0.001, 0.999]; beyond 1e-10 it is a clear failure.
    if p < 1e-10 or p > 1 - 1e-10:
        return "FAIL"
    if p < 0.001 or p > 0.999:
        return "WEAK"
    return "PASS"


def run_testu01_suite(bits=None, path=None):
    """Runs TestU01 Alphabit and Rabbit (and SmallCrush when the input is large
    enough to avoid rewinding) using the official TestU01 1.2.3 library."""
    if path is None and len(bits) < TU01_MIN_BITS:
        return {"error": f"Insufficient data: TestU01 Rabbit/Alphabit need at least {TU01_MIN_BITS:,} bits.",
                "insufficient": True}
    if path is None:
        # Only the tested prefix needs to be written out unless SmallCrush will run.
        if len(bits) // 8 < SMALLCRUSH_MIN_BYTES:
            bits = bits[:TU01_MAX_BITS]
    path, size, owned = _bits_or_path(bits, path)
    nbits = min(size * 8, TU01_MAX_BITS) // 32 * 32
    run_smallcrush = size >= SMALLCRUSH_MIN_BYTES
    try:
        if nbits < TU01_MIN_BITS:
            return {"error": f"Insufficient data: TestU01 Rabbit/Alphabit need at least {TU01_MIN_BITS:,} bits.",
                    "insufficient": True}
        src = shlex.quote(_to_linux_path(path))
        exe = shlex.quote(_to_linux_path(TU01_BIN))
        script = (
            f"test -x {exe} || {{ echo 'TestU01 harness not built: run backend/testu01/build.sh'; exit 3; }}\n"
            f"f=$(mktemp); cp {src} \"$f\"\n"
            f"echo '=== Alphabit'; {exe} alphabit \"$f\" {nbits}\n"
            f"echo '=== Rabbit'; {exe} rabbit \"$f\" {nbits}\n"
            + (f"echo '=== SmallCrush'; {exe} smallcrush \"$f\"\n" if run_smallcrush else "")
            + "rm -f \"$f\"\n"
        )
        output = _run_linux(script, timeout=1800)
    except FileNotFoundError:
        return {"error": "TestU01 needs Linux: install WSL with Ubuntu on Windows."}
    except subprocess.TimeoutExpired:
        return {"error": "TestU01 execution timed out after 30 minutes."}
    except Exception as e:
        return {"error": f"Failed to execute TestU01: {e}"}
    finally:
        if owned:
            try:
                os.unlink(path)
            except OSError:
                pass

    tests, skipped = [], []
    for battery, lines in _sections(output).items():
        exhausted = next((int(l.split("\t")[1]) for l in lines if l.startswith("EXHAUSTED\t")), 0)
        if exhausted:
            skipped.append({"battery": battery, "reason": "input exhausted; data would be reused"})
            continue
        for line in lines:
            parts = line.split("\t")
            if parts[0] != "P" or len(parts) != 3:
                continue
            p = float(parts[2])
            if p < 0:  # TestU01 uses -1 for statistics it could not compute
                continue
            tests.append({"name": f"{battery}: {parts[1]}", "battery": battery,
                          "p_value": round(p, 6), "status": _tu01_status(p)})
    if not run_smallcrush:
        skipped.append({"battery": "SmallCrush",
                        "reason": f"needs {SMALLCRUSH_MIN_BYTES:,} bytes, input has {size:,}"})

    if not tests:
        return {"error": "TestU01 executed but returned no results.", "skipped": skipped}
    pass_count = sum(t["status"] == "PASS" for t in tests)
    weak_count = sum(t["status"] == "WEAK" for t in tests)
    fail_count = sum(t["status"] == "FAIL" for t in tests)
    batteries = sorted({t["battery"] for t in tests})
    return {
        "battery": " + ".join(batteries),
        "bits_tested": nbits,
        "tests": tests,
        "skipped": skipped,
        "pass": pass_count,
        "weak": weak_count,
        "fail": fail_count,
        "total": len(tests),
        "pass_rate": round(pass_count / len(tests), 3),
    }


def run_dieharder_suite(bits=None, path=None):
    """Runs every Dieharder test rated "Good" at standard settings. Dieharder
    silently rewinds a file that is too short and keeps testing reused data,
    so any test that rewound is reported as insufficient and not counted."""
    path, size, owned = _bits_or_path(bits, path)
    insufficient = [{"test": t, "reason": f"needs more than {need:,} bytes, input has {size:,}"}
                    for t, need in DIEHARDER_TESTS.items() if size < need]
    runnable = [t for t, need in DIEHARDER_TESTS.items() if size >= need]
    try:
        if not runnable:
            return {"error": f"Insufficient data: every Dieharder test needs more than {size:,} bytes.",
                    "insufficient": True, "insufficient_tests": insufficient}
        src = shlex.quote(_to_linux_path(path))
        lines = [
            "command -v dieharder >/dev/null || { echo 'dieharder not installed: sudo apt install dieharder'; exit 3; }",
            f"f=$(mktemp); cp {src} \"$f\"",
        ]
        for t in runnable:
            lines.append(f"echo '=== {t}'; dieharder -d {t} -g 201 -f \"$f\" 2>&1")
        lines.append("rm -f \"$f\"")
        output = _run_linux("\n".join(lines) + "\n", timeout=3600)
    except FileNotFoundError:
        return {"error": "Dieharder needs Linux: install WSL with Ubuntu on Windows."}
    except subprocess.TimeoutExpired:
        return {"error": "Dieharder execution timed out after 60 minutes."}
    except Exception as e:
        return {"error": f"Failed to execute Dieharder: {e}"}
    finally:
        if owned:
            try:
                os.unlink(path)
            except OSError:
                pass

    tests = []
    for label, out in _sections(output).items():
        rewinds, rows = 0, []
        for line in out:
            m = re.search(r"rewound (\d+) times", line)
            if m:
                rewinds = int(m.group(1))
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6 and not line.startswith("#"):
                try:
                    p_val = float(parts[4])
                except ValueError:
                    continue
                rows.append({"name": parts[0], "ntup": parts[1], "tsamples": parts[2],
                             "psamples": parts[3], "p_value": round(p_val, 8), "result": parts[5]})
        if rewinds:
            insufficient.append({"test": int(label), "name": rows[0]["name"] if rows else label,
                                 "reason": f"input too short; Dieharder rewound it {rewinds} times"})
        elif rows:
            tests.extend(rows)

    pass_count = sum(r["result"] == "PASSED" for r in tests)
    weak_count = sum(r["result"] == "WEAK" for r in tests)
    fail_count = sum(r["result"] == "FAILED" for r in tests)
    total = pass_count + weak_count + fail_count
    if total == 0:
        return {"error": f"Insufficient data: every Dieharder test needs more than {size:,} bytes.",
                "insufficient": True, "insufficient_tests": insufficient}
    return {
        "bytes_tested": size,
        "tests": tests,
        "insufficient_tests": insufficient,
        "pass": pass_count,
        "fail": fail_count,
        "weak": weak_count,
        "total": total,
        "pass_rate": round(pass_count / total, 3),
    }
