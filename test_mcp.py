#!/usr/bin/env python3
"""End-to-end stdio test for the ChartBytes MCP server against the live API."""
import json
import subprocess
import sys

SRV = "/opt/data/workspace/hermes-money/work/chartbytes-mcp/server.py"

msgs = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
     "params": {"name": "generate_chart",
                "arguments": {"type": "donut", "data": [12, 19, 8, 24],
                              "labels": ["Q1", "Q2", "Q3", "Q4"], "title": "Revenue"}}},
    {"jsonrpc": "2.0", "id": 4, "method": "ping"},
]

payload = "\n".join(json.dumps(m) for m in msgs) + "\n"

proc = subprocess.run(["python3", SRV], input=payload, capture_output=True, text=True, timeout=60)
lines = [l for l in proc.stdout.splitlines() if l.strip()]
if proc.stderr:
    print("STDERR:", proc.stderr, file=sys.stderr)

resps = [json.loads(l) for l in lines]
by_id = {r.get("id"): r for r in resps}

assert by_id[1]["result"]["serverInfo"]["name"] == "chartbytes-mcp", by_id[1]
print("initialize OK:", by_id[1]["result"]["serverInfo"], "proto:", by_id[1]["result"]["protocolVersion"])

tools = by_id[2]["result"]["tools"]
assert len(tools) == 1 and tools[0]["name"] == "generate_chart"
print("tools/list OK: 1 tool ->", tools[0]["name"])

call = by_id[3]["result"]
assert call["isError"] is False, call
content = call["content"]
kinds = [c["type"] for c in content]
assert "image" in kinds and "text" in kinds, kinds
img = next(c for c in content if c["type"] == "image")
import base64
raw = base64.b64decode(img["data"])
assert raw[:8] == b"\x89PNG\r\n\x1a\n", raw[:8]
txt = next(c for c in content if c["type"] == "text")["text"]
print("tools/call OK: image", img["mimeType"], len(raw), "bytes; PNG magic verified")
print("  text block:", txt[:160].replace("\n", " | "))

assert by_id[4]["result"] == {}
print("ping OK")

print("\nALL CHECKS PASSED")
