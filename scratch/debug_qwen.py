import os
import time
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

prompt = """You are an expert algorithm designer.
Write a Python function named EXACTLY `heuristic` that solves the Traveling Salesman Problem (TSP).
Keep it simple and fast - avoid O(n^3) or higher complexity.
RETURN ONLY THE PYTHON FUNCTION. No explanation. No markdown fences."""

print("Calling Qwen 3 32B on Groq...")
t0 = time.time()
try:
    r = client.chat.completions.create(
        model="qwen/qwen3-32b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=3000,
        timeout=45.0
    )
    res = r.choices[0].message.content
    print(f"Success in {time.time()-t0:.2f}s!")
    print("--- RAW RESPONSE START ---")
    print(res[:1500])
    if len(res) > 1500:
        print("... [TRUNCATED] ...")
        print(res[-500:])
    print("--- RAW RESPONSE END ---")
except Exception as e:
    print(f"Failed: {e}")
