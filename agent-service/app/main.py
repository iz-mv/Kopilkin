import logging
import time

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langfuse.decorators import observe
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.agents.orchestrator import run_orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=agent-service message=%(message)s",
)
logger = logging.getLogger("kopilkin-agent-service")

app = FastAPI(title="Kopilkin Agent Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CHAT_REQUESTS_TOTAL = Counter(
    "kopilkin_agent_chat_requests_total",
    "Total number of chat requests received by the agent service",
)
CHAT_ERRORS_TOTAL = Counter(
    "kopilkin_agent_chat_errors_total",
    "Total number of failed chat requests in the agent service",
)
CHAT_LATENCY_SECONDS = Histogram(
    "kopilkin_agent_chat_latency_seconds",
    "Latency of /chat requests in seconds",
    buckets=(1, 3, 5, 10, 30, 60, 120, 300, 600),
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    agent_used: str


@app.get("/")
def root():
    return {"service": "agent-service", "status": "running"}


@app.get("/health")
def health():
    return {"service": "agent-service", "status": "healthy"}


@app.get("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/chat", response_model=ChatResponse)
@observe(name="chat_endpoint")
def chat(request: ChatRequest):
    CHAT_REQUESTS_TOTAL.inc()
    start = time.perf_counter()
    logger.info("chat_request_started user_id=%s", request.user_id)

    try:
        response = run_orchestrator(request.user_id, request.message)
        return {
            "response": response,
            "agent_used": "orchestrator"
        }
    except Exception:
        CHAT_ERRORS_TOTAL.inc()
        logger.exception("chat_request_failed user_id=%s", request.user_id)
        raise
    finally:
        duration = time.perf_counter() - start
        CHAT_LATENCY_SECONDS.observe(duration)
        logger.info("chat_request_finished user_id=%s duration_seconds=%.2f", request.user_id, duration)
