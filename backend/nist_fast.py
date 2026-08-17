import math
import numpy as np
from scipy import fftpack, linalg
from scipy.special import erfc, gammaincc, hyp1f1
from scipy.stats import norm

class NISTFast:
    @staticmethod
    def monobit_test(bits):
        """Frequency (Monobit) Test"""
        n = len(bits)
        if n == 0: return float('nan')
        s_obs = np.sum(bits * 2 - 1)
        s_obs = s_obs / math.sqrt(n)
        p_value = erfc(math.fabs(s_obs) / math.sqrt(2))
        return float(p_value)

    @staticmethod
    def block_frequency(bits, block_size=128):
        """Block Frequency Test"""
        n = len(bits)
        if n < block_size: return float('nan')
        num_blocks = n // block_size
        
        # Reshape into blocks and compute proportion of ones
        blocks = bits[:num_blocks * block_size].reshape(num_blocks, block_size)
        pi = blocks.sum(axis=1) / block_size
        
        chi_sq = 4.0 * block_size * np.sum((pi - 0.5) ** 2)
        p_value = gammaincc(num_blocks / 2.0, chi_sq / 2.0)
        return float(p_value)

    @staticmethod
    def run_test(bits):
        """Runs Test"""
        n = len(bits)
        if n == 0: return float('nan')
        pi = np.sum(bits) / n
        tau = 2 / math.sqrt(n)
        if abs(pi - 0.5) >= tau:
            return 0.0
            
        v_obs = np.sum(bits[:-1] != bits[1:]) + 1
        p_value = erfc(abs(v_obs - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi)))
        return float(p_value)

    @staticmethod
    def longest_one_block_test(bits):
        """Longest Run of Ones in a Block Test"""
        n = len(bits)
        if n < 128: return float('nan')
        elif n < 6272:
            k, m = 3, 8
            v_values, pi_values = [1, 2, 3, 4], [0.21484375, 0.3671875, 0.23046875, 0.1875]
        elif n < 750000:
            k, m = 5, 128
            v_values, pi_values = [4, 5, 6, 7, 8, 9], [0.1174035788, 0.242955959, 0.249363483, 0.17517706, 0.102701071, 0.112398847]
        else:
            k, m = 6, 10000
            v_values, pi_values = [10, 11, 12, 13, 14, 15, 16], [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]

        num_blocks = n // m
        blocks = bits[:num_blocks * m].reshape(num_blocks, m)
        frequencies = np.zeros(k + 1)

        for block in blocks:
            # Find lengths of runs of 1s
            ones_idx = np.where(block == 1)[0]
            if len(ones_idx) == 0:
                max_run = 0
            else:
                # Find consecutive sequences
                diffs = np.diff(ones_idx)
                splits = np.where(diffs != 1)[0] + 1
                runs = np.split(ones_idx, splits)
                max_run = max(len(r) for r in runs)

            if max_run < v_values[0]: frequencies[0] += 1
            elif max_run > v_values[-1]: frequencies[k] += 1
            else: frequencies[v_values.index(max_run)] += 1

        x_obs = np.sum((frequencies - num_blocks * np.array(pi_values)) ** 2 / (num_blocks * np.array(pi_values)))
        p_value = gammaincc(k / 2.0, x_obs / 2.0)
        return float(p_value)

    @staticmethod
    def binary_matrix_rank_text(bits, rows=32, cols=32):
        """Binary Matrix Rank Test"""
        n = len(bits)
        block_size = rows * cols
        num_blocks = n // block_size
        if num_blocks == 0: return float('nan')

        blocks = bits[:num_blocks * block_size].reshape(num_blocks, rows, cols)
        ranks = np.zeros(3)

        for matrix in blocks:
            m = matrix.copy()
            rank = 0
            for i in range(cols):
                pivot_row = np.argmax(m[rank:, i]) + rank
                if m[pivot_row, i] == 1:
                    if pivot_row != rank:
                        m[[rank, pivot_row]] = m[[pivot_row, rank]]
                    mask = m[:, i] == 1
                    mask[rank] = False
                    m[mask] ^= m[rank]
                    rank += 1
                if rank == rows:
                    break
            
            if rank == rows: ranks[0] += 1
            elif rank == rows - 1: ranks[1] += 1
            else: ranks[2] += 1

        pi = [0.2888, 0.5776, 0.1336]
        x_obs = np.sum((ranks - num_blocks * np.array(pi)) ** 2 / (num_blocks * np.array(pi)))
        p_value = math.exp(-x_obs / 2)
        return float(p_value)

    @staticmethod
    def spectral_test(bits):
        """Discrete Fourier Transform (Spectral) Test"""
        n = len(bits)
        if n == 0: return float('nan')
        
        # Transform bits to -1, +1
        seq = bits * 2.0 - 1.0
        
        # Fast Fourier Transform
        spectral = fftpack.fft(seq)
        modulus = np.abs(spectral[:n // 2])
        
        tau = math.sqrt(math.log(1 / 0.05) * n)
        n0 = 0.95 * (n / 2)
        n1 = np.sum(modulus < tau)
        
        d = (n1 - n0) / math.sqrt(n * 0.95 * 0.05 / 4)
        p_value = erfc(math.fabs(d) / math.sqrt(2))
        return float(p_value)

    @staticmethod
    def non_overlapping_test(bits, template=np.array([0,0,0,0,0,0,0,0,1]), num_blocks=8):
        """Non-overlapping Template Matching Test"""
        n = len(bits)
        m = len(template)
        block_size = n // num_blocks
        if block_size == 0: return float('nan')
        
        counts = np.zeros(num_blocks)
        for i in range(num_blocks):
            block = bits[i * block_size : (i + 1) * block_size]
            
            shape = (len(block) - m + 1, m)
            strides = (block.strides[0], block.strides[0])
            windows = np.lib.stride_tricks.as_strided(block, shape=shape, strides=strides)
            
            matches = np.all(windows == template, axis=1)
            
            idx = 0
            while idx < len(matches):
                if matches[idx]:
                    counts[i] += 1
                    idx += m
                else:
                    idx += 1
                    
        mean = (block_size - m + 1) / (2 ** m)
        variance = block_size * ((1 / (2 ** m)) - ((2 * m - 1) / (2 ** (2 * m))))
        
        x_obs = np.sum((counts - mean) ** 2) / variance
        p_value = gammaincc(num_blocks / 2.0, x_obs / 2.0)
        return float(p_value)

    @staticmethod
    def overlapping_patterns(bits, m=9, block_size=1032):
        """Overlapping Template Matching Test"""
        n = len(bits)
        num_blocks = n // block_size
        if num_blocks == 0: return float('nan')
        
        template = np.ones(m, dtype=np.int8)
        
        lambda_val = (block_size - m + 1) / (2 ** m)
        eta = lambda_val / 2.0
        
        def get_prob(u, x):
            if u == 0: return math.exp(-x)
            return x * math.exp(-2 * x) * (2 ** -u) * hyp1f1(u + 1, 2, x)
            
        pi = np.array([get_prob(i, eta) for i in range(5)])
        pi = np.append(pi, 1.0 - pi.sum())
        
        counts = np.zeros(6)
        for i in range(num_blocks):
            block = bits[i * block_size : (i + 1) * block_size]
            shape = (len(block) - m + 1, m)
            strides = (block.strides[0], block.strides[0])
            windows = np.lib.stride_tricks.as_strided(block, shape=shape, strides=strides)
            
            match_count = np.sum(np.all(windows == template, axis=1))
            if match_count <= 4:
                counts[match_count] += 1
            else:
                counts[5] += 1
                
        x_obs = np.sum((counts - num_blocks * pi) ** 2 / (num_blocks * pi))
        p_value = gammaincc(5.0 / 2.0, x_obs / 2.0)
        return float(p_value)

    @staticmethod
    def statistical_test(bits):
        """Maurer's Universal Statistical Test"""
        n = len(bits)
        if n < 387840: return float('nan')
        
        if n >= 1059061760: m = 16
        elif n >= 496435200: m = 15
        elif n >= 231669760: m = 14
        elif n >= 107560960: m = 13
        elif n >= 49643520: m = 12
        elif n >= 22753280: m = 11
        elif n >= 10342400: m = 10
        elif n >= 4654080: m = 9
        elif n >= 2068480: m = 8
        elif n >= 904960: m = 7
        else: m = 6
            
        num_blocks = n // m
        init_bits = 10 * (2 ** m)
        test_bits = num_blocks - init_bits
        
        blocks = bits[:num_blocks * m].reshape(num_blocks, m)
        powers = 1 << np.arange(m - 1, -1, -1)
        int_reps = np.dot(blocks, powers)
        
        vobs = np.zeros(2 ** m, dtype=np.int32)
        
        init_reps = int_reps[:init_bits]
        vobs[init_reps] = np.arange(1, init_bits + 1)
        
        test_reps = int_reps[init_bits:]
        indices = np.arange(init_bits + 1, num_blocks + 1)
        
        cumsum = 0.0
        for i, val in enumerate(test_reps):
            cumsum += math.log2((i + init_bits + 1) - vobs[val])
            vobs[val] = i + init_bits + 1
            
        c = 0.7 - 0.8 / m + (4 + 32 / m) * (test_bits ** (-3 / m)) / 15
        variance = [0, 0, 0, 0, 0, 0, 2.954, 3.125, 3.238, 3.311, 3.356, 3.384, 3.401, 3.410, 3.416, 3.419, 3.421]
        expected = [0, 0, 0, 0, 0, 0, 5.2177052, 6.1962507, 7.1836656, 8.1764248, 9.1723243,
                    10.170032, 11.168765, 12.168070, 13.167693, 14.167488, 15.167379]
        sigma = c * math.sqrt(variance[m] / test_bits)
        
        phi = cumsum / test_bits
        stat = abs(phi - expected[m]) / (math.sqrt(2) * sigma)
        p_value = erfc(stat)
        return float(p_value)

    @staticmethod
    def linear_complexity_test(bits, block_size=500):
        """Linear Complexity Test"""
        n = len(bits)
        num_blocks = n // block_size
        if num_blocks <= 1: return float('nan')
        
        pi = np.array([0.01047, 0.03125, 0.125, 0.5, 0.25, 0.0625, 0.020833])
        mean = 0.5 * block_size + (1.0 / 36) * (9 + (-1) ** (block_size + 1)) - ((block_size / 3.0 + 2.0 / 9) / 2 ** block_size)
        
        blocks = bits[:num_blocks * block_size].reshape(num_blocks, block_size)
        
        complexities = np.zeros(num_blocks)
        for idx, block in enumerate(blocks):
            c = np.zeros(block_size, dtype=np.int8)
            b = np.zeros(block_size, dtype=np.int8)
            c[0] = 1
            b[0] = 1
            l, m = 0, -1
            
            for i in range(block_size):
                d = (block[i] + np.dot(c[1:l+1], block[i-l:i][::-1])) % 2
                if d == 1:
                    temp = c.copy()
                    p = np.zeros(block_size, dtype=np.int8)
                    p[i-m:i-m+l] = b[:l]
                    if b[0] == 1:
                        p[i-m] = 1
                    else:
                        p[i-m:i-m+block_size] = b[:block_size-(i-m)]
                    
                    c = (c + p) % 2
                    if l <= 0.5 * i:
                        l = i + 1 - l
                        m = i
                        b = temp
            complexities[idx] = l
            
        t = (-1.0) ** block_size * (complexities - mean) + 2.0 / 9
        vg, _ = np.histogram(t, bins=[-np.inf, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, np.inf])
        
        x_obs = np.sum((vg - num_blocks * pi) ** 2 / (num_blocks * pi))
        p_value = gammaincc(6 / 2.0, x_obs / 2.0)
        return float(p_value)

    @staticmethod
    def serial_test(bits, m=16):
        """Serial Test"""
        n = len(bits)
        if n == 0: return (float('nan'), float('nan'))
        
        extended = np.concatenate((bits, bits[:m-1]))
        powers = 1 << np.arange(m - 1, -1, -1)
        
        sums = np.zeros(3)
        for i in range(3):
            k = m - i
            if k <= 0: continue
            
            shape = (n, k)
            strides = (extended.strides[0], extended.strides[0])
            windows = np.lib.stride_tricks.as_strided(extended, shape=shape, strides=strides)
            
            vals = np.dot(windows, powers[-k:])
            vobs = np.bincount(vals, minlength=2**k)
            sums[i] = np.sum(vobs ** 2) * (2 ** k) / n - n
            
        nabla1 = sums[0] - sums[1]
        nabla2 = sums[0] - 2 * sums[1] + sums[2]
        
        p_value1 = gammaincc(2 ** (m - 2), nabla1 / 2.0)
        p_value2 = gammaincc(2 ** (m - 3), nabla2 / 2.0)
        return float(p_value1), float(p_value2)

    @staticmethod
    def approximate_entropy_test(bits, m=10):
        """Approximate Entropy Test"""
        n = len(bits)
        if n == 0: return float('nan')
        
        extended = np.concatenate((bits, bits[:m+1]))
        
        sums = np.zeros(2)
        for i in range(2):
            k = m + i
            shape = (n, k)
            strides = (extended.strides[0], extended.strides[0])
            windows = np.lib.stride_tricks.as_strided(extended, shape=shape, strides=strides)
            
            powers = 1 << np.arange(k - 1, -1, -1)
            vals = np.dot(windows, powers)
            
            vobs = np.bincount(vals, minlength=2**k)
            vobs = vobs[vobs > 0]
            sums[i] = np.sum(vobs * np.log(vobs / n))
            
        sums /= n
        ape = sums[0] - sums[1]
        x_obs = 2.0 * n * (math.log(2) - ape)
        p_value = gammaincc(2 ** (m - 1), x_obs / 2.0)
        return float(p_value)

    @staticmethod
    def cumulative_sums_test(bits, mode=0):
        """Cumulative Sums Test (Forward/Backward)"""
        n = len(bits)
        if n == 0: return float('nan')
        
        seq = bits * 2 - 1
        if mode == 1:
            seq = seq[::-1]
            
        cumsum = np.cumsum(seq)
        abs_max = np.max(np.abs(cumsum))
        
        if abs_max == 0: return 1.0
        
        start1 = int(math.floor(0.25 * math.floor(-n / abs_max + 1)))
        end1 = int(math.floor(0.25 * math.floor(n / abs_max - 1)))
        
        terms1 = 0
        for k in range(start1, end1 + 1):
            terms1 += norm.cdf((4 * k + 1) * abs_max / math.sqrt(n)) - norm.cdf((4 * k - 1) * abs_max / math.sqrt(n))
            
        start2 = int(math.floor(0.25 * math.floor(-n / abs_max - 3)))
        end2 = int(math.floor(0.25 * math.floor(n / abs_max) - 1))
        
        terms2 = 0
        for k in range(start2, end2 + 1):
            terms2 += norm.cdf((4 * k + 3) * abs_max / math.sqrt(n)) - norm.cdf((4 * k + 1) * abs_max / math.sqrt(n))
            
        p_value = 1.0 - terms1 + terms2
        return float(p_value)

    @staticmethod
    def random_excursions_test(bits):
        """Random Excursions Test"""
        n = len(bits)
        if n == 0: return [float('nan')] * 8
        
        seq = bits * 2 - 1
        cumsum = np.cumsum(seq)
        cumsum = np.concatenate(([0], cumsum, [0]))
        
        zero_pos = np.where(cumsum == 0)[0]
        num_cycles = len(zero_pos) - 1
        if num_cycles < 500:
            return [float('nan')] * 8
            
        states = [-4, -3, -2, -1, 1, 2, 3, 4]
        state_counts = np.zeros((num_cycles, 8), dtype=np.int32)
        
        for i in range(num_cycles):
            cycle = cumsum[zero_pos[i]:zero_pos[i+1]+1]
            for j, state in enumerate(states):
                state_counts[i, j] = np.sum(cycle == state)
                
        state_counts = np.clip(state_counts, 0, 5)
        
        su = np.zeros((8, 6))
        for j in range(8):
            for count in range(6):
                su[j, count] = np.sum(state_counts[:, j] == count)
                
        def get_pi(k, x):
            x_abs = abs(x)
            if k == 0: return 1 - 1.0 / (2 * x_abs)
            elif k >= 5: return (1.0 / (2 * x_abs)) * (1 - 1.0 / (2 * x_abs)) ** 4
            else: return (1.0 / (4 * x * x)) * (1 - 1.0 / (2 * x_abs)) ** (k - 1)
            
        pi = np.array([[get_pi(k, x) for k in range(6)] for x in states])
        inner_term = num_cycles * pi
        
        x_obs = np.sum((su - inner_term) ** 2 / inner_term, axis=1)
        p_values = [float(gammaincc(2.5, x / 2.0)) for x in x_obs]
        return p_values

    @staticmethod
    def random_excursions_variant_test(bits):
        """Random Excursions Variant Test"""
        n = len(bits)
        if n == 0: return [float('nan')] * 18
        
        seq = bits * 2 - 1
        cumsum = np.cumsum(seq)
        cumsum = np.concatenate(([0], cumsum, [0]))
        
        zero_pos = np.where(cumsum == 0)[0]
        j = len(zero_pos) - 1
        if j < 500:
            return [float('nan')] * 18
            
        states = [x for x in range(-9, 10) if x != 0]
        p_values = []
        
        for state in states:
            count = np.sum(cumsum == state)
            den = math.sqrt(2 * j * (4 * abs(state) - 2))
            p_values.append(float(erfc(abs(count - j) / den)))
            
        return p_values
