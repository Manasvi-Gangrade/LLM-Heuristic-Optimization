import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import os
import time
import json
import signal
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field

import google.generativeai as genai
from groq import Groq
from openai import OpenAI

MODELS = {
    "llama-3.3-70b": {"provider": "groq", "model_id": "llama-3.3-70b-versatile", "display_name": "LLaMA 3.3 70B", "max_tokens": 800},
    "llama-3.1-8b": {"provider": "groq", "model_id": "llama-3.1-8b-instant", "display_name": "LLaMA 3.1 8B", "max_tokens": 800},
    "llama-4-scout": {"provider": "groq", "model_id": "meta-llama/llama-4-scout-17b-16e-instruct", "display_name": "LLaMA 4 Scout", "max_tokens": 1200},
    "gpt-oss-120b": {"provider": "groq", "model_id": "openai/gpt-oss-120b", "display_name": "GPT-OSS 120B", "max_tokens": 2000},
}

@dataclass
class HeuristicCandidate:
    code: str
    fitness: float
    quality_score: float
    runtime: float
    robustness: float
    generation: int
    model_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    candidate_id: str = ""
    parent_ids: List[str] = field(default_factory=list)
    operation: str = "initial"

    def __post_init__(self):
        if not self.candidate_id and self.code:
            import hashlib
            self.candidate_id = hashlib.md5(self.code.encode("utf-8")).hexdigest()

def serialize_candidate(c):
    return {
        "code": c.code,
        "fitness": c.fitness,
        "quality_score": c.quality_score,
        "runtime": c.runtime,
        "robustness": c.robustness,
        "generation": c.generation,
        "model_name": c.model_name,
        "metadata": c.metadata,
        "candidate_id": c.candidate_id,
        "parent_ids": c.parent_ids,
        "operation": c.operation
    }

def deserialize_candidate(d):
    return HeuristicCandidate(
        code=d["code"],
        fitness=d["fitness"],
        quality_score=d["quality_score"],
        runtime=d["runtime"],
        robustness=d["robustness"],
        generation=d["generation"],
        model_name=d["model_name"],
        metadata=d["metadata"],
        candidate_id=d.get("candidate_id", ""),
        parent_ids=d.get("parent_ids", []),
        operation=d.get("operation", "initial")
    )

def strip_comments_and_docstrings(code):
    import re
    # Remove docstrings
    code = re.sub(r'\"\"\"[\s\S]*?\"\"\"', '', code)
    code = re.sub(r"\'\'\'[\s\S]*?\'\'\'", '', code)
    # Remove single line comments and blank lines
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "#" in line:
            parts = line.split("#", 1)
            line = parts[0]
        lines.append(line.rstrip())
    return "\n".join([line for line in lines if line.strip()])

def characterize_heuristic(code):
    if not code:
        return {}
    lines = [line.strip() for line in code.split("\n") if line.strip()]
    loc = len(lines)
    
    num_loops = sum(1 for line in lines if line.startswith("for ") or line.startswith("while "))
    
    code_lower = code.lower()
    has_2opt = int("2-opt" in code_lower or "2opt" in code_lower or "two_opt" in code_lower)
    has_greedy = int("greedy" in code_lower or "nearest" in code_lower or "shortest" in code_lower)
    has_random = int("random" in code_lower or "np.random" in code_lower or "shuffle" in code_lower)
    has_savings = int("savings" in code_lower or "clarke" in code_lower)
    
    return {
        "loc": loc,
        "num_loops": num_loops,
        "strategy_2opt": has_2opt,
        "strategy_greedy": has_greedy,
        "strategy_random": has_random,
        "strategy_savings": has_savings
    }

def get_system_info():
    import platform
    import sys
    import multiprocessing
    import time
    
    cpu = platform.processor() or "Unknown"
    git_commit = "unknown"
    try:
        import subprocess
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
        
    return {
        "python_version": sys.version.split()[0],
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu,
        "cores": multiprocessing.cpu_count(),
        "git_commit": git_commit,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@dataclass
class ProblemInstance:
    instance_id: str
    data: Dict[str, Any]
    best_known_solution: float

@dataclass
class ExperimentResult:
    model_name: str
    best_fitness_history: List[float]
    best_candidate: Optional[HeuristicCandidate]
    avg_gap: float
    avg_runtime: float
    total_api_calls: int
    metrics_history: List[Dict[str, Any]] = field(default_factory=list)

def _eval_worker(fn_code, data_dict, queue):
    """Worker function for multiprocessing execution. Placed at top-level for Windows pickle compatibility."""
    try:
        import numpy as np
        import random
        import math
        from typing import List, Dict, Any, Tuple, Optional
        
        exec_globals = {
            "np": np,
            "random": random,
            "math": math,
            "List": List,
            "Dict": Dict,
            "Any": Any,
            "Tuple": Tuple,
            "Optional": Optional
        }
        
        # Execute code in clean namespace
        exec(fn_code, exec_globals)
        heuristic_fn = exec_globals.get("heuristic")
        if heuristic_fn is None:
            queue.put((None, "No heuristic function found in child process"))
            return
            
        res = heuristic_fn(data_dict)
        queue.put((res, None))
    except Exception as e:
        queue.put((None, str(e)))

TSP_DESCRIPTION = """
Traveling Salesman Problem (TSP)

Objective: Find shortest route visiting each city exactly once and returning to start.

Input format:
    problem_instance = {
        "n_cities": int,
        "dist_matrix": 2D numpy array of shape (n_cities, n_cities)
    }

IMPORTANT: Your function MUST be named EXACTLY "heuristic" (lowercase).
Return format: {"tour": [list of city indices], "cost": float}

Example (Nearest Neighbor baseline — try to beat this):
    def heuristic(problem_instance):
        n = problem_instance["n_cities"]
        dist = problem_instance["dist_matrix"]
        tour = [0]
        unvisited = set(range(1, n))
        while unvisited:
            current = tour[-1]
            nearest = min(unvisited, key=lambda c: dist[current][c])
            tour.append(nearest)
            unvisited.remove(nearest)
        cost = sum(dist[tour[i]][tour[i+1]] for i in range(n-1)) + dist[tour[-1]][tour[0]]
        return {"tour": tour, "cost": cost}

Try creative approaches: 2-opt local search, greedy insertion, savings algorithm, etc.
"""

class LLMClient:
    def __init__(self):
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self._gemini_ready = True
        else:
            print("WARNING: GEMINI_API_KEY not set")
            self._gemini_ready = False

        groq_key = os.environ.get("GROQ_API_KEY")
        if groq_key:
            self._groq = Groq(api_key=groq_key)
            self._groq_ready = True
        else:
            print("WARNING: GROQ_API_KEY not set")
            self._groq_ready = False

        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            self._openrouter = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
            self._openrouter_ready = True
        else:
            print("WARNING: OPENROUTER_API_KEY not set")
            self._openrouter_ready = False
        
        self._cache = {}
        self._trace_file = "api_trace.jsonl"

    def _countdown_sleep(self, seconds):
        for i in range(seconds, 0, -1):
            print(f"\r  Waiting... {i}s remaining", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 40 + "\r", end="", flush=True)

    def generate(self, model_key, prompt, temperature=0.8, max_tokens=None):
        config = MODELS[model_key]
        p = config["provider"]
        m = config["model_id"]
        
        if max_tokens is None:
            max_tokens = config.get("max_tokens", 800)
        
        cache_key = (model_key, prompt)
        if cache_key in self._cache:
            print(f"\n      ⚡ [Cache Hit] Reused previous cached LLM response for {model_key}!")
            return self._cache[cache_key]
            
        t0 = time.time()
        success = False
        response_raw = ""
        error_msg = None
        
        try:
            if p == "gemini":
                response_raw = self._gemini(m, prompt, temperature, max_tokens)
            elif p == "groq":
                response_raw = self._groq_call(m, prompt, temperature, max_tokens)
            elif p == "openrouter":
                response_raw = self._openrouter_call(m, prompt, temperature, max_tokens)
            success = True
            self._cache[cache_key] = response_raw
            return response_raw
        except Exception as e:
            error_msg = str(e)
            raise
        finally:
            latency = time.time() - t0
            in_tokens = len(prompt) // 4
            out_tokens = len(response_raw) // 4 if response_raw else 0
            # Track estimated cost ($0.15/1M input, $0.60/1M output for general models)
            est_cost = (in_tokens * 0.15 + out_tokens * 0.60) / 1_000_000
            
            trace_payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "model": model_key,
                "provider": p,
                "model_id": m,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "latency_sec": round(latency, 3),
                "input_tokens_est": in_tokens,
                "output_tokens_est": out_tokens,
                "estimated_cost_usd": round(est_cost, 6),
                "success": success,
                "error": error_msg,
                "full_prompt": prompt,
                "full_response": response_raw,
                "prompt_snippet": prompt[:300] + "..." if len(prompt) > 300 else prompt,
                "response_snippet": response_raw[:300] + "..." if len(response_raw) > 300 else response_raw
            }
            try:
                with open(self._trace_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(trace_payload) + "\n")
            except Exception as le:
                print(f"⚠️ Failed to write to api_trace: {le}")

    def _gemini(self, model_id, prompt, temperature, max_tokens):
        if not self._gemini_ready:
            raise RuntimeError("Gemini API key not configured")
        for attempt in range(5):
            try:
                model = genai.GenerativeModel(
                    model_id,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature, max_output_tokens=max_tokens),
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                    ])
                return model.generate_content(prompt, request_options={"timeout": 45.0}).text
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower() or "limit" in err.lower():
                    wait = 65 * (attempt + 1)
                    print("\n  Gemini rate limit/error - cooling down...")
                    self._countdown_sleep(wait)
                elif "timeout" in err.lower() or "deadline" in err.lower():
                    wait = 15 * (attempt + 1)
                    print("\n  Gemini timeout - retrying in...")
                    self._countdown_sleep(wait)
                else:
                    raise
        raise RuntimeError("Gemini exceeded retries")

    def _groq_call(self, model_id, prompt, temperature, max_tokens):
        if not self._groq_ready:
            raise RuntimeError("Groq API key not configured")
        temperature = min(temperature, 1.0)
        for attempt in range(10):
            try:
                r = self._groq.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature, max_tokens=max_tokens,
                    timeout=45.0)
                content = r.choices[0].message.content
                print(f"\n      [DEBUG RAW RESPONSE] First 150 chars of {model_id} output: {content[:150]!r}")
                time.sleep(5.0)  # Throttling delay to perfectly stay under Groq's 15 RPM limit
                return content
            except Exception as e:
                err = str(e)
                if "rate_limit" in err.lower() or "429" in err or "limit" in err.lower():
                    if "daily" in err.lower() or "quota" in err.lower():
                        print("\n  Groq Daily Limit/Quota reached! Skipping retry instantly to save laptop from heating...")
                        raise RuntimeError("Groq daily quota limit reached")
                    wait = 65  # Reset window duration for Groq (RPM/TPM bucket resets at 60s)
                    print(f"\n  [Groq Rate Limit Bucket Full] Waiting exactly {wait}s for window reset (Attempt {attempt+1}/10)...")
                    for remaining in range(wait, 0, -5):
                        print(f"    Cooldown: {remaining}s remaining...", end="\r", flush=True)
                        time.sleep(min(remaining, 5))
                    print("    Cooldown complete! Retrying request...")
                elif "timeout" in err.lower() or "connection" in err.lower():
                    wait = 15 * (attempt + 1)
                    print("\n  Groq timeout/connection error - retrying in " + str(wait) + "s...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Groq exceeded retries")

    def _openrouter_call(self, model_id, prompt, temperature, max_tokens):
        if not self._openrouter_ready:
            raise RuntimeError("OpenRouter API key not configured")
        
        import requests
        import json
        
        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        current_model = model_id
        
        for attempt in range(5):
            payload = {
                "model": current_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=15.0
                )
                if r.status_code == 200:
                    res_json = r.json()
                    
                    # 1. Check if OpenRouter returned an error inside status 200 response
                    if "error" in res_json:
                        err_msg = res_json["error"].get("message", "Unknown OpenRouter Error")
                        print(f"\n  OpenRouter API Error inside 200: {err_msg}")
                        if current_model != "openrouter/free":
                            print("  >> Defensive Fallback Triggered: Routing to 'openrouter/free'...")
                            current_model = "openrouter/free"
                            continue
                        raise RuntimeError(f"OpenRouter Error: {err_msg}")
                        
                    # 2. Check if choices is present and not empty
                    choices = res_json.get("choices")
                    if choices and len(choices) > 0:
                        content = choices[0].get("message", {}).get("content")
                        if content is not None:
                            time.sleep(1.5)  # Throttling cooldown to prevent OpenRouter 429 spike
                            return str(content)
                            
                    # 3. If we got empty or invalid JSON, retry/fallback
                    if current_model != "openrouter/free":
                        print("\n  OpenRouter returned invalid JSON structure. Retrying with fallback...")
                        current_model = "openrouter/free"
                        continue
                    raise RuntimeError(f"OpenRouter invalid JSON: {res_json}")
                    
                elif r.status_code == 404 and current_model != "openrouter/free":
                    print(f"\n  OpenRouter model '{current_model}' returned 404 (Not Found).")
                    print("  >> Defensive Fallback Triggered: Routing to 'openrouter/free'...")
                    current_model = "openrouter/free"
                    continue
                else:
                    err_msg = r.text
                    print(f"\n  OpenRouter API Error (Status {r.status_code}): {err_msg}")
                    # If model is not found or endpoint is not active, trigger fallback immediately
                    if (r.status_code == 400 or "endpoint" in err_msg.lower() or "model" in err_msg.lower()) and current_model != "openrouter/free":
                        print("  >> Defensive Fallback Triggered: Routing to 'openrouter/free'...")
                        current_model = "openrouter/free"
                        continue
                        
                    if r.status_code in [429, 500, 502, 503, 504]:
                        wait = 30 * (attempt + 1)
                        print(f"  Waiting {wait}s before retry...")
                        self._countdown_sleep(wait)
                    else:
                        raise RuntimeError(f"OpenRouter returned status {r.status_code}: {err_msg}")
            except Exception as e:
                err = str(e)
                if "timeout" in err.lower() or "connection" in err.lower():
                    wait = 15 * (attempt + 1)
                    print(f"\n  OpenRouter timeout/connection error - retrying...")
                    self._countdown_sleep(wait)
                else:
                    raise
        raise RuntimeError("OpenRouter exceeded retries")

class HeuristicGenerator:
    def __init__(self, client, model_key):
        self.client = client
        self.model_key = model_key
        # Route mutations and crossovers to smaller models to save massive tokens/TPM
        mutation_models = {
            "llama-3.3-70b": "llama-3.1-8b",
            "llama-3.1-8b": "llama-3.1-8b",
            "llama-4-scout": "llama-3.1-8b",
            "gpt-oss-120b": "llama-3.1-8b"
        }
        self.mutation_model_key = mutation_models.get(model_key, model_key)
        self.api_calls = 0

    def _extract(self, raw):
        if raw is None or not isinstance(raw, str):
            return ""
        import re
        
        # Strip closed <think>...</think> blocks
        raw_cleaned = re.sub(r'<think>[\s\S]*?</think>', '', raw)
        # Strip unclosed <think>... blocks (occurs on context truncation)
        raw_cleaned = re.sub(r'<think>[\s\S]*', '', raw_cleaned)
        
        # Try to find code between ```python and ```
        m = re.search(r'```python\s*([\s\S]*?)\s*```', raw_cleaned)
        if m:
            return m.group(1).strip()
        # Try to find code between ``` and ```
        m = re.search(r'```\s*([\s\S]*?)\s*```', raw_cleaned)
        if m:
            return m.group(1).strip()
        # Fallback: find the first def heuristic or def function definition and extract until end
        m = re.search(r'(def\s+\w+\s*\(problem_instance\)[\s\S]*)', raw_cleaned)
        if m:
            code = m.group(1)
            if "```" in code:
                code = code.split("```")[0]
            return code.strip()
        return raw_cleaned.strip()

    def _ensure_name(self, code):
        # Robust regex to match def <any_name>(problem_instance...) and change <any_name> to heuristic
        import re
        code = re.sub(r'def\s+\w+\s*\(\s*problem_instance[\s\S]*?\)', 'def heuristic(problem_instance)', code, count=1)
        return code

    def _call(self, prompt, temperature=0.8, model_key=None):
        self.api_calls += 1
        target_model = model_key if model_key is not None else self.model_key
        raw = self.client.generate(target_model, prompt, temperature=temperature)
        code = self._extract(raw)
        code = self._ensure_name(code)
        return code

    def generate_initial(self, temperature=0.85, strategy=None):
        prompt = "You are an expert algorithm designer.\n\n" + TSP_DESCRIPTION
        if strategy:
            prompt += f"\n\nFor this heuristic, specifically focus on a: {strategy} approach to ensure algorithmic diversity."
            
        prompt += ("\n\nWrite a Python function named EXACTLY `heuristic` that solves TSP.\n"
            "Keep it simple and fast - avoid O(n^3) or higher complexity.\n"
            "RETURN ONLY THE PYTHON FUNCTION. No explanation. No markdown fences.")
        return self._call(prompt, temperature, model_key=self.model_key)

    def mutate(self, parent_code, fitness, feedback, temperature=0.65):
        clean_parent = strip_comments_and_docstrings(parent_code)
        prompt = ("Improve this TSP heuristic:\n\n" + clean_parent +
            "\n\nFitness: " + str(round(fitness, 4)) +
            "\nFeedback: " + feedback +
            "\n\nWrite an improved version named EXACTLY `heuristic`.\n"
            "Keep complexity reasonable - avoid O(n^3) loops.\n"
            "RETURN ONLY THE PYTHON FUNCTION. No explanation.")
        return self._call(prompt, temperature, model_key=self.mutation_model_key)

    def crossover(self, code_a, fit_a, code_b, fit_b, temperature=0.65):
        clean_a = strip_comments_and_docstrings(code_a)
        clean_b = strip_comments_and_docstrings(code_b)
        prompt = ("Combine ideas from these two TSP heuristics:\n\n"
            "Heuristic A (fitness " + str(round(fit_a, 4)) + "):\n" + clean_a +
            "\n\nHeuristic B (fitness " + str(round(fit_b, 4)) + "):\n" + clean_b +
            "\n\nWrite a hybrid named EXACTLY `heuristic`.\n"
            "RETURN ONLY THE PYTHON FUNCTION. No explanation.")
        return self._call(prompt, temperature, model_key=self.mutation_model_key)

class HeuristicEvaluator:
    def __init__(self, instances, timeout=2.0):
        self.instances = instances
        self.timeout = timeout
        self.current_code = ""

    def _run_with_timeout(self, fn, data):
        """Run function with a hard timeout using multiprocessing on Windows/Unix, falling back to threading if unsupported."""
        import multiprocessing
        
        try:
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=_eval_worker, args=(self.current_code, data, queue))
            p.start()
            p.join(timeout=self.timeout)
            
            if p.is_alive():
                p.terminate()  # Hard-kill the timed-out process!
                p.join()
                return None, "timeout"
            
            if not queue.empty():
                res, err = queue.get()
                return res, err
            else:
                return None, "Process terminated unexpectedly without result"
        except Exception:
            # Fallback to threading if multiprocessing fails or is restricted by environment
            import threading
            result_container = [None]
            error_container = [None]

            def target():
                try:
                    result_container[0] = fn(data)
                except Exception as e:
                    error_container[0] = e

            t = threading.Thread(target=target)
            t.daemon = True
            t.start()
            t.join(timeout=self.timeout)

            if t.is_alive():
                return None, "timeout"
            if error_container[0] is not None:
                return None, str(error_container[0])
            return result_container[0], None

    def _validate_tour(self, result, inst):
        """Validate that the returned tour is mathematically valid and recalculate its actual cost."""
        if not isinstance(result, dict):
            return None, "Result must be a dictionary"
        
        tour = result.get("tour")
        if tour is None:
            return None, "Result dictionary missing 'tour' key"
        
        if not isinstance(tour, (list, np.ndarray)):
            return None, "'tour' must be a list or numpy array"
        
        tour = list(tour)
        n_cities = inst.data["n_cities"]
        if len(tour) != n_cities:
            return None, f"Tour length is {len(tour)}, expected {n_cities}"
        
        if set(tour) != set(range(n_cities)):
            return None, "Tour must visit each city exactly once"
            
        dist = inst.data["dist_matrix"]
        try:
            calculated_cost = float(sum(dist[tour[i]][tour[i+1]] for i in range(n_cities-1)) + dist[tour[-1]][tour[0]])
            if np.isnan(calculated_cost) or np.isinf(calculated_cost):
                return None, "Calculated cost is NaN or Inf"
            return calculated_cost, None
        except Exception as e:
            return None, f"Error calculating tour cost: {str(e)}"

    def evaluate(self, code):
        import hashlib
        def log_eval_failure(err_type, msg):
            code_hash = hashlib.md5(code.encode()).hexdigest() if code else "empty"
            payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error_type": err_type,
                "message": msg,
                "code_hash": code_hash,
                "code_snippet": code[:500] + "..." if code and len(code) > 500 else (code or "")
            }
            try:
                with open("failures.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload) + "\n")
            except Exception as le:
                print(f"⚠️ Failed to write to failures.jsonl: {le}")

        if not code or len(code.strip()) < 10:
            log_eval_failure("empty_code", "Code too short or empty")
            return 0.0, {"error": "Empty code"}

        self.current_code = code
        import random
        import math
        exec_globals = {
            "np": np,
            "random": random,
            "math": math,
            "List": List,
            "Dict": Dict,
            "Any": Any,
            "Tuple": Tuple,
            "Optional": Optional
        }
        try:
            exec(code, exec_globals)
            fn = exec_globals.get("heuristic")
            if fn is None:
                print(f"\n      [DEBUG EVAL FAIL] No heuristic function found. Code start: {code[:150]!r}")
                log_eval_failure("wrong_function_name", "No heuristic function found - wrong name returned by LLM")
                return 0.0, {"error": "No heuristic function found - LLM used wrong name"}

            gaps, runtimes = [], []
            instance_details = []
            for inst in self.instances:
                t0 = time.time()
                result, err = self._run_with_timeout(fn, inst.data)
                elapsed = time.time() - t0

                if err or result is None:
                    gaps.append(1.0)
                    runtimes.append(self.timeout)
                    instance_details.append({
                        "instance_id": inst.instance_id,
                        "cost": None,
                        "baseline": inst.best_known_solution,
                        "gap": 1.0,
                        "runtime": round(elapsed, 4),
                        "error": err or "Process timeout or silent error"
                    })
                    continue

                cost, val_err = self._validate_tour(result, inst)
                if val_err:
                    gaps.append(1.0)
                    runtimes.append(self.timeout)
                    instance_details.append({
                        "instance_id": inst.instance_id,
                        "cost": None,
                        "baseline": inst.best_known_solution,
                        "gap": 1.0,
                        "runtime": round(elapsed, 4),
                        "error": val_err
                    })
                    continue

                gap = (cost - inst.best_known_solution) / inst.best_known_solution
                gaps.append(min(gap, 10.0))
                runtimes.append(elapsed)
                instance_details.append({
                    "instance_id": inst.instance_id,
                    "cost": cost,
                    "baseline": inst.best_known_solution,
                    "gap": round(gap, 4),
                    "runtime": round(elapsed, 4),
                    "error": None
                })

            if not gaps:
                log_eval_failure("no_successful_evaluations", "All TSP instances failed to evaluate")
                return 0.0, {"error": "All instances failed"}

            avg_gap = float(np.mean(gaps))
            avg_rt = float(np.mean(runtimes))
            rob = float(np.std(gaps))

            qs = float(np.exp(-avg_gap))
            ts = float(np.clip(np.exp(-avg_rt / 10.0), 0, 1))
            rs = float(np.clip(np.exp(-rob), 0, 1))
            fit = 0.7*qs + 0.2*ts + 0.1*rs

            char = characterize_heuristic(code)
            return fit, {
                "fitness": fit, "avg_gap": avg_gap,
                "avg_runtime": avg_rt, "robustness": rob, "quality_score": qs,
                "instance_evals": instance_details,
                **char
            }
        except Exception as e:
            print(f"\n      [DEBUG EVAL FAIL] Exec/Syntax Error: {e}. Code start: {code[:150]!r}")
            log_eval_failure("syntax_or_exec_error", str(e))
            return 0.0, {"error": str(e)}

    def feedback_text(self, metrics, rank, total):
        if "error" in metrics:
            return "Error: " + metrics.get("error", "unknown")
        lines = [
            "Fitness: " + str(round(metrics.get("fitness", 0), 4)),
            "Gap from baseline: " + str(round(metrics.get("avg_gap", 1)*100, 2)) + "%",
            "Rank: " + str(rank) + "/" + str(total),
            "Suggestions:",
        ]
        if metrics.get("avg_gap", 1) > 0.1:
            lines.append("- Solution quality needs improvement, try 2-opt refinement")
        if metrics.get("avg_runtime", 0) > 3.0:
            lines.append("- Too slow, simplify the algorithm")
        return "\n".join(lines)

def code_similarity(code_a, code_b):
    """Compute basic token-level Jaccard similarity as a proxy for code similarity (Section 3.5.3)."""
    import re
    tokens_a = set(re.findall(r'\w+', code_a.lower()))
    tokens_b = set(re.findall(r'\w+', code_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)

class EvolutionaryEngine:
    def __init__(self, generator, evaluator, population_size=5, max_generations=10):
        self.gen = generator
        self.ev = evaluator
        self.pop_size = population_size
        self.max_gen = max_generations
        self.population = []
        self.generation = 0
        self.best_history = []

    def _tournament(self, k=3):
        k = min(k, len(self.population))
        idx = np.random.choice(len(self.population), size=k, replace=False)
        candidates = [self.population[i] for i in idx]
        return max(candidates, key=lambda c: c.fitness)

    def _make(self, code, op, g, parent_ids=None):
        fitness, metrics = self.ev.evaluate(code)
        
        # Calculate proper evolutionary novelty score relative to current population
        novelty_score = 0.0
        if self.population:
            sims = [code_similarity(code, c.code) for c in self.population if c.code]
            novelty_score = 1.0 - float(np.mean(sims)) if sims else 1.0
        else:
            novelty_score = 1.0

        p_ids = parent_ids if parent_ids is not None else []
        
        return HeuristicCandidate(
            code=code, fitness=fitness,
            quality_score=metrics.get("quality_score", 0),
            runtime=metrics.get("avg_runtime", 0),
            robustness=metrics.get("robustness", 0),
            generation=g, model_name=self.gen.model_key,
            metadata={"operation": op, "novelty_score": round(novelty_score, 4), **metrics},
            parent_ids=p_ids,
            operation=op)

    def initialize(self):
        print("  Generating " + str(self.pop_size) + " initial heuristics...")
        self.population = []
        strategies = [
            "Greedy Construction with look-ahead",
            "Local Search / 2-opt refinement",
            "Dynamic Programming approximation",
            "Probabilistic / Randomized sampling"
        ]
        for i in range(self.pop_size):
            print("    [" + str(i+1) + "/" + str(self.pop_size) + "] generating...", end=" ", flush=True)
            strat = strategies[i % len(strategies)]
            try:
                # Stage 2: Diversity-Aware Generation
                code = self.gen.generate_initial(temperature=0.85, strategy=strat)
                c = self._make(code, f"initial_{strat.split()[0].lower()}", 0, parent_ids=[])
            except Exception as e:
                print("FAILED: " + str(e)[:50])
                c = HeuristicCandidate(code="", fitness=0.0, quality_score=0.0,
                    runtime=0.0, robustness=0.0, generation=0,
                    model_name=self.gen.model_key, metadata={"error": str(e)},
                    parent_ids=[], operation="initial")
            self.population.append(c)
            print("fitness=" + str(round(c.fitness, 4)))
            time.sleep(1.5)

    def step(self):
        self.population.sort(key=lambda c: c.fitness, reverse=True)
        best = self.population[0].fitness
        avg = sum(c.fitness for c in self.population) / len(self.population)
        
        # Calculate Delta F_g (fitness improvement) for Eq 10
        delta_F = 0.0
        if len(self.best_history) > 0:
            delta_F = max(0.0, best - self.best_history[-1])
            
        self.best_history.append(best)
        print("  Gen " + str(self.generation) + " | Best=" + str(round(best,4)) + " | Avg=" + str(round(avg,4)))
        
        # Eq 9: Dynamic Temperature control
        g_ratio = self.generation / max(1, self.max_gen)
        temp_scale = 1.0 - 0.5 * g_ratio
        
        t_initial = 0.85 * temp_scale
        t_mutation = 0.65 * temp_scale
        t_crossover = 0.65 * temp_scale

        # Eq 10: Adaptive mutation rate control: m_g = m_0 * exp(-delta_F / sigma)
        # We set base mutation rate m0 = 0.40, and sigma = 0.1
        m_base = 0.40
        m_g = m_base * np.exp(-delta_F / 0.1)
        m_g = float(np.clip(m_g, 0.1, 0.7))
        
        # Adjust crossover rate dynamically (rest of budget)
        elite_rate = 0.2
        novelty_rate = 0.1
        crossover_g = max(0.1, 1.0 - elite_rate - novelty_rate - m_g)
        
        # Round counts
        n_elite = max(1, int(self.pop_size * elite_rate))
        n_mutation = max(1, int(self.pop_size * m_g))
        n_crossover = max(1, int(self.pop_size * crossover_g))
        n_novelty = max(0, self.pop_size - n_elite - n_mutation - n_crossover)
        
        # Section 3.5.3: Diversity Maintenance via pairwise similarity check
        n_pop = len(self.population)
        similarities = []
        for i in range(n_pop):
            for j in range(i + 1, n_pop):
                sim = code_similarity(self.population[i].code, self.population[j].code)
                similarities.append(sim)
        mean_sim = float(np.mean(similarities)) if similarities else 0.0
        
        print(f"    [Adaptive Rates] Elite: {n_elite} | Mut ({round(m_g*100)}%): {n_mutation} (temp={round(t_mutation,2)}) | Cross ({round(crossover_g*100)}%): {n_crossover} (temp={round(t_crossover,2)}) | Novel: {n_novelty}")
        print(f"    [Diversity Maintenance] Mean Code Similarity: {round(mean_sim, 3)}")
        
        # Track diversity metrics inside step state so experiment can save it
        if not hasattr(self, "metrics_history"):
            self.metrics_history = []
        self.metrics_history.append({
            "generation": self.generation,
            "best_fitness": best,
            "mean_fitness": avg,
            "mean_similarity": mean_sim,
            "mutation_rate": m_g,
            "temperature": t_mutation
        })
        
        # Jaccard trigger for extra novelty (Section 3.5.3)
        if mean_sim > 0.8:
            print("    ⚠️ High similarity detected! Injecting extra novelty to preserve diversity.")
            n_novelty = min(self.pop_size, n_novelty + 1)
            n_elite = max(1, n_elite - 1)
            
        next_gen = list(self.population[:n_elite])

        for _ in range(n_mutation):
            try:
                p = self._tournament()
                rank = self.population.index(p) + 1
                fb = self.ev.feedback_text(p.metadata, rank, len(self.population))
                code = self.gen.mutate(p.code, p.fitness, fb, temperature=t_mutation)
                next_gen.append(self._make(code, "mutation", self.generation+1, parent_ids=[p.candidate_id]))
            except Exception as e:
                print("  mutation skipped: " + str(e)[:40])
            time.sleep(1.5)

        for _ in range(n_crossover):
            try:
                p1 = self._tournament()
                p2 = self._tournament()
                code = self.gen.crossover(p1.code, p1.fitness, p2.code, p2.fitness, temperature=t_crossover)
                next_gen.append(self._make(code, "crossover", self.generation+1, parent_ids=[p1.candidate_id, p2.candidate_id]))
            except Exception as e:
                print("  crossover skipped: " + str(e)[:40])
            time.sleep(1.5)

        for _ in range(n_novelty):
            try:
                code = self.gen.generate_initial(temperature=t_initial)
                next_gen.append(self._make(code, "novelty", self.generation+1, parent_ids=[]))
            except Exception as e:
                print("  novelty skipped: " + str(e)[:40])
            time.sleep(1.5)

        if next_gen:
            self.population = next_gen
        self.generation += 1

    def converged(self, patience=3):
        if len(self.best_history) < patience:
            return False
        return (self.best_history[-1] - self.best_history[-patience]) < 0.001

    @property
    def best(self):
        return max(self.population, key=lambda c: c.fitness)

def generate_tsp_instances(n_instances=5, n_cities=20, seed=42):
    rng = np.random.default_rng(seed)
    instances = []
    for i in range(n_instances):
        coords = rng.uniform(0, 100, size=(n_cities, 2))
        dist = np.sqrt(((coords[:, None] - coords[None, :])**2).sum(-1))
        tour = [0]
        unvisited = set(range(1, n_cities))
        while unvisited:
            cur = tour[-1]
            nearest = min(unvisited, key=lambda c: dist[cur][c])
            tour.append(nearest)
            unvisited.remove(nearest)
        nn_cost = sum(dist[tour[j]][tour[j+1]] for j in range(n_cities-1)) + dist[tour[-1]][tour[0]]
        instances.append(ProblemInstance(
            instance_id="tsp_" + str(n_cities) + "_" + str(i),
            data={"n_cities": n_cities, "dist_matrix": dist},
            best_known_solution=nn_cost))
    return instances

class LLMHeuristicExperiment:
    def __init__(self, model_keys, instances):
        self.model_keys = model_keys
        self.instances = instances
        self.client = LLMClient()
        self.evaluator = HeuristicEvaluator(instances)
        self.results = {}

    def run(self, max_generations=3, population_size=3, patience=3, json_path="results_pilot.json", plot_path="comparison_pilot.png", run_gens=None):
        existing_data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}

        for model_key in self.model_keys:
            display = MODELS[model_key]["display_name"]
            
            # Smart Skip Check: if the model completed successfully in results_pilot.json
            if model_key in existing_data and existing_data[model_key].get("best_fitness", 0) > 0.0:
                # Check if checkpoint exists; if it does, we are micro-batching, so don't skip!
                ckpt_path = f"checkpoint_{model_key}.json"
                if not os.path.exists(ckpt_path):
                    print("\n" + "="*60)
                    print(f"  MODEL: {display} (SKIPPED - Already completed)")
                    print("="*60)
                    print(f"  Loaded pichla/previous results from {json_path} successfully!")
                    best_fit = existing_data[model_key]["best_fitness"]
                    best_code = existing_data[model_key]["best_code"]
                    avg_gap = existing_data[model_key]["avg_gap_pct"] / 100.0
                    avg_rt = existing_data[model_key]["avg_runtime_s"]
                    calls = existing_data[model_key]["api_calls"]
                    hist = existing_data[model_key].get("fitness_history", [best_fit])
                    
                    self.results[model_key] = ExperimentResult(
                        model_name=display,
                        best_fitness_history=hist,
                        best_candidate=HeuristicCandidate(
                            code=best_code,
                            fitness=best_fit,
                            quality_score=best_fit,
                            runtime=avg_rt,
                            robustness=1.0,
                            generation=0,
                            model_name=display,
                            metadata={"avg_gap": avg_gap, "avg_runtime": avg_rt}
                        ),
                        avg_gap=avg_gap,
                        avg_runtime=avg_rt,
                        total_api_calls=calls
                    )
                    continue

            print("\n" + "="*60)
            print("  MODEL: " + display)
            print("="*60)
            
            # Determine instances for search
            # Choose a unique random subset of 15 instances for search phase, but keep it stable for reproducibility
            is_final_mode = (len(self.instances) == 50)
            if is_final_mode:
                import random
                # Compute a deterministic seed from the model key string (e.g. sum of character codes)
                model_seed = 42 + sum(ord(c) for c in model_key)
                rng = random.Random(model_seed)
                search_instances = rng.sample(self.instances, 15)
                search_evaluator = HeuristicEvaluator(search_instances)
                print(f"🧬 [Stochastic Fitness Approximation] Searching on a deterministic random subset of 15 instances...")
            else:
                search_instances = self.instances
                search_evaluator = self.evaluator

            ckpt_path = f"checkpoint_{model_key}.json"
            generator = HeuristicGenerator(self.client, model_key)
            engine = EvolutionaryEngine(generator, search_evaluator, population_size=population_size, max_generations=max_generations)
            
            resuming = False
            if os.path.exists(ckpt_path):
                try:
                    with open(ckpt_path, "r") as f:
                        ckpt_data = json.load(f)
                    engine.generation = ckpt_data["generation"]
                    engine.best_history = ckpt_data["best_history"]
                    engine.population = [deserialize_candidate(d) for d in ckpt_data["population"]]
                    resuming = True
                    print("\n" + "="*60)
                    print(f"🟢 [RESUMING EVOLUTION] Loaded checkpoint successfully!")
                    print(f"   Resuming {display} from Generation {engine.generation}...")
                    print(f"   Loaded Population: {len(engine.population)} candidates")
                    print(f"   Loaded Best History: {[round(x, 4) for x in engine.best_history]}")
                    print("="*60 + "\n")
                except Exception as ce:
                    print(f"⚠️ Failed to load checkpoint: {ce}. Starting fresh...")
                    resuming = False

            try:
                if not resuming:
                    engine.initialize()
                
                start_gen = engine.generation
                end_gen = min(start_gen + run_gens, max_generations) if run_gens is not None else max_generations
                
                if start_gen >= max_generations:
                    print(f"✅ {display} already completed all {max_generations} generations!")
                    end_gen = start_gen
                
                for g in range(start_gen, end_gen):
                    engine.step()
                    
                    # Save checkpoint at the end of every generation
                    try:
                        ckpt_payload = {
                            "generation": engine.generation,
                            "best_history": engine.best_history,
                            "population": [serialize_candidate(c) for c in engine.population]
                        }
                        with open(ckpt_path, "w") as f:
                            json.dump(ckpt_payload, f, indent=2)
                        print(f"💾 Checkpoint saved for Generation {engine.generation} at {ckpt_path}")
                    except Exception as cse:
                        print(f"⚠️ Checkpoint save failed: {cse}")

                    if engine.converged(patience):
                        print("  Converged after " + str(g+1) + " generations.")
                        break
                        
                best = engine.best
                is_completed = (engine.generation >= max_generations or engine.converged(patience))
                
                # Full 50-instance evaluation for champion in final mode
                if is_final_mode:
                    print(f"\n🏅 [Full Academic Evaluation] Evaluating the champion heuristic on all 50 instances...")
                    full_fit, full_metrics = self.evaluator.evaluate(best.code)
                    best.fitness = full_fit
                    best.quality_score = full_metrics.get("quality_score", 0)
                    best.runtime = full_metrics.get("avg_runtime", 0)
                    best.robustness = full_metrics.get("robustness", 0)
                    best.metadata = {**best.metadata, **full_metrics}
                    print(f"   Champion Fitness on all 50 instances: {round(full_fit, 4)}")

                self.results[model_key] = ExperimentResult(
                    model_name=display,
                    best_fitness_history=engine.best_history,
                    best_candidate=best,
                    avg_gap=best.metadata.get("avg_gap", 1.0),
                    avg_runtime=best.metadata.get("avg_runtime", 0.0),
                    total_api_calls=generator.api_calls,
                    metrics_history=getattr(engine, "metrics_history", []))
                print("  DONE | Fitness: " + str(round(best.fitness,4)) + " | Gap: " + str(round(best.metadata.get("avg_gap",1)*100,2)) + "%")
                
                # Cleanup checkpoint on success
                if is_completed:
                    if os.path.exists(ckpt_path):
                        try:
                            os.remove(ckpt_path)
                            print(f"🗑️ Cleaned up checkpoint: {ckpt_path} (Run fully completed!)")
                        except Exception:
                            pass
                else:
                    print(f"\n⏸️ [Micro-Batch Completed] Reached generation limit ({engine.generation}/{max_generations}). Checkpoint preserved!")
                
                # Checkpoint results dynamically to prevent loss on rate limits
                self.save_results(json_path)
                try:
                    self.plot_comparison(plot_path, json_path)
                except Exception as pe:
                    print("  Plotting skipped or failed: " + str(pe))
            except Exception as e:
                print("  FAILED: " + str(e))

    def save_results(self, path="results_pilot.json"):
        # Load existing results to prevent losing other runs
        out = {}
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    out = json.load(f)
            except Exception:
                out = {}

        # 1. Update with active self.results
        for key, res in self.results.items():
            system_info = get_system_info()
            seeds_config = {
                "experiment_seed": 42,
                "model_seed": 42 + sum(ord(c) for c in key),
                "numpy_seed": 42,
                "instances_seed": 42
            }
            out[key] = {
                "model": res.model_name,
                "best_fitness": round(res.best_candidate.fitness, 4) if res.best_candidate else 0,
                "avg_gap_pct": round(res.avg_gap*100, 2),
                "avg_runtime_s": round(res.avg_runtime, 3),
                "api_calls": res.total_api_calls,
                "fitness_history": res.best_fitness_history,
                "best_code": res.best_candidate.code if res.best_candidate else "",
                "instance_evals": res.best_candidate.metadata.get("instance_evals", []) if res.best_candidate else [],
                "metrics_history": res.metrics_history,
                "seeds": seeds_config,
                "system_info": system_info
            }
            
        # Keep all models accumulated across all historic runs
        cleaned_out = out
                
        with open(path, "w") as f:
            json.dump(cleaned_out, f, indent=2)
        print("\nResults saved to " + path)

    def plot_comparison(self, save_path="comparison_pilot.png", json_path="results_pilot.json"):
        # Load accumulated data from JSON if available to prevent losing previous run plots
        data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        
        # If JSON is empty, fall back to current self.results
        if not data:
            for key, res in self.results.items():
                data[key] = {
                    "model": res.model_name,
                    "best_fitness": round(res.best_candidate.fitness, 4) if res.best_candidate else 0,
                    "avg_gap_pct": round(res.avg_gap*100, 2),
                    "avg_runtime_s": round(res.avg_runtime, 3),
                    "api_calls": res.total_api_calls,
                    "fitness_history": res.best_fitness_history,
                }
                
        if not data:
            print("No results to plot.")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("LLM-Heuristic: Multi-Model Comparison", fontsize=14, fontweight="bold")
        colors = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63"]
        ax = axes[0]
        for i, (key, info) in enumerate(data.items()):
            history = info.get("fitness_history")
            if history:
                ax.plot(history, marker="o", label=info["model"],
                    color=colors[i % len(colors)], linewidth=2)
        ax.set_xlabel("Generation")
        ax.set_ylabel("Best Fitness")
        ax.set_title("Convergence Curves")
        ax.legend()
        ax.grid(True, alpha=0.3)

        ax2 = axes[1]
        names = [info["model"] for info in data.values()]
        gaps = [min(info["avg_gap_pct"], 200.0) for info in data.values()]
        bars = ax2.bar(names, gaps, color=colors[:len(names)], edgecolor="black")
        ax2.set_ylabel("Avg Optimality Gap (%)")
        ax2.set_title("Solution Quality (lower = better)")
        ax2.tick_params(axis="x", rotation=15)
        for bar, gap in zip(bars, gaps):
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                str(round(gap,1))+"%", ha="center", va="bottom", fontsize=9)
        ax2.grid(True, alpha=0.3, axis="y")
        plt.tight_layout()
        plt.savefig(save_path, dpi=200, bbox_inches="tight")
        print("Plot saved to " + save_path)

    def print_summary(self, json_path="results_pilot.json"):
        data = {}
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        if not data:
            # Fallback to current self.results
            for key, res in self.results.items():
                data[key] = {
                    "model": res.model_name,
                    "best_fitness": round(res.best_candidate.fitness, 4) if res.best_candidate else 0,
                    "avg_gap_pct": round(res.avg_gap*100, 2),
                    "avg_runtime_s": round(res.avg_runtime, 3),
                    "api_calls": res.total_api_calls,
                }

        print("\n" + "="*65)
        print("MODEL                      FITNESS    GAP %   RUNTIME  API CALLS")
        print("-"*65)
        for key, info in data.items():
            print(info["model"].ljust(25) + "  " + str(round(info["best_fitness"], 4)).rjust(8) + "  " +
                str(round(info["avg_gap_pct"], 2)).rjust(6) + "%  " +
                str(round(info["avg_runtime_s"], 3)).rjust(8) + "s  " +
                str(info["api_calls"]).rjust(9))
        print("="*65)

        # LaTeX Table Generator for Research Paper
        print("\n" + "="*20 + " AUTO-LATEX TABLE FOR RESEARCH PAPER " + "="*20)
        print("\\begin{table}[h]")
        print("\\centering")
        print("\\caption{Performance Comparison of LLM-Heuristic Framework Across Models}")
        print("\\begin{tabular}{lcccc}")
        print("\\hline")
        print("\\textbf{Model} & \\textbf{Best Fitness} & \\textbf{Avg Gap (\\%)} & \\textbf{Avg Runtime (s)} & \\textbf{API Calls} \\\\ \\hline")
        for key, info in data.items():
            model_name = info["model"]
            best_fit = round(info["best_fitness"], 4)
            avg_gap = round(info["avg_gap_pct"], 2)
            avg_rt = round(info["avg_runtime_s"], 3)
            calls = info["api_calls"]
            print(f"{model_name} & {best_fit} & {avg_gap}\\% & {avg_rt}s & {calls} \\\\")
        print("\\hline")
        print("\\end{tabular}")
        print("\\label{tab:llm_heuristic_results}")
        print("\\end{table}")
        print("="*77 + "\n")

class DualLogger:
    def __init__(self, filepath):
        import sys
        self.terminal = sys.stdout
        self.log = open(filepath, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    def flush(self):
        self.terminal.flush()
        self.log.flush()

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="LLM-Heuristic Framework CLI")
    parser.add_argument("--mode", type=str, choices=["pilot", "final"], default="pilot",
                        help="Experiment execution scale (pilot or final)")
    parser.add_argument("--model", type=str, choices=["all", "llama-3.3-70b", "llama-3.1-8b", "llama-4-scout", "gpt-oss-120b"], default="all",
                        help="Specific model key to execute, or 'all' to benchmark all flagship models")
    parser.add_argument("--run-gens", type=int, default=None,
                        help="Micro-batch: Limit number of generations executed in this run before clean exit")
    args = parser.parse_args()

    mode = args.mode
    if mode == "pilot":
        log_file = "results_pilot.log"
        results_file = "results_pilot.json"
        plot_file = "comparison_pilot.png"
        n_instances = 10
        n_cities = 20
        pop_size = 6
        max_gen = 5
        patience = 3
    else:
        log_file = "results_final_run.log"
        results_file = "results_final_run.json"
        plot_file = "comparison_final_run.png"
        # Highly Optimized Academic Production Scale
        n_instances = 50
        n_cities = 50
        pop_size = 8       # Optimized from 15 (Saves 50% API calls)
        max_gen = 8        # Optimized from 20 (Evolution converges early)
        patience = 2       # Stronger convergence stopping
    
    # Redirect stdout to terminal and log file dynamically
    sys.stdout = DualLogger(log_file)

    print(f"LLM-Heuristic Framework - Running Mode: {mode.upper()}")
    print("="*60)

    instances = generate_tsp_instances(n_instances=n_instances, n_cities=n_cities, seed=42)
    print(f"Loaded {len(instances)} TSP instances with {instances[0].data['n_cities']} cities each\n")

    selected_models = ["llama-3.3-70b", "llama-3.1-8b", "llama-4-scout", "gpt-oss-120b"]
    if args.model != "all":
        selected_models = [args.model]

    experiment = LLMHeuristicExperiment(
        model_keys=selected_models,
        instances=instances)

    experiment.run(population_size=pop_size, max_generations=max_gen, patience=patience, json_path=results_file, plot_path=plot_file, run_gens=args.run_gens)
    experiment.print_summary(results_file)
    experiment.save_results(results_file)
    experiment.plot_comparison(plot_file, results_file)

    print(f"\nExperiment {mode.upper()} complete!")
    print(f"Logs successfully written to {log_file}")
    print(f"Results JSON saved to {results_file}")
    print(f"Plots saved to {plot_file}")
