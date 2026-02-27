# EtherCode Agent Runtime (EAR)

Backend modular en FastAPI para descubrir y ejecutar agentes Python desde el directorio `agents/` con autenticación por API key, logging estructurado y contrato estándar de ejecución.

## Características

- Descubrimiento automático de agentes mediante `manifest.json`.
- API REST versionada (`/v1`) para listar metadata y ejecutar agentes.
- Autenticación simple por header `X-API-Key`.
- Respuesta estándar con latencia en milisegundos.
- Manejo robusto de errores y timeouts por agente.
- Logging estructurado en JSON hacia stdout + persistencia en `runtime_requests.jsonl`.
- Documentación automática en `/docs` y esquema OpenAPI en `/openapi.json`.
- Base lista para escalar hacia multi-tenant (headers adicionales, múltiples API keys, rate limiting).

## Estructura

```text
ethercode-agent-runtime/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── dependencies.py
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── execution.py
│   │   └── response.py
│   ├── core/
│   │   ├── registry.py
│   │   ├── loader.py
│   │   ├── security.py
│   │   └── logger.py
│   ├── routes/
│   │   ├── agents.py
│   │   └── execution.py
│   └── services/
│       └── runner.py
├── agents/
│   └── sample_agent/
│       ├── agent.py
│       └── manifest.json
├── requirements.txt
├── README.md
├── .env.example
└── run.sh
```

## Instalación local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecutar

```bash
uvicorn app.main:app --reload
```

o usando helper script:

```bash
./run.sh
```

## Probar

```bash
curl -H "X-API-Key: supersecrettoken" http://localhost:8000/v1/agents
```

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecrettoken" \
  -d '{"input": {"message": "Hola"}, "context": {}}' \
  http://localhost:8000/v1/run/sample-agent
```

## Endpoints

- `GET /v1/agents`: lista resumida de agentes.
- `GET /v1/agents/{agent_id}`: metadata completa del agente.
- `POST /v1/run/{agent_id}`: ejecución del agente.

### Contrato de ejecución

```json
{
  "input": {"message": "Hola"},
  "context": {}
}
```

Respuesta éxito:

```json
{
  "success": true,
  "agent_id": "sample-agent",
  "latency_ms": 12,
  "output": {"response": "Echo: Hola"}
}
```

Respuesta error:

```json
{
  "success": false,
  "error": "Mensaje claro",
  "latency_ms": 5,
  "agent_id": "sample-agent"
}
```

## Despliegue en producción

### Railway

1. Crear proyecto en Railway.
2. Subir este repositorio.
3. Configurar variables de entorno (`AGENT_API_KEY`, `PORT`, etc.).
4. Comando de start:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Fly.io

```bash
fly launch
fly secrets set AGENT_API_KEY=supersecrettoken
```

## Integración desde frontend (Ether Code)

```js
await fetch("https://agent-runtime-url/v1/run/sample-agent", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "supersecrettoken"
  },
  body: JSON.stringify({
    input: { message: "Hola" },
    context: {}
  })
});
```

## Generación de API key

OpenSSL:

```bash
openssl rand -hex 32
```

Python:

```python
import secrets
secrets.token_hex(32)
```

## Extensibilidad planificada

- Middleware para rate limiting.
- Hooks para persistencia de logs en DB.
- Soporte para múltiples API keys (por tenant o entorno).
- Header futuro `X-Company-Id` para segmentación multi-tenant.
