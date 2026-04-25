from http.server import BaseHTTPRequestHandler
import json, os, requests, base64

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def ask_groq(prompt, image_base64=None, system="You are OpenClaw, a smart AI assistant for ZamVibe, Zambia's #1 entertainment platform. Be helpful, friendly and concise."):
    key = os.environ.get("GROQ_API_KEY", "")
    if image_base64:
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            {"type": "text", "text": prompt or "Describe this image in detail."}
        ]}]
    else:
        messages = [
            {"role": "system", "content": system},
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
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

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

def handle_command(token, chat_id, text):
    cmd = text.split()[0].lower()
    args = text[len(cmd):].strip()

    if cmd == "/help" or cmd == "/start":
        reply = (
            "<b>OpenClaw Bot Commands</b>\n\n"
            "/trend - Get latest Zambian entertainment trend\n"
            "/caption [topic] - Write viral social media caption\n"
            "/blog [topic] - Generate a full blog post\n"
            "/build [feature] - Generate code for ZamVibe\n"
            "/calendar - Get this week's content plan\n"
            "/help - Show this menu\n\n"
            "Or just send me any message, image or question!"
        )

    elif cmd == "/trend":
        reply = ask_groq(
            "Give me the hottest Zambian entertainment trend right now. "
            "Include: what it is, why it's trending, and how ZamVibe should cover it. "
            "Be specific and exciting.",
            system="You are Zambia's top entertainment journalist."
        )

    elif cmd == "/caption":
        topic = args or "Zambian entertainment"
        reply = ask_groq(
            f"Write 3 viral social media captions for: {topic}\n"
            f"Make them perfect for TikTok, Instagram and Facebook.\n"
            f"Include relevant hashtags. Make them exciting and Zambian.",
            system="You are a viral social media expert specializing in Zambian content."
        )

    elif cmd == "/blog":
        topic = args or "Zambian entertainment trends"
        reply = ask_groq(
            f"Write a short punchy blog post for ZamVibe about: {topic}\n"
            f"Include: catchy headline, intro, 2 key points, conclusion.\n"
            f"Keep it under 300 words. Make it engaging for young Zambians.",
            system="You are ZamVibe's lead content writer."
        )

    elif cmd == "/build":
        feature = args or "improve the homepage"
        reply = ask_groq(
            f"Suggest how to implement this ZamVibe feature: {feature}\n"
            f"Give: 1) What to build 2) Which files to edit 3) Key code snippet.\n"
            f"Be specific and technical.",
            system="You are a senior full-stack developer building ZamVibe."
        )

    elif cmd == "/calendar":
        reply = ask_groq(
            "Create a 7-day content calendar for ZamVibe, Zambia's entertainment platform.\n"
            "For each day include: theme, post idea, best time to post.\n"
            "Make it relevant to Zambian culture and current trends.",
            system="You are a content strategist for Zambian media."
        )

    else:
        reply = ask_groq(text)

    send_telegram(token, chat_id, reply)

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
                caption = msg.get("caption", "Describe this image in detail.")
                reply = ask_groq(caption, image_base64=img_b64) if img_b64 else "Could not process image."
            else:
                reply = "Could not access the image."
            send_telegram(token, chat_id, reply)

        # VOICE handler
        elif "voice" in msg:
            send_telegram(token, chat_id, "I received your voice message! Type /help to see what I can do.")

        # COMMAND or TEXT handler
        elif "text" in msg:
            text = msg["text"]
            if text.startswith("/"):
                handle_command(token, chat_id, text)
            else:
                reply = ask_groq(text)
                send_telegram(token, chat_id, reply)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OpenClaw Bot is running!")
