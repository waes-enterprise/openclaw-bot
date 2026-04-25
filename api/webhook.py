from http.server import BaseHTTPRequestHandler
import json, os, requests

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"
TELEGRAM_API = "https://api.telegram.org/bot"

def ask_groq(prompt):
    key = os.environ.get("GROQ_API_KEY", "")
    r = requests.post(GROQ_API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500})
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Error: {r.text}"

def send_telegram(token, chat_id, message):
    url = f"{TELEGRAM_API}{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        msg = body.get("message", {})
        chat_id = msg.get("chat", {}).get("id", "")
        text = msg.get("text", "")
        if text and chat_id:
            reply = ask_groq(text)
            send_telegram(token, chat_id, reply)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OpenClaw Bot is running!")
