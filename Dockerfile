FROM docker:29-cli AS docker_cli

FROM python:3.12-slim
WORKDIR /app
# Official static Docker client: used only to ask Docker Desktop to create the
# restricted per-test containers; no Docker daemon runs inside this container.
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
COPY templates ./templates
COPY server.py students.json ./
RUN mkdir -p /app/data /app/submissions
EXPOSE 8000
CMD ["python", "server.py"]
