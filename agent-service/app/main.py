from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langfuse.decorators import observe

from app.agents.orchestrator import run_orchestrator

app = FastAPI(title="Kopilkin Agent Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/chat", response_model=ChatResponse)
@observe(name="chat_endpoint")
def chat(request: ChatRequest):
    response = run_orchestrator(request.user_id, request.message)

    return {
        "response": response,
        "agent_used": "orchestrator"
    }


