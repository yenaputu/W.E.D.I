from flask import Flask, render_template, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

app = Flask(__name__)

# Load model dan tokenizer DeepSeek
model_id = "deepseek-ai/DeepSeek-V3"
tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    inputs = tokenizer(user_message, return_tensors="pt")
    outputs = model.generate(**inputs, max_length=256, pad_token_id=tokenizer.eos_token_id)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return jsonify({"response": response.strip()})

if __name__ == "__main__":
    app.run(debug=True)