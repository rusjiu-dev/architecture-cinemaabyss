import os
import random
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

MONOLITH_URL = os.getenv("MONOLITH_URL", "http://monolith:8080")
MOVIES_SERVICE_URL = os.getenv("MOVIES_SERVICE_URL", "http://movies-service:8081")
EVENTS_SERVICE_URL = os.getenv("EVENTS_SERVICE_URL", "http://events-service:8082")
GRADUAL_MIGRATION = os.getenv("GRADUAL_MIGRATION", "false").lower() == "true"
MOVIES_MIGRATION_PERCENT = int(os.getenv("MOVIES_MIGRATION_PERCENT", "0"))

app = FastAPI(title="CinemaAbyss Proxy Service")

# HTTP клиент с таймаутами
client = httpx.AsyncClient(timeout=30.0)


def should_route_to_movies() -> bool:
    """
    Определяет, должен ли запрос к /api/movies быть направлен в микросервис movies.
    При выключенном фиче-флаге всегда возвращает False.
    """
    if not GRADUAL_MIGRATION:
        return False
    return random.randint(1, 100) <= MOVIES_MIGRATION_PERCENT


@app.get("/health")
async def health():
    """Проверка работоспособности прокси."""
    return Response(content="Strangler Fig Proxy is healthy", media_type="text/plain")


@app.api_route("/api/movies/health", methods=["GET"])
async def movies_health():
    """Прокси для health-check микросервиса movies."""
    url = f"{MOVIES_SERVICE_URL}/api/movies/health"
    try:
        resp = await client.get(url)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=503)


@app.api_route("/api/events/health", methods=["GET"])
async def events_health():
    """Прокси для health-check микросервиса events."""
    url = f"{EVENTS_SERVICE_URL}/api/events/health"
    try:
        resp = await client.get(url)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=503)


@app.api_route("/api/events/{path:path}", methods=["POST"])
async def events_proxy(path: str, request: Request):
    """Прокси для всех запросов к микросервису events."""
    url = f"{EVENTS_SERVICE_URL}/api/events/{path}"
    body = await request.body()
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=body,
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=503)


@app.api_route("/api/movies", methods=["GET", "POST"])
async def movies_proxy(request: Request):
    """
    Прокси для /api/movies с процентной маршрутизацией.
    GET и POST запросы перенаправляются либо в монолит, либо в микросервис movies.
    """
    use_microservice = should_route_to_movies()
    target_url = MOVIES_SERVICE_URL if use_microservice else MONOLITH_URL
    path = request.url.path
    url = f"{target_url}{path}"
    
    body = await request.body()
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=body,
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=503)


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def monolith_proxy(path: str, request: Request):
    """
    Прокси для всех остальных запросов (users, payments, subscriptions).
    Направляются в монолит.
    """
    url = f"{MONOLITH_URL}/api/{path}"
    body = await request.body()
    try:
        resp = await client.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            content=body,
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=503)


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()