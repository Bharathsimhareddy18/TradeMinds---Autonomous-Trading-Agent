# TradeMinds — Autonomous Paper Trading Agent

A multi-agent autonomous trading system that executes Indian equity trades, 
manages positions, and answers natural language queries — without human intervention.

Live: https://trademind-agent.vercel.app

---

## System Architecture

<img width="5515" height="4728" alt="Momentum Trading Agent-2026-03-29-080350" src="https://github.com/user-attachments/assets/383df3a6-b129-47b2-bf89-e9eb46a517c5" />


---

## What It Does

TradeMinds runs three specialized agents on a live market schedule:

**Momentum Agent** — Runs at 9:15 AM IST. Scans top movers, news, and 
trend data. Uses GPT-4o-mini to decide BUY or SKIP. Holds position 
until 3:15 PM then exits with P&L calculation.

**Scalp Agent** — Starts at 9:55 AM IST. Runs an agentic tool loop 
(max 10 calls) analyzing news and price data. Self-determines next 
wake-up interval dynamically based on market conditions. Executes 
BUY or SKIP decisions independently.

**Chat Agent** — Always available via /chat endpoint. Has live tool 
access to account balance and full trade history. Answers natural 
language queries about trade decisions, P&L, and strategy reasoning.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, APScheduler |
| AI | GPT-4o-mini, Tool Calling |
| Data | yfinance, feedparser RSS |
| Database | Supabase (PostgreSQL) |
| Infrastructure | AWS EC2 |
| Frontend | Vercel |

---

## API Endpoints

| Endpoint | Description |
|---|---|
| GET / | Health check |
| GET /trades | Recent trade history |
| GET /account | Account balance and P&L |
| POST /chat | Natural language query interface |

---

## Screenshots

<img width="1920" height="1080" alt="Screenshot from 2026-03-30 17-18-30" src="https://github.com/user-attachments/assets/062ef953-167b-4002-88c9-24a90e20e26c" />

<img width="1918" height="1006" alt="image" src="https://github.com/user-attachments/assets/0bb72ea7-2656-4106-b8f9-75dfac7d3273" />

