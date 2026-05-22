import os
import time
from typing import Optional

import httpx
import redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse


AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:8002")
SAVINGS_SERVICE_URL = os.getenv("SAVINGS_SERVICE_URL", "http://localhost:8003")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8004")
INSTANCE_NAME = os.getenv("INSTANCE_NAME", "api-gateway")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
)

app = FastAPI(title="Kopilkin API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    current_window = int(time.time() // 60)

    key = f"rate_limit:{client_ip}:{current_window}"

    try:
        request_count = redis_client.incr(key)

        if request_count == 1:
            redis_client.expire(key, 60)

        if request_count > RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "limit_per_minute": RATE_LIMIT_PER_MINUTE,
                },
            )

    except Exception as error:
        print(f"[RateLimiter] Redis error: {error}")

    return await call_next(request)


@app.get("/health")
def health():
    return {
        "service": "api-gateway",
        "instance": INSTANCE_NAME,
        "status": "running",
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }


async def proxy_request(
    request: Request,
    target_base_url: str,
    path: Optional[str] = "",
):
    query_string = request.url.query

    if path:
        target_url = f"{target_base_url}/{path}"
    else:
        target_url = target_base_url

    if query_string:
        target_url = f"{target_url}?{query_string}"

    body = await request.body()

    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }

    response_headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in excluded_headers
    }

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.headers.get("content-type"),
    )


@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def auth_proxy(path: str, request: Request):
    return await proxy_request(
        request=request,
        target_base_url=AUTH_SERVICE_URL,
        path=path,
    )


@app.api_route("/transactions", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def transactions_root_proxy(request: Request):
    return await proxy_request(
        request=request,
        target_base_url=f"{TRANSACTION_SERVICE_URL}/transactions",
    )


@app.api_route("/transactions/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def transactions_proxy(path: str, request: Request):
    return await proxy_request(
        request=request,
        target_base_url=TRANSACTION_SERVICE_URL,
        path=f"transactions/{path}",
    )


@app.api_route("/summary/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def summary_proxy(path: str, request: Request):
    return await proxy_request(
        request=request,
        target_base_url=TRANSACTION_SERVICE_URL,
        path=f"summary/{path}",
    )


@app.api_route("/goals", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def goals_root_proxy(request: Request):
    return await proxy_request(
        request=request,
        target_base_url=f"{SAVINGS_SERVICE_URL}/goals",
    )


@app.api_route("/goals/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def goals_proxy(path: str, request: Request):
    return await proxy_request(
        request=request,
        target_base_url=SAVINGS_SERVICE_URL,
        path=f"goals/{path}",
    )


@app.api_route("/agent/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def agent_proxy(path: str, request: Request):
    return await proxy_request(
        request=request,
        target_base_url=AGENT_SERVICE_URL,
        path=path,
    )