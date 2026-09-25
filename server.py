#!/usr/bin/env python3
"""ChartBytes MCP server — expose the ChartBytes chart-image API to any MCP client.

A zero-dependency (stdlib-only) Model Context Protocol server that gives an LLM agent
one tool, `generate_chart`, which renders a chart to a static image URL (and returns the
image inline) so the agent can drop a chart into an email, README, Notion page, Slack
message, or PDF report — anywhere an <img> works but a JS charting library cannot.

Transport: stdio (newline-delimited JSON-RPC 2.0), the default MCP transport.
Configure any MCP client with:
  { "command": "python3", "args": ["server.py"] }
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

CHARTBYTES_URL = os.environ.get(
    "CHARTBYTES_URL", "https://chartbytes.meridian-digital.pro"
).rstrip("/")
CHARTBYTES_LICENSE = os.environ.get("CHARTBYTES_LICENSE", "").strip()

CHART_TYPES = ["bar", "hbar", "stacked", "pie", "donut"]
FORMATS = ["png", "svg"]
THEMES = ["light", "dark", "brand"]

SERVER_NAME = "chartbytes-mcp"
SERVER_VERSION = "0.3.0"


# --------------------------------------------------------------------------- #
# ChartBytes client
# --------------------------------------------------------------------------- #
def build_chart_url(args):
    """Validate + normalize tool arguments into a ChartBytes GET /chart URL."""
    # -- data (required): flat list, list of series, or a "1,2,3|4,5,6" string
    data = args.get("data")
    if data is None:
        raise ValueError("'data' is required")
    if isinstance(data, str):
        series_str = data
    else:
        if not isinstance(data, list) or not data:
            raise ValueError("'data' must be a non-empty list or string")
        if all(isinstance(x, (int, float)) for x in data):
            series = [data]
        elif all(isinstance(x, list) for x in data):
            series = data
        else:
            raise ValueError("'data' must be flat numbers or a list of series")
        series_str = "|".join(
            ",".join(str(v) for v in s) for s in series if s
        )
        if not series_str:
            raise ValueError("'data' contained no values")

    ctype = args.get("type", "bar")
    if ctype not in CHART_TYPES:
        raise ValueError(f"type must be one of {CHART_TYPES}")

    labels = args.get("labels")
    if isinstance(labels, list):
        labels = ",".join(str(l) for l in labels)
    elif labels is None:
        labels = ""

    fmt = args.get("format", "png")
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")

    theme = args.get("theme", "light")
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {THEMES}")

    qparams = {
        "t": ctype,
        "d": series_str,
        "labels": labels,
        "title": args.get("title", ""),
        "w": args.get("width", 600),
        "h": args.get("height", 300),
        "format": fmt,
        "theme": theme,
    }
    if CHARTBYTES_LICENSE:
        qparams["lic"] = CHARTBYTES_LICENSE
    q = urllib.parse.urlencode(qparams)
    return f"{CHARTBYTES_URL}/chart?{q}", fmt


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "chartbytes-mcp/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


# --------------------------------------------------------------------------- #
# MCP tool definitions
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "name": "generate_chart",
        "description": (
            "Render a chart as a static image (PNG or SVG) via the ChartBytes API and "
            "return it both inline (an image the caller can view) and as an embeddable "
            "URL + Markdown snippet for READMEs, emails, Notion, Slack, or PDFs — anywhere "
            "an <img> works but a JavaScript charting library cannot. Read-only: generates "
            "an image from the supplied data and never mutates external state."
        ),
        "annotations": {
            "readOnlyHint": True,
            "idempotentHint": True,
        },
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": CHART_TYPES,
                    "description": (
                        "Chart type to render: 'bar' (vertical bars), 'hbar' (horizontal "
                        "bars), 'stacked' (stacked vertical bars, one per series), 'pie' "
                        "(single-series pie), or 'donut' (single-series donut). Default 'bar'."
                    ),
                },
                "data": {
                    "type": ["array", "string"],
                    "description": (
                        "Required. Values to plot. A flat number list e.g. [12,19,8,24] "
                        "renders one series; a list of series e.g. [[4,8,6],[2,3,4]] renders "
                        "grouped/stacked bars; or pass a string '1,2,3|4,5,6' (series "
                        "separated by '|')."
                    ),
                },
                "labels": {
                    "type": ["array", "string"],
                    "description": (
                        "Category labels for the data, as a list of strings or a "
                        "comma-separated string. Optional."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Chart title shown above the plot. Optional.",
                },
                "width": {
                    "type": "integer",
                    "description": "Image width in pixels (default 600).",
                },
                "height": {
                    "type": "integer",
                    "description": "Image height in pixels (default 300).",
                },
                "format": {
                    "type": "string",
                    "enum": FORMATS,
                    "description": "Output format: 'png' (default) or 'svg'.",
                },
                "theme": {
                    "type": "string",
                    "enum": THEMES,
                    "description": (
                        "Color theme. 'light' is free; 'dark' and 'brand' require a "
                        "ChartBytes Pro license (a one-time paid upgrade). If Pro is "
                        "requested without a license the server explains how to buy it."
                    ),
                },
            },
            "required": ["data"],
        },
    },
]


# --------------------------------------------------------------------------- #
# JSON-RPC / MCP message handling
# --------------------------------------------------------------------------- #
def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def rpc_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def rpc_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message}}


def handle_call(call_id, name, arguments):
    arguments = arguments or {}
    if name == "generate_chart":
        try:
            url, fmt = build_chart_url(arguments)
            body, ctype = fetch(url)
        except ValueError as e:
            return rpc_error(call_id, -32602, f"Invalid arguments: {e}")
        except urllib.error.HTTPError as e:
            # 403 = a Pro-only feature (dark/brand theme) requested without a license.
            if e.code == 403:
                return rpc_result(call_id, {
                    "content": [{"type": "text", "text": (
                        "Chart not rendered: this request uses a Pro-only feature (dark or "
                        "brand theme). ChartBytes Pro is a $9 one-time upgrade that unlocks "
                        "dark/brand themes and 25,000 renders/month.\n"
                        "Buy: https://chartbytes.meridian-digital.pro/api/checkout\n"
                        "After purchase, set the CHARTBYTES_LICENSE environment variable to "
                        "your license key (shown after checkout) and re-run this tool."
                    )}],
                    "isError": False,
                })
            if e.code == 429:
                return rpc_result(call_id, {
                    "content": [{"type": "text", "text": (
                        "Chart not rendered: the free monthly render quota (500) is "
                        "exceeded. ChartBytes Pro ($9 one-time) raises it to 25,000/month: "
                        "https://chartbytes.meridian-digital.pro/api/checkout"
                    )}],
                    "isError": False,
                })
            return rpc_error(call_id, -32000, f"ChartBytes HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            return rpc_error(call_id, -32000, f"ChartBytes request failed: {e}")

        markdown = f"![chart]({url})"
        if fmt == "png":
            b64 = base64.b64encode(body).decode("ascii")
            content = [
                {"type": "image", "data": b64, "mimeType": "image/png"},
                {"type": "text", "text":
                    f"Chart rendered. URL: {url}\nMarkdown: {markdown}"},
            ]
        else:  # svg — return as text (also printable / embeddable)
            content = [
                {"type": "text", "text":
                    f"Chart rendered (SVG). URL: {url}\nMarkdown: {markdown}\n\n{body.decode('utf-8', 'replace')}"},
            ]
        return rpc_result(call_id, {"content": content, "isError": False})
    return rpc_error(call_id, -32601, f"Unknown tool: {name}")


def handle_request(req):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    # Notifications (no id) — nothing to reply to.
    if req_id is None:
        return None

    if method == "initialize":
        proto = params.get("protocolVersion", "2024-11-05")
        return rpc_result(req_id, {
            "protocolVersion": proto,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    if method == "ping":
        return rpc_result(req_id, {})
    if method == "tools/list":
        return rpc_result(req_id, {"tools": TOOLS})
    if method == "tools/call":
        return handle_call(req_id, params.get("name"), params.get("arguments"))
    if method == "resources/list":
        return rpc_result(req_id, {"resources": []})
    if method == "prompts/list":
        return rpc_result(req_id, {"prompts": []})
    return rpc_error(req_id, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    main()
