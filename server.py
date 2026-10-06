"""GoAI Moat — AI Visibility MCP (thin relay)

Thin relay only. This MCP holds NO API keys, NO billing logic, NO subprocess calls.
All credentials, account management, quota enforcement and the real multi-model
audit live on the GoAI Moat server. This server only forwards the caller's identity
(api_key / license_key / email) to the server's /api/audit endpoint and relays the result.
"""
from fastmcp import FastMCP
import os, json, urllib.request, urllib.error

# 香港服务器内部审计端点（本地同机直连，密钥/门禁都在那边）
AUDIT_URL = os.environ.get("AUDIT_URL", "http://127.0.0.1:8031")

mcp = FastMCP(
    name="GoAI Moat — AI Visibility",
    instructions=(
        "AI visibility audit for any website or brand. This is a thin relay: it forwards your request "
        "to the GoAI Moat server, which holds all credentials and enforces access/quota. "
        "Run a full audit with audit_ai_visibility(url, api_key); quick brand check with check_ai_mentions(brand); "
        "activate a license and get an api_key with check_license(license_key)."
    ),
)


def _post(path, payload):
    req = urllib.request.Request(
        AUDIT_URL.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"[:120]}


@mcp.tool()
def audit_ai_visibility(url: str, api_key: str = "", license_key: str = "", email: str = "") -> dict:
    """Full AI visibility audit of a website (multi-model AI mentions + GEO/SEO + 0-100 score).

    This is a thin relay: your api_key (or license_key/email) is forwarded to the GoAI Moat server,
    which authenticates, enforces quota, and runs the audit. All credentials live server-side.

    Args:
        url: Website URL (e.g. "https://example.com").
        api_key: Your GoAI Moat api_key (obtained via check_license after purchase).
        license_key: Gumroad license key (alternative to api_key).
        email: Your email (for the free 3-audit trial).
    """
    return _post("/api/audit", {
        "url": url, "tier": "audit",
        "api_key": api_key, "license_key": license_key, "email": email,
    })


@mcp.tool()
def check_ai_mentions(brand: str, api_key: str = "", email: str = "") -> dict:
    """Quick check: what do ChatGPT, Perplexity and Grok say about a brand?

    Args:
        brand: Brand name (e.g. "RolePaths").
        api_key: Your GoAI Moat api_key (optional; email free trial also works).
        email: Your email (for the free trial).
    """
    return _post("/api/audit", {"brand": brand, "api_key": api_key, "email": email})


@mcp.tool()
def check_license(license_key: str, email: str = "") -> dict:
    """Activate a Gumroad license and receive your GoAI Moat api_key.

    Args:
        license_key: The Gumroad license key from your purchase.
        email: Email to bind the api_key to.
    """
    return _post("/api/activate", {"license_key": license_key, "email": email})


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "127.0.0.1"),
                port=int(os.getenv("MCP_PORT", "8020")))
    else:
        mcp.run()
