# Lab 3 (sbx): proves the sandbox has its OWN Docker daemon.
# Building this inside a sandbox never touches your host's docker socket.
FROM python:3.12-slim
WORKDIR /app
COPY app/ ./app/
CMD ["python", "app/main.py"]
