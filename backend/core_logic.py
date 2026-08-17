import sys
import os
import math
import numpy as np
import time

# Add parent dir to path to import NIST modules and Extractors
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from backend.nist_fast import NISTFast
from Extractors import Extractors

# Exact same functions from ExtractorSuite..py adapted slightly for standalone use

def calculate_metrics(bits, original_length, exec_time=0.0):
    bits = np.asarray(bits, dtype=np.int8)
    total = len(bits)
    if total == 0:
        return {'total':0, 'bias':1.0, 'shannon':0.0, 'min_entropy':0.0, 'bit_rate':0, 'efficiency':0.0, 'time_sec':exec_time}
    ones = int(np.sum(bits))
    zeros = total - ones
    p1 = ones / total
    p0 = zeros / total
    bias = abs(ones - zeros) / total
    shannon = -(p1 * np.log2(p1) + p0 * np.log2(p0)) if 0 < p1 < 1 else 0.0
    min_entropy = -np.log2(max(p1, p0)) if total > 0 else 0.0
    bit_rate = int(total / max(0.001, exec_time))
    efficiency = total / (original_length + 1e-9)
    return {'total': total, 'bias': bias, 'shannon': shannon, 'min_entropy': min_entropy,
            'bit_rate': bit_rate, 'efficiency': efficiency, 'time_sec': exec_time}

def run_nist_suite(bits):
    bits = np.asarray(bits, dtype=np.int8)
    length = len(bits)

    p_values = []
    
    # Track pass/fail details
    test_details = []

    def safe_run(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None

    def single(result):
        if result is None:
            return float('nan')
        return float(result)

    def serial_combined(result):
        if result is None or (isinstance(result, tuple) and len(result) > 0 and math.isnan(result[0])):
            return float('nan')
        return float(min(result[0], result[1]))

    def excursions_combined(result):
        if result is None:
            return float('nan')
        valid_p = [float(item) for item in result if not math.isnan(float(item))]
        if not valid_p:
            return float('nan')
        return min(valid_p)

    def record_test(name, p_val):
        status = 'invalid'
        if not math.isnan(p_val) and p_val != -1.0:
            if p_val >= 0.01:
                status = 'pass'
            else:
                status = 'fail'
        test_details.append({'name': name, 'pValue': p_val, 'status': status})
        p_values.append(p_val)

    if length < 100:
        for name in [
            "Frequency (Monobit)", "Block Frequency", "Runs", "Longest Run of Ones",
            "Binary Matrix Rank", "Discrete Fourier Transform", "Non-overlapping Template",
            "Overlapping Template", "Maurer's Universal", "Linear Complexity", "Serial",
            "Approximate Entropy", "Cumulative Sums (Fwd)", "Cumulative Sums (Bwd)",
            "Random Excursions", "Random Excursions Variant"
        ]:
            record_test(name, float('nan'))
    else:
        record_test("Frequency (Monobit)", single(safe_run(NISTFast.monobit_test, bits)))
        record_test("Block Frequency", single(safe_run(NISTFast.block_frequency, bits)))
        record_test("Runs", single(safe_run(NISTFast.run_test, bits)))
        record_test("Longest Run of Ones", single(safe_run(NISTFast.longest_one_block_test, bits)))
        record_test("Binary Matrix Rank", single(safe_run(NISTFast.binary_matrix_rank_text, bits)))
        record_test("Discrete Fourier Transform", single(safe_run(NISTFast.spectral_test, bits)))
        record_test("Non-overlapping Template", single(safe_run(NISTFast.non_overlapping_test, bits)))
        record_test("Overlapping Template", single(safe_run(NISTFast.overlapping_patterns, bits)))
        if length >= 387840:
            record_test("Maurer's Universal", single(safe_run(NISTFast.statistical_test, bits)))
        else:
            record_test("Maurer's Universal", -1.0)
        record_test("Linear Complexity", single(safe_run(NISTFast.linear_complexity_test, bits)))
        record_test("Serial", serial_combined(safe_run(NISTFast.serial_test, bits)))
        record_test("Approximate Entropy", single(safe_run(NISTFast.approximate_entropy_test, bits)))
        record_test("Cumulative Sums (Fwd)", single(safe_run(NISTFast.cumulative_sums_test, bits, mode=0)))
        record_test("Cumulative Sums (Bwd)", single(safe_run(NISTFast.cumulative_sums_test, bits, mode=1)))
        record_test("Random Excursions", excursions_combined(safe_run(NISTFast.random_excursions_test, bits)))
        record_test("Random Excursions Variant", excursions_combined(safe_run(NISTFast.random_excursions_variant_test, bits)))

    passes = sum(1 for p in p_values if (not math.isnan(p)) and p != -1.0 and p >= 0.01)
    fails = sum(1 for p in p_values if (not math.isnan(p)) and p != -1.0 and 0 <= p < 0.01)
    invalid = sum(1 for p in p_values if math.isnan(p) or p == -1.0)
    total = len(p_values) if p_values else 1
    pass_rate = passes / total if total > 0 else 0.0

    return {
        'pass': passes, 
        'fail': fails, 
        'invalid': invalid, 
        'total': total, 
        'pass_rate': pass_rate,
        'details': test_details
    }
