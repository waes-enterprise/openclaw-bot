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

CEO_SYSTEM = """You are OpenClaw CEO, a world-class Chief Executive Officer with 20+ years leading 
billion-dollar media and tech companies across Africa and globally.
You think strategically, make bold decisions, and inspire teams.
You understand: vision setting, company culture, board relations, investor relations, 
market expansion, partnerships, crisis management, and scaling businesses.
You are building ZamVibe into Africa's biggest entertainment brand.
Give decisive, confident, executive-level guidance."""

CCO_SYSTEM = """You are OpenClaw CCO, an elite Chief Content Officer with 20+ years in global media.
You have launched content brands across Africa, Europe and USA.
You understand: content strategy, brand voice, audience development, monetization, 
editorial standards, influencer partnerships, and viral distribution.
You think in audiences, not just content. You build loyal communities.
Your job is to make ZamVibe the most trusted entertainment voice in Zambia."""

CFO_SYSTEM = """You are OpenClaw CFO, a world-class Chief Financial Officer with 20+ years in media and tech.
You specialize in: financial modeling, revenue streams, cost optimization, fundraising, 
investor pitches, cash flow management, African market economics, and startup finance.
You think in numbers, margins, and sustainable growth.
Help ZamVibe become financially strong and investor-ready."""

CMO_SYSTEM = """You are OpenClaw CMO, a legendary Chief Marketing Officer who has grown 
brands to millions of users across Africa.
You specialize in: growth hacking, brand positioning, paid ads, influencer marketing, 
community building, PR, viral campaigns, and African market penetration.
You know how to acquire users for almost nothing and retain them forever.
Make ZamVibe the most recognized entertainment brand in Zambia."""

CTO_SYSTEM = """You are OpenClaw CTO, a visionary Chief Technology Officer with 20+ years 
building scalable platforms used by millions.
You specialize in: system architecture, AI integration, cloud infrastructure, 
cybersecurity, mobile apps, API design, and tech team management.
You build technology that scales from 100 to 100 million users.
Make ZamVibe's tech stack world-class and future-proof."""

COO_SYSTEM = """You are OpenClaw COO, an expert Chief Operating Officer with 20+ years 
running operations for fast-growing media companies.
You specialize in: process optimization, team building, OKRs, project management, 
vendor relations, legal compliance, HR, and operational efficiency.
You turn chaotic startups into well-oiled machines.
Make ZamVibe run like a professional organization."""

LEGAL_SYSTEM = """You are OpenClaw Legal, a senior media and tech lawyer with 20+ years experience.
You specialize in: intellectual property, content licensing, data privacy (GDPR/POPIA), 
startup law, contracts, advertising law, and African media regulations.
Give clear, practical legal guidance for ZamVibe's operations.
Always note when professional legal counsel is needed."""

HR_SYSTEM = """You are OpenClaw HR, a world-class Chief People Officer with 20+ years 
building high-performance teams at media and tech companies.
You specialize in: talent acquisition, team culture, performance management, 
remote work, compensation, onboarding, and employee retention.
Help ZamVibe build a team that wins."""

SALES_SYSTEM = """You are OpenClaw Sales, an elite Chief Revenue Officer with 20+ years 
closing deals and building revenue engines for media companies.
You specialize in: advertising sales, sponsorships, brand partnerships, 
B2B sales, pricing strategy, and revenue diversification.
Help ZamVibe generate serious revenue from day one."""

AGENT_SYSTEM = """You are OpenClaw, the most advanced AI agent in Zambia — simultaneously a 
world-class CEO, CCO, CFO, CMO, CTO, COO, senior developer, and elite content creator.
You are building ZamVibe into Zambia's biggest digital media empire.
Be decisive, confident, strategic, and always give actionable, expert-level answers.
You think like a billion-dollar company but execute like a lean startup."""

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

def handle_command(token, chat_id, text):
    parts = text.split(None, 1)
    cmd = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ["/help", "/start"]:
        reply = (
            "<b>OpenClaw — Your AI Executive Team</b>\n\n"
            "<b>C-Suite Commands:</b>\n"
            "/ceo [question] - CEO strategy and vision\n"
            "/cco [question] - Content and brand strategy\n"
            "/cfo [question] - Finance and revenue\n"
            "/cmo [question] - Marketing and growth\n"
            "/cto [question] - Technology and architecture\n"
            "/coo [question] - Operations and processes\n"
            "/legal [question] - Legal guidance\n"
            "/hr [question] - People and team building\n"
            "/sales [question] - Revenue and partnerships\n\n"
            "<b>Executive Reports:</b>\n"
            "/boardreport - Full company status report\n"
            "/pitch - Investor pitch for ZamVibe\n"
            "/swot - SWOT analysis\n"
            "/roadmap - 90-day product roadmap\n"
            "/revenue - Revenue strategy\n\n"
            "<b>Developer Commands:</b>\n"
            "/code [task] - Write production code\n"
            "/review [code] - Senior code review\n"
            "/debug [problem] - Debug and fix\n"
            "/architect [feature] - System design\n"
            "/build [feature] - Build ZamVibe feature\n\n"
            "<b>Content Commands:</b>\n"
            "/trend - Latest Zambian trend\n"
            "/caption [topic] - Viral captions\n"
            "/blog [topic] - Full blog post\n"
            "/script [topic] - Video script\n"
            "/headline [topic] - Viral headlines\n"
            "/calendar - 7-day content calendar\n"
            "/strategy [goal] - Content strategy\n\n"
            "<b>Smart Commands:</b>\n"
            "/analyze [anything] - Deep analysis\n"
            "/idea - ZamVibe feature idea\n"
            "/roast [topic] - Honest critique\n"
            "/brainstorm [topic] - Ideas session\n\n"
            "Or send any message or image!"
        )
        send_telegram(token, chat_id, reply)

    # ===== C-SUITE COMMANDS =====
    elif cmd == "/ceo":
        question = args or "What should be ZamVibe's top priority right now?"
        send_telegram(token, chat_id, "Thinking like a CEO...")
        reply = ask_groq(
            f"As CEO of ZamVibe, answer this: {question}\n"
            f"Give: executive decision, strategic rationale, key risks, and next steps.",
            system=CEO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/cco":
        question = args or "How should ZamVibe build its content brand?"
        send_telegram(token, chat_id, "Thinking like a CCO...")
        reply = ask_groq(
            f"As CCO of ZamVibe, answer this: {question}\n"
            f"Give: content vision, brand voice, audience strategy, and execution plan.",
            system=CCO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/cfo":
        question = args or "How should ZamVibe generate revenue?"
        send_telegram(token, chat_id, "Thinking like a CFO...")
        reply = ask_groq(
            f"As CFO of ZamVibe, answer this: {question}\n"
            f"Give: financial analysis, revenue model, cost structure, and projections.",
            system=CFO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/cmo":
        question = args or "How do we grow ZamVibe to 100k users?"
        send_telegram(token, chat_id, "Thinking like a CMO...")
        reply = ask_groq(
            f"As CMO of ZamVibe, answer this: {question}\n"
            f"Give: marketing strategy, channels, campaigns, budget allocation, and KPIs.",
            system=CMO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/cto":
        question = args or "What is ZamVibe's ideal tech stack?"
        send_telegram(token, chat_id, "Thinking like a CTO...")
        reply = ask_groq(
            f"As CTO of ZamVibe, answer this: {question}\n"
            f"Give: technical recommendation, architecture decision, trade-offs, and implementation plan.",
            system=CTO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/coo":
        question = args or "How should ZamVibe structure its operations?"
        send_telegram(token, chat_id, "Thinking like a COO...")
        reply = ask_groq(
            f"As COO of ZamVibe, answer this: {question}\n"
            f"Give: operational framework, processes, team structure, and efficiency metrics.",
            system=COO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/legal":
        question = args or "What legal considerations does ZamVibe need to know?"
        send_telegram(token, chat_id, "Thinking like a lawyer...")
        reply = ask_groq(
            f"As legal counsel for ZamVibe, answer this: {question}\n"
            f"Give: legal analysis, risks, compliance requirements, and recommendations.",
            system=LEGAL_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/hr":
        question = args or "How should ZamVibe build its first team?"
        send_telegram(token, chat_id, "Thinking like a Chief People Officer...")
        reply = ask_groq(
            f"As Chief People Officer of ZamVibe, answer this: {question}\n"
            f"Give: hiring plan, team structure, culture recommendations, and compensation guidance.",
            system=HR_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/sales":
        question = args or "How should ZamVibe approach its first advertisers?"
        send_telegram(token, chat_id, "Thinking like a Chief Revenue Officer...")
        reply = ask_groq(
            f"As Chief Revenue Officer of ZamVibe, answer this: {question}\n"
            f"Give: sales strategy, target clients, pitch approach, pricing, and revenue targets.",
            system=SALES_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    # ===== EXECUTIVE REPORTS =====
    elif cmd == "/boardreport":
        send_telegram(token, chat_id, "Generating board report...")
        reply = ask_groq(
            "Generate a professional board report for ZamVibe covering:\n"
            "1. Executive Summary\n"
            "2. Product Status\n"
            "3. Content Performance\n"
            "4. Financial Overview\n"
            "5. Marketing & Growth\n"
            "6. Technology Updates\n"
            "7. Key Risks\n"
            "8. Next Quarter Priorities\n"
            "Make it professional and data-driven.",
            system=CEO_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/pitch":
        send_telegram(token, chat_id, "Building investor pitch...")
        reply = ask_groq(
            "Write a compelling investor pitch for ZamVibe:\n"
            "1. Problem we solve\n"
            "2. Our solution\n"
            "3. Market size (Zambia + Africa)\n"
            "4. Business model\n"
            "5. Traction so far\n"
            "6. Team\n"
            "7. Financial projections\n"
            "8. The ask (funding needed)\n"
            "Make it exciting and investor-ready.",
            system=CFO_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/swot":
        send_telegram(token, chat_id, "Running SWOT analysis...")
        reply = ask_groq(
            "Do a detailed SWOT analysis for ZamVibe:\n"
            "Strengths, Weaknesses, Opportunities, Threats.\n"
            "Be specific, honest, and strategic.\n"
            "End with 3 key strategic recommendations.",
            system=CEO_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/roadmap":
        send_telegram(token, chat_id, "Building 90-day roadmap...")
        reply = ask_groq(
            "Create a detailed 90-day roadmap for ZamVibe:\n"
            "Month 1: Foundation\n"
            "Month 2: Growth\n"
            "Month 3: Scale\n"
            "For each month include: product milestones, content goals, "
            "marketing targets, revenue goals, and team needs.",
            system=CEO_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/revenue":
        send_telegram(token, chat_id, "Building revenue strategy...")
        reply = ask_groq(
            "Create a comprehensive revenue strategy for ZamVibe:\n"
            "1. Primary revenue streams\n"
            "2. Advertising model\n"
            "3. Sponsorship opportunities\n"
            "4. Premium features\n"
            "5. Partnership revenue\n"
            "6. 12-month revenue projection\n"
            "Be specific about Zambian market rates and opportunities.",
            system=CFO_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    # ===== DEVELOPER COMMANDS =====
    elif cmd == "/code":
        task = args or "a responsive React component"
        send_telegram(token, chat_id, "Writing code...")
        reply = ask_groq(
            f"Write complete, production-ready code for: {task}\n"
            f"Include: imports, full implementation, comments, and usage example.",
            system=DEV_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/review":
        code = args or "No code provided"
        send_telegram(token, chat_id, "Reviewing code...")
        reply = ask_groq(
            f"Senior code review:\n\n{code}\n\n"
            f"Check: bugs, security, performance, best practices.",
            system=DEV_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/debug":
        problem = args or "No problem described"
        send_telegram(token, chat_id, "Debugging...")
        reply = ask_groq(
            f"Debug and fix: {problem}\n"
            f"Explain what's wrong and give the complete solution.",
            system=DEV_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/architect":
        feature = args or "ZamVibe platform"
        send_telegram(token, chat_id, "Designing architecture...")
        reply = ask_groq(
            f"System architecture for: {feature}\n"
            f"Include: tech stack, database, API design, scalability.",
            system=CTO_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/build":
        feature = args or "improve ZamVibe homepage"
        send_telegram(token, chat_id, "Building feature...")
        reply = ask_groq(
            f"Build this ZamVibe feature: {feature}\n"
            f"Give complete HTML/CSS/JS or Python code, ready to deploy.",
            system=DEV_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    # ===== CONTENT COMMANDS =====
    elif cmd == "/trend":
        send_telegram(token, chat_id, "Scanning Zambian trends...")
        reply = ask_groq(
            "Hottest Zambian entertainment trend RIGHT NOW?\n"
            "Give: trend name, why it's viral, key players, "
            "how ZamVibe should cover it, and 3 content ideas.",
            system=CONTENT_SYSTEM, max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/caption":
        topic = args or "Zambian entertainment"
        send_telegram(token, chat_id, "Writing viral captions...")
        reply = ask_groq(
            f"5 viral captions for: {topic}\n"
            f"1. TikTok 2. Instagram 3. Facebook 4. Twitter 5. WhatsApp\n"
            f"Add Zambian hashtags.",
            system=CONTENT_SYSTEM, max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/blog":
        topic = args or "Zambian entertainment 2026"
        send_telegram(token, chat_id, "Writing blog post...")
        reply = ask_groq(
            f"Full SEO blog post for ZamVibe about: {topic}\n"
            f"Include: headline, intro hook, 3 sections, conclusion with CTA.",
            system=CONTENT_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/script":
        topic = args or "Zambian music scene"
        send_telegram(token, chat_id, "Writing video script...")
        reply = ask_groq(
            f"Viral TikTok/YouTube script about: {topic}\n"
            f"Include: hook, content, CTA. Format: [SCENE] then dialogue.",
            system=CONTENT_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/headline":
        topic = args or "ZamVibe entertainment"
        reply = ask_groq(
            f"10 viral headlines about: {topic}\n"
            f"Mix: shocking, curiosity, listicle, emotional.",
            system=CONTENT_SYSTEM, max_tokens=800
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/calendar":
        send_telegram(token, chat_id, "Building content calendar...")
        reply = ask_groq(
            "7-day ZamVibe content calendar.\n"
            "Each day: theme, morning post, afternoon post, best times, platform focus.",
            system=CONTENT_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/strategy":
        goal = args or "grow ZamVibe to 100k users"
        send_telegram(token, chat_id, "Building strategy...")
        reply = ask_groq(
            f"Content strategy to: {goal}\n"
            f"Include: audience, content pillars, schedule, growth tactics, monetization, KPIs.",
            system=CONTENT_SYSTEM, max_tokens=2000
        )
        send_telegram(token, chat_id, reply)

    # ===== SMART COMMANDS =====
    elif cmd == "/analyze":
        subject = args or "ZamVibe platform"
        send_telegram(token, chat_id, "Analyzing...")
        reply = ask_groq(
            f"Deep expert analysis of: {subject}\n"
            f"Cover: strengths, weaknesses, opportunities, threats, recommendations.",
            system=AGENT_SYSTEM, max_tokens=1500
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/idea":
        reply = ask_groq(
            "One brilliant innovative feature idea for ZamVibe.\n"
            "Include: what it is, why users love it, how to build it, growth impact.",
            system=AGENT_SYSTEM, max_tokens=800
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/roast":
        subject = args or "ZamVibe"
        reply = ask_groq(
            f"Brutally honest critique of: {subject}\n"
            f"Every flaw and weakness. Then specific fixes for each.",
            system=AGENT_SYSTEM, max_tokens=1000
        )
        send_telegram(token, chat_id, reply)

    elif cmd == "/brainstorm":
        topic = args or "ZamVibe growth"
        send_telegram(token, chat_id, "Brainstorming...")
        reply = ask_groq(
            f"Generate 10 creative ideas for: {topic}\n"
            f"Mix bold, practical, and innovative ideas.\n"
            f"Rate each idea 1-10 for impact and feasibility.",
            system=AGENT_SYSTEM, max_tokens=1500
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
                caption = msg.get("caption", "Analyze this image. If code, review it. If design, critique it.")
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
