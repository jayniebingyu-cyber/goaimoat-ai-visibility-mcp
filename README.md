# GoAI Moat — AI Visibility MCP

Multi-model **AI visibility audit** for any website or brand. Asks ChatGPT (consumer app), Perplexity, and Grok what they actually know about a brand, scans the site for GEO/SEO health, and returns a 0–100 score with a benchmark percentile.

## What it does

- `audit_ai_visibility(url)` — full audit: multi-model AI mentions + GEO/SEO health + 0–100 score + benchmark percentile + prioritized issues.
- `check_ai_mentions(brand)` — quick check: what ChatGPT / Perplexity / Grok say about a brand.

## Why pay for this

Most "AI visibility" tools only check *your website*. This MCP checks what AI models **actually say** about the brand — the ground truth of whether AI will mention, recommend, or ignore you. The benchmark percentile (vs. 500+ cross-border brands) is data you can't get by calling an LLM yourself.

## Pricing

- **Free**: 3 audits per email.
- **Subscription**: `$98/month` — 10 audits/day, 100 audits/month.
- Activate via `check_license(license_key, email)`.

## Run locally (stdio)

```bash
pip install -r requirements.txt
python server.py
```

No credentials are required to start the server (introspection works). Credentials (`MONID_API_KEY`, `SERPER_API_KEY`, `GROK_API_KEY`, `PERPLEXITY_API_KEY`) are only needed at call time — the tool returns a clear error if they are missing.

## Hosted endpoint

```
https://ai-visibility.mcp.goaimoat.com/mcp
```

## License

MIT
