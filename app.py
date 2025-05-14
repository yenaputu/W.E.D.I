from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS agar bisa diakses dari browser W.E.D.I
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain aslimu kalau sudah host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_API_KEY = os.getenv("HF_API_KEY")

class Message(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(data: Message):
    prompt = data.message
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": 0.7,
            "max_new_tokens": 200
        }
    }

    response = requests.post(
        "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf",
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        generated = result[0]["generated_text"] if isinstance(result, list) else result.get("generated_text", "")
        return {"reply": generated[len(prompt):].strip()}
    else:
        return {"reply": "Maaf, server LLaMA tidak merespons."}))