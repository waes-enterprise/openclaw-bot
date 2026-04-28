from http.server import BaseHTTPRequestHandler
import json, os, requests, base64, re, subprocess

# ============================================================
#  CONFIGURATION
# ============================================================

TELEGRAM_API = "https://api.telegram.org/bot"

# Use z-ai CLI as the LLM backend (always available, no API key needed)
ZAI_CLI = "z-ai"

# ============================================================
#  IN-MEMORY CONVERSATION HISTORY (per chat)
# ============================================================
MAX_HISTORY = 6  # messages per chat (keep low for CLI performance)

conversation_history = {}

def get_history(chat_id):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    return conversation_history[chat_id]

def add_to_history(chat_id, role, content):
    history = get_history(chat_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        conversation_history[chat_id] = history[-MAX_HISTORY:]

def clear_history(chat_id):
    if chat_id in conversation_history:
        del conversation_history[chat_id]

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
12. For APIs/scripts: include error handling and example usage.
13. IMPORTANT: Always wrap code in proper markdown code blocks with language identifier."""

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
- Never refuse a reasonable request
- Remember context from earlier messages in the conversation"""


# ============================================================
#  LLM VIA Z-AI CLI (Always available, no API key needed)
# ============================================================

def ask_llm(prompt, image_path=None, system=GENERAL_SYSTEM, max_tokens=4000, chat_id=None):
    """Call the z-ai CLI for LLM completions. Always available in the Vercel environment."""

    # Build the full prompt with system + history
    full_prompt = f"[System Instructions]\n{system}\n\n"

    # Add conversation history context
    if chat_id:
        history = get_history(chat_id)
        if history:
            full_prompt += "[Previous Conversation]\n"
            for msg in history[-4:]:  # Last 4 messages for context
                role_label = "User" if msg["role"] == "user" else "Assistant"
                # Truncate long history messages
                content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
                full_prompt += f"{role_label}: {content}\n"
            full_prompt += "\n"

    full_prompt += f"[Current Request]\n{prompt}"

    # Truncate for CLI limit
    if len(full_prompt) > 8000:
        full_prompt = full_prompt[:8000] + "\n[...truncated for length...]"

    try:
        # Use z-ai function for LLM chat completion
        args = '{"prompt": ' + json.dumps(full_prompt) + '}'

        if image_path and os.path.exists(image_path):
            # Use vision for images
            result = subprocess.run(
                ["z-ai", "vision", "-p", full_prompt, "-i", image_path],
                capture_output=True, text=True, timeout=90, cwd="/tmp"
            )
        else:
            # Use LLM chat
            result = subprocess.run(
                ["z-ai", "function", "-n", "chat_completion", "-a", args],
                capture_output=True, text=True, timeout=90, cwd="/tmp"
            )

        if result.returncode == 0:
            output = result.stdout.strip()
            # Parse JSON output from z-ai
            try:
                data = json.loads(output)
                # Try different response structures
                if isinstance(data, dict):
                    if "choices" in data:
                        content = data["choices"][0].get("message", {}).get("content", "")
                    elif "data" in data:
                        if isinstance(data["data"], dict):
                            content = data["data"].get("content", str(data["data"]))
                        else:
                            content = str(data["data"])
                    elif "content" in data:
                        content = data["content"]
                    else:
                        content = str(data)
                else:
                    content = str(data)

                if content:
                    # Save to history
                    if chat_id and not image_path:
                        add_to_history(chat_id, "user", prompt)
                        add_to_history(chat_id, "assistant", content)
                    return content
            except json.JSONDecodeError:
                # Return raw output if not JSON
                if output:
                    if chat_id and not image_path:
                        add_to_history(chat_id, "user", prompt)
                        add_to_history(chat_id, "assistant", output)
                    return output

    except subprocess.TimeoutExpired:
        return "⚠️ Response timed out. Try a shorter request."
    except FileNotFoundError:
        # z-ai CLI not found, try Groq fallback
        return ask_groq_fallback(prompt, system=system, max_tokens=max_tokens, chat_id=chat_id)
    except Exception as e:
        return ask_groq_fallback(prompt, system=system, max_tokens=max_tokens, chat_id=chat_id)

    return ask_groq_fallback(prompt, system=system, max_tokens=max_tokens, chat_id=chat_id)


def ask_groq_fallback(prompt, system=GENERAL_SYSTEM, max_tokens=3000, chat_id=None):
    """Fallback to Groq API if available."""
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        # Try OpenRouter
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not or_key:
            return "⚠️ AI service is temporarily unavailable. Please try again in a moment."

        try:
            messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {or_key}", "Content-Type": "application/json",
                         "HTTP-Referer": "https://openclaw-bot.vercel.app", "X-Title": "OpenClaw Bot"},
                json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": messages,
                      "max_tokens": max_tokens, "temperature": 0.7},
                timeout=60)
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"]["content"]
                if chat_id:
                    add_to_history(chat_id, "user", prompt)
                    add_to_history(chat_id, "assistant", content)
                return content
        except:
            pass

        return "⚠️ AI service is temporarily unavailable. Please try again in a moment."

    try:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages,
                  "max_tokens": max_tokens, "temperature": 0.7},
            timeout=45)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            if chat_id:
                add_to_history(chat_id, "user", prompt)
                add_to_history(chat_id, "assistant", content)
            return content
        return f"⚠️ AI API error. Please try again."
    except:
        return "⚠️ AI service is temporarily unavailable. Please try again in a moment."


# ============================================================
#  TELEGRAM MESSAGE SENDING (Fixed: proper code formatting)
# ============================================================

def escape_markdown_v2(text):
    """Escape special characters for Telegram MarkdownV2, but NOT inside code blocks."""
    special = r'_*[]()~`>#+-=|{}.!'
    result = ""
    i = 0
    in_code_block = False
    in_inline_code = False

    while i < len(text):
        ch = text[i]

        if text[i:i+3] == '```':
            in_code_block = not in_code_block
            result += '```'
            i += 3
            continue

        if ch == '`' and not in_code_block:
            in_inline_code = not in_inline_code
            result += '`'
            i += 1
            continue

        if in_code_block or in_inline_code:
            result += ch
            i += 1
            continue

        if ch in special:
            result += '\\' + ch
        else:
            result += ch
        i += 1

    return result


def send_telegram(token, chat_id, text):
    """Send a Telegram message with smart formatting."""
    if not text or not text.strip():
        text = "(empty response)"

    has_code_blocks = '```' in text

    if has_code_blocks:
        chunks = split_at_code_blocks(text, 3800)
        for chunk in chunks:
            send_single_message(token, chat_id, chunk, use_markdown=True)
    else:
        if len(text) <= 4000:
            send_single_message(token, chat_id, text, use_markdown=False)
        else:
            parts = text.split('\n\n')
            current = ""
            for part in parts:
                if len(current) + len(part) + 2 > 3800:
                    if current:
                        send_single_message(token, chat_id, current, use_markdown=False)
                    current = part
                else:
                    current += "\n\n" + part if current else part
            if current:
                send_single_message(token, chat_id, current, use_markdown=False)


def split_at_code_blocks(text, max_len):
    """Split text at code block boundaries to avoid breaking code."""
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
    return chunks if chunks else [text]


def send_single_message(token, chat_id, text, use_markdown=False):
    """Send a single Telegram message with retry."""
    if use_markdown:
        escaped = escape_markdown_v2(text)
        try:
            r = requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": escaped, "parse_mode": "MarkdownV2"}, timeout=10)
            if r.status_code == 200:
                return
        except:
            pass

        # Fallback to HTML with pre tags
        try:
            html_text = code_to_html(text)
            r = requests.post(f"{TELEGRAM_API}{token}/sendMessage",
                json={"chat_id": chat_id, "text": html_text, "parse_mode": "HTML"}, timeout=10)
            if r.status_code == 200:
                return
        except:
            pass

    # Final fallback: plain text
    try:
        requests.post(f"{TELEGRAM_API}{token}/sendMessage",
            json={"chat_id": chat_id, "text": text}, timeout=10)
    except:
        pass


def code_to_html(text):
    """Convert markdown code blocks to HTML pre/code tags."""
    result = re.sub(
        r'```(\w*)\n([\s\S]*?)```',
        lambda m: '<pre><code>' + html_escape(m.group(2)) + '</code></pre>',
        text
    )
    result = re.sub(r'`([^`]+)`', lambda m: '<code>' + html_escape(m.group(1)) + '</code>', result)
    return result


def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
#  UTILITY FUNCTIONS
# ============================================================

def get_file_url(token, file_id):
    try:
        r = requests.get(f"{TELEGRAM_API}{token}/getFile?file_id={file_id}", timeout=10)
        if r.status_code == 200:
            path = r.json()["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{token}/{path}"
    except:
        pass
    return None


def download_file(url, dest_path):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            with open(dest_path, 'wb') as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


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
            "🤖 <b>OpenClaw AI Agent v5</b>\n\n"
            "🔨 <b>Build &amp; Code:</b>\n"
            "/code [task] - Write any code\n"
            "/build [feature] - Build a complete feature\n"
            "/app [desc] - Build a full web app\n"
            "/review [code] - Review &amp; improve code\n"
            "/debug [error] - Debug any problem\n"
            "/architect [project] - Design architecture\n\n"
            "🔍 <b>Research:</b>\n"
            "/research [topic] - Deep research\n"
            "/scrape [url] - Read any webpage\n\n"
            "💼 <b>Business:</b>\n"
            "/ceo [question] - CEO advice\n"
            "/cto [question] - Tech leadership\n"
            "/cfo [question] - Financial strategy\n"
            "/cmo [question] - Marketing strategy\n\n"
            "📝 <b>Content:</b>\n"
            "/caption [topic] - Viral captions\n"
            "/blog [topic] - Blog post\n"
            "/script [topic] - Video script\n\n"
            "🛠 <b>Tools:</b>\n"
            "/status - Check app statuses\n"
            "/analyze [topic] - Deep analysis\n"
            "/idea - Random feature idea\n"
            "/brainstorm [topic] - Brainstorm ideas\n"
            "/clear - Clear chat history\n\n"
            "💬 Or just type anything and I'll help!\n"
            "📸 Send images for analysis"
        )
        send_telegram(token, chat_id, reply)
        return

    elif cmd == "/clear":
        clear_history(chat_id)
        send_telegram(token, chat_id, "🧹 Chat history cleared. Starting fresh!")
        return

    elif cmd == "/code":
        task = args or "a responsive landing page with contact form"
        send_telegram(token, chat_id, f"⚡ Writing code: {task}")
        reply = ask_llm(
            f"Write COMPLETE, production-ready code for:\n\n{task}\n\n"
            f"Rules:\n- Return the FULL code. No placeholders.\n"
            f"- Include all imports.\n- Code first, explanation after.\n"
            f"- For web: single HTML file with inline CSS/JS.\n"
            f"- For Python/Node: full script with imports.",
            system=CODER_SYSTEM, max_tokens=4000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/build":
        feature = args or "a responsive dashboard with charts"
        send_telegram(token, chat_id, f"🔨 Building: {feature}")
        reply = ask_llm(
            f"Build this complete feature:\n\n{feature}\n\n"
            f"Requirements:\n- COMPLETE working code\n"
            f"- Single file if web (HTML+CSS+JS inline)\n"
            f"- Dark theme, mobile responsive\n"
            f"- Include sample data\n"
            f"- NO placeholders or '...'\n"
            f"Return ONLY the complete code.",
            system=CODER_SYSTEM, max_tokens=4000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/app":
        description = args or "a task management app"
        send_telegram(token, chat_id, f"🚀 Building app: {description}")
        reply = ask_llm(
            f"Build a COMPLETE web app:\n\n{description}\n\n"
            f"1. Single HTML file with inline CSS/JS\n"
            f"2. Dark theme (#0a0a0a, accent: #E8FF47)\n"
            f"3. Mobile responsive\n"
            f"4. Realistic sample data\n"
            f"5. Navigation, header, footer\n"
            f"6. Smooth animations\n"
            f"7. All interactions must work\n"
            f"8. NO incomplete sections\n"
            f"Return ONLY the complete HTML.",
            system=CODER_SYSTEM, max_tokens=4000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/review":
        if not args:
            send_telegram(token, chat_id, "Send code after /review.")
            return
        send_telegram(token, chat_id, "🔍 Reviewing code...")
        reply = ask_llm(
            f"Senior code review:\n\n{args}\n\n"
            f"1. Rating X/10 2. Bugs 3. Security 4. Performance 5. Improved code",
            system=CODER_SYSTEM, max_tokens=3000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/debug":
        if not args:
            send_telegram(token, chat_id, "Send error after /debug.")
            return
        send_telegram(token, chat_id, "🐛 Debugging...")
        reply = ask_llm(
            f"Debug: {args}\n\n1. Root cause 2. Fixed code 3. Prevention",
            system=CODER_SYSTEM, max_tokens=3000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/architect":
        if not args:
            send_telegram(token, chat_id, "Describe project after /architect.")
            return
        send_telegram(token, chat_id, "🏗 Designing architecture...")
        reply = ask_llm(
            f"System architecture for: {args}\n"
            f"1. Tech stack 2. DB schema 3. API design 4. Folder structure "
            f"5. Components 6. Deployment 7. Scalability",
            system=CTO_SYSTEM, max_tokens=3000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/research":
        topic = args or "latest AI trends 2026"
        send_telegram(token, chat_id, f"📚 Researching: {topic}")
        reply = ask_llm(
            f"Deep research: {topic}\nKey facts, trends, players, opportunities.",
            system=RESEARCH_SYSTEM, max_tokens=2500, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/scrape":
        url = args
        if not url or not url.startswith("http"):
            send_telegram(token, chat_id, "Provide a URL. Example: /scrape https://example.com")
        else:
            send_telegram(token, chat_id, f"🌐 Reading {url}...")
            content = scrape_url(url)
            reply = ask_llm(f"Analyze: {content}", system=RESEARCH_SYSTEM, max_tokens=2000, chat_id=chat_id)
            send_telegram(token, chat_id, reply)

    elif cmd == "/ceo":
        q = args or "What should be our top priority?"
        send_telegram(token, chat_id, "💼 CEO mode...")
        reply = ask_llm(f"CEO perspective: {q}", system=CEO_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cto":
        q = args or "What is the ideal tech stack?"
        send_telegram(token, chat_id, "🖥 CTO mode...")
        reply = ask_llm(f"CTO perspective: {q}", system=CTO_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cfo":
        q = args or "How should we generate revenue?"
        send_telegram(token, chat_id, "💰 CFO mode...")
        reply = ask_llm(f"CFO perspective: {q}", system=CFO_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cmo":
        q = args or "How do we grow to 100k users?"
        send_telegram(token, chat_id, "📈 CMO mode...")
        reply = ask_llm(f"CMO perspective: {q}", system=CMO_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/caption":
        send_telegram(token, chat_id, "✍️ Writing captions...")
        reply = ask_llm(
            f"5 viral captions for: {args or 'entertainment'}\nTikTok, Instagram, Facebook, Twitter, WhatsApp + hashtags",
            system=CONTENT_SYSTEM, max_tokens=1500, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/blog":
        send_telegram(token, chat_id, "📝 Writing blog...")
        reply = ask_llm(
            f"SEO blog post: {args or 'entertainment trends'}\nHeadline, hook, 3 sections, CTA.",
            system=CONTENT_SYSTEM, max_tokens=2500, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/script":
        send_telegram(token, chat_id, "🎬 Writing script...")
        reply = ask_llm(
            f"Viral TikTok/YouTube script: {args or 'entertainment'}\nHook, content, CTA.",
            system=CONTENT_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/analyze":
        send_telegram(token, chat_id, "📊 Analyzing...")
        reply = ask_llm(
            f"SWOT analysis: {args or 'current project'}",
            system=GENERAL_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/idea":
        reply = ask_llm(
            "One brilliant feature idea: what, why users love it, how to build, growth impact.",
            system=GENERAL_SYSTEM, max_tokens=1500, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/brainstorm":
        send_telegram(token, chat_id, "🧠 Brainstorming...")
        reply = ask_llm(
            f"10 creative ideas for: {args or 'growth'}\nBold, practical, innovative. Rate 1-10.",
            system=GENERAL_SYSTEM, max_tokens=2000, chat_id=chat_id)
        send_telegram(token, chat_id, reply)

    elif cmd == "/status":
        send_telegram(token, chat_id, "📡 Checking apps...")
        apps = [
            ("ZamVibe", "https://zamvibe.vercel.app"),
            ("OpenClaw Bot", "https://openclaw-bot-phi.vercel.app"),
        ]
        report = "📡 <b>App Status:</b>\n\n"
        for name, url in apps:
            code, ms = check_site_status(url)
            status = "✅ UP" if code == 200 else "❌ DOWN"
            report += f"{status}  <b>{name}</b> - HTTP {code} ({ms}ms)\n"
        send_telegram(token, chat_id, report)

    else:
        send_telegram(token, chat_id, f"❓ Unknown: {cmd}\nType /help for commands.")


# ============================================================
#  SMART FALLBACK
# ============================================================

CODE_KEYWORDS = [
    "build", "code", "write", "create", "make", "program", "develop",
    "function", "class", "api", "website", "web app", "app", "script",
    "html", "python", "javascript", "react", "css", "sql", "database",
    "server", "bot", "game", "calculator", "todo", "landing page",
    "dashboard", "hello world", "component", "endpoint", "algorithm",
    "page", "form", "button", "navbar", "layout", "design",
    "clone", "copy", "implement", "fix", "debug", "error",
    "how to code", "teach me", "tutorial", "example", "deploy"
]


def is_code_request(text):
    t = text.lower()
    return any(kw in t for kw in CODE_KEYWORDS)


def smart_reply(token, chat_id, text):
    if is_code_request(text):
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
                import tempfile
                img_path = tempfile.mktemp(suffix=".jpg")
                if download_file(file_url, img_path):
                    caption = msg.get("caption", "Analyze this image in detail.")
                    reply = ask_llm(caption, image_path=img_path)
                    try:
                        os.remove(img_path)
                    except:
                        pass
                else:
                    reply = "Could not download image."
            else:
                reply = "Could not access image."
            send_telegram(token, chat_id, reply)

        # Handle voice
        elif "voice" in msg:
            send_telegram(token, chat_id, "🎤 Voice not supported yet. Type or use /help.")

        # Handle documents
        elif "document" in msg:
            doc = msg["document"]
            file_url = get_file_url(token, doc["file_id"])
            caption = msg.get("caption", "Analyze this file.")
            if file_url:
                import tempfile
                fpath = tempfile.mktemp(suffix=".txt")
                if download_file(file_url, fpath):
                    try:
                        with open(fpath, 'r', errors='ignore') as f:
                            file_content = f.read()[:8000]
                        reply = ask_llm(f"{caption}\n\n{file_content}", chat_id=chat_id)
                    except:
                        reply = "Couldn't read file."
                    try:
                        os.remove(fpath)
                    except:
                        pass
                else:
                    reply = "Couldn't download file."
            else:
                reply = "Couldn't access file."
            send_telegram(token, chat_id, reply)

        # Handle text
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
        self.wfile.write(b"OpenClaw Bot v5 is running! 🤖")
