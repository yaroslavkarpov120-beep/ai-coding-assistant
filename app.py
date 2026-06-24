from flask import Flask, render_template, request, jsonify
from pathlib import Path
from openai import OpenAI
import subprocess, os

app = Flask(__name__)

API_KEY_FILE = Path.home() / ".ai_assistant_key"
client = OpenAI(
    api_key=API_KEY_FILE.read_text().strip(),
    base_url="https://openrouter.ai/api/v1"
)

MODELS = [
    "openai/gpt-oss-20b:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
]

SYSTEM = """Ты — AI Coding Assistant. Отвечай на русском языке.
Ты умеешь писать код, находить баги, объяснять решения.
Когда предлагаешь код — указывай имя файла. Отвечай конкретно."""

history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify({"reply": ""})

    if msg.startswith("run "):
        result = subprocess.run(msg[4:], shell=True, capture_output=True, text=True, timeout=30)
        return jsonify({"reply": f"```\n{result.stdout or result.stderr}\n```", "type": "command"})

    history.append({"role": "user", "content": msg})

    reply = None
    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}] + history[-20:],
            )
            reply = response.choices[0].message.content
            break
        except Exception:
            continue

    if not reply:
        return jsonify({"reply": "Все модели недоступны, попробуй через минуту.", "type": "error"})

    history.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply, "type": "ai"})

if __name__ == "__main__":
    app.run(debug=False, port=5000)
