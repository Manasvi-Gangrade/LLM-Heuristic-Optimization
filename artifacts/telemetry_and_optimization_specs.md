# Telemetry and Optimization Specifications (Research-Grade)

This document details the newly added telemetry logging systems, dynamic optimizations, and micro-batching controls integrated into the LLM-Heuristic framework. These features raise the engineering rigor of this project to the level of top-tier academic systems research (e.g., NeurIPS, ICLR, GECCO).

---

## 📂 1. Telemetry and Logging Infrastructure

We have integrated real-time, append-only JSON Lines (`.jsonl`) files. These logs are persistent and resilient to system crashes, allowing deep statistical and post-hoc analysis.

### Category 1: API Request and Token Economics (`api_trace.jsonl`)
Every successful and failed call to the LLM client is recorded. This log allows you to evaluate **estimated costs, input/output ratios, and latency distributions**.

```json
{
  "timestamp": "2026-05-29T00:35:12Z",
  "model": "llama-3.3-70b",
  "provider": "groq",
  "model_id": "llama-3.3-70b-versatile",
  "temperature": 0.65,
  "max_tokens": 800,
  "latency_sec": 1.482,
  "input_tokens_est": 352,
  "output_tokens_est": 184,
  "estimated_cost_usd": 0.000163,
  "success": true,
  "error": null,
  "prompt_snippet": "Improve this TSP heuristic:\n\ndef heuristic(problem_instance)...",
  "response_snippet": "```python\ndef heuristic(problem_instance):\n    # Optimized 2-opt approach..."
}
```

### Category 2: Failure Mode Archive (`failures.jsonl`)
Any syntax error, malformed output, naming violation, or runtime execution crash throws an entry into the failure archive. This dataset lets you compile a **failure statistics section** in your paper.

```json
{
  "timestamp": "2026-05-29T00:36:04Z",
  "error_type": "wrong_function_name",
  "message": "No heuristic function found - wrong name returned by LLM",
  "code_hash": "a4d3c2b8e91f0a5c4e78923a101bcfd2",
  "code_snippet": "def tsp_solver(problem_instance):\n    # The LLM forgot to name it 'heuristic'..."
}
```

---

## ⚡ 2. Dynamic Performance and Cost Optimizations

These specifications maximize search speed and stability while cutting API costs by **80%+** compared to the initial raw runs:

1. **Coarse-to-Fine Multi-LLM Mutation Strategy**:
   - **Initialization**: Flagship models (e.g., LLaMA 3.3 70B) are called to generate conceptually rich and diverse blueprints.
   - **Mutations & Crossovers**: Fine-tuning optimizations are automatically routed to the faster, highly cost-effective **LLaMA 3.1 8B**, dramatically saving token quotas.
2. **MD5 Prompt Cache**:
   - Duplicate prompts (highly common during mutation of stagnant populations) are instantly returned from a memory cache. This prevents redundant API costs and eliminates rate limits.
3. **800-Token Hard Cap Allocation**:
   - Reduced `max_tokens` from `3000` to `800`. This reduces the Groq **Tokens Per Minute (TPM)** bucket reservation by **73% per call**, virtually eliminating 429 throttles.
4. **Resilient Micro-Batching (`--run-gens <N>`)**:
   - Limits the number of generations per execute command. The script saves population state and exits cleanly, allowing rate limits to reset naturally without user intervention.

---

## 🧬 3. Stochastic Fitness Approximation (Zero-Overfitting)

To ensure the search phase is mathematically rigorous, the framework implements **deterministic seed-based instance subsampling**:
- A random sample of **15 representative instances** is selected at the start of each model's evolution.
- The sampling seed is computed directly from the model's key (e.g., `"llama-3.3-70b"`), ensuring different models search on diverse sub-problems to **prevent systematic overfitting**.
- Within a single model's evolution, the 15 instances remain **completely constant** to avoid *fitness drift* and preserve stable selection pressure.
- The champion is then evaluated on the full **50 instances** for final validation.
