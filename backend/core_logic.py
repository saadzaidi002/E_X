import sys
import os
import math
import numpy as np
import time

# Add parent dir to path to import NIST modules and Extractors
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from ApproximateEntropy import ApproximateEntropy as aet
from Complexity import ComplexityTest as ct
from CumulativeSum import CumulativeSums as cst
from FrequencyTest import FrequencyTest as ft
from Matrix import Matrix as mt
from RandomExcursions import RandomExcursions as ret
from RunTest import RunTest as rt
from Serial import Serial as serial
from Spectral import SpectralTest as st
from TemplateMatching import TemplateMatching as tm
from Universal import Universal as ut
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
    binary_data = ''.join(map(str, bits.tolist()))
    length = len(binary_data)

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
        return float(result[0])

    def serial_combined(result):
        if result is None:
            return float('nan')
        return float(min(result[0][0], result[1][0]))

    def excursions_combined(result):
        if result is None:
            return float('nan')
        valid_p = [float(item[-2]) for item in result if not math.isnan(float(item[-2]))]
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
        record_test("Frequency (Monobit)", single(safe_run(ft.monobit_test, binary_data)))
        record_test("Block Frequency", single(safe_run(ft.block_frequency, binary_data)))
        record_test("Runs", single(safe_run(rt.run_test, binary_data)))
        record_test("Longest Run of Ones", single(safe_run(rt.longest_one_block_test, binary_data)))
        record_test("Binary Matrix Rank", single(safe_run(mt.binary_matrix_rank_text, binary_data)))
        record_test("Discrete Fourier Transform", single(safe_run(st.spectral_test, binary_data)))
        record_test("Non-overlapping Template", single(safe_run(tm.non_overlapping_test, binary_data)))
        record_test("Overlapping Template", single(safe_run(tm.overlapping_patterns, binary_data)))
        if length >= 387840:
            record_test("Maurer's Universal", single(safe_run(ut.statistical_test, binary_data)))
        else:
            record_test("Maurer's Universal", -1.0)
        record_test("Linear Complexity", single(safe_run(ct.linear_complexity_test, binary_data)))
        record_test("Serial", serial_combined(safe_run(serial.serial_test, binary_data)))
        record_test("Approximate Entropy", single(safe_run(aet.approximate_entropy_test, binary_data)))
        record_test("Cumulative Sums (Fwd)", single(safe_run(cst.cumulative_sums_test, binary_data, mode=0)))
        record_test("Cumulative Sums (Bwd)", single(safe_run(cst.cumulative_sums_test, binary_data, mode=1)))
        record_test("Random Excursions", excursions_combined(safe_run(ret.random_excursions_test, binary_data)))
        record_test("Random Excursions Variant", excursions_combined(safe_run(ret.variant_test, binary_data)))

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
