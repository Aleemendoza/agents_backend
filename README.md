# EtherCode Agent Runtime (EAR)

MVP robusto para descubrir y ejecutar agentes Python locales con FastAPI, API key, observabilidad JSON y despliegue simple.

## 1) Estructura

```text
.
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── core/
│   │   ├── loader.py
│   │   ├── logger.py
│   │   ├── middleware.py
│   │   ├── registry.py
│   │   └── security.py
│   ├── routes/
│   │   ├── agents.py
│   │   ├── execution.py
│   │   ├── system.py
│   │   └── dev.py
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── execution.py
│   │   └── response.py
│   └── services/
│       └── runner.py
├── agents/
│   └── sample_agent/
│       ├── agent.py
│       └── manifest.json
├── tests/
│   └── test_smoke.py
├── scripts/
│   ├── dev.sh
│   ├── test.sh
│   └── gen_key.py
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── run.sh
```

## 2) Variables de entorno obligatorias

```env
ENV=development
SERVICE_NAME=ethercode-agent-runtime
SERVICE_VERSION=1.1.0
COMMIT_SHA=
PORT=8000
AGENT_API_KEY=supersecrettoken
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:3000
MAX_BODY_BYTES=262144
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MIN=60
REQUEST_LOG_FILE=runtime_requests.jsonl
```

Notas:
- En `production` el rate limit queda activo por defecto.
- En `production` no uses `CORS_ORIGINS=*`.

## 3) Levantar local (5 comandos)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
./scripts/dev.sh
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
bash scripts/dev.sh
```

## 4) Endpoints

- `GET /v1/version`
- `GET /v1/info`
- `GET /v1/agents` (API key)
- `GET /v1/agents/{agent_id}` (API key)
- `POST /v1/run/{agent_id}` (API key)
- `POST /v1/dev/reload-agents` (solo development + API key)
- `GET /v1/dev/requests/recent?limit=50` (solo development + API key)

Swagger: `http://localhost:8000/docs`

## 5) 6 curl commands de smoke test

### 1. version
```bash
curl http://localhost:8000/v1/version
```

### 2. info
```bash
curl http://localhost:8000/v1/info
```

### 3. list agents sin key (debe fallar 401)
```bash
curl http://localhost:8000/v1/agents
```

### 4. list agents con key
```bash
curl -H "X-API-Key: supersecrettoken" http://localhost:8000/v1/agents
```

### 5. run sample-agent
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecrettoken" \
  -d '{"input":{"message":"Hola"},"context":{}}' \
  http://localhost:8000/v1/run/sample-agent
```

### 6. reload agents (solo dev)
```bash
curl -X POST \
  -H "X-API-Key: supersecrettoken" \
  http://localhost:8000/v1/dev/reload-agents
```

## 6) JSONL observabilidad

Cada request se escribe en `runtime_requests.jsonl` con:
- `request_id`
- `agent_id`
- `success`
- `latency_ms`
- `status_code`
- `timestamp`
- `path`, `method`
- `input_size_bytes`, `output_size_bytes`

No se persisten payloads crudos (`input/context`) para evitar PII.

## 7) Rate limit y body size

- Rate limit IP en memoria (`60s`, `RATE_LIMIT_PER_MIN`).
- Exceso: `429 {"success": false, "error": "rate_limited"}`.
- Límite body JSON: `MAX_BODY_BYTES` (default `256KB`).
- Exceso: `413 {"success": false, "error": "payload_too_large"}`.

## 8) Tests

```bash
./scripts/test.sh
```

Incluye smoke de:
- version
- auth obligatoria en list agents
- ejecución de sample-agent

## 9) Integración segura con frontend (NO exponer API key)

### Opción A: Next.js API Route proxy

`app/api/ear/[...path]/route.ts`

```ts
import { NextRequest } from "next/server";

const EAR_URL = process.env.EAR_URL!;
const EAR_API_KEY = process.env.EAR_API_KEY!;

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  const url = `${EAR_URL}/${params.path.join("/")}${req.nextUrl.search}`;
  const res = await fetch(url, {
    headers: { "X-API-Key": EAR_API_KEY }
  });
  return new Response(await res.text(), { status: res.status, headers: { "Content-Type": "application/json" } });
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  const body = await req.text();
  const res = await fetch(`${EAR_URL}/${params.path.join("/")}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": EAR_API_KEY
    },
    body
  });
  return new Response(await res.text(), { status: res.status, headers: { "Content-Type": "application/json" } });
}
```

Fetch desde frontend:

```ts
await fetch("/api/ear/v1/run/sample-agent", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ input: { message: "Hola" }, context: {} })
});
```

## 10) Deploy

### Railway
1. Crear proyecto.
2. Subir repo.
3. Configurar env vars.
4. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Fly.io
```bash
fly launch
fly secrets set AGENT_API_KEY=<tu_key>
```

### Docker
```bash
docker build -t ear .
docker run -p 8000:8000 --env-file .env ear
```

## 11) Generar API key

```bash
openssl rand -hex 32
python scripts/gen_key.py
```

## 12) Checklist final

- [ ] `uvicorn app.main:app --reload` levanta
- [ ] `/docs` responde
- [ ] `/v1/agents` lista `sample-agent` con `status=healthy`
- [ ] `/v1/run/sample-agent` responde echo
- [ ] `runtime_requests.jsonl` guarda `request_id` y `latency_ms`
- [ ] rate limit responde 429 al exceder
- [ ] tests smoke pasan
