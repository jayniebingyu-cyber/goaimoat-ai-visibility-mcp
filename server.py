"""
GoAI Moat — AI Visibility Audit MCP Server (v2 with freemium gating)
让 AI Agent 调用我们的「AI 可见度诊断」能力。

免费层：get_checklist / get_fix_priority 全免费；audit_ai_visibility 每邮箱 1 次完整深度诊断。
付费层：Gumroad license key（$29/年）解锁无限次深度诊断。
License 验证走 Gumroad License API（服务器直连），验证成功后本地缓存。
"""
from fastmcp import FastMCP
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error

mcp = FastMCP(
    name="GoAI Moat — AI Visibility Audit",
    instructions=(
        "Diagnose a brand's visibility in AI answers (ChatGPT, Perplexity, Google AI Overviews, Amazon Rufus). "
        "Use audit_ai_visibility to run a deep audit: free tier gives 1 full audit per email; "
        "a license key (https://niebingyu.gumroad.com/l/njpksu) unlocks unlimited audits. "
        "get_checklist returns the full 30-point checklist, get_fix_priority turns a score into an action plan."
    ),
)

DATA_DIR = os.environ.get("MCP_DATA_DIR", "/opt/gg-ai-brief/data")
QUOTA_FILE = os.path.join(DATA_DIR, "mcp_quota.json")
LICENSE_CACHE = os.path.join(DATA_DIR, "mcp_licenses.json")
GUMROAD_PRODUCT_ID = os.environ.get("GUMROAD_MCP_PRODUCT_ID", "MLYxk9ZsxLN2CkJCbFgV4g==")
GUMROAD_TOKEN = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
BUY_URL = "https://niebingyu.gumroad.com/l/njpksu"
FREE_AUDITS_PER_EMAIL = 1

# 30 项检查清单（5 类 × 6 项）
CHECKLIST = {
    "on_site_content": [
        "Does the site have a blog/guide section, not just product pages?",
        "Does content directly answer buyer questions (not just 'buy now')?",
        "Is content structured (clear H2/H3, direct answers)?",
        "Are there FAQ sections with question + answer pairs?",
        "Is the site crawlable (no heavy JS-only rendering, proper meta)?",
        "Is content fresh (updated within 90 days)?",
    ],
    "third_party_footprint": [
        "Mentioned in independent media/reviews?",
        "On review platforms (Trustpilot, G2, Amazon)?",
        "Appear in 'best of' / comparison lists?",
        "Mentioned on Reddit or niche communities?",
        "Wikipedia or authoritative directory entry?",
        "Press/PR coverage in last 12 months?",
    ],
    "ai_answer_layer": [
        "ChatGPT mentions the brand for its category?",
        "Perplexity cites the brand?",
        "Google AI Overview surfaces the brand?",
        "When AI mentions the brand, does it say the RIGHT thing?",
        "Does AI cite the brand's own content or only third-party?",
        "Does AI answer the top objection ('is it worth it?')?",
    ],
    "structured_data": [
        "FAQPage schema on FAQ content?",
        "Organization schema with name/logo/social?",
        "Product/Service schema on offerings?",
        "Google Business Profile complete?",
        "Site mobile-friendly and fast?",
        "Consistent entity presence across platforms?",
    ],
    "community_consistency": [
        "Active social profiles with recent posts?",
        "Answering questions in communities as an expert?",
        "UGC (unboxings, reviews, testimonials)?",
        "Consistent brand story across every channel?",
        "Unique citable assets (case studies, data, patents, awards)?",
        "A system to keep publishing (not one-off content)?",
    ],
}

TIERS = [
    (0, 9, "Invisible", "AI barely knows you exist. Fix P0 immediately."),
    (10, 19, "Fragmented", "AI mentions you inconsistently / with someone else's words. Fix P0 + P1."),
    (20, 25, "Visible", "AI surfaces you reliably. Optimize P1 + P2."),
    (26, 30, "Cited", "AI cites you as an authority. Maintain and defend."),
]

PRIORITY = {
    "P0": [
        "Build an on-site content layer that answers buyer questions",
        "Find out what AI actually says about you, then fill the gap",
        "Answer your top objection in writing",
    ],
    "P1": [
        "Get third-party mentions (reviews, lists, Reddit)",
        "Add structured data (FAQPage, Organization schema)",
        "Set up a consistent publishing system",
    ],
    "P2": [
        "Build authority assets (Wikipedia, directory, press)",
        "Grow community presence + unique citable assets",
    ],
}

# 深度诊断独享内容（付费解锁部分）
DEEP_PLAYBOOK = {
    "ai_probe_prompts": "Test 10 buyer-intent prompts across ChatGPT/Perplexity/Gemini: 'best {category} for {use case}', '{brand} vs {competitor}', 'is {brand} worth it', '{category} recommendation 2026', plus your 3 top objections. Record: mentioned? cited? correct facts?",
    "competitor_gap_method": "For each top-3 competitor: run the same 10 probes, log share-of-voice per model, diff their third-party footprint vs yours (reviews, lists, Reddit), then target the 3 highest-gap surfaces first.",
    "citation_vs_mention": "Being mentioned is visibility; being CITED (with a link) drives conversion. Only ~11% of domains are cited by both ChatGPT and Perplexity — win one model's citations first, they compound.",
    "negative_ugc_risk": "AI amplifies negative UGC: up to ~73% of negative review content gets scraped into AI answers. Audit what AI says when asked 'complaints about {brand}' — this is the highest-risk blind spot.",
    "thirty_day_plan": {
        "week_1": "Baseline: run 10 probes on 3 models for you + 3 competitors. Log share-of-model.",
        "week_2": "Fix P0 on-site: FAQ section with real buyer questions + FAQPage schema, answer your #1 objection in a dedicated page.",
        "week_3": "Third-party: pitch 2 comparison-list placements, seed 1 Reddit/community answer per week as an expert (not as ads).",
        "week_4": "Re-run probes, measure delta, lock a monthly publishing cadence (2 posts + 1 FAQ + 1 community answer).",
    },
}


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _verify_license(license_key: str) -> dict:
    """Gumroad License API 验证；成功后本地缓存，避免重复网络调用。"""
    license_key = (license_key or "").strip()
    if not license_key:
        return {"valid": False, "reason": "empty license key"}
    cache = _load_json(LICENSE_CACHE, {})
    if license_key in cache:
        return {"valid": True, "email": cache[license_key].get("email"), "cached": True}
    if not GUMROAD_TOKEN:
        return {"valid": False, "reason": "server license verification not configured"}
    try:
        data = urllib.parse.urlencode({
            "product_id": GUMROAD_PRODUCT_ID,
            "license_key": license_key,
            "access_token": GUMROAD_TOKEN,
        }).encode()
        req = urllib.request.Request("https://api.gumroad.com/v2/licenses/verify", data=data, method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
        if resp.get("success"):
            purchase = resp.get("purchase", {})
            if purchase.get("refunded") or purchase.get("chargebacked"):
                return {"valid": False, "reason": "purchase refunded/chargebacked"}
            email = purchase.get("email", "")
            cache[license_key] = {"email": email, "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            _save_json(LICENSE_CACHE, cache)
            return {"valid": True, "email": email}
        return {"valid": False, "reason": "invalid license key"}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"valid": False, "reason": "invalid license key"}
        return {"valid": False, "reason": f"verification error: HTTP {e.code}"}
    except Exception as e:
        return {"valid": False, "reason": f"verification error: {e}"}


def _check_free_quota(email: str) -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return {"allowed": False, "reason": "valid email required for the free audit"}
    quota = _load_json(QUOTA_FILE, {})
    rec = quota.get(email, {"count": 0})
    if rec.get("count", 0) >= FREE_AUDITS_PER_EMAIL:
        return {
            "allowed": False,
            "reason": f"free audit already used for {email}",
            "buy_url": BUY_URL,
        }
    rec["count"] = rec.get("count", 0) + 1
    rec["last_brand"] = time.strftime("%Y-%m-%d")
    quota[email] = rec
    _save_json(QUOTA_FILE, quota)
    return {"allowed": True, "remaining_free": FREE_AUDITS_PER_EMAIL - rec["count"]}


def _score_to_tier(score: int) -> dict:
    for lo, hi, tier, note in TIERS:
        if lo <= score <= hi:
            return {"tier": tier, "note": note, "score": score}
    return {"tier": "Unknown", "note": "", "score": score}


@mcp.tool()
def audit_ai_visibility(
    brand_name: str,
    category: str = "",
    email: str = "",
    license_key: str = "",
    score: int = -1,
) -> dict:
    """Deep-audit a brand's visibility in AI answers (ChatGPT, Perplexity, AI Overviews).

    FREE TIER: 1 full deep audit per email — pass your email to unlock it.
    UNLIMITED: pass a license_key from https://niebingyu.gumroad.com/l/njpksu ($29/year).
    Without email/license you get the audit framework and tier mapping only.

    Args:
        brand_name: The brand/company to audit.
        category: Product/service category (e.g. "phone case", "DTC fashion").
        email: Your email — unlocks 1 free full audit.
        license_key: Gumroad license key — unlocks unlimited full audits.
        score: Optional known 0-30 checklist score. If provided, a tier + fix plan is included for free.
    """
    result = {
        "brand_name": brand_name,
        "category": category,
        "core_thesis": "Being good is no longer enough — you have to be *sayable by AI*.",
    }

    if score >= 0:
        result["diagnosis"] = _score_to_tier(min(score, 30))
        result["fix_priority"] = PRIORITY

    # 授权判定：license 优先，其次 email 免费额度
    if license_key:
        lic = _verify_license(license_key)
        if not lic.get("valid"):
            result["access"] = "denied"
            result["license_error"] = lic.get("reason")
            result["buy_url"] = BUY_URL
            result["free_option"] = "Retry with your email for 1 free audit."
            return result
        result["access"] = "licensed"
        result["licensed_to"] = lic.get("email")
    else:
        q = _check_free_quota(email)
        if not q.get("allowed"):
            result["access"] = "paywall"
            result["paywall_reason"] = q.get("reason")
            result["buy_url"] = BUY_URL
            result["hint"] = (
                "Free tier = 1 full audit per email (retry with a valid email), "
                "or buy a $29/year license for unlimited audits."
            )
            if score >= 0:
                result["note"] = "Basic tier diagnosis above was free. Deep playbook requires access."
            return result
        result["access"] = "free"
        result["remaining_free_audits"] = q.get("remaining_free", 0)

    # —— 深度诊断内容（需授权）——
    result["deep_playbook"] = DEEP_PLAYBOOK
    result["key_data"] = {
        "dual_engine_citation_overlap": "~11% of domains cited by both ChatGPT and Perplexity",
        "mention_vs_citation": "Being mentioned ≠ being cited. Citation drives conversion.",
        "negative_ugc_amplification": "AI scrapes and amplifies negative UGC — audit your complaint-layer visibility.",
    }
    result["next_step"] = (
        f"Run get_checklist, score all 30 items for '{brand_name}', then re-call with score to get tier + priorities. "
        "Deep audit includes AI probe prompts, competitor-gap method and a 30-day plan."
    )
    return result


@mcp.tool()
def get_checklist() -> dict:
    """Return the full 30-point AI visibility checklist (5 categories × 6 checks). Free."""
    return CHECKLIST


@mcp.tool()
def get_fix_priority(score: int) -> dict:
    """Turn a 0-30 visibility score into a tier and prioritized fix plan. Free.

    Args:
        score: The total score (0-30) from the 30-point checklist.
    """
    return {
        "diagnosis": _score_to_tier(min(score, 30)),
        "priority_actions": PRIORITY,
    }


@mcp.tool()
def check_license(license_key: str) -> dict:
    """Check whether a Gumroad license key is valid for unlimited audits.

    Args:
        license_key: The license key received after purchase.
    """
    lic = _verify_license(license_key)
    if lic.get("valid"):
        return {"valid": True, "email": lic.get("email"), "unlimited_audits": True}
    return {"valid": False, "reason": lic.get("reason"), "buy_url": BUY_URL}


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "8000")),
        )
    else:
        mcp.run()  # stdio (local)
