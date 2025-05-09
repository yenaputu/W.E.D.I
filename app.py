from flask import Flask, request, render_template, jsonify import subprocess

app = Flask(name)

@app.route("/") def home(): return render_template("index.html")

@app.route("/ask", methods=["POST"]) def ask(): user_input = request.json.get("message") # Di sini kamu bisa ganti dengan pemanggilan model llama response = subprocess.getoutput(f"llama run --prompt "{user_input}"") return jsonify({"response": response})

if name == "main": app.run(debug=True)

templates/index.html

<!DOCTYPE html><html>
<head>
    <title>LLaMA Chatbot</title>
    <script>
        async function sendMessage() {
            const msg = document.getElementById("message").value;
            const res = await fetch("/ask", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: msg})
            });
            const data = await res.json();
            document.getElementById("chat").innerHTML += `<div><b>You:</b> ${msg}</div><div><b>Bot:</b> ${data.response}</div>`;
        }
    </script>
</head>
<body>
    <h1>LLaMA Chatbot</h1>
    <input id="message" type="text" placeholder="Tanya sesuatu...">
    <button onclick="sendMessage()">Kirim</button>
    <div id="chat"></div>
</body>
</html>static/style.css (Opsional CSS)

body { font-family: Arial, sans-serif; margin: 20px; }
