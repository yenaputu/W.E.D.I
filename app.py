import requests

API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf"
headers = {"Authorization": "Bearer YOUR_HF_API_KEY"}

def generate_response(prompt):
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 100}
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()[0]["generated_text"]

# Contoh
print(generate_response("Halo, siapa kamu?"))