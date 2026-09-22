# GoAI Moat — AI Visibility Audit MCP Server

Remote MCP server that diagnoses a brand's visibility in AI answers (ChatGPT, Perplexity, Google AI Overviews, Amazon Rufus).

**Endpoint:** `https://mcp.goaimoat.com/mcp` (streamable HTTP)

## Tools

- `audit_ai_visibility` — deep audit: AI probe prompts, competitor-gap method, 30-day fix plan. Free tier: 1 full audit per email. Unlimited: license key from https://niebingyu.gumroad.com/l/njpksu
- `get_checklist` — the full 30-point AI visibility checklist (free)
- `get_fix_priority` — turn a 0-30 score into tier + prioritized fixes (free)
- `check_license` — validate a Gumroad license key (free)

## Connect (Claude Desktop / Cursor / any MCP client)

```json
{
  "mcpServers": {
    "goaimoat-ai-visibility": {
      "url": "https://mcp.goaimoat.com/mcp"
    }
  }
}
```

## Core thesis

Being good is no longer enough — you have to be *sayable by AI*.

## License

Copyright GoAI Moat (goaimoat.com). All rights reserved.
