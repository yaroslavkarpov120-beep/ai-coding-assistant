from flask import Flask, render_template, request, jsonify, session
from pathlib import Path
from openai import OpenAI
import subprocess, os, secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

FREE_LIMIT = 20
MY_API_KEY = (Path.home() / ".ai_assistant_key").read_text().strip()

MODELS = [
    "openai/gpt-oss-20b:free",
    "google/gemma-4-31b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
]

SYSTEM = """Ты — AI Coding Assistant. Отвечай на русском языке.
Ты умеешь писать код, находить баги, объяснять решения.
Когда предлагаешь код — указывай имя файла. Отвечай конкретно."""

histories = {}

def get_client(user_key=None):
    key = user_key if user_key else MY_API_KEY
    return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")

@app.route("/")
def index():
    if "id" not in session:
        session["id"] = secrets.token_hex(8)
        session["count"] = 0
        session["user_key"] = ""
    return render_template("index.html")

@app.route("/status")
def status():
    count = session.get("count", 0)
    has_key = bool(session.get("user_key"))
    remaining = max(0, FREE_LIMIT - count) if not has_key else 999
    return jsonify({"remaining": remaining, "has_key": has_key, "limit": FREE_LIMIT})

@app.route("/set_key", methods=["POST"])
def set_key():
    key = request.json.get("key", "").strip()
    if not key:
        return jsonify({"ok": False})
    session["user_key"] = key
    return jsonify({"ok": True})

@app.route("/chat", methods=["POST"])
def chat():
    sid = session.get("id", "anon")
    count = session.get("count", 0)
    user_key = session.get("user_key", "")

    if not user_key and count >= FREE_LIMIT:
        return jsonify({"reply": "", "type": "limit"})

    msg = request.json.get("message", "").strip()
    if not msg:
        return jsonify({"reply": ""})

    if msg.startswith("run "):
        result = subprocess.run(msg[4:], shell=True, capture_output=True, text=True, timeout=30)
        return jsonify({"reply": f"```\n{result.stdout or result.stderr}\n```", "type": "command"})

    if sid not in histories:
        histories[sid] = []
    histories[sid].append({"role": "user", "content": msg})

    client = get_client(user_key)
    reply = None
    for model in MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM}] + histories[sid][-20:],
            )
            reply = response.choices[0].message.content
            break
        except Exception:
            continue

    if not reply:
        return jsonify({"reply": "Все модели недоступны, попробуй через минуту.", "type": "error"})

    histories[sid].append({"role": "assistant", "content": reply})

    if not user_key:
        session["count"] = count + 1

    remaining = max(0, FREE_LIMIT - session["count"]) if not user_key else 999
    return jsonify({"reply": reply, "type": "ai", "remaining": remaining})

if __name__ == "__main__":
    app.run(debug=False, port=5000)
