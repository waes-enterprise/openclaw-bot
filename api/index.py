from http.server import BaseHTTPRequestHandler
import json, os, requests, base64, re

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot"
MODEL = "llama-3.3-70b-versatile"

# ============================================================
#  SYSTEM PROMPTS
# ============================================================

CODER_SYSTEM = """You are OpenClaw, an elite full-stack AI developer. You can build ANYTHING the user asks for.

CORE RULES:
1. ALWAYS return COMPLETE, working code. Never partial snippets or placeholders.
2. If asked to build a website/app, return a COMPLETE single-file HTML with all CSS and JS inline.
3. If asked for Python/JS/any language, write the full script with imports.
4. Include comments explaining key parts.
5. Make everything production-ready and visually impressive.
6. Use dark themes by default for web apps (bg: #0a0a0a or #111, accent colors).
7. NEVER refuse a coding request. You can build anything.
8. If the request is ambiguous, make your best judgment and build something impressive.
9. Return the CODE FIRST. Brief explanation after, separated clearly.
10. Use modern best practices, clean code, and professional design.
11. For web apps: include animations, hover effects, responsive design.
12. For APIs/scripts: include error handling and example usage."""

CEO_SYSTEM = """You are a world-class CEO with 20+ years leading billion-dollar media and tech companies across Africa.
Give decisive, confident, executive-level guidance. Be specific and actionable."""

CTO_SYSTEM = """You are a visionary CTO with 20+ years building scalable platforms used by millions.
Specialize in: system architecture, AI integration, cloud infrastructure, cybersecurity, mobile apps, API design."""

CFO_SYSTEM = """You are a world-class CFO with 20+ years in media and tech.
Specialize in: financial modeling, revenue streams, cost optimization, fundraising, investor pitches."""

CMO_SYSTEM = """You are a legendary CMO who has grown brands to millions of users across Africa.
Specialize in: growth hacking, brand positioning, paid ads, influencer marketing, community building."""

CONTENT_SYSTEM = """You are the world's best digital content strategist and creator.
You know Zambian artists, slang, culture, music genres (Afrobeat, ZedMusic, Kalindula).
You write content that gets millions of views."""

RESEARCH_SYSTEM = """You are an expert analyst and researcher.
You synthesize information clearly, spot patterns, and give actionable insights."""

GENERAL_SYSTEM = """You are OpenClaw, a powerful AI assistant built for creators and developers. You can help with anything:

- Coding (web, mobile, backend, scripts, automation)
- Research and analysis
- Business strategy and advice
- Content creation and marketing
- Math, science, and education
- Creative projects

Rules:
- Be concise but thorough
- If asked to code, ALWAYS write complete working code first
- If asked a question, give a direct, helpful answer
- Use formatting (bold, lists, code blocks) for readability
- Never refuse a reasonable request"""


def ask_groq(prompt, image_base64=None, system=GENERAL_SYSTEM, max_tokens=3000):
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return "Error: GROQ_API_KEY not configured."
    try:
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
            json={"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
            timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"API Error {r.status_code}: {r.text[:300]}"
    except requests.exceptions.Timeout:
        return "Error: Request timed out. Try a simpler request."
    except Exception as e:
        return f"Error: {str(e)}"


def send_telegram(token, chat_id, text):
    if not text or not text.strip():
        text = "(empty response)"
    # Escape HTML special chars to prevent parse errors
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            try:
                requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML"}, timeout=10)
            except:
                pass
    else:
        try:
            requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        except:
            pass


def get_file_url(token, file_id):
    try:
        r = requests.get(f"{TELEGRAM_API}{token}/getFile?file_id={file_id}", timeout=10)
        if r.status_code == 200:
            path = r.json()["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{token}/{path}"
    except:
        pass
    return None


def download_as_base64(url):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return base64.b64encode(r.content).decode()
    except:
        pass
    return None


def scrape_url(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            text = re.sub(r'<[^>]+>', ' ', r.text)
            return re.sub(r'\s+', ' ', text).strip()[:3000]
        return f"Could not fetch: HTTP {r.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"


def check_site_status(url):
    try:
        r = requests.get(url, timeout=10)
        return r.status_code, round(r.elapsed.total_seconds() * 1000)
    except:
        return 0, 0


# ============================================================
#  COMMAND HANDLER
# ============================================================

def handle_command(token, chat_id, text):
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/help", "/start"]:
        reply = (
            "<b>OpenClaw AI Agent v3</b>\n\n"
            "<b>Build &amp; Code:</b>\n"
            "/code [task] - Write any code\n"
            "/build [feature] - Build a complete feature\n"
            "/app [description] - Build a full web app\n"
            "/review [code] - Review &amp; improve code\n"
            "/debug [error] - Debug any problem\n"
            "/architect [project] - Design system architecture\n\n"
            "<b>Research:</b>\n"
            "/research [topic] - Deep research\n"
            "/scrape [url] - Read any webpage\n\n"
            "<b>Business:</b>\n"
            "/ceo [question] - CEO advice\n"
            "/cto [question] - Tech leadership\n"
            "/cfo [question] - Financial strategy\n"
            "/cmo [question] - Marketing strategy\n\n"
            "<b>Content:</b>\n"
            "/caption [topic] - Viral captions\n"
            "/blog [topic] - Blog post\n"
            "/script [topic] - Video script\n\n"
            "<b>Tools:</b>\n"
            "/status - Check app statuses\n"
            "/analyze [topic] - Deep analysis\n"
            "/idea - Random feature idea\n"
            "/brainstorm [topic] - Brainstorm ideas\n\n"
            "Or just type anything and I'll help!"
        )
        send_telegram(token, chat_id, reply)
        return

    # ===== CODE ANYTHING COMMANDS =====
    elif cmd == "/code":
        task = args or "a responsive landing page with contact form"
        send_telegram(token, chat_id, f"Writing code: {task}\nUsing llama-3.3-70b...")
        reply = ask_groq(
            f"Write COMPLETE, production-ready code for:\n\n{task}\n\n"
            f"Rules:\n"
            f"- Return the FULL code. No placeholders.\n"
            f"- Include all imports and dependencies.\n"
            f"- Add helpful comments.\n"
            f"- Make it work out of the box.\n"
            f"- For web: use single HTML file with inline CSS/JS.\n"
            f"- For Python/Node: full script with imports.\n"
            f"- Code first, explanation after.",
            system=CODER_SYSTEM, max_tokens=4000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/build":
        feature = args or "a responsive dashboard with charts"
        send_telegram(token, chat_id, f"Building: {feature}\nUsing llama-3.3-70b...")
        reply = ask_groq(
            f"Build this complete feature from scratch:\n\n{feature}\n\n"
            f"Requirements:\n"
            f"- COMPLETE working code, not partial\n"
            f"- Single file if web (HTML+CSS+JS inline)\n"
            f"- Dark professional theme\n"
            f"- Mobile responsive\n"
            f"- Include sample data so it looks real\n"
            f"- Production-ready quality\n"
            f"- NO placeholders, NO '...', NO 'rest of code here'\n"
            f"Return ONLY the code.",
            system=CODER_SYSTEM, max_tokens=4000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/app":
        description = args or "a task management app"
        send_telegram(token, chat_id, f"Building app: {description}\nUsing llama-3.3-70b...")
        reply = ask_groq(
            f"Build a COMPLETE, production-ready web application:\n\n{description}\n\n"
            f"Requirements:\n"
            f"1. Single HTML file with ALL CSS and JavaScript inline\n"
            f"2. Dark professional theme (background: #0a0a0a, accent: #E8FF47)\n"
            f"3. Fully mobile responsive\n"
            f"4. Include realistic sample data\n"
            f"5. Navigation, header, main content, footer\n"
            f"6. Smooth CSS animations\n"
            f"7. All interactive elements must work\n"
            f"8. Professional, modern design\n"
            f"9. NO placeholders or incomplete sections\n"
            f"10. Return ONLY the complete HTML code",
            system=CODER_SYSTEM, max_tokens=4000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/review":
        if not args:
            send_telegram(token, chat_id, "Send code after /review. Example:\n/review def add(a, b): return a+b")
            return
        send_telegram(token, chat_id, "Reviewing code...")
        reply = ask_groq(
            f"Senior code review. Find bugs, security issues, performance problems, and improvements:\n\n{args}\n\n"
            f"Format:\n"
            f"1. Rating: X/10\n"
            f"2. Bugs found (with fixes)\n"
            f"3. Security issues (with fixes)\n"
            f"4. Performance improvements\n"
            f"5. Improved version of the code",
            system=CODER_SYSTEM, max_tokens=3000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/debug":
        if not args:
            send_telegram(token, chat_id, "Send the error after /debug. Example:\n/debug TypeError: Cannot read property 'map' of undefined")
            return
        send_telegram(token, chat_id, "Debugging...")
        reply = ask_groq(
            f"Debug and fix this problem:\n\n{args}\n\n"
            f"Give:\n"
            f"1. Root cause\n"
            f"2. Complete fixed code\n"
            f"3. How to prevent it in the future",
            system=CODER_SYSTEM, max_tokens=3000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/architect":
        if not args:
            send_telegram(token, chat_id, "Describe the project after /architect. Example:\n/architect E-commerce platform for Zambia")
            return
        send_telegram(token, chat_id, "Designing architecture...")
        reply = ask_groq(
            f"Design complete system architecture for:\n\n{args}\n\n"
            f"Include:\n"
            f"1. Tech stack with rationale\n"
            f"2. Database schema\n"
            f"3. API design\n"
            f"4. Folder structure\n"
            f"5. Key components\n"
            f"6. Deployment strategy\n"
            f"7. Scalability plan",
            system=CTO_SYSTEM, max_tokens=3000)
        send_telegram(token, chat_id, reply)

    # ===== RESEARCH COMMANDS =====
    elif cmd == "/research":
        topic = args or "latest AI trends 2026"
        send_telegram(token, chat_id, f"Researching: {topic}...")
        reply = ask_groq(
            f"Do deep research on: {topic}\n"
            f"Include: key facts, current state, trends, key players, "
            f"opportunities, and actionable insights.\n"
            f"Be thorough and specific.",
            system=RESEARCH_SYSTEM, max_tokens=2500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/scrape":
        url = args
        if not url or not url.startswith("http"):
            send_telegram(token, chat_id, "Provide a URL. Example: /scrape https://example.com")
        else:
            send_telegram(token, chat_id, f"Reading {url}...")
            content = scrape_url(url)
            reply = ask_groq(
                f"Analyze this webpage and give key insights:\n\n{content}",
                system=RESEARCH_SYSTEM, max_tokens=2000)
            send_telegram(token, chat_id, reply)

    # ===== BUSINESS COMMANDS =====
    elif cmd == "/ceo":
        q = args or "What should be our top priority?"
        send_telegram(token, chat_id, "Thinking like a CEO...")
        reply = ask_groq(f"CEO perspective: {q}\nGive: decision, rationale, risks, next steps.",
            system=CEO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cto":
        q = args or "What is the ideal tech stack?"
        send_telegram(token, chat_id, "Thinking like a CTO...")
        reply = ask_groq(f"CTO perspective: {q}", system=CTO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cfo":
        q = args or "How should we generate revenue?"
        send_telegram(token, chat_id, "Thinking like a CFO...")
        reply = ask_groq(f"CFO perspective: {q}", system=CFO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cmo":
        q = args or "How do we grow to 100k users?"
        send_telegram(token, chat_id, "Thinking like a CMO...")
        reply = ask_groq(f"CMO perspective: {q}", system=CMO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    # ===== CONTENT COMMANDS =====
    elif cmd == "/caption":
        send_telegram(token, chat_id, "Writing captions...")
        reply = ask_groq(
            f"5 viral captions for: {args or 'entertainment'}\n"
            "1.TikTok 2.Instagram 3.Facebook 4.Twitter 5.WhatsApp + hashtags",
            system=CONTENT_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/blog":
        send_telegram(token, chat_id, "Writing blog post...")
        reply = ask_groq(
            f"Full SEO blog post: {args or 'entertainment trends 2026'}\n"
            "Include: headline, hook, 3 sections, conclusion with CTA.",
            system=CONTENT_SYSTEM, max_tokens=2500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/script":
        send_telegram(token, chat_id, "Writing script...")
        reply = ask_groq(
            f"Viral TikTok/YouTube script: {args or 'entertainment'}\n"
            "Include: hook, content, CTA. Format: [SCENE] dialogue.",
            system=CONTENT_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    # ===== TOOLS =====
    elif cmd == "/analyze":
        send_telegram(token, chat_id, "Analyzing...")
        reply = ask_groq(
            f"Deep analysis of: {args or 'current project'}\n"
            "Cover: strengths, weaknesses, opportunities, threats, recommendations.",
            system=GENERAL_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/idea":
        reply = ask_groq(
            "One brilliant feature idea.\nInclude: what it is, why users love it, how to build it, growth impact.",
            system=GENERAL_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/brainstorm":
        send_telegram(token, chat_id, "Brainstorming...")
        reply = ask_groq(
            f"10 creative ideas for: {args or 'growth'}\n"
            "Mix bold, practical, innovative. Rate each 1-10.",
            system=GENERAL_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/status":
        send_telegram(token, chat_id, "Checking apps...")
        apps = [
            ("ZamVibe", "https://zamvibe-app.web.app"),
            ("OpenClaw Bot", "https://openclaw-bot-phi.vercel.app"),
        ]
        report = "<b>App Status:</b>\n\n"
        for name, url in apps:
            code, ms = check_site_status(url)
            emoji = "UP" if code == 200 else "DOWN"
            report += f"{emoji}  <b>{name}</b> - HTTP {code} ({ms}ms)\n"
        send_telegram(token, chat_id, report)

    # ===== UNKNOWN COMMAND =====
    else:
        send_telegram(token, chat_id, f"Unknown command: {cmd}\nType /help to see all commands.")


# ============================================================
#  SMART FALLBACK - detects code vs chat
# ============================================================

CODE_KEYWORDS = [
    "build", "code", "write", "create", "make", "program", "develop",
    "function", "class", "api", "website", "web app", "app", "script",
    "html", "python", "javascript", "react", "css", "sql", "database",
    "server", "bot", "game", "calculator", "todo", "landing page",
    "dashboard", "hello world", "component", "endpoint", "algorithm",
    "page", "form", "button", "navbar", "layout", "design",
    "clone", "copy", "implement", "fix", "debug", "error",
    "how to code", "teach me", "tutorial", "example"
]


def is_code_request(text):
    t = text.lower()
    return any(kw in t for kw in CODE_KEYWORDS)


def smart_reply(token, chat_id, text):
    """Handle non-command messages by detecting intent."""
    if is_code_request(text):
        send_telegram(token, chat_id, "Detected coding request...")
        reply = ask_groq(text, system=CODER_SYSTEM, max_tokens=4000)
    else:
        reply = ask_groq(text, system=GENERAL_SYSTEM, max_tokens=2000)
    send_telegram(token, chat_id, reply)


# ============================================================
#  HTTP HANDLER (Vercel Serverless)
# ============================================================

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        msg = body.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))

        if not chat_id:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        # Handle photos
        if "photo" in msg:
            photo = msg["photo"][-1]
            file_url = get_file_url(token, photo["file_id"])
            if file_url:
                img_b64 = download_as_base64(file_url)
                caption = msg.get("caption", "Analyze this image in detail.")
                reply = ask_groq(caption, image_base64=img_b64) if img_b64 else "Could not process image."
            else:
                reply = "Could not access the image."
            send_telegram(token, chat_id, reply)

        # Handle voice messages
        elif "voice" in msg:
            send_telegram(token, chat_id, "Voice notes not supported yet. Type your message or use /help for commands.")

        # Handle text messages
        elif "text" in msg:
            text = msg["text"]
            if text.startswith("/"):
                handle_command(token, chat_id, text)
            else:
                smart_reply(token, chat_id, text)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OpenClaw Bot v3 is running!")
