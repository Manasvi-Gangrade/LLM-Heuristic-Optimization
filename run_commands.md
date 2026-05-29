# 🚀 LLM Heuristic Optimization - Command Cheat Sheet

This cheat sheet provides copy-paste ready commands for executing benchmarks, resuming evolutions, generating LaTeX tables, and maintaining a clean workspace structure.

---

## 🛠️ 1. Active Virtual Environment
Before running any script, make sure your virtual environment is active in your terminal:
```powershell
# In PowerShell (Windows)
venv\Scripts\activate
```

---

## 🏆 2. Academic Production & Final Sweeps
Use these commands to run heavy academic-grade sweeps (50 instances, 50 cities each) for your research paper:

```bash
# Run the complete multi-model sequential final evaluation sweep
python llm_heuristic_framework.py --mode final --model all --run-gens 2
```

---

## ⏸️ 3. Micro-Batched Runs (Recommended for Rate Limits)
Highly recommended to avoid token limits. Execute a clean batch of 2 generations, let the server cool down, and run it again to resume seamlessly from the checkpoint!

```bash
# Run exactly 2 generations of LLaMA 3.3 70B and exit cleanly with checkpoint
python llm_heuristic_framework.py --mode final --model llama-3.3-70b --run-gens 2

# Resume LLaMA 3.3 70B from checkpoint for another 2 generations
python llm_heuristic_framework.py --mode final --model llama-3.3-70b --run-gens 2
```

---

## 📊 4. Offline Evaluation & Post-Processing
No need to re-run heavy evolutions to recreate charts or print LaTeX tables. Use these instant utilities:

```bash
# Print comparison tables and LaTeX code for paper on demand
python print_final_summary.py

# Regenerate comparison plot comparison_final_run.png from results_final_run.json
python -c "from llm_heuristic_framework import LLMHeuristicExperiment; exp = LLMHeuristicExperiment([], []); exp.plot_comparison('results/comparison_final_run.png', 'results/results_final_run.json')"
```

---

## 🧹 5. Workspace Cleaning Utility
Keep your workspace clean, move completed outputs to dedicated folders, and remove temporary run elements:

```bash
# Execute the comprehensive cleanup script
python cleanup_workspace.py
```
This utility organizes your workspace into:
- **`results/`**: For finalized logs, JSON data, and visual performance charts.
- **`artifacts/`**: For paper drafts, telemetry specifications, and submission packages.
