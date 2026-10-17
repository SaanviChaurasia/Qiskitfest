# Phase 1 - O1 Max-Cut A/B Benchmark

**Selected problem statement:** O1, Max-Cut (Quantum Optimization). This project implements one problem statement only.

## Status

This is a reproducible project scaffold, not yet an official completed benchmark. The PDFs give only a high-level description of the processor models. They do not contain the exact Max-Cut instance, processor coupling maps, complete noise and compilation parameters, or organizer repository template. The files marked `.template.json` are not official challenge inputs and must not be submitted as such.

The overview describes Processor A as a five-qubit fixed-baseline graph with a synthetic noise model. It describes Processor B as a seven-qubit heavy-hex-inspired graph with a contemporary compilation baseline. Exact qubit connections and settings must come from the Challenge Kit.

## Why O1

Max-Cut asks us to split graph vertices into two groups so as many (or as much total weight of) edges as possible cross between the groups. It has a clear classical objective and a compact QAOA circuit. That makes it a useful fit for comparing objective quality, circuit depth, two-qubit gates, routing and qubit use. The official instance and method take precedence over this suggested implementation.

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

## Run after adding Challenge Kit inputs

```bash
python main.py --instance data/instance.json --processor-a processors/processor_A.json --processor-b processors/processor_B.json --shots 4096 --seed 20261009 --p 1 --gamma 0.5 --beta 0.25
```

The script computes an exhaustive classical optimum for small instances, builds the same p-layer QAOA circuit for both processors, transpiles each against its coupling map, runs a fixed-seed ideal (noiseless) Aer simulation, and writes JSON/CSV results and circuit text. The cost unitary is based on C = sum(w * (1 - Z_i Z_j) / 2), implemented with Qiskit RZZ(-gamma * w); the mixer uses RX(2 * beta). Fixed angles are a simple baseline, not optimized parameters.

The runner currently does not implement the organizer noise model. If a non-ideal `noise_model` is provided, it stops with an error rather than silently ignoring noise. The Challenge Kit's noise model, optimizer settings, transpiler method, shot/seed settings and required execution backend must be integrated before treating any result as a final challenge result.

## Outputs after a valid run

- `results/tables/benchmark.json`: instance, exact classical baseline and processor outputs.
- `results/tables/ab_comparison.csv`: concise A/B table.
- `results/transpiled_processor_A.txt` and `results/transpiled_processor_B.txt`: transpiled circuits.
- `results/figures/`: reserved for plots generated from real run results.

The `swap_count` field counts explicit SWAP instructions. Some compilers decompose routing into native gates, so inspect the full operation list and compare total two-qubit gates as well. Local simulator runtime is not hardware execution time.

## Fair comparison

Use the same instance, logical circuit, angles or optimizer, shots, seeds and analysis for A and B. Record each processor definition, noise assumptions, transpiler and software version. Compare sampled objective values with the exact classical optimum, then use compiled circuit metrics as evidence for differences. Connectivity alone may not explain a result if gate sets, noise and compilation differ.

## AI assistance disclosure

AI assistance was used to review the supplied instructions and draft this scaffold and code.
