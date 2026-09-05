FROM docker:27-cli AS dockercli

FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

# The sandbox (services/execution/sandbox.py) and the MCP client
# (services/mcp/mcp_client.py) both shell out to the `docker` CLI / a
# python3 subprocess from inside this container. That needs the Docker
# CLI installed here plus the host's docker socket mounted in
# (see docker-compose.yml) -- a "Docker-outside-of-Docker" setup. Debian's
# own docker.io apt package only ships dockerd, not the client, so the
# binary is copied from Docker's official minimal -cli image instead.
# Running as root is what keeps docker.sock access simple; the usual
# non-root hardening is skipped deliberately for this reason.
COPY --from=dockercli /usr/local/bin/docker /usr/local/bin/docker

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Single worker, intentionally: ConversationMemory (services/memory/) is
# an in-process dict, not a shared store. Multiple workers/replicas would
# each get their own copy, silently fragmenting chat history per request.
# Don't add --workers here until memory is backed by something shared
# (e.g. Redis) -- that's follow-up work, not part of this milestone.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
