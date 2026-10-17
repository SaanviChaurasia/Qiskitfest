from __future__ import annotations
import argparse, json, csv
from pathlib import Path
from itertools import product

ROOT = Path(__file__).resolve().parent

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def validate_instance(data):
    nodes = data["nodes"]
    edges = data["edges"]
    weights = data.get("weights", [1.0] * len(edges))
    if len(weights) != len(edges) or len(set(nodes)) != len(nodes):
        raise ValueError("Instance must have unique nodes and one weight per edge")
    node_set = set(nodes)
    for edge in edges:
        if len(edge) != 2 or edge[0] not in node_set or edge[1] not in node_set or edge[0] == edge[1]:
            raise ValueError(f"Invalid edge: {edge}")
    return nodes, edges, [float(w) for w in weights]

def cut_value(bitstring, nodes, edges, weights):
    assignment = {node: int(bitstring[i]) for i, node in enumerate(nodes)}
    return sum(w for (u, v), w in zip(edges, weights) if assignment[u] != assignment[v])

def exact_baseline(instance):
    nodes, edges, weights = validate_instance(instance)
    best = max((cut_value(bits, nodes, edges, weights), bits) for bits in map("".join, product("01", repeat=len(nodes))))
    return {"best_cut": best[0], "best_assignment": best[1], "method": "exhaustive classical enumeration"}

def processor_target(processor):
    if processor.get("num_qubits") is None or not processor.get("coupling_map"):
        raise ValueError("Processor template is incomplete. Replace it with the exact official Processor A/B definition from the Challenge Kit.")
    from qiskit.transpiler import CouplingMap
    return CouplingMap(processor["coupling_map"])

def build_qaoa_circuit(instance, gammas, betas, n_physical, measure=True):
    from qiskit import QuantumCircuit
    nodes, edges, weights = validate_instance(instance)
    logical = {node: i for i, node in enumerate(nodes)}
    qc = QuantumCircuit(n_physical, len(nodes) if measure else 0)
    for q in range(len(nodes)):
        qc.h(q)
    for gamma in gammas:
        for (u, v), weight in zip(edges, weights):
            qc.rzz(-gamma * weight, logical[u], logical[v])
    for beta in betas:
        for q in range(len(nodes)):
            qc.rx(2.0 * beta, q)
    if measure:
        qc.measure(range(len(nodes)), range(len(nodes)))
    return qc

def run_processor(instance, processor, shots, seed, p, gamma, beta):
    if processor.get("noise_model") not in (None, "ideal"):
        raise NotImplementedError(
            "This starter runner is ideal/noiseless. Convert the official processor noise data "
            "to its prescribed simulator/backend before reporting benchmark results."
        )
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    coupling = processor_target(processor)
    if len(instance["nodes"]) > int(processor["num_qubits"]):
        raise ValueError("Problem instance has more logical qubits than the processor definition allows")
    qc = build_qaoa_circuit(instance, [gamma] * p, [beta] * p, int(processor["num_qubits"]))
    compiled = transpile(qc, coupling_map=coupling, basis_gates=processor.get("basis_gates") or None,
                         optimization_level=1, seed_transpiler=seed)
    sim = AerSimulator(seed_simulator=seed)
    result = sim.run(compiled, shots=shots, seed_simulator=seed).result()
    counts = result.get_counts()
    nodes, edges, weights = validate_instance(instance)
    total = sum(counts.values())
    avg_cut = sum(cut_value(bits.replace(" ", "")[::-1][:len(nodes)], nodes, edges, weights) * n for bits, n in counts.items()) / total
    two_q = sum(n for inst, qargs, cargs in compiled.data if len(qargs) == 2)
    operations = compiled.count_ops()
    return {"processor": processor["name"], "shots": shots, "seed": seed, "p": p, "gamma": gamma, "beta": beta,
            "mean_cut": avg_cut, "best_cut": max(cut_value(bits.replace(" ", "")[::-1][:len(nodes)], nodes, edges, weights) for bits in counts),
            "depth": compiled.depth(), "two_qubit_gates": two_q, "swap_count": int(operations.get("swap", 0)),
            "physical_qubits": compiled.num_qubits, "operations": dict(operations), "counts": counts,
            "transpiled_qasm": compiled.draw(output="text", fold=-1).__str__()}

def main():
    parser = argparse.ArgumentParser(description="Reproducible Phase 1 O1 Max-Cut A/B benchmark")
    parser.add_argument("--instance", default="data/instance.json")
    parser.add_argument("--processor-a", default="processors/processor_A.json")
    parser.add_argument("--processor-b", default="processors/processor_B.json")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=20261009)
    parser.add_argument("--p", type=int, default=1)
    parser.add_argument("--gamma", type=float, default=0.5)
    parser.add_argument("--beta", type=float, default=0.25)
    args = parser.parse_args()
    if args.shots <= 0 or args.p <= 0:
        parser.error("--shots and --p must both be positive")
    instance = load_json(args.instance)
    exact = exact_baseline(instance)
    rows = []
    for path in (args.processor_a, args.processor_b):
        rows.append(run_processor(instance, load_json(path), args.shots, args.seed, args.p, args.gamma, args.beta))
    out = ROOT / "results"
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "tables" / "benchmark.json").write_text(json.dumps({"problem": instance, "classical_baseline": exact, "runs": rows}, indent=2), encoding="utf-8")
    keys = ["processor", "shots", "seed", "p", "mean_cut", "best_cut", "depth", "two_qubit_gates", "swap_count", "physical_qubits"]
    with (out / "tables" / "ab_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys); writer.writeheader(); writer.writerows({k:r[k] for k in keys} for r in rows)
    for i, row in enumerate(rows, 1):
        (out / f"transpiled_processor_{'A' if i == 1 else 'B'}.txt").write_text(row["transpiled_qasm"], encoding="utf-8")
    print(json.dumps({"classical_baseline": exact, "runs": [{k:r[k] for k in keys} for r in rows]}, indent=2))

if __name__ == "__main__":
    main()

