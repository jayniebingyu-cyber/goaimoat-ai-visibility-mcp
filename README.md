# GoAI Moat — AI Visibility MCP (thin relay)

Multi-model **AI visibility audit** for any website or brand — ChatGPT (consumer app), Perplexity, and Grok, plus GEO/SEO health and a 0–100 score with benchmark percentile.

**Thin relay by design**: this MCP holds **no API keys, no billing logic, and makes no direct upstream calls**. It forwards your request (with your `api_key` / `license_key` / `email`) to the GoAI Moat server, which holds all credentials and enforces access and quota. The MCP is only the request-initiating interface.

## Tools

- `audit_ai_visibility(url, api_key=..., license_key=..., email=...)` — full audit: multi-model AI mentions + GEO/SEO health + 0–100 score + benchmark percentile + prioritized issues.
- `check_ai_mentions(brand, api_key=..., email=...)` — quick check: what ChatGPT / Perplexity / Grok say about a brand.
- `check_license(license_key, email=...)` — activate a license and receive your api_key.

## Pricing

- **Free**: 3 audits per email.
- **Subscription**: `$98/month`. Activate via `check_license`.

## Run locally (stdio)

```bash
pip install -r requirements.txt
python server.py
```

No credentials are needed here — authentication, quota, and the actual audit all live on the GoAI Moat server. The server returns a clear error if your api_key/license/email is missing or exhausted.

## Hosted endpoint

```
https://ai-visibility.mcp.goaimoat.com/mcp
```

## License

MIT
