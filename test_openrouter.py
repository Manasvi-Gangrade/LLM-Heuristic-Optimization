import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

or_key = os.environ.get("OPENROUTER_API_KEY")
if or_key:
    client = OpenAI(api_key=or_key, base_url="https://openrouter.ai/api/v1")
    try:
        print("\nACTIVE OPENROUTER MODELS (Sample List):")
        print("=======================================")
        models = client.models.list()
        # OpenRouter returns a huge list, print first 20 popular/free ones
        count = 0
        for model in models.data:
            m_id = model.id.lower()
            # print some common ones
            if any(kw in m_id for kw in ["deepseek", "llama-3.3", "llama-3.1", "qwen", "gemini"]):
                print(f"- {model.id}")
                count += 1
                if count >= 20:
                    break
        if count == 0:
            for model in models.data[:20]:
                print(f"- {model.id}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("OPENROUTER_API_KEY not configured in .env")
