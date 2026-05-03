FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY infra/matrix/requirements.txt .
ENV VIRTUAL_ENV=/app/.venv
RUN uv venv /app/.venv && uv pip install -r requirements.txt
ENV PATH="/app/.venv/bin:$PATH"

COPY src/matrix_common ./matrix_common
COPY src/matrix_api ./matrix_api

EXPOSE 8083
CMD ["uvicorn", "matrix_api.main:app", "--host", "0.0.0.0", "--port", "8083", "--no-access-log"]
