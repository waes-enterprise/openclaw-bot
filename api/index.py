from http.server import BaseHTTPRequestHandler
import json, os, requests, base64

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def ask_groq(prompt, image_base64=None, image_type="image/jpeg"):
    key = os.environ.get("GROQ_API_KEY", "")
    if image_base64:
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{image_base64}"}},
            {"type": "text", "text": prompt or "Describe this image in detail."}
        ]}]
    else:
        messages = [
            {"role": "system", "content": "You are OpenClaw, a smart AI assistant for ZamVibe, Zambia's entertainment platform. Be helpful, friendly and concise."},
            {"role": "user", "content": prompt}
        ]
    r = requests.post(GROQ_API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "max_tokens": 500})
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Error: {r.text}"

def send_telegram(token, chat_id, text):
    requests.post(f"{TELEGRAM_API}{token}/sendMessage",
        json={"chat_id": chat_id, "text": text})

def send_voice(token, chat_id, text):
    tts_url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(tts_url, json={"chat_id": chat_id, "text": f"🔊 {text}"})

def get_file_url(token, file_id):
    r = requests.get(f"{TELEGRAM_API}{token}/getFile?file_id={file_id}")
    if r.status_code == 200:
        path = r.json()["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{token}/{path}"
    return None

def download_as_base64(url):
    r = requests.get(url)
    if r.status_code == 200:
        return base64.b64encode(r.content).decode()
    return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        msg = body.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not chat_id:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # IMAGE handler
        if "photo" in msg:
            photo = msg["photo"][-1]
            file_url = get_file_url(token, photo["file_id"])
            if file_url:
                img_b64 = download_as_base64(file_url)
                caption = msg.get("caption", "What do you see in this image?")
                if img_b64:
                    reply = ask_groq(caption, image_base64=img_b64)
                else:
                    reply = "Sorry I could not download the image."
            else:
                reply = "Sorry I could not access the image."
            send_telegram(token, chat_id, reply)

        # VOICE handler
        elif "voice" in msg:
            file_url = get_file_url(token, msg["voice"]["file_id"])
            reply = "I received your voice message! Voice transcription coming soon. Please type your message for now."
            send_telegram(token, chat_id, reply)

        # TEXT handler
        elif "text" in msg:
            text = msg["text"]
            reply = ask_groq(text)
            send_telegram(token, chat_id, reply)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OpenClaw Bot is running!")
