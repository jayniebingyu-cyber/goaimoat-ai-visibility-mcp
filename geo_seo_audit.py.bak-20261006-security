#!/usr/bin/env python3
"""GEO+SEO 网站评估引擎：技术扫描 + DeepSeek 生成评分报告。

供 geo_audit_service.py（webhook 服务）调用，也可独立运行：
    python3 geo_seo_audit.py https://example.com
"""
import json, re, os, time
import urllib.request
from urllib.parse import urlparse

# AI 爬虫 user-agent 清单（源自 geo-seo-optimizer skill，实测口径）
AI_BOTS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "Claude-User",
    "PerplexityBot", "Perplexity-User",
    "Google-Extended", "Applebot-Extended", "Googlebot",
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# 完整浏览器 headers（Cloudflare 反爬会检测 header 完整性 + UA 一致性）
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


def fetch(url, timeout=20):
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 503, 403):
                time.sleep(2 + attempt * 3)  # 限流/反爬退避重试
                continue
            raise
        except Exception as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def _clean(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def scan_site(url):
    """技术基线扫描，返回可事实核对的 checks dict（零虚构）。"""
    url = url.rstrip("/")
    c = {"url": url}
    try:
        html = fetch(url)
        c["accessible"] = True
    except Exception as e:
        c["accessible"] = False
        c["error"] = f"{type(e).__name__}: {e}"[:120]
        # 降级：用 Google 索引（Serper）判断「Google 眼里网站是否可见」，
        # 避免把 Cloudflare 拦截（我们被拦，但 Googlebot 不被拦）误判为「网站差」。
        host = (urlparse(url).hostname or "").replace("www.", "")
        g = google_index_lookup(host) if host else {}
        if g.get("g_indexed"):
            c["accessible"] = True
            c["via_google_index"] = True
            c["title"] = g.get("g_title")
            c["meta_description"] = g.get("g_description")
        return c

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    c["title"] = _clean(m.group(1))[:120] if m else None

    m = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    c["meta_description"] = (m.group(1)[:160] if m else None)

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
    c["h1_count"] = len(h1s)
    c["h1"] = _clean(h1s[0])[:120] if h1s else None

    m = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)', html, re.I)
    c["canonical"] = m.group(1) if m else None

    c["viewport"] = bool(re.search(r'name=["\']viewport["\']', html, re.I))
    c["lang"] = (re.search(r'<html[^>]*lang=["\']([^"\']+)', html, re.I) or [None, None])[1]

    schemas = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.I | re.S)
    types = []
    for s in schemas:
        types += re.findall(r'"@type"\s*:\s*"([^"]+)"', s)
    c["schema_types"] = sorted(set(types))
    c["has_org_schema"] = "Organization" in types
    c["has_faq_schema"] = "FAQPage" in types
    # 提取 Organization Schema 的 name（用于品牌名推断，优先于 title 瞎猜）
    org_name = None
    for s in schemas:
        if '"organization"' in s.lower():
            m = re.search(r'"name"\s*:\s*"([^"]+)"', s)
            if m:
                org_name = m.group(1)
                break
    c["org_schema_name"] = org_name

    try:
        robots = fetch(url + "/robots.txt")
        c["robots_exists"] = True
        # 正确检测（2026-09-29 修正）：robots.txt 默认允许所有爬虫，
        # 只有显式 Disallow 才是「阻止」。之前的「显式放行」检查是错的。
        all_blocked = (
            "User-agent: *" in robots
            and "Disallow: /" in robots.split("User-agent: *", 1)[1].split("User-agent:", 1)[0][:600]
        )
        blocked = []
        for b in AI_BOTS:
            if f"User-agent: {b}" in robots:
                seg = robots.split(f"User-agent: {b}", 1)[1].split("User-agent:", 1)[0][:600]
                if "Disallow: /" in seg:
                    blocked.append(b)
            elif all_blocked:
                blocked.append(b)
        c["ai_bots_blocked"] = sorted(blocked)          # 被阻止的 AI 爬虫（真正缺口）
        c["ai_visibility_open"] = len(blocked) == 0      # 未被阻止 = AI 可见性开放
        c["sitemap_declared"] = "Sitemap:" in robots
    except Exception:
        c["robots_exists"] = False
        c["ai_bots_blocked"] = []
        c["ai_visibility_open"] = None   # 无 robots.txt，状态未知（通常意味着默认开放）
        c["sitemap_declared"] = False

    for extra in ("sitemap.xml", "llms.txt"):
        try:
            fetch(url + "/" + extra)
            c[extra.replace(".", "_") + "_exists"] = True
        except Exception:
            c[extra.replace(".", "_") + "_exists"] = False

    # ---- 扩充检查项（深度诊断用）----
    # H2 结构
    h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.I | re.S)
    c["h2_count"] = len(h2s)
    # 图片 alt 覆盖率
    imgs = re.findall(r"<img[^>]*>", html, re.I)
    imgs_with_alt = sum(1 for i in imgs if re.search(r'alt=["\']', i, re.I))
    c["img_total"] = len(imgs)
    c["img_alt_count"] = imgs_with_alt
    # Open Graph 标签
    m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)', html, re.I)
    c["og_title"] = m.group(1) if m else None
    m = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    c["og_description"] = m.group(1) if m else None
    # Twitter Card
    c["twitter_card"] = bool(re.search(r'name=["\']twitter:card["\']', html, re.I))
    # 链接统计（内链/外链）
    links = re.findall(r'<a[^>]*href=["\']([^"\']+)', html, re.I)
    host = urlparse(url).netloc
    c["internal_links"] = sum(1 for l in links if host in l or l.startswith("/") or l.startswith("#"))
    c["external_links"] = sum(1 for l in links if l.startswith("http") and host not in l)
    # 页面大小（粗略）
    c["page_size_kb"] = round(len(html.encode("utf-8")) / 1024, 1)

    # ---- 正文内容抓取（GEO 内容专项检测，对标自足性段落/AI 可提取格式）----
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.I | re.S)
    clean_ps = [p for p in (_clean(x) for x in paragraphs) if p and len(p) > 20]
    c["first_paragraph"] = clean_ps[0][:300] if clean_ps else None
    body_text = " ".join(clean_ps)
    c["body_word_count"] = len(body_text.split())
    c["body_has_numbers"] = bool(re.search(r"\d", body_text))
    FLUFF_WORDS = ["high-quality", "high quality", "premium", "excellent", "best-in-class",
                   "top-notch", "cutting-edge", "world-class", "industry-leading",
                   "superior", "unparalleled", "innovative", "state-of-the-art"]
    fluff = [w for w in FLUFF_WORDS if w in body_text.lower()]
    c["body_fluff_words"] = fluff
    c["body_has_fluff"] = len(fluff) > 0

    return c


def load_credentials():
    creds = {}
    p = os.path.expanduser("~/.workbuddy/secrets/platform-credentials.env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
    return creds


def google_index_lookup(domain):
    """用 Serper 查 Google 真实索引，拿 title/description（绕过 Cloudflare 拦截）。

    Googlebot 是声明过的爬虫可绕开 Cloudflare，但我们直接抓取会被拦。用 Serper 拿
    Google 实际索引到的内容，判断「Google 眼里网站是否可见」——避免把「我们被拦」
    误判为「网站差」。
    """
    key = load_credentials().get("SERPER_API_KEY", "")
    if not key:
        return {}
    try:
        req = urllib.request.Request(
            "https://google.serper.dev/search",
            data=json.dumps({"q": f"site:{domain}", "num": 3}).encode(),
            headers={"Content-Type": "application/json", "X-API-KEY": key})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        org = d.get("organic", [])
        for o in org:
            link = o.get("link", "")
            if domain in link:
                return {"g_indexed": True, "g_title": o.get("title", ""),
                        "g_description": o.get("snippet", ""), "g_link": link}
        return {"g_indexed": bool(org), "g_organic_count": len(org)}
    except Exception as e:
        return {"g_error": f"{type(e).__name__}: {e}"[:80]}


def deepseek_chat(prompt, temperature=0.3, max_tokens=1600):
    creds = load_credentials()
    key = creds.get("DEEPSEEK_API_KEY", "")
    base = creds.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if not key:
        return None, "未配置 DEEPSEEK_API_KEY"
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(base + "/chat/completions", data=data,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:120]


def call_openai(prompt):
    """通过新加坡跳板调 OpenAI GPT-5 nano（香港 IP 被 OpenAI 地区限制）。
    ⚠️ OpenAI 账号 2026-10-02 已封禁，此函数已弃用，改走 call_chatgpt_cloro。"""
    url = "http://43.160.199.215:8032/proxy"
    data = json.dumps({
        "token": "sg-llm-proxy-2026",
        "provider": "openai",
        "prompt": prompt,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
        if body.get("error"):
            return None, f"OpenAI: {body['error']}"[:80]
        return (body.get("text") or "").strip(), None
    except Exception as e:
        return None, f"OpenAI: {type(e).__name__}: {e}"[:80]


def call_chatgpt_cloro(prompt, country="US"):
    """用 Monid 的 cloro /chatgpt/ask 模拟 ChatGPT 消费者版回答（替代 OpenAI API）。

    cloro 走 ChatGPT 消费者版（logged-out + 强制联网），返回 text + 引用来源，
    比 OpenAI API 更接近「用户实际问 ChatGPT」的效果，且带引用来源（GEO 审计更有价值）。
    价格约 $0.0056/次，走 Monid 扣费（异步 run + 轮询）。
    """
    import subprocess
    key = load_credentials().get("MONID_API_KEY", "")
    if not key:
        return None, "未配置 MONID_API_KEY"
    env = {**os.environ, "MONID_API_KEY": key}
    try:
        r = subprocess.run(
            ["monid", "run", "-p", "cloro", "-e", "/chatgpt/ask", "-i",
             json.dumps({"prompt": prompt, "country": country})],
            capture_output=True, text=True, timeout=40, env=env)
        m = re.search(r"Run ID:\s*([0-9A-Z]+)", r.stdout + r.stderr)
        if not m:
            return None, "cloro: 未获取 run ID"
        run_id = m.group(1)
        for _ in range(20):  # 最多约 60 秒
            time.sleep(3)
            r2 = subprocess.run(["monid", "runs", "get", "-r", run_id],
                                capture_output=True, text=True, timeout=40, env=env)
            out = r2.stdout + r2.stderr
            if "COMPLETED" in out:
                tm = re.search(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', out, re.S)
                if tm:
                    try:
                        return tm.group(1).encode().decode("unicode_escape"), None
                    except Exception:
                        return tm.group(1), None
                return None, "cloro: 完成但无 text"
            if "FAILED" in out or "ERROR" in out:
                return None, "cloro: 调用失败"
        return None, "cloro: 超时"
    except Exception as e:
        return None, f"cloro: {type(e).__name__}: {e}"[:80]


def call_chatgpt_blockrun(prompt, model="gpt-4o-mini"):
    """用 Monid 的 blockrun /chat/completions 调 GPT（$0.0022/次，裸模型无联网）。

    比 cloro 便宜 72%（$0.0022 vs $0.008）且快一倍（9s vs 25s），
    但走的是 OpenAI 兼容协议裸模型，无联网搜索、无引用来源。
    适合降本场景（内容审计/意图分析），不适合「模拟用户问 ChatGPT 消费者版」。
    """
    import subprocess
    key = load_credentials().get("MONID_API_KEY", "")
    if not key:
        return None, "未配置 MONID_API_KEY"
    env = {**os.environ, "MONID_API_KEY": key}
    try:
        body = json.dumps({"model": model,
                           "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 500})
        r = subprocess.run(["monid", "run", "-p", "blockrun.ai", "-e", "/api/v1/chat/completions",
                            "-i", body], capture_output=True, text=True, timeout=40, env=env)
        m = re.search(r"Run ID:\s*([0-9A-Z]+)", r.stdout + r.stderr)
        if not m:
            return None, "blockrun: 未获取 run ID"
        run_id = m.group(1)
        for _ in range(15):  # 最多约 45 秒
            time.sleep(3)
            r2 = subprocess.run(["monid", "runs", "get", "-r", run_id],
                                capture_output=True, text=True, timeout=40, env=env)
            out = r2.stdout + r2.stderr
            if "COMPLETED" in out:
                cm = re.search(r'"role"\s*:\s*"assistant"[^}]*?"content"\s*:\s*"((?:[^"\\]|\\.)*)"', out, re.S)
                if cm:
                    try:
                        return cm.group(1).encode().decode("unicode_escape"), None
                    except Exception:
                        return cm.group(1), None
                return None, "blockrun: 完成但无 content"
            if "FAILED" in out or "ERROR" in out:
                return None, "blockrun: 调用失败"
        return None, "blockrun: 超时"
    except Exception as e:
        return None, f"blockrun: {type(e).__name__}: {e}"[:80]


def call_chatgpt(prompt):
    """ChatGPT 统一入口：blockrun 主用（$0.0022 裸模型）+ cloro 备份（$0.008 联网+来源）。"""
    text, err = call_chatgpt_blockrun(prompt)
    if err:
        text, err = call_chatgpt_cloro(prompt)
    return text, err


def call_gemini(prompt):
    """调用 Gemini API（海外模型，模拟买家问 Gemini）。"""
    creds = load_credentials()
    key = creds.get("GEMINI_API_KEY", "")
    if not key:
        return None, "未配置 GEMINI_API_KEY"
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json", "X-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
        return body["candidates"][0]["content"]["parts"][0]["text"].strip(), None
    except Exception as e:
        return None, f"Gemini: {type(e).__name__}: {e}"[:80]


def call_perplexity(prompt):
    """调用 Perplexity Agent API（联网搜索，web-grounded）。"""
    creds = load_credentials()
    key = creds.get("PERPLEXITY_API_KEY", "")
    if not key:
        return None, "未配置 PERPLEXITY_API_KEY"
    url = "https://api.perplexity.ai/v1/agent"
    data = json.dumps({
        "preset": "low",
        "input": prompt,
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
        # Agent API 答案在 output[].content[].text（web-grounded，带引用）
        for o in body.get("output", []):
            if o.get("type") == "message":
                for c in o.get("content", []):
                    if c.get("type") == "output_text":
                        return (c.get("text") or "").strip(), None
        return "", "Perplexity: 响应无答案文本"
    except Exception as e:
        return None, f"Perplexity: {type(e).__name__}: {e}"[:80]


def call_claude(prompt):
    """调用 Anthropic Claude（海外模型，待补 CLAUDE_API_KEY）。"""
    creds = load_credentials()
    key = creds.get("CLAUDE_API_KEY", "")
    if not key:
        return None, "未配置 CLAUDE_API_KEY"
    url = "https://api.anthropic.com/v1/messages"
    data = json.dumps({
        "model": "claude-sonnet-4-5",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
        parts = body.get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text").strip(), None
    except Exception as e:
        return None, f"Claude: {type(e).__name__}: {e}"[:80]


def call_grok(prompt):
    """调用 xAI Grok API（海外模型，香港可直连）。"""
    creds = load_credentials()
    key = creds.get("GROK_API_KEY", "")
    if not key:
        return None, "未配置 GROK_API_KEY"
    url = "https://api.x.ai/v1/chat/completions"
    data = json.dumps({
        "model": "grok-4.3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
        return body["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, f"Grok: {type(e).__name__}: {e}"[:80]


def infer_brand(checks):
    """推断品牌名：优先 Organization Schema name，其次 og:title，最后 title 推断（防误判）。"""
    # 1. 优先 Organization Schema 的 name
    org = (checks.get("org_schema_name") or "").strip()
    if org and len(org) <= 40 and not any(w in org.lower() for w in ("shopify", "powered by", "wordpress", "wix")):
        return org[:40]
    # 2. og:title（通常是品牌名）
    og = (checks.get("og_title") or "").strip()
    if og and len(og) <= 40:
        return og[:40]
    # 3. title 推断（处理 HTML 实体 + 优先取 | 后的站点名）
    title = (checks.get("title") or "").replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
    if "|" in title:
        parts = [p.strip() for p in title.split("|") if p.strip()]
        if parts:
            return parts[-1][:40]
    for sep in (" — ", " - ", " · "):
        if sep in title:
            return title.split(sep)[0].strip()[:40]
    return title[:40]


def score_site(checks, probe_results=None):
    """统一评分体系：综合 0-100 = SEO×4 + GEO×6（GEO 权重 60%）。

    SEO 健康度（0-10）：技术健康 + 内容 + 关键词。
    GEO 适配度（0-10）：AI 爬虫放行 + Schema + AI 实测（多模型×3问，按比例计分）。
    """
    seo = 0.0
    if checks.get("has_org_schema"): seo += 1
    if checks.get("robots_exists"): seo += 1
    if checks.get("sitemap_xml_exists"): seo += 1
    if checks.get("llms_txt_exists"): seo += 1
    if checks.get("title"): seo += 0.5
    if checks.get("meta_description"): seo += 0.5
    if checks.get("h1_count", 0) > 0: seo += 0.5
    if checks.get("canonical"): seo += 0.5
    if checks.get("has_faq_schema"): seo += 1
    seo += 2  # 内容基础 + 关键词（暂按中等 2 分计，后续可细化）
    seo = round(min(10, seo), 1)

    geo = 0.0
    if checks.get("ai_visibility_open"): geo += 2
    if checks.get("has_org_schema"): geo += 1.5
    if checks.get("has_faq_schema"): geo += 1.5
    if probe_results:
        n = len(probe_results) or 1
        accurate = sum(1 for p in probe_results if p.get("mentioned"))
        geo += accurate * (5.0 / n)  # AI 实测满分 5，按实际问数（模型数 × 3）
    geo = round(min(10, geo), 1)

    total = round(seo * 4 + geo * 6)
    return {"seo": seo, "geo": geo, "total": total, "percentile": _percentile(total)}


def _percentile(total):
    """综合评分 → 市场分位（基于 91 站基准的估算）。"""
    if total >= 85: return "前 10%"
    if total >= 70: return "前 37%"
    if total >= 55: return "中段（前 37%–81%）"
    if total >= 30: return "后 19%"
    return "底部"


def _traffic_band(total):
    """综合评分 → 估算月自然流量区间（估算值，非承诺）。"""
    if total >= 85: return "50万+"
    if total >= 70: return "10万–50万"
    if total >= 55: return "1万–10万"
    if total >= 30: return "1千–1万"
    return "低于 1千"


def ai_gap(total):
    """综合评分 → AI 引流缺口（错失的 AI 流量）。分数越高缺口越小（负相关）。"""
    if total >= 85:
        return {"level": "基本无缺口", "desc": "AI 高度认可你的品牌，能稳定正确引用，保持现有优势即可"}
    if total >= 70:
        return {"level": "少量错失", "desc": "AI 基本能正确引用你，但部分推荐位仍被竞争对手占据，存在少量 AI 流量流失"}
    if total >= 50:
        return {"level": "部分错失", "desc": "AI 能识别你但推荐不稳定，相当一部分 AI 推荐流量正在流向对手"}
    if total >= 30:
        return {"level": "明显错失", "desc": "AI 偶有提及但描述不准，大部分 AI 推荐位已被竞争对手占据"}
    return {"level": "严重错失", "desc": "AI 渠道近乎零贡献，你在 AI 推荐里几乎缺席——头部同品类品牌已有约 30-40% 新客来自 AI，这部分你正在流失"}


def build_content_plan(brand, category=""):
    """内容与社交传播整改建议，用 Perplexity 联网搜具体频道/媒体/频率。"""
    cat = category or "品牌所在品类"
    prompt = (f"针对中国出海品牌「{brand}」（品类：{cat}），给出 GEO 内容传播的具体建议，输出严格 JSON：\n"
              "{{\"reddit_channels\": [\"该品类最相关的 3 个 subreddit 名（形如 r/xxx）\"], "
              "\"x_frequency\": \"X/Twitter 建议发布频率\", "
              "\"linkedin_frequency\": \"LinkedIn 建议发布频率\", "
              "\"media\": [\"该品类 2-3 个权威评测媒体或行业网站\"]}}\n"
              "基于真实常识，不要臆造。")
    text, err = call_perplexity(prompt)
    d = {}
    if not err and text:
        t = text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            if t.lower().startswith("json"):
                t = t[4:]
            t = t.strip()
        try:
            d = json.loads(t)
        except Exception:
            s, e = t.find("{"), t.rfind("}")
            if s != -1 and e != -1:
                try:
                    d = json.loads(t[s:e + 1])
                except Exception:
                    d = {}
    def _clean(s):
        return re.sub(r'\s*\[web:\d+\]', '', str(s)).strip()
    channels = [c for c in (_clean(x) for x in d.get("reddit_channels", [])) if c][:3]
    media = [c for c in (_clean(x) for x in d.get("media", [])) if c][:3]
    xf = _clean(d.get("x_frequency", "每周 2-3 次"))
    lif = _clean(d.get("linkedin_frequency", "每周 1-2 次"))
    return [
        {"name": "Reddit 参与", "fix": f"养号（Karma 500+）后，优先在 {('、'.join(channels) if channels else '相关 subreddit')} 用真实用户口吻回答「{cat}怎么选」等问题"},
        {"name": "X / Twitter 内容", "fix": f"{xf}发布「{brand}」的行业数据、观点、使用场景，建立权威信号"},
        {"name": "LinkedIn 交叉验证", "fix": f"{lif}发布品牌洞察与创始人观点，作为第三方信源交叉验证"},
        {"name": "第三方权威提及", "fix": f"三步落地：①在 X/LinkedIn 发带数据的行业观点时 @{('、'.join(media[:2]) if media else '权威媒体')}，争取转发互动；②响应记者求助平台（Help a B2B Writer / Connectively）里与「{cat}」相关的问题，换取媒体引用；③向 {media[0] if media else '行业媒体'} 投稿干货文章，换取反向链接与品牌提及"},
    ]


def ai_probe(brand_name, category=""):
    """多模型 AI 实测（诊断核心）：Gemini + Perplexity（联网搜索）+ DeepSeek 各问一遍。

    返回结构化结果：每个（模型 × 问题）→ 是否提到品牌 + AI 的回答。
    这是「AI 里你是什么样子」的核心证据，零虚构（真实提问记录）。
    """
    probes = [
        ("发现", f"What are the best {category or 'products'} brands? Give your top recommendations."),
        ("认知", f"What do you know about {brand_name}? What do they sell and what's their reputation?"),
        ("信任", f"Would you recommend {brand_name} to a friend? Why or why not?"),
    ]
    # ChatGPT 主用 cloro（联网消费者版，带引用来源）；blockrun（裸模型无联网）仅作内容审计补充，不进前端展示
    models = [("ChatGPT", call_chatgpt_cloro), ("Perplexity", call_perplexity)]
    creds = load_credentials()
    if creds.get("GROK_API_KEY"):
        models.append(("Grok", call_grok))
    if creds.get("GEMINI_API_KEY"):
        models.append(("Gemini", call_gemini))
    if creds.get("CLAUDE_API_KEY"):
        models.append(("Claude", call_claude))
    results = []
    for angle, q in probes:
        for mname, mfunc in models:
            text, err = mfunc(q)
            ans = text or ("（调用失败：" + str(err)[:60] + "）")
            mentioned = brand_name.lower() in ans.lower() if brand_name else False
            results.append({"model": mname, "question": q, "angle": angle, "mentioned": mentioned, "answer": ans[:250]})
    return results


def generate_assessment(checks):
    """用 DeepSeek 生成评分 + 诊断 + 建议（结构化 JSON）。"""
    prompt = f"""你是 GEO+SEO 双轨优化专家。以下是网站 {checks.get('url')} 的技术扫描结果（全部实测）：

{json.dumps(checks, ensure_ascii=False, indent=2)}

请基于这些**真实扫描数据**（不要臆造数据），输出严格 JSON，字段如下：
{{
  "seo_score": 0-10 整数（技术健康/内容基础/关键词），
  "geo_score": 0-10 整数（AI 可引用性/Schema/爬虫放行），
  "summary": "2-3 句话的总体判断",
  "problems": [ {{"level": "P0/P1/P2", "item": "具体问题", "fix": "修复建议"}} ] （3-6 条，按优先级），
  "strengths": ["已做对的点"] （1-3 条）
}}

零虚构：扫描里没有的字段不要编造。只输出 JSON。"""
    text, err = deepseek_chat(prompt)
    if err:
        return {"error": err, "checks": checks}
    # 稳健解析 JSON
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except Exception:
                pass
        return {"raw": text, "checks": checks}


def analyze_probe_results(brand_name, probe_results):
    """用 DeepSeek 分析每个 AI 快照，给出中文结论（好/差，好在哪差在哪）。"""
    prompt = f"""你是 AI 可见性分析师。品牌「{brand_name}」的海外 AI 实测结果如下（每条含 question 问题、model 模型、answer 回答）：

{json.dumps(probe_results, ensure_ascii=False, indent=2)}

请逐条分析，输出严格 JSON：
{{"analyses": [{{"model": "模型名", "angle": "发现/认知/信任（与输入中该条的 angle 一致）", "translation": "该条 answer 的忠实中文翻译（不增删不改写）", "verdict": "好/中/差", "point": "针对该条具体回答的一句话结论（说明这一问暴露了品牌可见性的什么具体表现）", "good": "这一条里好在哪（无则省略）", "bad": "这一条里差在哪（无则省略）"}}]}}

关键要求：
1. 每条的 angle 必须与输入中该条的 angle 完全一致（发现/认知/信任），用于对齐。
2. translation 必须忠实翻译该条 answer 的原文，不做任何改动或润色。
3. point 必须针对该条的具体回答内容（结合它问的是什么问题、答了什么），不能泛泛而谈。
4. 同一模型的 3 次提问（发现/认知/信任三个不同角度），point 必须分别反映这三个角度的不同结论，绝不允许雷同。
5. 只输出 JSON，基于真实回答，不要臆造。"""
    text, err = deepseek_chat(prompt)
    if err:
        return []
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t).get("analyses", [])
    except Exception:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s:e + 1]).get("analyses", [])
            except Exception:
                pass
        return []


def build_detail_checks(checks):
    """生成确定性检查清单，按大类分组（体检报告式），每组含评分小结。"""
    items = []
    cur = {"cat": "网页技术"}
    def set_cat(cat):
        cur["cat"] = cat
    def add(name, ok, detail, suggestion):
        items.append({"category": cur["cat"], "name": name, "ok": bool(ok), "detail": detail, "suggestion": suggestion})

    t = checks.get("title")
    add("Title 标签存在", t, f"当前：{t or '缺失'}", "为每个页面设置唯一 title，长度 30-60 字符，含核心关键词 + 品牌名")
    add("Title 长度适中", t and 10 <= len(t) <= 60, f"当前 {len(t) if t else 0} 字符", "标题过长会被截断，过短浪费展示空间，控制在 30-60 字符")
    md = checks.get("meta_description")
    add("Meta 描述存在", md, f"当前：{md or '缺失'}", "设置 70-160 字符的描述，含卖点 + 行动号召")
    add("Meta 描述长度适中", md and 50 <= len(md) <= 160, f"当前 {len(md) if md else 0} 字符", "过长会被截断，建议控制在 160 字符内")
    add("H1 唯一", checks.get("h1_count") == 1, f"当前 {checks.get('h1_count', 0)} 个", "每页只保留 1 个 H1，且与 title 语义一致")
    add("H2 层级结构", checks.get("h2_count", 0) > 0, f"当前 {checks.get('h2_count', 0)} 个", "用 H2-H3 搭建内容层级，利于爬虫理解页面结构")
    add("Canonical 标签", checks.get("canonical"), f"当前：{checks.get('canonical') or '缺失'}", "设置 canonical，避免重复内容分散权重")
    add("Viewport（移动适配）", checks.get("viewport"), "当前：" + ("已设置" if checks.get("viewport") else "缺失"), "必须设置 viewport，移动端体验是重要排名因素")
    add("lang 语言声明", checks.get("lang"), f"当前：{checks.get('lang') or '缺失'}", "在 html 标签声明 lang，帮助搜索引擎识别语言")
    add("HTTPS 加密", checks.get("url", "").startswith("https"), "当前：" + ("HTTPS" if checks.get("url", "").startswith("https") else "非 HTTPS"), "全站 HTTPS，是 SEO 基本门槛")
    img_t, img_a = checks.get("img_total", 0), checks.get("img_alt_count", 0)
    add("图片 Alt 覆盖", img_a > 0 and (img_t == 0 or img_a >= img_t * 0.8), f"当前 {img_a}/{img_t} 张有 alt", "为所有图片添加描述性 alt，利于图片搜索和可访问性")
    add("OG Title 标签", checks.get("og_title"), f"当前：{checks.get('og_title') or '缺失'}", "设置 og:title，社交分享时显示正确标题")
    add("OG 描述标签", checks.get("og_description"), f"当前：{checks.get('og_description') or '缺失'}", "设置 og:description，社交分享时显示正确摘要")
    add("Twitter Card", checks.get("twitter_card"), "当前：" + ("已设置" if checks.get("twitter_card") else "缺失"), "设置 twitter:card，提升社交分享体验")
    add("站内链接", checks.get("internal_links", 0) > 0, f"当前 {checks.get('internal_links', 0)} 条", "合理的内链结构帮助爬虫发现页面、传递权重")
    set_cat("结构化数据")
    st = checks.get("schema_types", [])
    add("Organization Schema", checks.get("has_org_schema"), "当前：" + ("已设置" if checks.get("has_org_schema") else "缺失"), "添加 Organization Schema，让 AI 确认你是可信实体")
    add("FAQPage Schema", checks.get("has_faq_schema"), "当前：" + ("已设置" if checks.get("has_faq_schema") else "缺失"), "添加 FAQPage Schema，问答内容更易被 AI 引用")
    add("Product Schema", "Product" in st, "当前：" + ("已设置" if "Product" in st else "缺失"), "电商页面添加 Product Schema，提升商品在搜索的展示")
    add("BreadcrumbList Schema", "BreadcrumbList" in st, "当前：" + ("已设置" if "BreadcrumbList" in st else "缺失"), "添加面包屑 Schema，改善搜索结果展示")
    set_cat("AI 爬虫与收录")
    add("robots.txt 存在", checks.get("robots_exists"), "当前：" + ("存在" if checks.get("robots_exists") else "缺失"), "提供 robots.txt 明确爬虫规则")
    add("AI 爬虫放行", checks.get("ai_visibility_open"), "当前：" + ("已放行" if checks.get("ai_visibility_open") else ("部分被阻止" if checks.get("ai_visibility_open") is not None else "未知")), "确保 GPTBot/ClaudeBot/PerplexityBot 等 AI 爬虫未被阻止")
    add("llms.txt 存在", checks.get("llms_txt_exists"), "当前：" + ("存在" if checks.get("llms_txt_exists") else "缺失"), "提供 llms.txt 让 AI 爬虫读取站点结构化说明")
    add("Sitemap.xml 存在", checks.get("sitemap_xml_exists"), "当前：" + ("存在" if checks.get("sitemap_xml_exists") else "缺失"), "提供 sitemap.xml 帮助搜索引擎完整收录")
    add("Sitemap 在 robots 声明", checks.get("sitemap_declared"), "当前：" + ("已声明" if checks.get("sitemap_declared") else "未声明"), "在 robots.txt 中声明 sitemap 地址")
    ps = checks.get("page_size_kb", 0)
    add("页面大小合理", ps < 500, f"当前 {ps}KB", "页面过大会拖慢加载，建议压缩图片和资源")

    # ---- GEO 内容专项（对标"自足性段落"与"AI 可提取格式"，第 4/7/12 篇方法论）----
    set_cat("内容质量")
    fp = checks.get("first_paragraph")
    add("首段结论先行", fp is not None, "当前：" + (f"首段 {len(fp)} 字" if fp else "无正文首段"),
        "首段应直接给结论（谁、什么问题、什么数字、什么结果），AI 才能直接摘取")
    add("首段长度 ≤80 字", fp is not None and len(fp) <= 80, f"当前 {len(fp) if fp else 0} 字",
        "首段超过 80 字会被 AI 判定信息冗余，压缩成结论+数据+出处")
    add("正文含具体数据", bool(checks.get("body_has_numbers")),
        "当前：" + ("含数字/数据" if checks.get("body_has_numbers") else "无具体数字"),
        "正文应含具体参数、测试数据、百分比等可验证信息——AI 需要数据，不需要形容词")
    add("无空泛形容词", not checks.get("body_has_fluff"),
        "当前：" + ("含空话（" + "、".join(checks.get("body_fluff_words", [])[:3]) + "）" if checks.get("body_has_fluff") else "无空话"),
        "避免 high-quality、premium、excellent 这类无法验证的形容词，改为可量化的数据")
    wc = checks.get("body_word_count", 0)
    add("正文信息密度足够", wc > 300, f"当前 {wc} 词",
        "正文信息量应 >300 词，支撑 AI 提取完整答案（谁/问题/数字/结果）")
    add("H2/H3 覆盖用户问题", checks.get("h2_count", 0) >= 2, f"当前 {checks.get('h2_count', 0)} 个 H2",
        "用 H2/H3 标题对应真实用户问题，让 AI 按问题定位答案")

    # 组装分组 + 每组评分小结
    groups = {}
    for it in items:
        groups.setdefault(it["category"], []).append(it)
    result = []
    for cat, its in groups.items():
        ok_cnt = sum(1 for i in its if i["ok"])
        result.append({"category": cat, "score": round(ok_cnt / len(its) * 10),
                       "passed": ok_cnt, "total": len(its), "items": its})
    return result


def ai_audit_content(checks):
    """用海外模型审计内容「AI 可引用性」（语义层，确定性扫描做不到的语感判断）。"""
    content = {
        "url": checks.get("url"),
        "title": checks.get("title"),
        "meta_description": checks.get("meta_description"),
        "h1": checks.get("h1"),
        "first_paragraph": checks.get("first_paragraph"),
        "body_word_count": checks.get("body_word_count"),
    }
    prompt = ("You are an AI-visibility auditor. Evaluate whether this webpage is \"AI-citable\" — "
              "whether an AI assistant (ChatGPT / Perplexity / Gemini) would likely quote or cite this page "
              "when a user asks about the brand.\n\nPage content:\n"
              + json.dumps(content, ensure_ascii=False, indent=2)
              + "\n\nCriteria: conclusion-first opening; concrete data points (numbers/params/results); "
              "no empty adjectives (high-quality/premium); self-contained paragraphs; clear question-answer structure.\n"
              "Output STRICT JSON only, all text in Chinese: {\"score\": 0-10, \"verdict\": \"中文一句话总评\", "
              "\"strengths\": [\"中文 AI 友好点\"], \"weaknesses\": [\"中文 AI 不友好点\"]}")
    text, err = call_chatgpt_blockrun(prompt)  # blockrun 降本（$0.0022），内容审计无需联网，不进前端展示
    if err:
        text, err = deepseek_chat(prompt)  # 降级用 DeepSeek
    if err:
        return {}
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except Exception:
                pass
        return {}


def ai_intent_questions(checks):
    """用海外模型列出目标品类的 5 个核心用户问题（关键词意图分析，第 4 篇方法论）。"""
    prompt = ("Based on this website's brand and industry, list the 5 most important questions a potential "
              "customer would ask an AI assistant (ChatGPT / Perplexity) when researching this product category. "
              "Rank by priority. Output STRICT JSON only: {\"questions\": [{\"en\": \"English question\", \"zh\": \"中文翻译\"}, ...]}\n\n"
              "Website context:\n" + json.dumps({
                  "url": checks.get("url"),
                  "title": checks.get("title"),
                  "h1": checks.get("h1"),
                  "first_paragraph": checks.get("first_paragraph"),
              }, ensure_ascii=False))
    text, err = call_perplexity(prompt)  # OpenAI 已封禁，改用 Perplexity
    if err:
        return []
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t).get("questions", [])
    except Exception:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s:e + 1]).get("questions", [])
            except Exception:
                pass
        return []


def ai_reddit_mentions(brand):
    """用 Perplexity 间接搜品牌在 Reddit 的提及（我们无法直连 Reddit，借其联网能力做交叉验证）。"""
    if not brand:
        return {}
    prompt = (f"Search Reddit for discussions that mention the brand '{brand}'. "
              "Report: (1) roughly how many relevant Reddit threads mention it, (2) whether Reddit users "
              "recommend it, (3) a one-sentence summary of what they say. "
              "Output STRICT JSON only, summary in Chinese: {\"mentioned\": true/false, \"threadCount\": <int>, "
              "\"sentiment\": \"positive/neutral/negative\", \"summary\": \"中文总结\"}")
    text, err = call_perplexity(prompt)
    if err:
        return {}
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
        t = t.strip()
    try:
        return json.loads(t)
    except Exception:
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(t[s:e + 1])
            except Exception:
                pass
        return {}


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    c = scan_site(url)
    print(json.dumps(c, ensure_ascii=False, indent=2))
    a = generate_assessment(c)
    print(json.dumps(a, ensure_ascii=False, indent=2))
