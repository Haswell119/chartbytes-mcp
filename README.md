# ChartBytes MCP server

[![Haswell119/chartbytes-mcp MCP server](https://glama.ai/mcp/servers/Haswell119/chartbytes-mcp/badges/score.svg)](https://glama.ai/mcp/servers/Haswell119/chartbytes-mcp)

A [Model Context Protocol](https://modelcontextprotocol.io) server that gives any MCP
client (Claude, Cursor, Claude Code, or any agent) the `generate_chart` tool — render a
chart to a **static image URL** via [ChartBytes](https://chartbytes.meridian-digital.pro) and get
it back both inline (to see) and as a URL/markdown snippet (to embed).

Zero dependencies — pure Python stdlib. One file, runs over stdio.

## Why

Charting libraries render in a browser. But an agent writing an email, a GitHub README, a
Notion page, a Slack message, or a PDF report has no browser. ChartBytes returns a plain
`<img>` / `![chart](url)` that renders anywhere. This server exposes that to agents.

## Install & configure

No install required — just point your MCP client at `server.py`:

```json
{
  "mcpServers": {
    "chartbytes": {
      "command": "python3",
      "args": ["server.py"]
    }
  }
}
```

Optional: `"env": { "CHARTBYTES_URL": "https://chartbytes.meridian-digital.pro" }` (defaults to
the hosted endpoint).

## Tool: `generate_chart`

| argument | meaning | default |
|----------|---------|---------|
| `data` | values — flat list `[12,19,8,24]`, series list `[[4,8,6],[2,3,4]]`, or `"1,2,3\|4,5,6"` | required |
| `type` | `bar` · `hbar` · `stacked` · `pie` · `donut` | `bar` |
| `labels` | category labels (list or comma string) | `1,2,3…` |
| `title` | chart title | — |
| `width` / `height` | size in px | `600` × `300` |
| `format` | `png` · `svg` | `png` |
| `theme` | `light` (free) · `dark` · `brand` (Pro) | `light` |

The tool returns the rendered image inline (PNG) plus the URL and a markdown snippet you
can paste straight into a README, email or Notion block.

## Example session

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_chart","arguments":{"type":"donut","data":[12,19,8,24],"labels":["Q1","Q2","Q3","Q4"],"title":"Revenue"}}}' \
  | python3 server.py
```

## Pricing

The server is MIT and free. ChartBytes itself is free for 500 renders/month (light theme);
Pro (one-time $9) unlocks dark/brand themes, 25k renders/month and immutable caching:
<https://buy.stripe.com/fZu7sNdbW1HPgNSgOrgUM05>.

## License

MIT. Built by Meridian Digital.
