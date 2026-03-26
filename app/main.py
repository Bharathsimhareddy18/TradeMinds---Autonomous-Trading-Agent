
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.scheduler import start_scheduler, scheduler
from app.services.chat_agent import run_chat_agent
from app.config import supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="TradeMinds",
    description="Autonomous Trading Agent — momentum + scalp strategies",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class ChatRequest(BaseModel):
    question: str


@app.get("/")
def root():
    return {
        "message": "Welcome to TradeMinds Autonomous Trading Agent API!",
        "Version": "3.0.0",
        "Documentation": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "running"}


@app.get("/account")
def get_account():
    """Current balance, total P&L, win rate."""
    return supabase.table("account").select("*").eq("id", 1).execute().data[0]


@app.get("/trades")
def get_trades(limit: int = 20):
    """Latest trades — both momentum and scalp."""
    return supabase.table("trades") \
        .select("*") \
        .order("timestamp", desc=True) \
        .limit(limit) \
        .execute().data


@app.get("/trades/{date}")
def get_trades_by_date(date: str):
    """
    All trades for a specific date.
    Format: 2024-03-26
    """
    return supabase.table("trades") \
        .select("*") \
        .gte("timestamp", f"{date}T00:00:00") \
        .lte("timestamp", f"{date}T23:59:59") \
        .order("timestamp", desc=True) \
        .execute().data


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    Ask anything about trade history in natural language.
    Example: 'Why did you skip trading at 11AM today?'
    """
    answer = await run_chat_agent(req.question)
    return {"answer": answer}
