import os
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai

gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    try:
        print("\nACTIVE GEMINI MODELS:")
        print("=====================")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("GEMINI_API_KEY not configured in .env")
