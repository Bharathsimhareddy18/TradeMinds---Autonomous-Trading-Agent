from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Trademind - Autonomous Trading Agent API is running!"}

