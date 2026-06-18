from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.schemas import TransactionCreate, TransactionResponse, SummaryResponse
from app.service import (
    create_transaction_logic,
    delete_transaction_logic,
    get_user_summary_logic,
    get_user_transactions_logic,
)
from app.grpc_server import start_grpc_server, stop_grpc_server


app = FastAPI(title="Kopilkin Transaction Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def on_startup():
    start_grpc_server()


@app.on_event("shutdown")
def on_shutdown():
    stop_grpc_server()


@app.get("/")
def root():
    return {
        "service": "transaction-service",
        "status": "running",
        "grpc": "enabled",
    }


@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    return create_transaction_logic(data=data, db=db)


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
def get_user_transactions(user_id: str, db: Session = Depends(get_db)):
    return get_user_transactions_logic(user_id=user_id, db=db)


@app.get("/transactions/{user_id}/summary", response_model=SummaryResponse)
def get_user_summary(user_id: str, db: Session = Depends(get_db)):
    return get_user_summary_logic(user_id=user_id, db=db)


@app.get("/summary/{user_id}", response_model=SummaryResponse)
def get_user_summary_alias(user_id: str, db: Session = Depends(get_db)):
    return get_user_summary_logic(user_id=user_id, db=db)


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, db: Session = Depends(get_db)):
    return delete_transaction_logic(transaction_id=transaction_id, db=db)
