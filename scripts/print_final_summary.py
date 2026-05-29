import json
import os

def main():
    # Dynamically find the project root directory whether run from root or inside a subfolder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = current_dir if os.path.exists(os.path.join(current_dir, "results")) else os.path.dirname(current_dir)

    json_path = os.path.join(project_root, "results", "results_final_run.json")
    report_path = os.path.join(project_root, "results", "final_results_report.html")
    
    if not os.path.exists(json_path):
        print(f"Results file '{json_path}' not found yet. Run the benchmarks first!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Proactively merge human baseline results if available
    baseline_path = os.path.join(project_root, "results", "baseline_results.json")
    baselines = {}
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baselines = json.load(f)
        except Exception:
            pass

    rows = []
    # 1. Load LLM evolved models
    for model_key, details in data.items():
        if not isinstance(details, dict) or "best_fitness" not in details:
            continue
        display_name = details.get("model", model_key)
        best_fit = details.get("best_fitness", 0.0)
        avg_gap = details.get("avg_gap_pct", 0.0)
        avg_rt = details.get("avg_runtime_s", 0.0)
        calls = details.get("api_calls", 0)
        best_code = details.get("best_code", "")
        rows.append((model_key, display_name, best_fit, avg_gap, avg_rt, calls, best_code))

    # 2. Load Human designed baselines
    for base_key, details in baselines.items():
        if not isinstance(details, dict) or "best_fitness" not in details:
            continue
        display_name = details.get("model", base_key)
        best_fit = details.get("best_fitness", 0.0)
        avg_gap = details.get("avg_gap_pct", 0.0)
        avg_rt = details.get("avg_runtime_s", 0.0)
        calls = 0  # 0 API calls for human-crafted solvers
        best_code = ""  # No generated code for human baselines
        rows.append((base_key.lower().replace(" ", "_"), display_name, best_fit, avg_gap, avg_rt, calls, best_code))

    # Sort rows by quality (lowest gap is best)
    rows.sort(key=lambda x: x[3])

    # Console outputs
    print("\n" + "="*85)
    print(f"{'LLM HEURISTIC OPTIMIZATION - COMPLETE FINAL BENCHMARKS':^80}")
    print("="*85)
    
    headers = f"{'MODEL / METHOD':<25} | {'BEST FITNESS':<12} | {'AVG GAP %':<12} | {'AVG RUNTIME (s)':<16} | {'API CALLS':<10}"
    print(headers)
    print("-"*85)

    for _, display_name, best_fit, avg_gap, avg_rt, calls, _ in rows:
        row_str = f"{display_name:<25} | {best_fit:<12.4f} | {avg_gap:<11.2f}% | {avg_rt:<15.3f}s | {calls:<10}"
        print(row_str)

    print("="*85)

    # LaTeX Table Console Generator
    print("\n" + "="*20 + " AUTO-LATEX TABLE FOR RESEARCH PAPER " + "="*20)
    latex = []
    latex.append(r"\begin{table}[h]")
    latex.append(r"\centering")
    latex.append(r"\caption{Performance Comparison of LLM-Heuristic Framework Across Flagship Models}")
    latex.append(r"\begin{tabular}{lcccc}")
    latex.append(r"\hline")
    latex.append(r"\textbf{Model} & \textbf{Best Fitness} & \textbf{Avg Gap (\%)} & \textbf{Avg Runtime (s)} & \textbf{API Calls} \\ \hline")
    for _, display_name, best_fit, avg_gap, avg_rt, calls, _ in rows:
        latex.append(f"{display_name} & {best_fit:.4f} & {avg_gap:.2f}\\% & {avg_rt:.3f}s & {calls} \\\\")
    latex.append(r"\hline")
    latex.append(r"\end{tabular}")
    latex.append(r"\label{tab:llm_heuristic_results}")
    latex.append(r"\end{table}")
    latex_str = "\n".join(latex)
    print(latex_str)
    print("="*77 + "\n")

    # Extract Champion heuristic (must contain evolved Python code)
    champion_model = max([r for r in rows if r[6]], key=lambda x: x[3] * -1.0)
    champ_name = champion_model[1]
    champ_code = champion_model[6].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Generate Metrics Cards HTML (No Emojis)
    cards_html = ""
    for model_key, display_name, best_fit, avg_gap, avg_rt, calls, _ in rows:
        badge_cls = "gap-winner" if avg_gap <= -12.0 else ("gap-runner" if avg_gap <= -5.0 else "gap-normal")
        cards_html += f"""
            <div class="metric-card">
                <div class="card-header">
                    <span class="model-title">{display_name}</span>
                    <span class="gap-badge {badge_cls}">{avg_gap:.2f}% Gap</span>
                </div>
                <div class="metric-val">{best_fit:.4f}</div>
                <div class="sub-metrics">
                    <span>Runtime: {avg_rt:.3f}s</span>
                    <span>API Calls: {calls}</span>
                </div>
            </div>"""

    # Generate Table Rows HTML
    table_rows_html = ""
    for _, display_name, best_fit, avg_gap, avg_rt, calls, _ in rows:
        table_rows_html += f"""
                        <tr>
                            <td style="font-weight: 600;">{display_name}</td>
                            <td style="font-family: 'JetBrains Mono', monospace;">{best_fit:.4f}</td>
                            <td class="table-gap-cell" style="font-family: 'JetBrains Mono', monospace; font-weight: 700;">{avg_gap:.2f}%</td>
                            <td style="font-family: 'JetBrains Mono', monospace;">{avg_rt:.3f}s</td>
                            <td style="font-family: 'JetBrains Mono', monospace;">{calls}</td>
                        </tr>"""

    # Collect lists for Chart.js
    chart_labels = [row[1] for row in rows]
    chart_gaps = [abs(row[3]) for row in rows] # Absolute gap percentages
    chart_runtimes = [row[4] for row in rows]   # Average runtimes
    chart_calls = [row[5] for row in rows]      # API calls

    # Pure HTML/CSS Base Template (Zero double-curly braces required!)
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM-Heuristic Optimization - Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --accent-grad: linear-gradient(135deg, #2563eb 0%, #059669 100%);
            --glow-color: rgba(37, 99, 235, 0.05);
            --neon-green: #047857;
            --neon-blue: #1d4ed8;
            --neon-yellow: #b45309;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --border-color: rgba(0, 0, 0, 0.06);
            --shadow-color: rgba(0, 0, 0, 0.03);
            --code-bg: #f8fafc;
            --code-text: #0f172a;
            --latex-box-bg: #f8fafc;
            --latex-box-border: rgba(147, 51, 234, 0.15);
            --latex-box-text: #6b21a8;
            --th-border: rgba(0, 0, 0, 0.08);
            --tr-hover: rgba(0, 0, 0, 0.015);
            --table-gap-color: #047857;
        }

        body.dark-mode {
            --bg-color: #0b0f19;
            --card-bg: #151e2e;
            --accent-grad: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
            --glow-color: rgba(59, 130, 246, 0.15);
            --neon-green: #10b981;
            --neon-blue: #3b82f6;
            --neon-yellow: #f59e0b;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --border-color: rgba(255, 255, 255, 0.05);
            --shadow-color: rgba(0, 0, 0, 0.3);
            --code-bg: #080c14;
            --code-text: #38bdf8;
            --latex-box-bg: #080c14;
            --latex-box-border: rgba(168, 85, 247, 0.2);
            --latex-box-text: #a855f7;
            --th-border: rgba(255, 255, 255, 0.1);
            --tr-hover: rgba(255, 255, 255, 0.02);
            --table-gap-color: #10b981;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            padding: 2rem;
            min-height: 100vh;
            transition: background-color 0.3s ease, color 0.3s ease;
            background-image: radial-gradient(circle at 10% 20%, rgba(37, 99, 235, 0.04) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(5, 150, 105, 0.04) 0%, transparent 40%);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Top Controls */
        .top-controls {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 1rem;
        }

        .theme-toggle-btn {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            border-radius: 12px;
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 10px var(--shadow-color);
            transition: all 0.2s ease;
        }

        .theme-toggle-btn:hover {
            transform: scale(1.03);
            border-color: var(--neon-blue);
        }

        header {
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }

        .badge {
            display: inline-block;
            background: var(--accent-grad);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.2);
        }

        h1 {
            font-size: 2.7rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, var(--text-main), var(--text-muted));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        header p {
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .metric-card {
            background-color: var(--card-bg);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px var(--shadow-color);
            transition: transform 0.3s ease, border-color 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: var(--accent-grad);
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            border-color: rgba(37, 99, 235, 0.25);
        }

        .metric-card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .model-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-main);
        }

        .gap-badge {
            font-size: 0.9rem;
            font-weight: 700;
            padding: 0.25rem 0.6rem;
            border-radius: 8px;
        }

        .gap-winner {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--neon-green);
            border: 1px solid rgba(16, 185, 129, 0.25);
        }

        .gap-runner {
            background-color: rgba(59, 130, 246, 0.1);
            color: var(--neon-blue);
            border: 1px solid rgba(59, 130, 246, 0.25);
        }

        .gap-normal {
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--neon-yellow);
            border: 1px solid rgba(245, 158, 11, 0.25);
        }

        .metric-val {
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 1rem;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-main);
        }

        .sub-metrics {
            display: flex;
            justify-content: space-between;
            border-top: 1px solid var(--border-color);
            padding-top: 0.75rem;
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        /* Dual Column Chart Grid */
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }

        @media (max-width: 900px) {
            .chart-grid {
                grid-template-columns: 1fr;
            }
        }

        .chart-panel {
            background-color: var(--card-bg);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px var(--shadow-color);
        }

        /* Table & code split section */
        .content-split {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 2rem;
            margin-bottom: 3rem;
        }

        @media (max-width: 900px) {
            .content-split {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background-color: var(--card-bg);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px var(--shadow-color);
            position: relative;
        }

        .panel-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--text-main);
        }

        .panel-title-text {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .copy-btn {
            background-color: rgba(37, 99, 235, 0.08);
            border: 1px solid rgba(37, 99, 235, 0.2);
            color: var(--neon-blue);
            padding: 0.35rem 0.75rem;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .copy-btn:hover {
            background-color: var(--neon-blue);
            color: white;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            color: var(--text-muted);
            font-weight: 600;
            padding: 1rem;
            border-bottom: 1px solid var(--th-border);
            font-size: 0.9rem;
        }

        td {
            padding: 1.2rem 1rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.95rem;
        }

        tr:hover td {
            background-color: var(--tr-hover);
        }

        .table-gap-cell {
            color: var(--table-gap-color);
        }

        .code-container {
            position: relative;
        }

        pre {
            background-color: var(--code-bg);
            padding: 1.2rem;
            border-radius: 12px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            max-height: 480px;
            color: var(--code-text);
        }

        /* Latex panel */
        .latex-panel {
            background-color: var(--card-bg);
            border-radius: 20px;
            padding: 2rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px var(--shadow-color);
            margin-top: 2rem;
        }

        .latex-box {
            background-color: var(--latex-box-bg);
            padding: 1.5rem;
            border-radius: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            line-height: 1.6;
            color: var(--latex-box-text);
            overflow-x: auto;
            white-space: pre;
            border: 1px solid var(--latex-box-border);
        }

        /* Explainer Accordion (No Emojis) */
        .explainer-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .explainer-card {
            background: rgba(37, 99, 235, 0.03);
            border: 1px dashed rgba(37, 99, 235, 0.15);
            border-radius: 10px;
            padding: 1rem;
        }

        .explainer-card h4 {
            font-size: 0.95rem;
            color: var(--neon-blue);
            margin-bottom: 0.4rem;
        }

        .explainer-card p {
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* Toast message */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--accent-grad);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.9rem;
            box-shadow: 0 10px 25px rgba(37, 99, 235, 0.4);
            transform: translateY(150%);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .toast.show {
            transform: translateY(0);
        }

        footer {
            text-align: center;
            padding: 3rem 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <!-- Floating Toast Notification -->
    <div id="toast" class="toast">Block Copied to Clipboard!</div>

    <div class="container">
        <!-- Top controls for Light/Dark Mode -->
        <div class="top-controls">
            <button id="themeToggle" class="theme-toggle-btn">
                <span id="themeText">Dark Mode</span>
            </button>
        </div>

        <header>
            <div class="badge">Experimental Results</div>
            <h1>LLM-Heuristic: Automated Design Dashboard</h1>
            <p>High-fidelity final evaluations of evolved meta-heuristics on academic TSP benchmarks (50 Cities, 50 Instances)</p>
        </header>

        <!-- Metric cards -->
        <div class="metrics-grid">
            __METRIC_CARDS__
        </div>

        <!-- Dual Column Chart section -->
        <div class="chart-grid">
            <!-- Gap Chart Panel -->
            <div class="chart-panel">
                <div class="panel-title" style="margin-bottom: 1rem; font-size: 1.25rem;">Optimality Gap Reduction (%)</div>
                <div style="position: relative; height:240px; width:100%">
                    <canvas id="gapChart"></canvas>
                </div>
            </div>
            
            <!-- Latency / API Chart Panel -->
            <div class="chart-panel">
                <div class="panel-title" style="margin-bottom: 1rem; font-size: 1.25rem;">Computation Latency (s) & API Costs</div>
                <div style="position: relative; height:240px; width:100%">
                    <canvas id="efficiencyChart"></canvas>
                </div>
            </div>
        </div>

        <div class="content-split">
            <!-- Table Panel -->
            <div class="panel">
                <div class="panel-title">Comparative Benchmarks Summary</div>
                <table>
                    <thead>
                        <tr>
                            <th>Model</th>
                            <th>Best Fitness</th>
                            <th>Avg Gap (%)</th>
                            <th>Runtime (s)</th>
                            <th>API Calls</th>
                        </tr>
                    </thead>
                    <tbody>
                        __TABLE_ROWS__
                    </tbody>
                </table>
            </div>

            <!-- Code Panel -->
            <div class="panel">
                <div class="panel-title">
                    <div class="panel-title-text">Champion Heuristic (__CHAMP_NAME__)</div>
                    <button class="copy-btn" onclick="copyChampionCode()">Copy Code</button>
                </div>
                <div class="code-container">
                    <pre><code id="champCode">__CHAMP_CODE__</code></pre>
                </div>
                <div class="explainer-cards">
                    <div class="explainer-card">
                        <h4>Greedy Start</h4>
                        <p>Constructs initial deterministic baseline tour via robust Nearest Neighbor solver.</p>
                    </div>
                    <div class="explainer-card">
                        <h4>2-Opt Loop</h4>
                        <p>Applies local edge-swaps to untangle crossing paths and reach local minima.</p>
                    </div>
                    <div class="explainer-card">
                        <h4>Multi-Restart</h4>
                        <p>Triggers constrained restart runs to dynamically escape local bounds.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- LaTeX Exporter -->
        <div class="latex-panel">
            <div class="panel-title">
                <div class="panel-title-text">Academic LaTeX Table Code</div>
                <button class="copy-btn" onclick="copyLatexCode()">Copy LaTeX</button>
            </div>
            <div class="latex-box" id="latexCode">__LATEX_TABLE__</div>
        </div>

        <footer>
            <p>LLM-Heuristic Framework • ICETICS 2026 Academic Publication</p>
        </footer>
    </div>

    <!-- Interactive Logic Block -->
    <script>
        // Data populated from python
        const labels = __CHART_LABELS__;
        const gaps = __CHART_GAPS__;
        const runtimes = __CHART_RUNTIMES__;
        const apiCalls = __CHART_CALLS__;

        // Render gorgeous bar chart (Optimality Gaps)
        const ctx = document.getElementById('gapChart').getContext('2d');
        const gapChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Optimality Gap Reduction (%)',
                    data: gaps,
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(59, 130, 246, 0.85)',
                        'rgba(99, 102, 241, 0.85)',
                        'rgba(245, 158, 11, 0.85)'
                    ],
                    borderColor: [
                        '#10b981',
                        '#3b82f6',
                        '#6366f1',
                        '#f59e0b'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Cost Reduction (%)',
                            font: {
                                family: 'Outfit',
                                weight: 'bold'
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

        // Render Latency & API efficiency chart
        const ctx2 = document.getElementById('efficiencyChart').getContext('2d');
        const efficiencyChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'bar',
                        label: 'Average Runtime (s)',
                        data: runtimes,
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderColor: '#3b82f6',
                        borderWidth: 1.5,
                        borderRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        type: 'line',
                        label: 'API Calls',
                        data: apiCalls,
                        borderColor: '#10b981',
                        backgroundColor: '#10b981',
                        borderWidth: 3,
                        pointBackgroundColor: '#10b981',
                        pointRadius: 4,
                        yAxisID: 'y1',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Runtime (Seconds)',
                            font: { family: 'Outfit', weight: 'bold' }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Total API Requests',
                            font: { family: 'Outfit', weight: 'bold' }
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });

        // Theme Toggle Handler
        const themeBtn = document.getElementById('themeToggle');
        const body = document.body;
        const themeText = document.getElementById('themeText');

        themeBtn.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            themeText.innerText = isDark ? 'Light Mode' : 'Dark Mode';
            
            // Adjust chart scales grid colors on theme change
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.05)';
            const fontColor = isDark ? '#9ca3af' : '#64748b';

            // Update Chart 1
            gapChart.options.scales.y.grid.color = gridColor;
            gapChart.options.scales.y.ticks.color = fontColor;
            gapChart.options.scales.x.ticks.color = fontColor;
            gapChart.update();

            // Update Chart 2
            efficiencyChart.options.scales.y.grid.color = gridColor;
            efficiencyChart.options.scales.y.ticks.color = fontColor;
            efficiencyChart.options.scales.y1.ticks.color = fontColor;
            efficiencyChart.options.scales.x.ticks.color = fontColor;
            efficiencyChart.update();
        });

        // Copy functions & toast notifications
        function showToast(message) {
            const toast = document.getElementById('toast');
            toast.innerText = message;
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2500);
        }

        function copyChampionCode() {
            const code = document.getElementById('champCode').innerText;
            navigator.clipboard.writeText(code);
            showToast('Champion Heuristic Copied!');
        }

        function copyLatexCode() {
            const latex = document.getElementById('latexCode').innerText;
            navigator.clipboard.writeText(latex);
            showToast('LaTeX Table Code Copied!');
        }
    </script>
</body>
</html>
"""

    # Clean string replacement strategy
    final_html = html_template.replace("__METRIC_CARDS__", cards_html)
    final_html = final_html.replace("__TABLE_ROWS__", table_rows_html)
    final_html = final_html.replace("__CHAMP_NAME__", champ_name)
    final_html = final_html.replace("__CHAMP_CODE__", champ_code)
    
    latex_escaped = latex_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    final_html = final_html.replace("__LATEX_TABLE__", latex_escaped)

    # Inject dynamic chart datasets
    final_html = final_html.replace("__CHART_LABELS__", json.dumps(chart_labels))
    final_html = final_html.replace("__CHART_GAPS__", json.dumps(chart_gaps))
    final_html = final_html.replace("__CHART_RUNTIMES__", json.dumps(chart_runtimes))
    final_html = final_html.replace("__CHART_CALLS__", json.dumps(chart_calls))

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"SUCCESS! The dashboard is now highly enhanced and fully interactive:")
    print(f"Dashboard Location: {report_path}")
    print(f"Features: Dynamic Dark/Light Theme toggle, dual-column charts, active copy-buttons, and explainer blocks! 🚀📊")

if __name__ == "__main__":
    main()
