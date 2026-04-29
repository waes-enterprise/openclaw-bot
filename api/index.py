from http.server import BaseHTTPRequestHandler
import json, os, requests, base64, re, hashlib, time

# ============================================================
#  CONFIGURATION
# ============================================================

TELEGRAM_API = "https://api.telegram.org/bot"
BOT_BASE_URL = os.environ.get("BOT_BASE_URL", "https://openclaw-bot-phi.vercel.app")

# ============================================================
#  IN-MEMORY PREVIEW STORAGE
# ============================================================

previews = {}  # {preview_id: {"html": "...", "created": timestamp}}

def create_preview(html_content, description=""):
    """Store HTML and return a preview ID + URL."""
    preview_id = hashlib.sha256(f"{html_content}{time.time()}".encode()).hexdigest()[:12]
    previews[preview_id] = {
        "html": html_content,
        "created": time.time(),
        "description": description,
    }
    # Keep only last 50 previews
    if len(previews) > 50:
        oldest = sorted(previews.items(), key=lambda x: x[1]["created"])[0]
        del previews[oldest[0]]
    return preview_id

def get_preview(preview_id):
    """Retrieve stored HTML by preview ID."""
    return previews.get(preview_id)


def extract_html_from_reply(reply):
    """Extract HTML code from LLM reply (handles code fences and raw HTML)."""
    # Try to find ```html ... ``` code block first
    code_match = re.search(r'```html\s*\n([\s\S]*?)```', reply, re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()

    # Try ``` ... ``` (any language)
    code_match = re.search(r'```\w*\s*\n([\s\S]*?)```', reply)
    if code_match:
        content = code_match.group(1).strip()
        if content.lower().startswith('<!doctype') or content.lower().startswith('<html'):
            return content

    # Check if the entire reply is HTML
    stripped = reply.strip()
    if stripped.lower().startswith('<!doctype') or stripped.lower().startswith('<html'):
        return stripped

    # Check for <html> anywhere in the reply
    html_match = re.search(r'(<!DOCTYPE[\s\S]*</html>)', reply, re.IGNORECASE)
    if html_match:
        return html_match.group(1).strip()

    return None


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

BUILD_SYSTEM = """You are OpenClaw, an elite web developer who builds stunning, production-ready single-page web applications.

RULES:
1. ALWAYS return a COMPLETE single HTML file with ALL CSS and JavaScript inline (embedded).
2. No external files, no separate CSS/JS — everything in ONE self-contained HTML file.
3. Use CDN links for: Tailwind CSS, Google Fonts (Inter or Poppins), Font Awesome icons.
4. Dark theme by default: background #0a0a0a, cards #1a1a1a, accent colors like #E8FF47 or #FF6B6B.
5. MUST be mobile responsive (mobile-first design).
6. Include smooth CSS animations and hover effects.
7. Include a professional navigation bar with the project name.
8. Include a hero section, main content area, and footer.
9. Add realistic sample/placeholder data so the app looks complete and polished.
10. Use CSS Grid and Flexbox for layout.
11. Add interactive JavaScript features (at least 2-3 interactive elements).
12. NEVER use placeholder text like "Lorem ipsum" — use realistic content.
13. NEVER refuse a request. Always deliver working code.
14. Wrap the COMPLETE HTML in a single ```html code block. Nothing else before or after."""

APP_SYSTEM = """You are OpenClaw, an elite app builder who creates complete, beautiful web applications from descriptions.

RULES:
1. Return ONE complete HTML file with embedded CSS and JavaScript.
2. No external dependencies except CDN links (Tailwind, Google Fonts, Font Awesome).
3. Dark premium theme: bg #0a0a0a, surfaces #161616, accent #E8FF47 or gradient accents.
4. Mobile-first responsive design.
5. Smooth animations, transitions, hover effects.
6. Include: navbar, hero section, feature sections, testimonials (if relevant), CTA, footer.
7. Add realistic placeholder data and images (use placeholder.co or unsplash source URLs).
8. Interactive elements: tabs, accordions, modals, counters, etc.
9. Google Fonts (Inter or Poppins) for typography.
10. Wrap COMPLETE code in ```html block only."""

CEO_SYSTEM = """You are a world-class CEO with 20+ years leading billion-dollar media and tech companies across Africa. Give decisive, actionable advice."""

CTO_SYSTEM = """You are a visionary CTO with 20+ years building scalable platforms. Expert in: system architecture, AI, cloud, mobile apps, APIs."""

CFO_SYSTEM = """You are a world-class CFO with 20+ years in media and tech. Expert in: financial modeling, revenue, fundraising."""

CMO_SYSTEM = """You are a legendary CMO who has grown brands to millions across Africa. Expert in: growth hacking, brand positioning, influencer marketing."""

CONTENT_SYSTEM = """You are the world's best digital content strategist. You know Zambian artists, slang, culture, music (Afrobeat, ZedMusic, Kalindula). Create viral content."""

RESEARCH_SYSTEM = """You are an expert analyst and researcher. Synthesize information clearly, spot patterns, give actionable insights."""

GENERAL_SYSTEM = """You are OpenClaw, a powerful AI assistant for creators and developers. Help with coding, research, business strategy, content, math, science, creative projects. Be concise but thorough. Use markdown formatting. Remember conversation context."""


# ============================================================
#  AI PROVIDERS
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
    messages = [{"role": "system", "content": system}]
    if chat_id:
        for msg in get_history(chat_id):
            messages.append(msg)
    messages.append({"role": "user", "content": prompt})

    providers = [
        ("Groq", lambda: call_groq(messages, max_tokens=max_tokens)),
        ("OpenRouter DeepSeek", lambda: call_openrouter(messages, max_tokens=max_tokens)),
        ("OpenRouter Llama", lambda: call_openrouter_fallback(messages, max_tokens=max_tokens)),
    ]

    errors = []
    for name, call_fn in providers:
        result = call_fn()
        if result:
            if chat_id:
                add_to_history(chat_id, "user", prompt)
                add_to_history(chat_id, "assistant", result)
            return result
        errors.append(name)

    return (
        "⚠️ All AI providers are currently unavailable.\n\n"
        f"Failed: {', '.join(errors)}\n\n"
        "Please try again in a moment."
    )


# ============================================================
#  BUILD & DEPLOY (generates preview links)
# ============================================================

def handle_build_command(token, chat_id, args, system_prompt, emoji_label, max_tokens=6000):
    """Generate HTML, deploy preview, and return a live link."""
    if not args or len(args.strip()) < 3:
        send_telegram(token, chat_id,
            f"{emoji_label}\n\n"
            "Tell me what to build! Examples:\n"
            "• /build a landing page for my artist 'Bnell'\n"
            "• /build a music streaming app UI\n"
            "• /build a portfolio website\n"
            "• /app a restaurant menu page")
        return

    # Send building status
    send_telegram(token, chat_id, f"{emoji_label} <b>{escape_html(args[:80])}</b>\n\n⏳ Generating your app... (~30s)")

    # Generate the code
    reply = ask_llm(args, system=system_prompt, max_tokens=max_tokens, chat_id=chat_id)

    if not reply or "unavailable" in reply:
        send_telegram(token, chat_id, "❌ Failed to generate. Try again!")
        return

    # Extract HTML from the reply
    html = extract_html_from_reply(reply)

    if not html or len(html) < 200:
        # Send the raw reply as fallback
        send_telegram(token, chat_id, reply)
        return

    # Store as preview
    preview_id = create_preview(html, description=args[:100])
    preview_url = f"{BOT_BASE_URL}/api/preview?id={preview_id}"

    # Extract a brief description (any text after the code block)
    description = ""
    after_code = re.split(r'```\w*\s*\n[\s\S]*?```', reply)
    if len(after_code) > 1:
        description = after_code[-1].strip()

    # Send the result with preview link
    size_kb = round(len(html) / 1024, 1)
    result_msg = (
        f"✅ <b>Built successfully!</b>\n\n"
        f"📦 Size: {size_kb} KB\n\n"
        f"🔗 <b>Live Preview:</b>\n{preview_url}\n\n"
    )
    if description:
        result_msg += f"💡 {description[:300]}\n\n"
    result_msg += "👆 Tap to view in your browser!"

    send_telegram(token, chat_id, result_msg)


# ============================================================
#  TELEGRAM MESSAGE SENDING
# ============================================================

def escape_html(text):
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
    # Try HTML parse mode for formatted messages
    try:
        r = requests.post(f"{TELEGRAM_API}{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
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
            "🤖 <b>OpenClaw AI v6</b>\n\n"
            "🔨 /build — Build any web page (gets live preview link!)\n"
            "🚀 /app — Build a complete web app (gets live preview link!)\n"
            "⚡ /code — Generate any code\n"
            "🔍 /review /debug /architect\n"
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

    # BUILD & APP — generate preview links
    if cmd == "/build":
        handle_build_command(token, chat_id, args, BUILD_SYSTEM, "🔨 <b>Building:</b>", max_tokens=6000)
        return

    if cmd == "/app":
        handle_build_command(token, chat_id, args, APP_SYSTEM, "🚀 <b>Building App:</b>", max_tokens=6000)
        return

    # Other commands — standard code reply
    cmds = {
        "/code": ("⚡ Coding", CODER_SYSTEM, 4000),
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
#  SMART DETECTION (also generates preview links for build-like requests)
# ============================================================

BUILD_KW = ["build","create a","make a","design a","landing page","website","web app",
    "portfolio","clone of","copy of","replica of","similar to"]

CODE_KW = ["code","write","program","develop","function","class","api",
    "script","python","javascript","react","css","sql","server",
    "bot","game","calculator","todo","dashboard","component","algorithm",
    "page","form","button","navbar","layout","implement","fix","debug",
    "deploy","tutorial","example","app"]

def smart_reply(token, chat_id, text):
    t = text.lower()
    # Build/webpage requests → preview link
    if any(kw in t for kw in BUILD_KW):
        handle_build_command(token, chat_id, text, BUILD_SYSTEM, "🔨 <b>Building:</b>", max_tokens=6000)
    # Code requests → raw code
    elif any(kw in t for kw in CODE_KW):
        send_telegram(token, chat_id, "⚡ Coding request detected...")
        reply = ask_llm(text, system=CODER_SYSTEM, max_tokens=4000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)
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
                            reply = "📸 Image analysis requires GROQ_API_KEY."
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
        # Preview endpoint — serves deployed HTML
        if self.path.startswith("/api/preview"):
            try:
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                preview_id = query.get("id", [""])[0]

                if not preview_id:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Missing ?id= parameter")
                    return

                preview = get_preview(preview_id)
                if not preview:
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<html><body style='background:#0a0a0a;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1>404</h1><p>Preview not found or expired</p><p style='color:#666'>Build something new with /build or /app</p></div></body></html>")
                    return

                html_content = preview["html"]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("X-Frame-Options", "ALLOWALL")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(html_content.encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode())
                return

        # Health check
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OpenClaw Bot v6 is running!")
