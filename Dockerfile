FROM python:3.11-slim
WORKDIR /app
COPY server.py ./
ENTRYPOINT ["python3", "server.py"]
