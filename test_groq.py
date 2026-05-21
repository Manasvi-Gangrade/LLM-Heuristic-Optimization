import os
from dotenv import load_dotenv
load_dotenv()

from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
try:
    models = client.models.list()
    print("\nACTIVE GROQ MODELS:")
    print("===================")
    for model in models.data:
        print(f"- {model.id}")
except Exception as e:
    print(f"Error: {e}")
