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


# Dieharder, run the way `dieharder -a` runs it: the same 114 result lines from
# the same tests and ntuple variants. Each entry is run on its own against the
# start of the file, and an entry whose data would have to be reused (Dieharder
# silently rewinds a short file) is reported as skipped, never counted.
#
# Table values: (test, ntup or None, name, result lines, reliability, rewinds on
# an 8 MiB file). Data read >= rewinds x 8 MiB, which is used to skip entries
# that cannot fit without running them; anything else must also finish without
# rewinding. Reliability is Dieharder's own rating from `dieharder -l`; like
# `dieharder -a`, all 114 entries are run and scored, including the ones it rates
# "Suspect" or "Do Not Use" (their rating is kept for display).
_MIB8 = 8 * 1024 * 1024
# rgb_lagged_sum reads (52 + 47.67 n) x 8 MiB for ntup n (measured for n = 0..15);
# rounded down, so it stays a lower bound.
_LAGGED_SUM_REWINDS = [int(52 + 47.67 * n) for n in range(33)]
_A_ENTRIES = [
    (0, None, "diehard_birthdays", 1, "good", 6),
    (1, None, "diehard_operm5", 1, "good", 52),
    (2, None, "diehard_rank_32x32", 1, "good", 65),
    (3, None, "diehard_rank_6x8", 1, "good", 33),
    (4, None, "diehard_bitstream", 1, "good", 17),
    (5, None, "diehard_opso", 1, "suspect", 104),
    (6, None, "diehard_oqso", 1, "suspect", 71),
    (7, None, "diehard_dna", 1, "suspect", 36),
    (8, None, "diehard_count_1s_str", 1, "good", 7),
    (9, None, "diehard_count_1s_byt", 1, "good", 65),
    (10, None, "diehard_parking_lot", 1, "good", 5),
    (11, None, "diehard_2dsphere", 1, "good", 5),
    (12, None, "diehard_3dsphere", 1, "good", 5),
    (13, None, "diehard_squeeze", 1, "good", 114),
    (14, None, "diehard_sums", 1, "do not use", 4),
    (15, None, "diehard_runs", 2, "good", 9),
    (16, None, "diehard_craps", 2, "good", 68),
    (17, None, "marsaglia_tsang_gcd", 2, "good", 958),
    (100, None, "sts_monobit", 1, "good", 9),
    (101, None, "sts_runs", 1, "good", 9),
    (102, None, "sts_serial", 30, "good", 9),
] + [(200, n, "rgb_bitdist", 1, "good", r) for n, r in zip(range(1, 13), (14, 23, 33, 42, 52, 61, 71, 81, 90, 100, 109, 119))] \
  + [(201, n, "rgb_minimum_distance", 1, "good", r) for n, r in zip(range(2, 6), (14, 19, 23, 28))] \
  + [(202, n, "rgb_permutations", 1, "good", r) for n, r in zip(range(2, 6), (14, 19, 23, 28))] \
  + [(203, n, "rgb_lagged_sum", 1, "good", r) for n, r in zip(range(0, 33), _LAGGED_SUM_REWINDS)] \
  + [
    (204, None, "rgb_kstest_test", 1, "good", 9),
    (205, None, "dab_bytedistrib", 1, "good", 78),
    (206, None, "dab_dct", 1, "good", 10),
    (207, None, "dab_filltree", 2, "good", 58),
    (208, None, "dab_filltree2", 2, "good", 18),
    (209, None, "dab_monobit2", 1, "good", 35),
]
DIEHARDER_ENTRIES = [
    {"test": t, "ntup": n, "name": name, "lines": lines, "reliability": rel, "need": rw * _MIB8}
    for t, n, name, lines, rel, rw in _A_ENTRIES
]
DIEHARDER_TOTAL_LINES = sum(e["lines"] for e in DIEHARDER_ENTRIES)           # 114, as in `dieharder -a`
DIEHARDER_SCORED_LINES = DIEHARDER_TOTAL_LINES                             # every entry counts, as in `dieharder -a`


def _entry_label(e):
    return f"{e['name']}" + (f" (ntup {e['ntup']})" if e["ntup"] is not None else "")


def run_dieharder_suite(bits=None, path=None):
    """Runs the `dieharder -a` set of tests, entry by entry, at standard settings.
    Returns counts over all 114 result lines: passed / weak / failed / skipped
    (not enough data to run without reusing it). `total` is 114 for every input."""
    path, size, owned = _bits_or_path(bits, path)
    plan, entries_out = [], []
    for i, e in enumerate(DIEHARDER_ENTRIES):
        if size < e["need"]:
            entries_out.append({"label": _entry_label(e), "lines": e["lines"], "status": "skipped",
                                "reason": f"needs more than {e['need'] / 2**20:,.0f} MiB, input has {size / 2**20:,.0f} MiB"})
        else:
            plan.append(i)
            entries_out.append(None)
    try:
        if plan:
            src = shlex.quote(_to_linux_path(path))
            lines = [
                "command -v dieharder >/dev/null || { echo 'dieharder not installed: sudo apt install dieharder'; exit 3; }",
                f"f=$(mktemp); cp {src} \"$f\"",
            ]
            for i in plan:
                e = DIEHARDER_ENTRIES[i]
                ntup = f" -n {e['ntup']}" if e["ntup"] is not None else ""
                lines.append(f"echo '=== {i}'; dieharder -d {e['test']}{ntup} -g 201 -f \"$f\" 2>&1")
            lines.append("rm -f \"$f\"")
            output = _run_linux("\n".join(lines) + "\n", timeout=3 * 3600)
        else:
            output = ""
    except FileNotFoundError:
        return {"error": "Dieharder needs Linux: install WSL with Ubuntu on Windows."}
    except subprocess.TimeoutExpired:
        return {"error": "Dieharder execution timed out after 3 hours."}
    except Exception as e:
        return {"error": f"Failed to execute Dieharder: {e}"}
    finally:
        if owned:
            try:
                os.unlink(path)
            except OSError:
                pass

    sections = _sections(output)
    tests = []
    for i in plan:
        e = DIEHARDER_ENTRIES[i]
        rewinds, rows = 0, []
        for line in sections.get(str(i), []):
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
            entries_out[i] = {"label": _entry_label(e), "lines": e["lines"], "status": "skipped",
                              "reason": f"input too short; Dieharder rewound it {rewinds} times"}
        elif not rows:
            entries_out[i] = {"label": _entry_label(e), "lines": e["lines"], "status": "skipped", "reason": "no output"}
        else:
            entries_out[i] = {"label": _entry_label(e), "lines": len(rows), "status": "run"}
            tests.extend(rows)

    pass_count = sum(r["result"] == "PASSED" for r in tests)
    weak_count = sum(r["result"] == "WEAK" for r in tests)
    fail_count = sum(r["result"] == "FAILED" for r in tests)
    skipped = sum(x["lines"] for x in entries_out if x["status"] == "skipped")
    excluded = sum(x["lines"] for x in entries_out if x["status"] == "excluded")
    result = {
        "bytes_tested": size,
        "tests": tests,
        "entries": entries_out,
        "insufficient_tests": [x for x in entries_out if x["status"] == "skipped"],
        "pass": pass_count,
        "weak": weak_count,
        "fail": fail_count,
        "skipped": skipped,
        "excluded": excluded,
        "total": DIEHARDER_SCORED_LINES,
        "all_entries": DIEHARDER_TOTAL_LINES,
        "pass_rate": round(pass_count / DIEHARDER_SCORED_LINES, 3),
    }
    if not tests:
        result["insufficient"] = True
    return result
