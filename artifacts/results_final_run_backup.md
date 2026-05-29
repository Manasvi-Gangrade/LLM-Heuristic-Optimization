# 📊 LLM-Heuristic Framework - Final Run Log Backup

This file preserves the raw log execution history of the high-density stress run (**50 TSP instances with 50 cities each**) on **LLaMA 3.3 70B** before modifying the rate-limit timeout catcher.

---

## 📝 Raw Console Log Details
```text
LLM-Heuristic Framework - Running Mode: FINAL
============================================================
Loaded 50 TSP instances with 50 cities each


============================================================
  MODEL: LLaMA 3.3 70B
============================================================
  Generating 15 initial heuristics...
    [1/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.9554
    [2/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matri'
fitness=1.0282
    [3/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    dp = [[float(\'inf\')] * n for _ in'
fitness=0.5213
    [4/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    import numpy as np\n    import random\n\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matr'
fitness=0.5213
    [5/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.8164
    [6/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matri'
fitness=1.0306
    [7/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.3576
    [8/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    import numpy as np\n    import random\n\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matr'
fitness=0.3204
    [9/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.886
    [10/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    import numpy as np\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = lis'
fitness=1.0272
    [11/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    dp = [[float(\'inf\')] * n for _ in'
fitness=0.5213
    [12/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\nimport numpy as np\nimport random\n\ndef heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_ma'
fitness=0.3158
    [13/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.814
    [14/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = list(range(n))\n    import '
fitness=1.0287
    [15/15] generating... 
      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
fitness=0.5213
  Gen 0 | Best=1.0306 | Avg=0.711
    [Adaptive Rates] Elite: 3 | Mut (40%): 6 (temp=0.65) | Cross (30%): 4 (temp=0.65) | Novel: 2
    [Diversity Maintenance] Mean Code Similarity: 0.507

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisite'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisite'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    '

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisite'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisite'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n\n   '

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: 'def heuristic(problem_instance):\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n    tour = [0]\n    unvisited = set(ra'
  Gen 1 | Best=1.0454 | Avg=0.9503
    [Adaptive Rates] Elite: 3 | Mut (34%): 5 (temp=0.63) | Cross (36%): 5 (temp=0.63) | Novel: 2
    [Diversity Maintenance] Mean Code Similarity: 0.617

  Groq rate limit - waiting 30s...

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n\n   '

      [DEBUG EVAL FAIL] Exec/Syntax Error: unmatched ')' (<string>, line 37). Code start: 'def heuristic(problem_instance):\n    import numpy as np\n    n = problem_instance["n_cities"]\n    dist = problem_instance["dist_matrix"]\n\n    # Christo'

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

      [DEBUG RAW RESPONSE] First 150 chars of llama-3.3-70b-versatile output: '```python\ndef heuristic(problem_instance):\n    import numpy as np\n    import random\n    n = problem_instance["n_cities"]\n    dist = problem_instance["'

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

  Groq rate limit - waiting 120s...

  Groq rate limit - waiting 150s...
  mutation skipped: Groq exceeded retries

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

  Groq rate limit - waiting 120s...

  Groq rate limit - waiting 150s...
  mutation skipped: Groq exceeded retries

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

  Groq rate limit - waiting 120s...

  Groq rate limit - waiting 150s...
  mutation skipped: Groq exceeded retries

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

  Groq rate limit - waiting 120s...

  Groq rate limit - waiting 150s...
  crossover skipped: Groq exceeded retries

  Groq rate limit - waiting 30s...

  Groq rate limit - waiting 60s...

  Groq rate limit - waiting 90s...

  Groq rate limit - waiting 120s...

  Groq rate limit - waiting 150s...
```
