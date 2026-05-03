FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install sops for SOPS-encrypted secrets decryption
RUN curl -LO https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64 \
    && install -m 755 sops-v3.9.4.linux.amd64 /usr/local/bin/sops \
    && rm sops-v3.9.4.linux.amd64

# Install Node.js 22 + claude CLI
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && rm -rf /var/lib/apt/lists/*

# Create ppowell user (uid 1000) matching the agent01 host user
RUN useradd -r -u 1000 -g 0 -d /home/ppowell -M ppowell

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY infra/matrix/bridge-requirements.txt .
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv /app/.venv && uv pip install -r bridge-requirements.txt
ENV PATH="/app/.venv/bin:$PATH"

COPY src/matrix_common ./matrix_common
COPY src/matrix_bridge ./matrix_bridge

CMD ["python", "-m", "matrix_bridge.main"]
