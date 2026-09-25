FROM python:3.11-slim
LABEL org.opencontainers.image.source="https://github.com/Haswell119/chartbytes-mcp"
LABEL org.opencontainers.image.description="ChartBytes MCP server — generate chart images (PNG/SVG) for AI agents"
LABEL io.modelcontextprotocol.server.name="io.github.Haswell119/chartbytes-mcp"
WORKDIR /app
COPY server.py ./
ENTRYPOINT ["python3", "server.py"]
