"""
Human-Designed Baseline Heuristics for TSP
===========================================

This script implements three classical, human-designed heuristics for the
Traveling Salesman Problem (TSP). These serve as the comparison baseline
in the paper:

    "Can LLMs Design Better Heuristics Than Human Experts?
     A Benchmark Study on Combinatorial Optimization"
    — Manasvi Gangrade, IIST Indore, 2026

PURPOSE
-------
In our LLM-Heuristic framework, LLM-generated heuristics are compared
against these three well-established algorithms that represent decades of
human algorithmic expertise. A meaningful result is achieved when LLM-generated
heuristics match or outperform these baselines on the same benchmark instances.

THE THREE BASELINES
-------------------

1. NEAREST NEIGHBOR (NN)
   ----------------------
   Origin: One of the oldest and most widely-known TSP heuristics.
   Strategy: Start at city 0. At each step, move to the closest unvisited city.
             Repeat until all cities are visited, then return to start.
   Complexity: O(n^2) time, O(n) space.
   Strengths: Extremely fast, simple to implement, intuitive.
   Weaknesses: Greedy — makes locally optimal choices that are globally suboptimal.
               Typically produces tours 20-25% longer than the true optimal.
   Reference: Rosenkrantz et al. (1977), "An Analysis of Several Heuristics
              for the Traveling Salesman Problem."

2. 2-OPT LOCAL SEARCH
   -------------------
   Origin: Developed by Lin (1965), one of the most influential TSP improvements.
   Strategy: Start with a Nearest Neighbor tour. Then iteratively try all pairs
             of edges (i, j). If reversing the segment between i and j reduces
             total tour cost, apply the reversal. Repeat until no improvement
             is possible (local optimum reached).
   Complexity: O(n^2) per pass, multiple passes until convergence.
   Strengths: Significantly improves NN tours. Simple, reliable, widely used
              in practice as a post-processing step.
   Weaknesses: Can get stuck in local optima. Does not guarantee global optimum.
               Slower than pure NN due to repeated improvement passes.
   Reference: Lin, S. (1965), "Computer Solutions of the Traveling Salesman
              Problem." Bell System Technical Journal.

3. GREEDY EDGE INSERTION
   ----------------------
   Origin: A classical construction heuristic distinct from nearest-neighbor.
   Strategy: Instead of building a tour city-by-city, sort ALL edges (pairs of
             cities) by length from shortest to longest. Greedily add edges to
             the tour if: (a) neither endpoint already has degree 2, and
             (b) adding the edge does not create a subtour (cycle) before all
             cities are included. Continue until a complete Hamiltonian cycle
             is formed.
   Complexity: O(n^2 log n) for sorting, O(n^2) for construction.
   Strengths: Takes a global view of edge costs rather than a local greedy
              approach. Often produces different (sometimes better) tours than NN.
   Weaknesses: More complex to implement correctly. Not as easily improvable
               by local search as NN-based tours.
   Reference: Bentley, J.L. (1992), "Fast Algorithms for Geometric Traveling
              Salesman Problems." ORSA Journal on Computing.

HOW TO USE THIS FILE
--------------------
1. Run standalone to see baseline performance on random TSP instances:
       python human_baselines.py

2. Import into your main experiment for direct comparison:
       from human_baselines import run_all_baselines, generate_tsp_instances

3. Results are saved to: baseline_results.json
   These numbers go directly into Table 1 of the paper as human-expert baselines.

INTERPRETING RESULTS
--------------------
- avg_gap_pct: Average percentage gap from the Nearest Neighbor reference solution.
  Negative = better than NN. Positive = worse than NN.
- avg_runtime_s: Average seconds to solve one instance.
- The LLM framework results (from results_final_run.json) should be compared
  directly against these numbers in the paper.
"""

import json
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


# ── Data Class (same as main framework) ──────────────────────────────────────

@dataclass
class ProblemInstance:
    instance_id: str
    data: Dict[str, Any]
    best_known_solution: float  # Nearest Neighbor cost used as reference


# ── Baseline 1: Nearest Neighbor ─────────────────────────────────────────────

def nearest_neighbor(instance: ProblemInstance) -> Dict[str, Any]:
    """
    Nearest Neighbor TSP Heuristic.

    Constructs a tour by always moving to the closest unvisited city.
    This is the simplest greedy construction heuristic and serves as
    the primary reference baseline throughout the paper.

    Time Complexity: O(n^2)
    """
    n = instance.data["n_cities"]
    dist = instance.data["dist_matrix"]

    tour = [0]
    unvisited = set(range(1, n))

    while unvisited:
        current = tour[-1]
        nearest = min(unvisited, key=lambda c: dist[current][c])
        tour.append(nearest)
        unvisited.remove(nearest)

    cost = sum(dist[tour[i]][tour[i+1]] for i in range(n-1)) + dist[tour[-1]][tour[0]]
    return {"tour": tour, "cost": float(cost)}


# ── Baseline 2: 2-Opt Local Search ───────────────────────────────────────────

def two_opt(instance: ProblemInstance) -> Dict[str, Any]:
    """
    2-Opt Local Search TSP Heuristic.

    Starts with a Nearest Neighbor tour and improves it by iteratively
    reversing segments of the tour whenever doing so reduces total cost.
    Terminates when no improving 2-opt move exists (local optimum).

    This is the most widely used TSP improvement heuristic in practice
    and represents a significantly higher level of human expertise than NN.

    Time Complexity: O(n^2) per pass, O(n^3) worst case total.
    """
    n = instance.data["n_cities"]
    dist = instance.data["dist_matrix"]

    # Step 1: Build initial tour using Nearest Neighbor
    tour = [0]
    unvisited = set(range(1, n))
    while unvisited:
        current = tour[-1]
        nearest = min(unvisited, key=lambda c: dist[current][c])
        tour.append(nearest)
        unvisited.remove(nearest)

    def tour_cost(t):
        return sum(dist[t[i]][t[(i+1) % n]] for i in range(n))

    best_cost = tour_cost(tour)

    # Step 2: Iteratively apply 2-opt improvements
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # Calculate gain from reversing segment tour[i:j+1]
                a, b = tour[i-1], tour[i]
                c, d = tour[j], tour[(j+1) % n]
                delta = (dist[a][c] + dist[b][d]) - (dist[a][b] + dist[c][d])
                if delta < -1e-10:
                    # Apply reversal
                    tour[i:j+1] = reversed(tour[i:j+1])
                    best_cost += delta
                    improved = True
                    break
            if improved:
                break

    return {"tour": tour, "cost": float(best_cost)}


# ── Baseline 3: Greedy Edge Insertion ────────────────────────────────────────

def greedy_edge(instance: ProblemInstance) -> Dict[str, Any]:
    """
    Greedy Edge Insertion TSP Heuristic.

    Constructs a tour by sorting all possible edges by length and greedily
    adding the shortest valid edge that does not: (a) give any city degree > 2,
    or (b) create a premature subtour (cycle before all cities are included).

    This takes a fundamentally different construction approach from Nearest
    Neighbor, considering global edge costs rather than local decisions.

    Time Complexity: O(n^2 log n) for sorting + O(n^2) for construction.
    """
    n = instance.data["n_cities"]
    dist = instance.data["dist_matrix"]

    # Step 1: Generate and sort all edges by distance
    edges = []
    for i in range(n):
        for j in range(i+1, n):
            edges.append((dist[i][j], i, j))
    edges.sort(key=lambda x: x[0])

    # Step 2: Union-Find for cycle detection
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px == py:
            return False
        if rank[px] < rank[py]:
            px, py = py, px
        parent[py] = px
        if rank[px] == rank[py]:
            rank[px] += 1
        return True

    # Step 3: Greedily add edges
    degree = [0] * n
    adjacency = [[] for _ in range(n)]
    edges_added = 0

    for cost, u, v in edges:
        if edges_added == n:
            break
        # Skip if either endpoint already has degree 2
        if degree[u] >= 2 or degree[v] >= 2:
            continue
        # Skip if adding this edge creates a premature cycle
        if edges_added < n - 1 and find(u) == find(v):
            continue
        # Add edge
        union(u, v)
        adjacency[u].append(v)
        adjacency[v].append(u)
        degree[u] += 1
        degree[v] += 1
        edges_added += 1

    # Step 4: Reconstruct tour from adjacency list
    # Find a starting node (degree 1 if any, else 0)
    start = 0
    for i in range(n):
        if degree[i] == 1:
            start = i
            break

    tour = [start]
    visited = {start}
    current = start

    while len(tour) < n:
        moved = False
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                tour.append(neighbor)
                visited.add(neighbor)
                current = neighbor
                moved = True
                break
        if not moved:
            break

    # Fallback: if greedy construction fails to build valid tour, use NN
    if len(tour) != n:
        return nearest_neighbor(instance)

    cost = sum(dist[tour[i]][tour[i+1]] for i in range(n-1)) + dist[tour[-1]][tour[0]]
    return {"tour": tour, "cost": float(cost)}


# ── Evaluator ─────────────────────────────────────────────────────────────────

def evaluate_baseline(
    heuristic_fn,
    instances: List[ProblemInstance],
    name: str
) -> Dict[str, Any]:
    """
    Evaluate a single baseline heuristic across all instances.
    Returns a metrics dictionary matching the format of LLM framework results.
    """
    gaps = []
    runtimes = []
    successes = 0

    for inst in instances:
        t0 = time.time()
        try:
            result = heuristic_fn(inst)
            elapsed = time.time() - t0
            cost = result["cost"]
            gap = (cost - inst.best_known_solution) / inst.best_known_solution
            gaps.append(gap)
            runtimes.append(elapsed)
            successes += 1
        except Exception as e:
            gaps.append(1.0)
            runtimes.append(0.0)

    avg_gap = float(np.mean(gaps))
    avg_runtime = float(np.mean(runtimes))
    robustness = float(np.std(gaps))

    # Same fitness formula as LLM framework for fair comparison
    qs = float(np.exp(-avg_gap))
    ts = float(np.clip(np.exp(-avg_runtime / 10.0), 0, 1))
    rs = float(np.clip(np.exp(-robustness), 0, 1))
    fitness = 0.7 * qs + 0.2 * ts + 0.1 * rs

    return {
        "model": name,
        "best_fitness": round(fitness, 4),
        "avg_gap_pct": round(avg_gap * 100, 2),
        "avg_runtime_s": round(avg_runtime, 6),
        "successes": successes,
        "total": len(instances),
        "robustness_std": round(robustness, 4),
    }


# ── Instance Generator (identical to main framework) ─────────────────────────

def generate_tsp_instances(
    n_instances: int = 50,
    n_cities: int = 50,
    seed: int = 42
) -> List[ProblemInstance]:
    """
    Generate random Euclidean TSP instances.
    IMPORTANT: Use identical parameters (n_instances=50, n_cities=50, seed=42)
    as the main LLM experiment to ensure fair comparison on same instances.
    """
    rng = np.random.default_rng(seed)
    instances = []

    for i in range(n_instances):
        coords = rng.uniform(0, 100, size=(n_cities, 2))
        dist = np.sqrt(((coords[:, None] - coords[None, :]) ** 2).sum(-1))

        # Nearest Neighbor cost as reference baseline
        tour = [0]
        unvisited = set(range(1, n_cities))
        while unvisited:
            cur = tour[-1]
            nearest = min(unvisited, key=lambda c: dist[cur][c])
            tour.append(nearest)
            unvisited.remove(nearest)
        nn_cost = (sum(dist[tour[j]][tour[j+1]] for j in range(n_cities-1))
                   + dist[tour[-1]][tour[0]])

        instances.append(ProblemInstance(
            instance_id="tsp_" + str(n_cities) + "_" + str(i),
            data={"n_cities": n_cities, "dist_matrix": dist},
            best_known_solution=nn_cost,
        ))

    return instances


# ── Run All Baselines ─────────────────────────────────────────────────────────

def run_all_baselines(
    instances: List[ProblemInstance],
    save_path: str = "results/baseline_results.json"
) -> Dict[str, Any]:
    """
    Run all three human-designed baselines and save results.
    Output format matches LLM framework results for direct comparison.
    """
    baselines = [
        ("Nearest Neighbor",    nearest_neighbor),
        ("2-Opt Local Search",  two_opt),
        ("Greedy Edge",         greedy_edge),
    ]

    results = {}
    print("="*65)
    print("HUMAN-DESIGNED BASELINE EVALUATION")
    print("="*65)
    print(f"Instances: {len(instances)} | Cities per instance: {instances[0].data['n_cities']}")
    print("-"*65)

    for name, fn in baselines:
        print(f"Running {name}...", end=" ", flush=True)
        metrics = evaluate_baseline(fn, instances, name)
        results[name] = metrics
        print(f"fitness={metrics['best_fitness']} | gap={metrics['avg_gap_pct']}% | "
              f"runtime={metrics['avg_runtime_s']}s")

    # Save to JSON
    with open(save_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nBaseline results saved to {save_path}")

    # Print summary table
    print("\n" + "="*65)
    print("BASELINE SUMMARY TABLE")
    print("="*65)
    print(f"{'METHOD':<25} {'FITNESS':>8} {'GAP %':>8} {'RUNTIME':>10}")
    print("-"*65)
    for name, m in results.items():
        print(f"{name:<25} {m['best_fitness']:>8.4f} {m['avg_gap_pct']:>7.2f}% {m['avg_runtime_s']:>9.6f}s")
    print("="*65)

    # LaTeX table for paper
    print("\n" + "="*20 + " LATEX TABLE FOR PAPER " + "="*20)
    print(r"\begin{table}[h]")
    print(r"\centering")
    print("\caption{Human-Designed Baseline Performance on TSP-50}")
    print("\begin{tabular}{lccc}")
    print("\hline")
    print("\textbf{Method} & \textbf{Fitness} & \textbf{Avg Gap (\%)} & \textbf{Avg Runtime (s)} \\ \hline")
    for name, m in results.items():
        print(f"{name} & {m['best_fitness']} & {m['avg_gap_pct']}\% & {m['avg_runtime_s']}s \\")
    print("\hline")
    print("\end{tabular}")
    print("\label{tab:baselines}")
    print("\end{table}")
    print("="*63)

    return results


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Human-Designed Baseline Heuristics for TSP")
    print("=" * 65)
    print("Generating 50 TSP instances with 50 cities (same as LLM experiment)...")
    print()

    # IMPORTANT: Use identical parameters as main LLM experiment
    # n_instances=50, n_cities=50, seed=42 — do NOT change these
    instances = generate_tsp_instances(
        n_instances=50,
        n_cities=50,
        seed=42
    )

    results = run_all_baselines(instances, save_path="results/baseline_results.json")

    print()
    print("NEXT STEP:")
    print("  Compare baseline_results.json with results_final_run.json")
    print("  to see how LLM-generated heuristics perform vs human experts.")
    print()
    print("  LLM gap < Baseline gap = LLM beats human expert baseline!")
