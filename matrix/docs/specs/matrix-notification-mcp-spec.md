# Matrix Notification Platform and MCP Server Specification

## Overview

This specification defines the deployment and integration of a Matrix-based notification platform on `agent01`. The system will:

- Deploy a Matrix homeserver using Synapse in Docker on `agent01`
- Use PostgreSQL for Synapse persistence instead of SQLite
- Create a dedicated Matrix bot account for automation notifications
- Provide a Python-based Matrix notification API for simple REST-style message delivery
- Provide a Python-based MCP server so Claude/agent tooling can send Matrix notifications through controlled tools
- Store all secrets, access tokens, shared secrets, database passwords, and default room mappings in the project SOPS encrypted secrets file
- Keep federation disabled by default unless explicitly enabled later

This is intended to behave like the existing Signal notification platform, but using Matrix rooms as the destination instead of Signal recipients.

---

## Architecture

### Components

1. **Synapse Matrix homeserver**
   - Runs as a Docker container on `agent01`
   - Listens internally on `:8008`
   - Stores configuration, signing keys, media, and runtime state under a persistent volume
   - Uses PostgreSQL for production-grade persistence
   - Public registration is disabled
   - Federation is disabled by default for this iteration

2. **PostgreSQL**
   - Runs as a Docker container on `agent01`
   - Stores Synapse database state
   - Uses a persistent volume
   - Not exposed outside the Docker network

3. **matrix-api**
   - Python/FastAPI service
   - Runs as a Docker container on `agent01`
   - Listens on `:8083`
   - Provides simple REST endpoints such as `/health`, `/send`, `/rooms`, and `/send-template`
   - Authenticates callers with a bearer token
   - Sends messages to Matrix using the bot account access token and Matrix Client-Server API
   - Implemented as a Python package under `src/matrix_api/`

4. **matrix-mcp**
   - Python MCP server using the official MCP Python SDK / FastMCP
   - Runs as a Docker container on `agent01`
   - Exposes MCP tools over Streamable HTTP on `:8093` at `/mcp`
   - Uses the same Matrix sender library as `matrix-api`
   - Allows Claude/agent tooling to send notifications, create rooms, invite users, and query configured destinations
   - Implemented as a Python package under `src/matrix_mcp/`

5. **n8n / other automation tools**
   - Can call `matrix-api` directly using HTTP POST
   - Can send to configured rooms without knowing Matrix implementation details

### Deferred

- Public federation with other Matrix homeservers
- TURN server / voice / video
- Element Web deployment
- Push gateway deployment
- End-to-end encryption for automation rooms
- Bridging to Signal, ntfy, Discord, Slack, or email

---

## High-Level Flow

### REST notification flow

```text
[n8n / scripts / services]
          |
       HTTP :8083
          |
   [matrix-api — FastAPI]
   auth, validation, rate-limit
          |
 Matrix Client-Server API
          |
 [Synapse homeserver :8008]
          |
      Matrix room
```

### MCP notification flow

```text
[Claude / MCP client / agent tooling]
          |
 Streamable HTTP :8093/mcp
          |
 [matrix-mcp — FastMCP]
 tools, validation, allowlist checks
          |
 Matrix Client-Server API
          |
 [Synapse homeserver :8008]
          |
      Matrix room
```

---

## Deployment Target

### Host

- Target host: `agent01`
- Runtime: Docker + Docker Compose
- Required host directories:
  - `/opt/matrix/synapse-data`
  - `/opt/matrix/postgres-data`
  - `/opt/matrix/app-data`
  - `/opt/matrix/config`
- Required internal ports:
  - `8008` — Synapse client API, internal only unless reverse proxied
  - `8083` — matrix-api REST service, internal only
  - `8093` — matrix-mcp Streamable HTTP endpoint, internal only

### Network exposure

- Do not expose PostgreSQL outside the Docker bridge network
- Do not expose Synapse directly to the internet in this iteration
- Restrict `8083` and `8093` to trusted internal networks on `agent01`
- If external access is needed later, place Synapse behind the existing NGINX/oauth2-proxy/Keycloak pattern instead of exposing raw ports

---

## Design Decisions

### Homeserver implementation

Use **Synapse** for the initial Matrix deployment.

Rationale:

- It is the reference Matrix homeserver implementation
- It has a maintained Docker image
- It is widely documented
- It is sufficient for a private notification platform

### Database

Use PostgreSQL rather than Synapse's default SQLite.

Rationale:

- SQLite is acceptable for quick testing, but not the right default for a persistent service
- PostgreSQL makes backup, migration, and operational recovery cleaner

### Federation

Disable federation by default.

Rationale:

- This service is for private infrastructure notifications
- Federation expands the attack surface and introduces identity/domain considerations
- It can be enabled later if there is a real requirement

### Encryption

Do not enable end-to-end encryption for the automation rooms in the first iteration.

Rationale:

- Bot automation with encrypted Matrix rooms requires persistent device/session state and key management
- Plain Matrix rooms on a private homeserver are simpler and more reliable for infrastructure alerts
- Transport security and host/network access controls are the first-layer protections

### Notification destination model

The application should send to **named destinations**, not hardcoded room IDs in every workflow.

Example:

```json
{
  "destination": "home-alerts",
  "message": "Hubitat Home Rebooted"
}
```

The destination maps to a Matrix room ID in configuration:

```json
{
  "home-alerts": "!abcdefg12345:matrix.powellcompanies.com",
  "elastic-alerts": "!zyxwvut98765:matrix.powellcompanies.com"
}
```

---

## Docker Compose

### `infra/matrix/docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: matrix-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${MATRIX_POSTGRES_DB}
      POSTGRES_USER: ${MATRIX_POSTGRES_USER}
      POSTGRES_PASSWORD: ${MATRIX_POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    volumes:
      - ./postgres-data:/var/lib/postgresql/data
    networks:
      - matrix-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${MATRIX_POSTGRES_USER} -d ${MATRIX_POSTGRES_DB}"]
      interval: 30s
      timeout: 5s
      retries: 5

  synapse:
    image: matrixdotorg/synapse:latest
    container_name: matrix-synapse
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      SYNAPSE_SERVER_NAME: ${MATRIX_SERVER_NAME}
      SYNAPSE_REPORT_STATS: "no"
      TZ: ${TZ:-America/Chicago}
    volumes:
      - ./synapse-data:/data
    ports:
      - "8008:8008"
    networks:
      - matrix-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8008/_matrix/client/versions"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 30s

  matrix-api:
    build:
      context: ../..
      dockerfile: infra/matrix/api.Dockerfile
    container_name: matrix-api
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      synapse:
        condition: service_healthy
    ports:
      - "8083:8083"
    networks:
      - matrix-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8083/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

  matrix-mcp:
    build:
      context: ../..
      dockerfile: infra/matrix/mcp.Dockerfile
    container_name: matrix-mcp
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      synapse:
        condition: service_healthy
    ports:
      - "8093:8093"
    networks:
      - matrix-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8093/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

networks:
  matrix-net:
    driver: bridge
```

---

## Initial Synapse Configuration

### Generate the Synapse configuration

Before first normal startup, generate `homeserver.yaml`:

```bash
cd infra/matrix
mkdir -p synapse-data postgres-data

docker run -it --rm \
  --mount type=bind,src="$PWD/synapse-data",dst=/data \
  -e SYNAPSE_SERVER_NAME="$MATRIX_SERVER_NAME" \
  -e SYNAPSE_REPORT_STATS=no \
  matrixdotorg/synapse:latest generate
```

### Required `homeserver.yaml` changes

After generation, update `synapse-data/homeserver.yaml`:

```yaml
server_name: "${MATRIX_SERVER_NAME}"
public_baseurl: "https://${MATRIX_PUBLIC_BASEURL}/"

listeners:
  - port: 8008
    tls: false
    type: http
    x_forwarded: true
    bind_addresses: ['0.0.0.0']
    resources:
      - names: [client]
        compress: false

registration_shared_secret: "${MATRIX_REGISTRATION_SHARED_SECRET}"
enable_registration: false

# Private notification platform default.
federation_domain_whitelist: []

# PostgreSQL database.
database:
  name: psycopg2
  args:
    user: "${MATRIX_POSTGRES_USER}"
    password: "${MATRIX_POSTGRES_PASSWORD}"
    database: "${MATRIX_POSTGRES_DB}"
    host: "postgres"
    cp_min: 5
    cp_max: 10

# For first iteration, keep rooms unencrypted unless explicitly changed by users.
# E2EE bot support is deferred.
```

Implementation note: Synapse config files do not automatically expand shell variables in all contexts. Claude must either render the real values into `homeserver.yaml` from SOPS-decrypted environment at deploy time, or use Synapse-supported environment/config templating if available in the deployed image version. Do not commit rendered secrets.

---

## Secrets

All secrets are stored in the project SOPS encrypted secrets file and injected as environment variables at deploy time.

| Secret | Env Var | Description |
|---|---|---|
| Matrix server name | `MATRIX_SERVER_NAME` | Matrix server name, e.g. `matrix.powellcompanies.com` |
| Matrix public base URL | `MATRIX_PUBLIC_BASEURL` | External URL host if reverse proxied; may match server name |
| PostgreSQL DB name | `MATRIX_POSTGRES_DB` | Synapse database name |
| PostgreSQL user | `MATRIX_POSTGRES_USER` | Synapse DB user |
| PostgreSQL password | `MATRIX_POSTGRES_PASSWORD` | Synapse DB password |
| Registration shared secret | `MATRIX_REGISTRATION_SHARED_SECRET` | Secret used to create users non-interactively |
| Bot Matrix user ID | `MATRIX_BOT_USER_ID` | Example: `@notification-bot:matrix.powellcompanies.com` |
| Bot Matrix password | `MATRIX_BOT_PASSWORD` | Used only during initial login/token creation |
| Bot Matrix access token | `MATRIX_BOT_ACCESS_TOKEN` | Token used by matrix-api and matrix-mcp |
| Matrix API bearer token | `MATRIX_API_KEY` | Required for REST `/send` requests |
| MCP bearer token | `MATRIX_MCP_API_KEY` | Required at HTTP edge if using protected reverse proxy/header auth |
| Default destination | `MATRIX_DEFAULT_DESTINATION` | Example: `home-alerts` |
| Destination map JSON | `MATRIX_DESTINATIONS_JSON` | JSON map of friendly names to room IDs |
| Rate limit | `MATRIX_RATE_LIMIT` | Default: `30/minute` |

No secret may be hardcoded in Dockerfiles, source code, docker-compose, or example payloads.

---

## Matrix Bot Account Setup

### Create admin user

Create an admin user from inside the Synapse container after first startup:

```bash
docker exec -it matrix-synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -u admin \
  -p "$MATRIX_ADMIN_PASSWORD" \
  -a \
  http://localhost:8008
```

### Create notification bot user

```bash
docker exec -it matrix-synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -u notification-bot \
  -p "$MATRIX_BOT_PASSWORD" \
  http://localhost:8008
```

### Login as bot and capture access token

```bash
curl -sS -X POST "http://agent01:8008/_matrix/client/v3/login" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "m.login.password",
    "identifier": {
      "type": "m.id.user",
      "user": "notification-bot"
    },
    "password": "REPLACE_WITH_BOT_PASSWORD",
    "initial_device_display_name": "matrix-notification-bot"
  }'
```

Store the returned `access_token` in SOPS as `MATRIX_BOT_ACCESS_TOKEN`.

Do not keep bot passwords or access tokens in shell history. Use temporary files or SOPS-driven deploy scripts where possible.

---

## Room Setup

Create one or more rooms for notification destinations.

Recommended initial rooms:

| Destination | Purpose |
|---|---|
| `home-alerts` | Home automation alerts |
| `infra-alerts` | Infrastructure alerts |
| `elastic-alerts` | Elastic/SIEM alerts |
| `test-alerts` | End-to-end testing |

Room creation can be done using Element, curl, or a helper script. The bot account must be joined to each room and must have permission to send messages.

Destination map example:

```json
{
  "home-alerts": "!abc123:matrix.powellcompanies.com",
  "infra-alerts": "!def456:matrix.powellcompanies.com",
  "elastic-alerts": "!ghi789:matrix.powellcompanies.com",
  "test-alerts": "!jkl012:matrix.powellcompanies.com"
}
```

---

## Matrix Client API Usage

The sender implementation must use the Matrix Client-Server API endpoint for sending message events:

```text
PUT /_matrix/client/v3/rooms/{roomId}/send/m.room.message/{txnId}
```

Request body for a plain text notification:

```json
{
  "msgtype": "m.text",
  "body": "Hubitat Home Rebooted"
}
```

Request body for a formatted notification:

```json
{
  "msgtype": "m.text",
  "body": "Elastic ingestion warning: cluster 40 PQ is growing",
  "format": "org.matrix.custom.html",
  "formatted_body": "<strong>Elastic ingestion warning</strong>: cluster 40 PQ is growing"
}
```

Implementation requirements:

- Generate a unique transaction ID for each attempted message
- Use `Authorization: Bearer ${MATRIX_BOT_ACCESS_TOKEN}`
- Treat duplicate transaction IDs as idempotent; do not reuse them across different messages
- Validate room IDs before sending
- Allow only destinations configured in `MATRIX_DESTINATIONS_JSON` unless admin override is explicitly enabled

---

## matrix-api: Python Package (`src/matrix_api/`)

### Package Layout

```text
src/matrix_api/
├── __init__.py
├── main.py              # FastAPI app, lifespan, routes
├── config.py            # Settings loaded from env via pydantic-settings
├── models.py            # Request/response schemas
├── matrix_client.py     # Async Matrix Client-Server API wrapper
├── destinations.py      # Destination map loader and validator
├── templates.py         # Optional message templates
├── ratelimit.py         # Token-bucket rate limiter
└── logging_config.py    # Structured logging setup
```

### API Design

#### Health check

```http
GET /health
```

Returns `200 OK` if:

- matrix-api is running
- Synapse client versions endpoint is reachable
- Bot token can authenticate or perform a lightweight account check

Response:

```json
{
  "status": "ok",
  "homeserver": "http://synapse:8008",
  "bot_user_id": "@notification-bot:matrix.powellcompanies.com"
}
```

#### List destinations

```http
GET /destinations
Authorization: Bearer <MATRIX_API_KEY>
```

Response:

```json
{
  "default": "home-alerts",
  "destinations": [
    "home-alerts",
    "infra-alerts",
    "elastic-alerts",
    "test-alerts"
  ]
}
```

#### Send message

```http
POST /send
Authorization: Bearer <MATRIX_API_KEY>
Content-Type: application/json
```

Request body:

```json
{
  "destination": "home-alerts",
  "message": "Hubitat Home Rebooted",
  "formatted_message": null,
  "severity": "info",
  "metadata": {
    "source": "hubitat",
    "event_type": "reboot"
  }
}
```

Rules:

- `destination` is optional and defaults to `MATRIX_DEFAULT_DESTINATION`
- `destination` must exist in `MATRIX_DESTINATIONS_JSON`
- `message` is required
- `formatted_message` is optional HTML and must be sanitized or generated from trusted templates only
- `severity` is optional: `debug`, `info`, `warning`, `error`, `critical`
- `metadata` is optional and should be included in logs, not blindly rendered into HTML

Response:

```json
{
  "status": "ok",
  "destination": "home-alerts",
  "room_id": "!abc123:matrix.powellcompanies.com",
  "event_id": "$eventid:matrix.powellcompanies.com"
}
```

#### Send templated message

```http
POST /send-template
Authorization: Bearer <MATRIX_API_KEY>
Content-Type: application/json
```

Request body:

```json
{
  "destination": "elastic-alerts",
  "template": "elastic_pq_warning",
  "values": {
    "cluster": "cluster-40",
    "pipeline": "data-router",
    "pq_size_gb": 82.5
  }
}
```

Templates must be stored in source-controlled non-secret files. Template rendering must escape untrusted values.

### Backend Logic

1. Verify `Authorization: Bearer` token against `MATRIX_API_KEY`
2. Validate request body
3. Apply rate limiter
4. Resolve destination to Matrix room ID
5. Build Matrix message payload
6. Send `PUT /_matrix/client/v3/rooms/{roomId}/send/m.room.message/{txnId}`
7. Return Matrix `event_id` on success
8. Log request metadata, destination, result, and error details without logging secrets

### Error Handling

| Condition | Behavior |
|---|---|
| Auth failure | `401 Unauthorized` |
| Rate limit exceeded | `429 Too Many Requests` + `Retry-After` |
| Invalid payload | `422 Unprocessable Entity` |
| Unknown destination | `404 Not Found` |
| Synapse unreachable | `503 Service Unavailable` |
| Matrix auth/token failure | `502 Bad Gateway` with sanitized error |
| Matrix send failure | Retry up to 3x with exponential backoff, then `502` |

---

## matrix-mcp: Python MCP Server (`src/matrix_mcp/`)

### Package Layout

```text
src/matrix_mcp/
├── __init__.py
├── server.py            # FastMCP server and tool registration
├── config.py            # Env settings
├── matrix_client.py     # Shared Matrix client wrapper or import from common package
├── destinations.py      # Destination validation
├── schemas.py           # Pydantic models for tool arguments/results
└── logging_config.py    # Structured logging to stderr/file
```

### Transport

Use Streamable HTTP for the deployed service:

```text
http://agent01:8093/mcp
```

A local STDIO mode may be supported for development, but production on `agent01` should use HTTP transport so multiple clients can connect without shell access.

### MCP Tools

#### `send_matrix_message`

Send a message to a configured Matrix destination.

Input schema:

```json
{
  "destination": "home-alerts",
  "message": "Hubitat Home Rebooted",
  "severity": "info"
}
```

Rules:

- `destination` is optional and defaults to `MATRIX_DEFAULT_DESTINATION`
- `destination` must exist in the allowlisted destination map
- `message` must be plain text
- The tool must return the Matrix `event_id` and destination used

Output:

```json
{
  "status": "ok",
  "destination": "home-alerts",
  "event_id": "$eventid:matrix.powellcompanies.com"
}
```

#### `send_matrix_template`

Send a message using a server-side template.

Input schema:

```json
{
  "destination": "elastic-alerts",
  "template": "elastic_pq_warning",
  "values": {
    "cluster": "cluster-40",
    "pq_size_gb": 82.5
  }
}
```

Rules:

- Only templates bundled with the service may be used
- User-supplied template strings are not allowed
- All rendered values must be escaped unless explicitly trusted

#### `list_matrix_destinations`

Return configured destination names and the default destination.

Input schema:

```json
{}
```

Output:

```json
{
  "default": "home-alerts",
  "destinations": ["home-alerts", "infra-alerts", "elastic-alerts", "test-alerts"]
}
```

#### `create_matrix_room`

Create a new private Matrix room for notifications.

Input schema:

```json
{
  "name": "Elastic Alerts",
  "alias": "elastic-alerts",
  "invite_users": ["@patrick:matrix.powellcompanies.com"]
}
```

Rules:

- This tool is admin-level and must be disabled by default unless `MATRIX_MCP_ENABLE_ADMIN_TOOLS=true`
- Room alias must be validated
- The bot must remain joined to the room
- The new room ID should be returned so the operator can add it to `MATRIX_DESTINATIONS_JSON`

#### `invite_matrix_user`

Invite a Matrix user to a configured destination room.

Input schema:

```json
{
  "destination": "home-alerts",
  "user_id": "@patrick:matrix.powellcompanies.com"
}
```

Rules:

- Admin-level; disabled unless `MATRIX_MCP_ENABLE_ADMIN_TOOLS=true`
- Destination must be allowlisted
- User ID must match Matrix ID format

### MCP Security Requirements

- MCP tools must be narrowly scoped to Matrix notification actions
- Do not expose arbitrary Matrix API passthrough tools
- Do not expose shell execution tools
- Do not expose raw access tokens or room IDs unless explicitly needed in admin output
- Log to stderr or files; do not corrupt STDIO JSON-RPC if STDIO mode is used for local development
- Validate all tool inputs with Pydantic
- Keep admin tools disabled by default
- Require network-level restriction and/or reverse proxy auth for `:8093`

---

## Shared Python Client Package

To avoid duplicate Matrix send logic, create a shared package:

```text
src/matrix_common/
├── __init__.py
├── client.py            # MatrixClient class
├── config.py            # Shared settings model
├── destinations.py      # Destination map parser
├── messages.py          # Message payload builders
├── errors.py            # Typed exceptions
└── retry.py             # Retry helpers
```

Both `matrix-api` and `matrix-mcp` should import from `matrix_common`.

---

## Dockerfiles

### `infra/matrix/api.Dockerfile`

```dockerfile
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
CMD ["uvicorn", "matrix_api.main:app", "--host", "0.0.0.0", "--port", "8083"]
```

### `infra/matrix/mcp.Dockerfile`

```dockerfile
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
COPY src/matrix_mcp ./matrix_mcp

EXPOSE 8093
CMD ["python", "-m", "matrix_mcp.server"]
```

### `infra/matrix/requirements.txt`

```text
fastapi
uvicorn[standard]
httpx
pydantic
pydantic-settings
mcp[cli]
python-json-logger
```

---

## Example MCP Server Skeleton

```python
# src/matrix_mcp/server.py

import logging
from typing import Literal

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from matrix_common.client import MatrixClient
from matrix_common.config import Settings
from matrix_common.destinations import DestinationResolver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()
resolver = DestinationResolver.from_json(settings.matrix_destinations_json)
client = MatrixClient(
    homeserver_url=settings.matrix_homeserver_url,
    access_token=settings.matrix_bot_access_token,
)

mcp = FastMCP("matrix-notifications")

Severity = Literal["debug", "info", "warning", "error", "critical"]

class SendMatrixMessageResult(BaseModel):
    status: str
    destination: str
    event_id: str

@mcp.tool()
async def send_matrix_message(
    message: str = Field(..., min_length=1, max_length=8000),
    destination: str | None = None,
    severity: Severity = "info",
) -> SendMatrixMessageResult:
    """Send a plain text notification to an allowlisted Matrix destination."""
    dest_name = destination or settings.matrix_default_destination
    room_id = resolver.resolve(dest_name)
    event_id = await client.send_text(room_id=room_id, body=message, severity=severity)
    return SendMatrixMessageResult(status="ok", destination=dest_name, event_id=event_id)

@mcp.tool()
async def list_matrix_destinations() -> dict:
    """List configured Matrix notification destinations."""
    return {
        "default": settings.matrix_default_destination,
        "destinations": resolver.names(),
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

Implementation note: This is a skeleton only. Claude must implement the actual `matrix_common` package, config loading, error handling, retries, health endpoint, and HTTP bind/port settings.

---

## Example Matrix Client Skeleton

```python
# src/matrix_common/client.py

from __future__ import annotations

import uuid
from urllib.parse import quote

import httpx

class MatrixClient:
    def __init__(self, homeserver_url: str, access_token: str, timeout: float = 15.0):
        self.homeserver_url = homeserver_url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout

    async def send_text(self, room_id: str, body: str, severity: str = "info") -> str:
        txn_id = str(uuid.uuid4())
        encoded_room_id = quote(room_id, safe="")
        url = (
            f"{self.homeserver_url}"
            f"/_matrix/client/v3/rooms/{encoded_room_id}"
            f"/send/m.room.message/{txn_id}"
        )
        payload = {
            "msgtype": "m.text",
            "body": body,
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as http:
            response = await http.put(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["event_id"]
```

---

## n8n Integration

### Reusable Workflow: `Send Matrix Message`

#### Node 1: Trigger

- Manual / Webhook / Scheduled / Alert-driven

#### Node 2: Set Message

```json
{
  "destination": "{{ $json["destination"] || "home-alerts" }}",
  "message": "Alert: {{ $json["event"] }}",
  "severity": "{{ $json["severity"] || "info" }}"
}
```

#### Node 3: HTTP Request

- Method: `POST`
- URL: `http://agent01:8083/send`
- Headers:
  - `Authorization: Bearer {{ $env.MATRIX_API_KEY }}`
  - `Content-Type: application/json`
- Body: JSON from Node 2

`MATRIX_API_KEY` must be stored as an n8n credential or environment variable. Do not hardcode it in workflows.

---

## Claude Code MCP Registration

Once deployed, add the MCP server to Claude Code from a trusted workstation that can reach `agent01:8093`:

```bash
claude mcp add --transport http matrix-notifications http://agent01:8093/mcp
```

If the MCP endpoint is later protected by oauth2-proxy or another auth layer, configure the MCP client with the required headers/tokens according to the active Claude Code MCP configuration format.

---

## Security

- Public Matrix registration is disabled
- Bot token is stored only in SOPS and injected at runtime
- PostgreSQL is internal-only
- Synapse is internal-only for this iteration
- `matrix-api` requires bearer token auth
- `matrix-mcp` must be restricted to trusted clients by firewall, VPN, or reverse proxy auth
- MCP admin tools are disabled by default
- Destination allowlist prevents arbitrary room sends
- Logs must never include access tokens, bearer tokens, database passwords, or registration shared secrets
- HTML formatted messages must be sanitized or generated only from trusted templates
- Do not enable federation until a separate federation security review is completed

---

## Logging & Observability

- All containers log to stdout/stderr
- `matrix-api` and `matrix-mcp` use structured JSON logging
- Log fields should include:
  - service name
  - request ID
  - destination
  - Matrix room ID hash or redacted room ID
  - event ID on success
  - latency
  - error type
- Optional: forward container logs to Elasticsearch using the existing logging pipeline

---

## Backups

Back up the following:

- PostgreSQL database volume: `postgres-data`
- Synapse data volume: `synapse-data`
- Rendered non-secret config files needed for recovery
- SOPS encrypted secrets file

Recovery must be tested by restoring to a temporary Docker Compose project and verifying:

- Synapse starts
- Bot account can authenticate
- Existing rooms are visible
- A test message can be sent to `test-alerts`

---

## Deployment Checklist

- [ ] Create `infra/matrix/docker-compose.yml`
- [ ] Create `infra/matrix/api.Dockerfile`
- [ ] Create `infra/matrix/mcp.Dockerfile`
- [ ] Create `infra/matrix/requirements.txt`
- [ ] Generate `synapse-data/homeserver.yaml`
- [ ] Configure Synapse for PostgreSQL
- [ ] Disable public registration
- [ ] Keep federation disabled by default
- [ ] Add Matrix secrets to SOPS
- [ ] Start PostgreSQL and Synapse
- [ ] Create admin user
- [ ] Create `notification-bot` user
- [ ] Login as bot and store `MATRIX_BOT_ACCESS_TOKEN` in SOPS
- [ ] Create initial Matrix rooms
- [ ] Invite bot to rooms
- [ ] Build `src/matrix_common/`
- [ ] Build `src/matrix_api/`
- [ ] Build `src/matrix_mcp/`
- [ ] Deploy `matrix-api`
- [ ] Deploy `matrix-mcp`
- [ ] Verify `GET http://agent01:8083/health`
- [ ] Verify `GET http://agent01:8093/health`
- [ ] Test REST send to `test-alerts`
- [ ] Register MCP server in Claude Code
- [ ] Test `send_matrix_message` MCP tool
- [ ] Restrict ports `8008`, `8083`, and `8093` on `agent01`
- [ ] Document room IDs in SOPS-backed destination map
- [ ] Add backup procedure

---

## Acceptance Criteria

The implementation is complete when:

1. `docker compose up -d` on `agent01` starts PostgreSQL, Synapse, matrix-api, and matrix-mcp
2. Synapse health check returns successfully
3. Public registration is disabled
4. Bot account can send a message to `test-alerts`
5. `POST /send` sends a Matrix message using a friendly destination name
6. MCP tool `send_matrix_message` sends a Matrix message using a friendly destination name
7. Secrets are loaded from SOPS-decrypted environment only
8. No token or password appears in logs
9. Ports are restricted to the trusted internal network
10. Restarting containers does not lose Synapse state, bot identity, rooms, or messages

---

## Summary

This design deploys a private Matrix notification platform on `agent01` using Synapse, PostgreSQL, a FastAPI REST notification service, and a FastMCP-based MCP server. It gives n8n and scripts a simple `/send` API while giving Claude/agent tooling a controlled MCP tool interface. The design intentionally keeps federation, public registration, TURN, Element Web, and E2EE out of the first iteration to keep the notification platform reliable, private, and easy to operate.
