"""
Brute Force vs Quantum (Grover's Algorithm) Search Simulation
==========================================================================

This script compares two approaches to cracking a randomly chosen password
string by exhaustive search:

1. Brute force: Python loop that tries every possible
   combination until it finds the password. On average this takes N/2 tries
   for a search space of size N (worst case N tries) where N = total possible
   combinations for the password.

2. QUANTUM SEARCH (Grover's Algorithm): Quantum circuit, running on 
   Qiskit local simulator using amplitude amplification
   to find the password in roughly sqrt(N) queries instead of N/2.

"""

import time
import random
import string
import math

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.circuit.library import MCXGate


# Brute Force
def brute_force(password, alphabet, length):
    """
    Iterates over every possible password combination until the
    correct one is found.
    """
    start = time.perf_counter()
    guesses = 0
    indices = [0] * length

    while True:
        candidate = "".join(alphabet[i] for i in indices)
        guesses += 1
        if candidate == password:
            return candidate, guesses, time.perf_counter() - start

        # increment indices
        pos = length - 1
        while pos >= 0:
            indices[pos] += 1
            if indices[pos] < len(alphabet):
                break
            indices[pos] = 0
            pos -= 1
        else:
            break  # all combinations exhausted

    return None, guesses, time.perf_counter() - start



# Quantum Search
def build_grover_circuit(n_qubits, target_bitstring):
    """
    Build a Grover's algorithm circuit that searches an unsorted space of
    2^n_qubits items for a single marked target item (target_bitstring),
    using the optimal number of Grover iterations.
    """
    qc = QuantumCircuit(n_qubits, n_qubits)

    # Step 1: put all qubits into equal superposition of all possible
    # values (this is the quantum equivalent of "considering every
    # combination at once").
    qc.h(range(n_qubits))

    # Optimal number of Grover iterations for a single marked item:
    # roughly (pi/4) * sqrt(N), where N = 2^n_qubits
    n_iterations = max(1, round((math.pi / 4) * math.sqrt(2 ** n_qubits)))

    for _ in range(n_iterations):
        _add_oracle(qc, n_qubits, target_bitstring)
        _add_diffuser(qc, n_qubits)

    qc.measure(range(n_qubits), range(n_qubits))
    return qc, n_iterations


def _add_oracle(qc, n_qubits, target_bitstring):
    """
    Marks the target bitstring by flipping its phase (multiplies its
    amplitude by -1). This is the quantum equivalent of "checking if this
    is the password." Each call to this function is one oracle query and
    directly comparable to one brute force guess.
    """
    # Flip qubits that should be 0 in the target, so the all-ones pattern
    # corresponds exactly to the target string.
    for i, bit in enumerate(reversed(target_bitstring)):
        if bit == "0":
            qc.x(i)

    # Multi-controlled Z: flip the phase only when all qubits are |1>
    if n_qubits == 1:
        qc.z(0)
    else:
        qc.h(n_qubits - 1)
        qc.append(MCXGate(n_qubits - 1), list(range(n_qubits - 1)) + [n_qubits - 1])
        qc.h(n_qubits - 1)

    # Undo the X flips
    for i, bit in enumerate(reversed(target_bitstring)):
        if bit == "0":
            qc.x(i)


def _add_diffuser(qc, n_qubits):
    """
    The "diffuser" amplifies the marked state's probability by reflecting
    all amplitudes about their average. This is what makes the password
    string increasingly likely to be measured after each iteration.
    """
    qc.h(range(n_qubits))
    qc.x(range(n_qubits))

    if n_qubits == 1:
        qc.z(0)
    else:
        qc.h(n_qubits - 1)
        qc.append(MCXGate(n_qubits - 1), list(range(n_qubits - 1)) + [n_qubits - 1])
        qc.h(n_qubits - 1)

    qc.x(range(n_qubits))
    qc.h(range(n_qubits))


def quantum_grover_search(n_qubits, target_bitstring):
    """
    Runs the Grover circuit on Qiskit's Aer simulator and returns the
    most frequently measured bitstring, the number of oracle queries
    used, and the time of the simulation.
    """
    start = time.perf_counter()

    qc, n_iterations = build_grover_circuit(n_qubits, target_bitstring)

    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=1024).result()
    counts = result.get_counts()

    elapsed = time.perf_counter() - start

    most_common = max(counts, key=counts.get)
    confidence = counts[most_common] / sum(counts.values())

    return most_common, n_iterations, elapsed, confidence


# String to bitstring helpers
def string_to_index(s, alphabet):
    """Convert a string into its index within the full space of
    alphabet^length combinations (treating it like a base-N number)."""
    base = len(alphabet)
    index = 0
    for ch in s:
        index = index * base + alphabet.index(ch)
    return index


def index_to_bitstring(index, n_qubits):
    return format(index, f"0{n_qubits}b")


def bitstring_to_string(bitstring, alphabet, length):
    """Convert a bitstring back into the original alphabet-based string."""
    base = len(alphabet)
    index = int(bitstring, 2)
    chars = []
    for _ in range(length):
        chars.append(alphabet[index % base])
        index //= base
    return "".join(reversed(chars))


# Demo Code
def run_demo(length=6, alphabet=string.ascii_lowercase[:6]):
    """
    Picks a random password string of the given length over a given
    small alphabet, then attempts to guess it normally and quantumly.
    """
    base = len(alphabet)
    space_size = base ** length
    n_qubits = math.ceil(math.log2(space_size))
    padded_space = 2 ** n_qubits
 
    password = "".join(random.choice(alphabet) for _ in range(length))
    password_index = string_to_index(password, alphabet)
    password_bits = index_to_bitstring(password_index, n_qubits)
 
    print("=" * 70)
    print(f"PASSWORD TO CRACK: '{password}'")
    print(f"Alphabet: '{alphabet}' ({base} symbols) | Length: {length}")
    print(f"Search space size: {space_size} combinations "
          f"(padded to {padded_space} = 2^{n_qubits} for {n_qubits} qubits)")
    print("=" * 70)
 
    # Normal
    print("\n[1] Running brute-force search...")
    found, guesses, c_time = brute_force(password, alphabet, length)
    print(f"    Found: '{found}'")
    print(f"    Guesses needed: {guesses} (out of {space_size} possible)")
    print(f"    Time: {c_time*1000:.3f} ms")
 
    # Quantum
    print("\n[2] Running quantum simulator...")
    q_result_bits, q_iterations, q_time, confidence = quantum_grover_search(
        n_qubits, password_bits
    )
    q_result_str = bitstring_to_string(q_result_bits, alphabet, length)
    success = (q_result_str == password)
    print(f"    Found: '{q_result_str}' (confidence: {confidence*100:.1f}%, "
          f"{'CORRECT' if success else 'WRONG'})")
    print(f"    Oracle queries (Grover iterations): {q_iterations} "
          f"(vs {padded_space} in the padded space it searches)")
    print(f"    Simulation time: {q_time*1000:.3f} ms "
          f"(includes overhead of simulating a quantum computer)")
 
    # Comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Metric':<35}{'Traditional':<18}{'Quantum':<18}")
    print(f"{'-'*70}")
    print(f"{'Queries needed':<35}{guesses:<18}{q_iterations:<18}")
    speedup = guesses / q_iterations if q_iterations else float('inf')
    print(f"{'Query speedup factor':<35}{'1x':<18}{f'{speedup:.1f}x':<18}")
    print(f"{'Time (this machine)':<35}{f'{c_time*1000:.3f} ms':<18}"
          f"{f'{q_time*1000:.3f} ms':<18}")
 
    return {
        "password": password,
        "space_size": space_size,
        "padded_space": padded_space,
        "n_qubits": n_qubits,
        "bf_guesses": guesses,
        "bf_time": c_time,
        "quantum_iterations": q_iterations,
        "quantum_time": q_time,
        "quantum_confidence": confidence,
        "quantum_success": success,
    }

def run_multiple(n_runs=100, length=6, alphabet=string.ascii_lowercase[:6]):
    results = []
    for i in range(n_runs):
        print(f"\n{'='*70}")
        print(f"RUN {i+1} of {n_runs}")
        r = run_demo(length=length, alphabet=alphabet)
        results.append(r)
    return results


# Results
import numpy as np

def print_results(results):
    bf        = [r["bf_guesses"]         for r in results]
    quantum   = [r["quantum_iterations"] for r in results]
    conf      = [r["quantum_confidence"] for r in results]
    success   = [r["quantum_success"]    for r in results]
 
    real_space   = results[0]["space_size"]
    padded_space = results[0]["padded_space"]
    n_qubits     = results[0]["n_qubits"]
    n_runs       = len(results)
 
    # Measure how brute force varies
    avg_c = np.mean(bf)
    std_c = np.std(bf)
    theoretical_c = (real_space + 1) / 2        
 
    # Grover's query count is fixed but measurement quality varies.
    q_queries = quantum[0]
    q_is_constant = (len(set(quantum)) == 1)
    theoretical_q = (math.pi / 4) * math.sqrt(padded_space)  # padded space
 
    success_rate = np.mean(success) * 100
    avg_conf     = np.mean(conf) * 100
 
    speedup = avg_c / q_queries if q_queries else float("inf")
 
    print("\n" + "=" * 70)
    print("SIMULATION SUMMARY")
    print("=" * 70)
    print(f"Runs: {n_runs}  |  Real space: {real_space}  |  "
          f"Padded space: {padded_space} (2^{n_qubits})")
    print("-" * 70)
    print(f"{'Metric':<32}{'Brute Force':<19}{'Quantum (Grover)':<19}")
    print("-" * 70)
    print(f"{'Search space':<32}{real_space:<19}{padded_space:<19}")
    print(f"{'Queries (measured)':<32}"
          f"{f'{avg_c:.1f}':<19}"
          f"{f'{q_queries} (fixed)':<19}")
    print(f"{'Queries (theoretical)':<32}"
          f"{f'{theoretical_c:.1f}':<19}{f'{theoretical_q:.1f}':<19}")
    print("-" * 70)
    print(f"Grover success rate (top result correct): {success_rate:.1f}%")
    print(f"Grover mean confidence:                   {avg_conf:.1f}%")
    if not q_is_constant:
        print("WARNING: Grover query count varied across runs (unexpected).")
    print("-" * 70)
    print(f"Query speedup (brute force avg / Grover): {speedup:.1f}x")
    print("=" * 70)



# Main
if __name__ == "__main__":
    N_RUNS = 50
    results = run_multiple(n_runs=N_RUNS, length=6, alphabet=string.ascii_lowercase[:6])
    print_results(results)