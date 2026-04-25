from http.server import BaseHTTPRequestHandler
import json, os, requests, base64, re

GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
TELEGRAM_API = "https://api.telegram.org/bot"
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

DEV_SYSTEM = """You are OpenClaw Dev, a world-class senior software engineer with 15+ years experience. 
You specialize in: React, Next.js, Node.js, Python, Firebase, Vercel, GitHub Actions, REST APIs, and mobile-first design.
You write clean, production-ready, well-commented code. You think like a CTO.
You are building ZamVibe — Zambia's #1 entertainment platform.
When asked to code: always give complete, copy-paste ready solutions."""

CONTENT_SYSTEM = """You are OpenClaw Content, the world's best digital content strategist and creator.
You have deep knowledge of: viral content, SEO, social media algorithms, African entertainment, Zambian culture.
You write content that gets millions of views. You understand TikTok, Instagram, Facebook, YouTube algorithms.
You know Zambian artists, slang, culture, music genres (Afrobeat, ZedMusic, Kalindula)."""

CEO_SYSTEM = """You are OpenClaw CEO, a world-class Chief Executive Officer with 20+ years leading 
billion-dollar media and tech companies across Africa and globally.
You are building ZamVibe into Africa's biggest entertainment brand.
Give decisive, confident, executive-level guidance."""

CCO_SYSTEM = """You are OpenClaw CCO, an elite Chief Content Officer with 20+ years in global media.
You understand: content strategy, brand voice, audience development, monetization, 
editorial standards, influencer partnerships, and viral distribution."""

CFO_SYSTEM = """You are OpenClaw CFO, a world-class Chief Financial Officer with 20+ years in media and tech.
You specialize in: financial modeling, revenue streams, cost optimization, fundraising, 
investor pitches, cash flow management, African market economics, and startup finance."""

CMO_SYSTEM = """You are OpenClaw CMO, a legendary Chief Marketing Officer who has grown 
brands to millions of users across Africa.
You specialize in: growth hacking, brand positioning, paid ads, influencer marketing, 
community building, PR, viral campaigns, and African market penetration."""

CTO_SYSTEM = """You are OpenClaw CTO, a visionary Chief Technology Officer with 20+ years 
building scalable platforms used by millions.
You specialize in: system architecture, AI integration, cloud infrastructure, 
cybersecurity, mobile apps, API design, and tech team management."""

COO_SYSTEM = """You are OpenClaw COO, an expert Chief Operating Officer with 20+ years 
running operations for fast-growing media companies.
You specialize in: process optimization, team building, OKRs, project management, 
vendor relations, legal compliance, HR, and operational efficiency."""

LEGAL_SYSTEM = """You are OpenClaw Legal, a senior media and tech lawyer with 20+ years experience.
You specialize in: intellectual property, content licensing, data privacy, 
startup law, contracts, advertising law, and African media regulations."""

HR_SYSTEM = """You are OpenClaw HR, a world-class Chief People Officer with 20+ years 
building high-performance teams at media and tech companies."""

SALES_SYSTEM = """You are OpenClaw Sales, an elite Chief Revenue Officer with 20+ years 
closing deals and building revenue engines for media companies."""

RESEARCH_SYSTEM = """You are OpenClaw Research, an expert analyst and researcher.
You synthesize information clearly, spot patterns, and give actionable insights.
You research markets, competitors, trends, and technologies."""

DEVOPS_SYSTEM = """You are OpenClaw DevOps, a senior DevOps engineer with 15+ years experience.
You specialize in: CI/CD, Vercel, Firebase, GitHub Actions, monitoring, and deployment automation.
You make deployments fast, reliable, and automated."""

AGENT_SYSTEM = """You are OpenClaw, the most advanced AI agent in Zambia — simultaneously a 
world-class CEO, CCO, CFO, CMO, CTO, COO, senior developer, elite content creator,
expert researcher, and DevOps engineer.
You are building ZamVibe into Zambia's biggest digital media empire.
Be decisive, confident, strategic, and always give actionable, expert-level answers."""

def ask_groq(prompt, image_base64=None, system=AGENT_SYSTEM, max_tokens=1500):
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

def scrape_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OpenClaw/1.0)"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            text = re.sub(r'<[^>]+>', ' ', r.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:3000]
        return f"Could not fetch URL: {r.status_code}"
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def check_vercel_deployments(token):
    try:
        r = requests.get("https://api.vercel.com/v6/deployments",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 5})
        if r.status_code == 200:
            deployments = r.json().get("deployments", [])
            result = []
            for d in deployments:
                result.append(
                    f"• {d.get('name','?')} — {d.get('state','?')} "
                    f"({d.get('url','?')})"
                )
            return "\n".join(result) if result else "No deployments found"
        return f"Error: {r.status_code}"
    except Exception as e:
        return f"Error: {str(e)}"

def trigger_vercel_deploy(token, project_id):
    try:
        r = requests.post(f"https://api.vercel.com/v13/deployments",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"name": project_id, "target": "production"})
        return r.status_code in [200, 201, 202]
    except:
        return False

def check_site_status(url):
    try:
        r = requests.get(url, timeout=10)
        return r.status_code, round(r.elapsed.total_seconds() * 1000)
    except:
        return 0, 0

def handle_command(token, chat_id, text):
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""
    vercel_token = os.environ.get("VERCEL_TOKEN", "")

    if cmd in ["/help", "/start"]:
        reply = (
            "<b>OpenClaw — Full AI Operating System</b>\n\n"
            "<b>Research & Web:</b>\n"
            "/research [topic] - Deep research on any topic\n"
            "/scrape [url] - Read and analyze any webpage\n"
            "/competitor [url] - Analyze competitor site\n"
            "/trends - Scrape latest Zambian trends\n\n"
            "<b>Deployment & DevOps:</b>\n"
            "/deployments - Check all Vercel deployments\n"
            "/status - Check all your apps status\n"
            "/deploy [project] - Trigger deployment\n"
            "/logs - Check deployment logs\n\n"
            "<b>C-Suite Commands:</b>\n"
            "/ceo /cco /cfo /cmo /cto /coo /legal /hr /sales\n\n"
            "<b>Executive Reports:</b>\n"
            "/boardreport /pitch /swot /roadmap /revenue\n\n"
            "<b>Developer Commands:</b>\n"
            "/code /review /debug /architect /build\n\n"
            "<b>Content Commands:</b>\n"
            "/trend /caption /blog /script /headline /calendar /strategy\n\n"
            "<b>Smart Commands:</b>\n"
            "/analyze /idea /roast /brainstorm\n\n"
            "Send any message, URL or image!"
        )
        send_telegram(token, chat_id, reply)

    # ===== RESEARCH & WEB COMMANDS =====
    elif cmd == "/research":
        topic = args or "ZamVibe competitors in Africa"
        send_telegram(token, chat_id, f"Researching: {topic}...")
        reply = ask_groq(
            f"Do deep research on: {topic}\n"
            f"Include: key facts, current state, trends, key players, "
            f"opportunities, and actionable insights for ZamVibe.\n"
            f"Be thorough and specific.",
            system=RESEARCH_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/scrape":
        url = args
        if not url or not url.startswith("http"):
            send_telegram(token, chat_id, "Please provide a URL. Example: /scrape https://example.com")
        else:
            send_telegram(token, chat_id, f"Reading {url}...")
            content = scrape_url(url)
            analysis = ask_groq(
                f"Analyze this webpage content and give key insights:\n\n{content}",
                system=RESEARCH_SYSTEM, max_tokens=1000
            )
            send_telegram(token, chat_id, analysis)

    elif cmd == "/competitor":
        url = args
        if not url or not url.startswith("http"):
            send_telegram(token, chat_id, "Please provide a competitor URL. Example: /competitor https://competitor.com")
        else:
            send_telegram(token, chat_id, f"Analyzing competitor: {url}...")
            content = scrape_url(url)
            analysis = ask_groq(
                f"Analyze this competitor website for ZamVibe:\n\n{content}\n\n"
                f"Give: what they do well, weaknesses, opportunities for ZamVibe, "
                f"and how to outcompete them.",
                system=RESEARCH_SYSTEM, max_tokens=1500
            )
            send_telegram(token, chat_id, analysis)

    elif cmd == "/trends":
        send_telegram(token, chat_id, "Researching Zambian trends...")
        zed_content = scrape_url("https://www.znbc.co.zm")
        analysis = ask_groq(
            f"Based on this Zambian news content, what are the top entertainment trends?\n\n"
            f"{zed_content}\n\n"
            f"Give: top 5 trends, why each is trending, and content ideas for ZamVibe.",
            system=CONTENT_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, analysis)

    # ===== DEPLOYMENT & DEVOPS COMMANDS =====
    elif cmd == "/deployments":
        send_telegram(token, chat_id, "Checking Vercel deployments...")
        if vercel_token:
            status = check_vercel_deployments(vercel_token)
            send_telegram(token, chat_id, f"<b>Vercel Deployments:</b>\n{status}")
        else:
            send_telegram(token, chat_id,
                "VERCEL_TOKEN not set. Add it to Vercel environment variables to enable deployment tracking.")

    elif cmd == "/status":
        send_telegram(token, chat_id, "Checking all apps...")
        apps = [
            ("ZamVibe", "https://zamvibe-app.web.app"),
            ("OpenClaw Bot", "https://openclaw-bot-phi.vercel.app"),
            ("Housemate ZM", "https://housemate-zm.vercel.app"),
        ]
        report = "<b>App Status Report:</b>\n\n"
        for name, url in apps:
            code, ms = check_site_status(url)
            emoji = "✅" if code == 200 else "❌"
            speed = f"{ms}ms" if ms > 0 else "timeout"
            report += f"{emoji} <b>{name}</b>\n{url}\nHTTP {code} | {speed}\n\n"
        send_telegram(token, chat_id, report)

    elif cmd == "/deploy":
        project = args or "zamvibe"
        send_telegram(token, chat_id,
            f"To deploy {project} to Vercel:\n\n"
            f"1. Go to vercel.com/{project}\n"
            f"2. Click Deployments\n"
            f"3. Click Redeploy\n\n"
            f"Or push to GitHub main branch to auto-deploy.\n\n"
            f"Want me to generate a GitHub Actions deployment workflow for {project}?"
        )

    elif cmd == "/logs":
        send_telegram(token, chat_id,
            "<b>Check logs here:</b>\n\n"
            "Vercel: vercel.com/waes-enterprise\n"
            "GitHub Actions: github.com/waes-enterprise/openclaw-agent/actions\n"
            "Firebase: console.firebase.google.com\n\n"
            "What specific error are you seeing? Send it and I'll debug it."
        )

    # ===== C-SUITE COMMANDS =====
    elif cmd == "/ceo":
        question = args or "What should be ZamVibe's top priority right now?"
        send_telegram(token, chat_id, "Thinking like a CEO...")
        reply = ask_groq(
            f"As CEO of ZamVibe: {question}\n"
            f"Give: decision, strategic rationale, risks, next steps.",
            system=CEO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cco":
        question = args or "How should ZamVibe build its content brand?"
        send_telegram(token, chat_id, "Thinking like a CCO...")
        reply = ask_groq(f"As CCO of ZamVibe: {question}",
            system=CCO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cfo":
        question = args or "How should ZamVibe generate revenue?"
        send_telegram(token, chat_id, "Thinking like a CFO...")
        reply = ask_groq(f"As CFO of ZamVibe: {question}",
            system=CFO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cmo":
        question = args or "How do we grow ZamVibe to 100k users?"
        send_telegram(token, chat_id, "Thinking like a CMO...")
        reply = ask_groq(f"As CMO of ZamVibe: {question}",
            system=CMO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/cto":
        question = args or "What is ZamVibe's ideal tech stack?"
        send_telegram(token, chat_id, "Thinking like a CTO...")
        reply = ask_groq(f"As CTO of ZamVibe: {question}",
            system=CTO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/coo":
        question = args or "How should ZamVibe structure its operations?"
        send_telegram(token, chat_id, "Thinking like a COO...")
        reply = ask_groq(f"As COO of ZamVibe: {question}",
            system=COO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/legal":
        question = args or "What legal considerations does ZamVibe need?"
        send_telegram(token, chat_id, "Thinking like a lawyer...")
        reply = ask_groq(f"As legal counsel for ZamVibe: {question}",
            system=LEGAL_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/hr":
        question = args or "How should ZamVibe build its first team?"
        send_telegram(token, chat_id, "Thinking like a CPO...")
        reply = ask_groq(f"As Chief People Officer of ZamVibe: {question}",
            system=HR_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/sales":
        question = args or "How should ZamVibe approach its first advertisers?"
        send_telegram(token, chat_id, "Thinking like a CRO...")
        reply = ask_groq(f"As Chief Revenue Officer of ZamVibe: {question}",
            system=SALES_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    # ===== EXECUTIVE REPORTS =====
    elif cmd == "/boardreport":
        send_telegram(token, chat_id, "Generating board report...")
        reply = ask_groq(
            "Generate a professional board report for ZamVibe covering:\n"
            "1. Executive Summary 2. Product Status 3. Content Performance\n"
            "4. Financial Overview 5. Marketing & Growth 6. Technology\n"
            "7. Key Risks 8. Next Quarter Priorities",
            system=CEO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/pitch":
        send_telegram(token, chat_id, "Building investor pitch...")
        reply = ask_groq(
            "Investor pitch for ZamVibe:\n"
            "1. Problem 2. Solution 3. Market size\n"
            "4. Business model 5. Traction 6. Team\n"
            "7. Financials 8. The ask",
            system=CFO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/swot":
        send_telegram(token, chat_id, "Running SWOT analysis...")
        reply = ask_groq(
            "SWOT analysis for ZamVibe. Be specific and honest. "
            "End with 3 key strategic recommendations.",
            system=CEO_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/roadmap":
        send_telegram(token, chat_id, "Building 90-day roadmap...")
        reply = ask_groq(
            "90-day roadmap for ZamVibe:\n"
            "Month 1: Foundation, Month 2: Growth, Month 3: Scale\n"
            "For each: product milestones, content goals, marketing, revenue, team.",
            system=CEO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/revenue":
        send_telegram(token, chat_id, "Building revenue strategy...")
        reply = ask_groq(
            "Revenue strategy for ZamVibe:\n"
            "1. Primary streams 2. Advertising 3. Sponsorships\n"
            "4. Premium features 5. Partnerships 6. 12-month projection",
            system=CFO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    # ===== DEVELOPER COMMANDS =====
    elif cmd == "/code":
        task = args or "a responsive React component"
        send_telegram(token, chat_id, "Writing code...")
        reply = ask_groq(
            f"Write complete production-ready code for: {task}\n"
            f"Include imports, full implementation, comments, usage example.",
            system=DEV_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/review":
        send_telegram(token, chat_id, "Reviewing code...")
        reply = ask_groq(
            f"Senior code review:\n\n{args}\n\n"
            f"Check: bugs, security, performance, best practices.",
            system=DEV_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/debug":
        send_telegram(token, chat_id, "Debugging...")
        reply = ask_groq(
            f"Debug and fix: {args}\nExplain what's wrong and give the complete solution.",
            system=DEV_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/architect":
        send_telegram(token, chat_id, "Designing architecture...")
        reply = ask_groq(
            f"System architecture for: {args}\n"
            f"Include: tech stack, database, API design, scalability.",
            system=CTO_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/build":
        send_telegram(token, chat_id, "Building feature...")
        reply = ask_groq(
            f"Build this ZamVibe feature: {args}\n"
            f"Give complete HTML/CSS/JS or Python code ready to deploy.",
            system=DEV_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    # ===== CONTENT COMMANDS =====
    elif cmd == "/trend":
        send_telegram(token, chat_id, "Scanning trends...")
        reply = ask_groq(
            "Hottest Zambian entertainment trend RIGHT NOW?\n"
            "Give: trend, why viral, key players, content ideas for ZamVibe.",
            system=CONTENT_SYSTEM, max_tokens=1000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/caption":
        send_telegram(token, chat_id, "Writing captions...")
        reply = ask_groq(
            f"5 viral captions for: {args or 'Zambian entertainment'}\n"
            f"1.TikTok 2.Instagram 3.Facebook 4.Twitter 5.WhatsApp + hashtags",
            system=CONTENT_SYSTEM, max_tokens=1000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/blog":
        send_telegram(token, chat_id, "Writing blog post...")
        reply = ask_groq(
            f"Full SEO blog post for ZamVibe: {args or 'Zambian entertainment 2026'}\n"
            f"Include: headline, hook, 3 sections, conclusion with CTA.",
            system=CONTENT_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/script":
        send_telegram(token, chat_id, "Writing script...")
        reply = ask_groq(
            f"Viral TikTok/YouTube script: {args or 'Zambian music scene'}\n"
            f"Include: hook, content, CTA. Format: [SCENE] then dialogue.",
            system=CONTENT_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/headline":
        reply = ask_groq(
            f"10 viral headlines: {args or 'ZamVibe entertainment'}\n"
            f"Mix: shocking, curiosity, listicle, emotional.",
            system=CONTENT_SYSTEM, max_tokens=800)
        send_telegram(token, chat_id, reply)

    elif cmd == "/calendar":
        send_telegram(token, chat_id, "Building calendar...")
        reply = ask_groq(
            "7-day ZamVibe content calendar.\n"
            "Each day: theme, morning post, afternoon post, best times, platform.",
            system=CONTENT_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/strategy":
        send_telegram(token, chat_id, "Building strategy...")
        reply = ask_groq(
            f"Content strategy to: {args or 'grow ZamVibe to 100k users'}\n"
            f"Include: audience, pillars, schedule, growth tactics, monetization, KPIs.",
            system=CONTENT_SYSTEM, max_tokens=2000)
        send_telegram(token, chat_id, reply)

    # ===== SMART COMMANDS =====
    elif cmd == "/analyze":
        send_telegram(token, chat_id, "Analyzing...")
        reply = ask_groq(
            f"Deep analysis of: {args or 'ZamVibe platform'}\n"
            f"Cover: strengths, weaknesses, opportunities, threats, recommendations.",
            system=AGENT_SYSTEM, max_tokens=1500)
        send_telegram(token, chat_id, reply)

    elif cmd == "/idea":
        reply = ask_groq(
            "One brilliant ZamVibe feature idea.\n"
            "Include: what it is, why users love it, how to build it, growth impact.",
            system=AGENT_SYSTEM, max_tokens=800)
        send_telegram(token, chat_id, reply)

    elif cmd == "/roast":
        reply = ask_groq(
            f"Brutally honest critique of: {args or 'ZamVibe'}\n"
            f"Every flaw and weakness. Then specific fixes.",
            system=AGENT_SYSTEM, max_tokens=1000)
        send_telegram(token, chat_id, reply)

    elif cmd == "/brainstorm":
        send_telegram(token, chat_id, "Brainstorming...")
        reply = ask_groq(
            f"10 creative ideas for: {args or 'ZamVibe growth'}\n"
            f"Mix bold, practical, innovative. Rate each 1-10.",
            system=AGENT_SYSTEM, max_tokens=1500)
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
                caption = msg.get("caption",
                    "Analyze this image. If code, review it. If design, critique it.")
                reply = ask_groq(caption, image_base64=img_b64) if img_b64 else "Could not process image."
            else:
                reply = "Could not access the image."
            send_telegram(token, chat_id, reply)

        elif "voice" in msg:
            send_telegram(token, chat_id,
                "Voice received! Type /help to see all commands.")

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
