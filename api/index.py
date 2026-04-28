from http.server import BaseHTTPRequestHandler
import json, os, requests, base64, re

# ============================================================
#  CONFIGURATION - Multiple AI providers for reliability
# ============================================================

TELEGRAM_API = "https://api.telegram.org/bot"

# Provider 1: Cloudflare Workers AI (free, no API key needed for some models)
# Provider 2: Groq (free tier, needs GROQ_API_KEY)
# Provider 3: OpenRouter (free tier, needs OPENROUTER_API_KEY)

# ============================================================
#  IN-MEMORY CONVERSATION HISTORY
# ============================================================
MAX_HISTORY = 8

conversation_history = {}

def get_history(chat_id):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content[:500]})
    if len(history) > MAX_HISTORY:
        conversation_history[chat_id] = history[-MAX_HISTORY:]

def clear_history(chat_id):
    if chat_id in conversation_history:
        del conversation_history[chat_id]


# ============================================================
#  SYSTEM PROMPTS
# ============================================================

CODER_SYSTEM = """You are OpenClaw, an elite full-stack AI developer. You can build ANYTHING.

RULES:
1. ALWAYS return COMPLETE, working code. Never partial snippets or placeholders.
2. For websites: single HTML file with ALL CSS and JS inline.
3. For Python/JS: full script with imports.
4. Dark themes by default (bg: #0a0a0a, accent: #E8FF47 or #FF6B6B).
5. Mobile responsive, animations, professional design.
6. NEVER refuse a coding request.
7. Code first, brief explanation after.
8. Wrap ALL code in markdown code blocks with language identifier (```html, ```python, etc)."""

CEO_SYSTEM = """You are a world-class CEO with 20+ years leading billion-dollar media and tech companies across Africa. Give decisive, actionable advice."""

CTO_SYSTEM = """You are a visionary CTO with 20+ years building scalable platforms. Expert in: system architecture, AI, cloud, mobile apps, APIs."""

CFO_SYSTEM = """You are a world-class CFO with 20+ years in media and tech. Expert in: financial modeling, revenue, fundraising."""

CMO_SYSTEM = """You are a legendary CMO who has grown brands to millions across Africa. Expert in: growth hacking, brand positioning, influencer marketing."""

CONTENT_SYSTEM = """You are the world's best digital content strategist. You know Zambian artists, slang, culture, music (Afrobeat, ZedMusic, Kalindula). Create viral content."""

RESEARCH_SYSTEM = """You are an expert analyst and researcher. Synthesize information clearly, spot patterns, give actionable insights."""

GENERAL_SYSTEM = """You are OpenClaw, a powerful AI assistant for creators and developers. Help with coding, research, business strategy, content, math, science, creative projects. Be concise but thorough. Use markdown formatting. Remember conversation context."""


# ============================================================
#  AI PROVIDERS - Try multiple for reliability
# ============================================================

def call_groq(messages, model="llama-3.3-70b-versatile", max_tokens=4000):
    """Provider 1: Groq (fast, free tier)."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return None
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=45)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None


def call_openrouter(messages, max_tokens=4000):
    """Provider 2: OpenRouter (free deepseek model)."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return None
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://openclaw-bot.vercel.app", "X-Title": "OpenClaw Bot"},
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": messages,
                  "max_tokens": max_tokens, "temperature": 0.7},
            timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None


def call_openrouter_fallback(messages, max_tokens=4000):
    """Provider 3: OpenRouter with alternative free model."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return None
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                     "HTTP-Referer": "https://openclaw-bot.vercel.app", "X-Title": "OpenClaw Bot"},
            json={"model": "meta-llama/llama-3.1-8b-instruct:free", "messages": messages,
                  "max_tokens": max_tokens, "temperature": 0.7},
            timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass
    return None


def ask_llm(prompt, system=GENERAL_SYSTEM, max_tokens=4000, chat_id=None):
    """Try multiple providers for maximum reliability."""

    # Build messages with system + history
    messages = [{"role": "system", "content": system}]

    # Add conversation history
    if chat_id:
        for msg in get_history(chat_id):
            messages.append(msg)

    # Add current prompt
    messages.append({"role": "user", "content": prompt})

    # Try each provider in order
    providers = [
        ("Groq", lambda: call_groq(messages, max_tokens=max_tokens)),
        ("OpenRouter DeepSeek", lambda: call_openrouter(messages, max_tokens=max_tokens)),
        ("OpenRouter Llama", lambda: call_openrouter_fallback(messages, max_tokens=max_tokens)),
    ]

    errors = []
    for name, call_fn in providers:
        result = call_fn()
        if result:
            # Save to history
            if chat_id:
                add_to_history(chat_id, "user", prompt)
                add_to_history(chat_id, "assistant", result)
            return result
        errors.append(name)

    # All providers failed
    return (
        "⚠️ All AI providers are currently unavailable.\n\n"
        f"Failed: {', '.join(errors)}\n\n"
        "To fix this, add an API key on Vercel:\n"
        "1. Go to vercel.com → openclaw-bot → Settings → Environment Variables\n"
        "2. Add GROQ_API_KEY from console.groq.com (free)\n"
        "3. Or add OPENROUTER_API_KEY from openrouter.ai (free)\n\n"
        "Please try again after adding a key."
    )


# ============================================================
#  TELEGRAM MESSAGE SENDING
# ============================================================

def escape_markdown_v2(text):
    """Escape for MarkdownV2, preserving code blocks."""
    special = r'_*[]()~`>#+-=|{}.!'
    result = ""
    i = 0
    in_code = False
    in_inline = False

    while i < len(text):
        ch = text[i]
        if text[i:i+3] == '```':
            in_code = not in_code
            result += '```'
            i += 3
            continue
        if ch == '`' and not in_code:
            in_inline = not in_inline
            result += '`'
            i += 1
            continue
        if in_code or in_inline:
            result += ch
            i += 1
            continue
        if ch in special:
            result += '\\' + ch
        else:
            result += ch
        i += 1
    return result


def split_at_code_blocks(text, max_len=3800):
    """Split text at code block boundaries."""
    chunks = []
    parts = re.split(r'(```[\s\S]*?```)', text)
    current = ""
    for part in parts:
        if len(current) + len(part) > max_len and current:
            chunks.append(current.strip())
            current = part
        else:
            current += part
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def code_to_html(text):
    """Convert code blocks to HTML pre/code."""
    result = re.sub(r'```(\w*)\n([\s\S]*?)```',
        lambda m: '<pre><code>' + m.group(2).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + '</code></pre>', text)
    result = re.sub(r'`([^`]+)`', lambda m: '<code>' + m.group(1).replace("&","&amp;").replace("<","&lt;") + '</code>', result)
    return result


def send_telegram(token, chat_id, text):
    if not text or not text.strip():
        text = "(empty response)"

    if '```' in text:
        for chunk in split_at_code_blocks(text):
            _send(token, chat_id, chunk)
    elif len(text) <= 4000:
        _send(token, chat_id, text)
    else:
        parts = text.split('\n\n')
        current = ""
        for p in parts:
            if len(current) + len(p) + 2 > 3800 and current:
                _send(token, chat_id, current)
                current = p
            else:
                current += "\n\n" + p if current else p
        if current:
            _send(token, chat_id, current)


def _send(token, chat_id, text):
    # Try MarkdownV2
    if '```' in text:
        try:
            r = requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": escape_markdown_v2(text), "parse_mode": "MarkdownV2"}, timeout=10)
            if r.status_code == 200:
                return
        except:
            pass
        # Fallback to HTML with code blocks
        try:
            r = requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": code_to_html(text), "parse_mode": "HTML"}, timeout=10)
            if r.status_code == 200:
                return
        except:
            pass
    # Plain text fallback
    try:
        requests.post(f"{TELEGRAM_API}{token}/sendMessage",
            json={"chat_id": chat_id, "text": text}, timeout=10)
    except:
        pass


# ============================================================
#  UTILITIES
# ============================================================

def get_file_url(token, file_id):
    try:
        r = requests.get(f"{TELEGRAM_API}{token}/getFile?file_id={file_id}", timeout=10)
        if r.status_code == 200:
            return f"https://api.telegram.org/file/bot{token}/{r.json()['result']['file_path']}"
    except:
        pass
    return None


def scrape_url(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', r.text)).strip()[:3000]
        return f"HTTP {r.status_code}"
    except Exception as e:
        return f"Error: {e}"


def check_site_status(url):
    try:
        r = requests.get(url, timeout=10)
        return r.status_code, round(r.elapsed.total_seconds() * 1000)
    except:
        return 0, 0


# ============================================================
#  COMMANDS
# ============================================================

def handle_command(token, chat_id, text):
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/help", "/start"]:
        send_telegram(token, chat_id,
            "🤖 <b>OpenClaw AI v5</b>\n\n"
            "🔨 /code /build /app /review /debug /architect\n"
            "🔍 /research /scrape\n"
            "💼 /ceo /cto /cfo /cmo\n"
            "📝 /caption /blog /script\n"
            "🛠 /status /analyze /idea /brainstorm /clear\n\n"
            "💬 Just type anything! 📸 Send images")
        return

    if cmd == "/clear":
        clear_history(chat_id)
        send_telegram(token, chat_id, "🧹 History cleared!")
        return

    cmds = {
        "/code": ("⚡ Coding", CODER_SYSTEM, 4000),
        "/build": ("🔨 Building", CODER_SYSTEM, 4000),
        "/app": ("🚀 App", CODER_SYSTEM, 4000),
        "/review": ("🔍 Reviewing", CODER_SYSTEM, 3000),
        "/debug": ("🐛 Debugging", CODER_SYSTEM, 3000),
        "/architect": ("🏗 Architecture", CTO_SYSTEM, 3000),
        "/research": ("📚 Researching", RESEARCH_SYSTEM, 2500),
        "/ceo": ("💼 CEO", CEO_SYSTEM, 2000),
        "/cto": ("🖥 CTO", CTO_SYSTEM, 2000),
        "/cfo": ("💰 CFO", CFO_SYSTEM, 2000),
        "/cmo": ("📈 CMO", CMO_SYSTEM, 2000),
        "/caption": ("✍️ Captions", CONTENT_SYSTEM, 1500),
        "/blog": ("📝 Blog", CONTENT_SYSTEM, 2500),
        "/script": ("🎬 Script", CONTENT_SYSTEM, 2000),
        "/analyze": ("📊 Analyzing", GENERAL_SYSTEM, 2000),
        "/brainstorm": ("🧠 Brainstorm", GENERAL_SYSTEM, 2000),
    }

    if cmd in cmds:
        emoji, sys_prompt, tokens = cmds[cmd]
        send_telegram(token, chat_id, f"{emoji} {args or cmd[1:]}...")
        reply = ask_llm(args or cmd, system=sys_prompt, max_tokens=tokens, chat_id=chat_id)
        send_telegram(token, chat_id, reply)
        return

    if cmd == "/idea":
        reply = ask_llm("One brilliant feature idea: what, why, how to build, impact.", system=GENERAL_SYSTEM, max_tokens=1500, chat_id=chat_id)
        send_telegram(token, chat_id, reply)
        return

    if cmd == "/scrape":
        if not args or not args.startswith("http"):
            send_telegram(token, chat_id, "Provide a URL: /scrape https://example.com")
        else:
            send_telegram(token, chat_id, f"🌐 Reading {args}...")
            content = scrape_url(args)
            reply = ask_llm(f"Analyze: {content}", system=RESEARCH_SYSTEM, max_tokens=2000, chat_id=chat_id)
            send_telegram(token, chat_id, reply)
        return

    if cmd == "/status":
        send_telegram(token, chat_id, "📡 Checking...")
        apps = [("ZamVibe", "https://zamvibe.vercel.app"), ("OpenClaw", "https://openclaw-bot-phi.vercel.app")]
        report = "📡 <b>Status:</b>\n\n"
        for name, url in apps:
            code, ms = check_site_status(url)
            report += f"{'✅' if code == 200 else '❌'} <b>{name}</b> - {code} ({ms}ms)\n"
        send_telegram(token, chat_id, report)
        return

    send_telegram(token, chat_id, f"❓ Unknown: {cmd}\nType /help")


# ============================================================
#  SMART DETECTION
# ============================================================

CODE_KW = ["build","code","write","create","make","program","develop","function","class","api",
    "website","web app","script","html","python","javascript","react","css","sql","server",
    "bot","game","calculator","todo","landing page","dashboard","component","algorithm",
    "page","form","button","navbar","layout","design","clone","implement","fix","debug",
    "deploy","tutorial","example","app"]

def smart_reply(token, chat_id, text):
    t = text.lower()
    if any(kw in t for kw in CODE_KW):
        send_telegram(token, chat_id, "⚡ Coding request detected...")
        reply = ask_llm(text, system=CODER_SYSTEM, max_tokens=4000, chat_id=chat_id)
    else:
        reply = ask_llm(text, system=GENERAL_SYSTEM, max_tokens=2000, chat_id=chat_id)
    send_telegram(token, chat_id, reply)


# ============================================================
#  HTTP HANDLER
# ============================================================

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except:
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK"); return

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK"); return

        msg = body.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if not chat_id:
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK"); return

        try:
            if "photo" in msg:
                photo = msg["photo"][-1]
                file_url = get_file_url(token, photo["file_id"])
                if file_url:
                    try:
                        img_data = requests.get(file_url, timeout=15).content
                        img_b64 = base64.b64encode(img_data).decode()
                        caption = msg.get("caption", "Analyze this image.")
                        # Use Groq vision if available
                        groq_key = os.environ.get("GROQ_API_KEY", "")
                        if groq_key:
                            vision_messages = [{"role": "user", "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                                {"type": "text", "text": caption}
                            ]}]
                            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                                json={"model": "llama-3.2-11b-vision-preview", "messages": vision_messages, "max_tokens": 1500},
                                timeout=45)
                            if r.status_code == 200:
                                reply = r.json()["choices"][0]["message"]["content"]
                            else:
                                reply = "Could not process image."
                        else:
                            reply = "📸 Image analysis requires GROQ_API_KEY to be set on Vercel.\nAdd it at: vercel.com → openclaw-bot → Settings → Environment Variables\nGet a free key at: console.groq.com"
                    except:
                        reply = "Could not process image."
                else:
                    reply = "Could not access image."
                send_telegram(token, chat_id, reply)

            elif "voice" in msg:
                send_telegram(token, chat_id, "🎤 Voice not supported. Type your message!")

            elif "document" in msg:
                send_telegram(token, chat_id, "📎 File support coming soon!")

            elif "text" in msg:
                text = msg["text"]
                if text.startswith("/"):
                    handle_command(token, chat_id, text)
                else:
                    smart_reply(token, chat_id, text)
        except Exception as e:
            try:
                send_telegram(token, chat_id, f"⚠️ Error: {str(e)[:200]}")
            except:
                pass

        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OpenClaw Bot v5 is running!")
