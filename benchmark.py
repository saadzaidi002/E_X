import sys
import time
import numpy as np

# Add parent path so we can import Extractors
sys.path.append('E:/Extractors')
from Extractors import Extractors

# The 5 methods
methods_to_test = [
    Extractors.lhl_extractor,
    Extractors.goldreich_levin,
    Extractors.chor_goldreich,
    Extractors.trevisan_extractor,
    Extractors.quantum_proof_extractor
]

sizes = [1000, 5000, 10000, 20000, 50000, 100000, 200000]

print("Benchmarking slow methods to find 2-second threshold...")

thresholds = {}

for func in methods_to_test:
    name = func.__name__
    print(f"\nTesting {name}:")
    for size in sizes:
        data = np.random.randint(0, 2, size, dtype=np.int8)
        start = time.time()
        res = func(data)
        elapsed = time.time() - start
        print(f"  {size} bits -> {elapsed:.4f} sec")
        if elapsed > 1.5:
            thresholds[name] = size
            print(f"  --> Threshold hit at {size} bits")
            break
    if name not in thresholds:
        thresholds[name] = sizes[-1] # fallback

print("\nFinal Thresholds:", thresholds)
