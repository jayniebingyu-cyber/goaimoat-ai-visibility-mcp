# GoAI Moat — AI Visibility Audit MCP Server

> 让 AI Agent 调用我们的「AI 可见度诊断」能力，帮它们的用户诊断品牌在 AI 问答中的可见度。
> 这是「面向 Agent 收费」的第一个产品。

## 连接信息

- **MCP 端点**：`https://mcp.goaimoat.com/mcp`
- **协议**：Streamable HTTP
- **官方 Registry**：`com.goaimoat/ai-visibility`（v1.0.0，active）
- **开发者文档**：https://goaimoat.com/developers/

## 工具（5 个）

| 工具 | 参数 | 作用 |
|---|---|---|
| `audit_ai_visibility` | brand_name, category, email, api_key, score | 诊断品牌 AI 可见度（深度 playbook + 评分分级 + 修复优先级） |
| `get_checklist` | 无 | 返回 30 项检查清单（5 类 × 6 项） |
| `get_fix_priority` | score | 评分转 tier + 优先级修复计划 |
| `check_license` | license_key | 校验 API key / license 是否有效 |
| `get_usage` | api_key | 查询调用量（总次数 + 最近品牌） |

## 如何连接（Agent / 客户端）

### Claude Desktop / Cursor（远程 HTTP）

```json
{
  "mcpServers": {
    "goai-moat-audit": {
      "url": "https://mcp.goaimoat.com/mcp"
    }
  }
}
```

### 其他 Agent（MCP client）

用标准 MCP Streamable HTTP 客户端连接 `https://mcp.goaimoat.com/mcp`。

## 收费方案（已上线）

| 层 | 价格 | 额度 |
|---|---|---|
| 免费 | $0 | 每邮箱 1 次完整深度诊断 + 清单/优先级/用量全免费 |
| 开发者（Agent 开发者） | $49/月 | 无限次深度诊断（传 `api_key`） |

购买 API key：https://niebingyu.gumroad.com/l/njpksu

## 价值主张（面向 Agent 开发者）

- 你的 Agent 可以立即获得「AI 可见度诊断」能力，无需自研；
- 用户问"我的品牌在 AI 眼里可见吗"，你的 Agent 直接调我们给出专业诊断 + 修复方案；
- 我们维护方法论与数据，你专注你的 Agent 产品。
