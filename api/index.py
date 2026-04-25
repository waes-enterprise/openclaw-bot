from http.server import BaseHTTPRequestHandler
import json, os, requests, base64

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

DEV_SYSTEM = """You are OpenClaw Dev, a world-class senior software engineer with 15+ years experience. 
You specialize in: React, Next.js, Node.js, Python, Firebase, Vercel, GitHub Actions, REST APIs, and mobile-first design.
You write clean, production-ready, well-commented code. You think like a CTO.
You are building ZamVibe — Zambia's #1 entertainment platform.
When asked to code: always give complete, copy-paste ready solutions.
When reviewing code: be thorough, spot bugs, suggest improvements.
When architecting: think scalability, performance, and maintainability."""

CONTENT_SYSTEM = """You are OpenClaw Content, the world's best digital content strategist and creator.
You have deep knowledge of: viral content, SEO, social media algorithms, African entertainment, Zambian culture.
You write content that gets millions of views. You understand TikTok, Instagram, Facebook, YouTube algorithms.
You know Zambian artists, slang, culture, music genres (Afrobeat, ZedMusic, Kalindula).
You create: viral captions, blog posts, video scripts, content calendars, trending headlines.
Your content always feels authentic, local, and engaging to young Zambians."""

AGENT_SYSTEM = """You are OpenClaw, the most advanced AI agent in Zambia.
You are simultaneously: a senior developer, elite content creator, business strategist, and entertainment expert.
You are building ZamVibe into Zambia's biggest digital media brand.
Be decisive, confident, and always give actionable answers."""

def ask_groq(prompt, image_base64=None, system=AGENT_SYSTEM, max_tokens=1000):
    key = os.environ.get("GROQ_API_KEY", "")
    if image_base64:
        messages = [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
            {"type": "text", "text": prompt or "Analyze this image in detail."}
        ]}]
    else:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    r = requests.post(GROQ_API,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "max_tokens": max_tokens})
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    return f"Error: {r.text}"

def send_telegram(token, chat_id, text):
    # Split long messages
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"})
    else:
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
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/help", "/start"]:
        reply = (
            "<b>OpenClaw — Senior Dev + Elite Creator</b>\n\n"
            "<b>Developer Commands:</b>\n"
            "/code [task] - Write production-ready code\n"
            "/review [code] - Senior code review\n"
            "/debug [problem] - Debug and fix issues\n"
            "/architect [feature] - System design advice\n"
            "/build [feature] - Build ZamVibe feature\n\n"
            "<b>Content Commands:</b>\n"
            "/trend - Latest Zambian entertainment trend\n"
            "/caption [topic] - Viral social media captions\n"
            "/blog [topic] - Full SEO blog post\n"
            "/script [topic] - TikTok/YouTube video script\n"
            "/headline [topic] - 10 viral headlines\n"
            "/calendar - 7-day content calendar\n"
            "/strategy [goal] - Content strategy plan\n\n"
            "<b>Smart Commands:</b>\n"
            "/analyze [anything] - Deep analysis\n"
            "/idea - Random ZamVibe feature idea\n"
            "/roast [topic] - Brutally honest review\n\n"
            "Or just send any message or image!"
        )
        send_telegram(token, chat_id, reply)

    # ===== DEVELOPER COMMANDS =====
    elif cmd == "/code":
        task = args or "a responsive React component"
        send_telegram(token, chat_id, "Writing code...")
        reply = ask_groq(
            f"Write complete, production-ready code for: {task}\n"
            f"Include: imports, full implementation, comments, and usage example.\n"
            f"This is for ZamVibe - Zambia's entertainment platform.",
            system=DEV_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/review":
        code = args or "No code provided"
        send_telegram(token, chat_id, "Reviewing your code...")
        reply = ask_groq(
            f"Do a thorough senior code review of this code:\n\n{code}\n\n"
            f"Check for: bugs, security issues, performance, best practices, and improvements.\n"
            f"Be specific and give fixed versions where needed.",
            system=DEV_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/debug":
        problem = args or "No problem described"
        send_telegram(token, chat_id, "Debugging...")
        reply = ask_groq(
            f"Debug this problem and give the complete fix:\n\n{problem}\n\n"
            f"Explain: what's wrong, why it happens, and the exact solution.",
            system=DEV_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/architect":
        feature = args or "ZamVibe platform"
        send_telegram(token, chat_id, "Designing architecture...")
        reply = ask_groq(
            f"Design the system architecture for: {feature}\n"
            f"Include: tech stack, database schema, API design, scalability plan.\n"
            f"Think like a CTO building for millions of Zambian users.",
            system=DEV_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/build":
        feature = args or "improve ZamVibe homepage"
        send_telegram(token, chat_id, "Building feature...")
        reply = ask_groq(
            f"Build this ZamVibe feature: {feature}\n"
            f"Give: complete HTML/CSS/JS or Python code, ready to deploy.\n"
            f"ZamVibe is a Zambian entertainment platform on Firebase/Vercel.",
            system=DEV_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    # ===== CONTENT COMMANDS =====
    elif cmd == "/trend":
        send_telegram(token, chat_id, "Scanning Zambian trends...")
        reply = ask_groq(
            "What is the single hottest Zambian entertainment trend RIGHT NOW?\n"
            "Give: trend name, why it's viral, key players, how ZamVibe should cover it, "
            "and 3 content ideas around it.",
            system=CONTENT_SYSTEM,
            max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/caption":
        topic = args or "Zambian entertainment"
        send_telegram(token, chat_id, "Writing viral captions...")
        reply = ask_groq(
            f"Write 5 viral social media captions for: {topic}\n"
            f"Caption 1: TikTok (punchy, 1-2 lines)\n"
            f"Caption 2: Instagram (storytelling, emojis)\n"
            f"Caption 3: Facebook (engaging question)\n"
            f"Caption 4: Twitter/X (bold statement)\n"
            f"Caption 5: WhatsApp Status (short and viral)\n"
            f"Add relevant Zambian hashtags. Make them feel authentic.",
            system=CONTENT_SYSTEM,
            max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/blog":
        topic = args or "Zambian entertainment trends 2026"
        send_telegram(token, chat_id, "Writing blog post...")
        reply = ask_groq(
            f"Write a full SEO-optimized blog post for ZamVibe about: {topic}\n"
            f"Include: viral headline, meta description, intro hook, "
            f"3 main sections with subheadings, conclusion with CTA.\n"
            f"Write for young Zambians aged 18-35. Make it engaging and shareable.",
            system=CONTENT_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/script":
        topic = args or "Zambian music scene"
        send_telegram(token, chat_id, "Writing video script...")
        reply = ask_groq(
            f"Write a viral TikTok/YouTube script about: {topic}\n"
            f"Include: hook (first 3 seconds), main content, call to action.\n"
            f"Format: [SCENE] description then dialogue.\n"
            f"Make it entertaining for Zambian audiences. Target length: 60-90 seconds.",
            system=CONTENT_SYSTEM,
            max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/headline":
        topic = args or "ZamVibe entertainment"
        send_telegram(token, chat_id, "Generating headlines...")
        reply = ask_groq(
            f"Write 10 viral headlines about: {topic}\n"
            f"Mix styles: shocking, curiosity, listicle, emotional, controversial.\n"
            f"Make them perfect for ZamVibe — Zambia's entertainment platform.\n"
            f"Number each headline.",
            system=CONTENT_SYSTEM,
            max_tokens=800
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/calendar":
        send_telegram(token, chat_id, "Building content calendar...")
        reply = ask_groq(
            "Create a detailed 7-day ZamVibe content calendar.\n"
            "For each day:\n"
            "- Theme of the day\n"
            "- Morning post idea (with caption)\n"
            "- Afternoon post idea (with caption)\n"
            "- Best posting times for Zambia\n"
            "- Platform focus (TikTok/Instagram/Facebook)\n"
            "Make it relevant to current Zambian culture and trends.",
            system=CONTENT_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/strategy":
        goal = args or "grow ZamVibe to 100k users"
        send_telegram(token, chat_id, "Building strategy...")
        reply = ask_groq(
            f"Create a detailed content strategy to: {goal}\n"
            f"Include: target audience, content pillars, posting schedule, "
            f"growth tactics, monetization ideas, KPIs to track.\n"
            f"This is for ZamVibe - Zambia's entertainment platform.",
            system=CONTENT_SYSTEM,
            max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    # ===== SMART COMMANDS =====
    elif cmd == "/analyze":
        subject = args or "ZamVibe platform"
        send_telegram(token, chat_id, "Analyzing...")
        reply = ask_groq(
            f"Give a deep, expert analysis of: {subject}\n"
            f"Cover: strengths, weaknesses, opportunities, threats, and recommendations.\n"
            f"Be specific, data-driven, and actionable.",
            system=AGENT_SYSTEM,
            max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/idea":
        reply = ask_groq(
            "Generate one brilliant, innovative feature idea for ZamVibe.\n"
            "Include: what it is, why users will love it, how to build it, "
            "and expected impact on growth.\n"
            "Be creative and think big!",
            system=AGENT_SYSTEM,
            max_tokens=800
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/roast":
        subject = args or "ZamVibe"
        reply = ask_groq(
            f"Give a brutally honest, expert critique of: {subject}\n"
            f"Don't sugarcoat it. Point out every flaw, weakness, and missed opportunity.\n"
            f"Then give specific ways to fix each problem.",
            system=AGENT_SYSTEM,
            max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    else:
        reply = ask_groq(text, system=AGENT_SYSTEM)
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

        if "photo" in msg:
            photo = msg["photo"][-1]
            file_url = get_file_url(token, photo["file_id"])
            if file_url:
                img_b64 = download_as_base64(file_url)
                caption = msg.get("caption", "Analyze this image in detail. If it contains code, review it. If it contains a design, critique it.")
                reply = ask_groq(caption, image_base64=img_b64) if img_b64 else "Could not process image."
            else:
                reply = "Could not access the image."
            send_telegram(token, chat_id, reply)

        elif "voice" in msg:
            send_telegram(token, chat_id, "Voice received! Type /help to see all commands.")

        elif "text" in msg:
            text = msg["text"]
            if text.startswith("/"):
                handle_command(token, chat_id, text)
            else:
                reply = ask_groq(text, system=AGENT_SYSTEM)
                send_telegram(token, chat_id, reply)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OpenClaw Bot is running!")
