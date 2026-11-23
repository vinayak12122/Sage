import os
import uvicorn
import asyncio

from contextlib import asynccontextmanager
from llm.engine import engine
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.auth import router as auth_router
from routes.chat import router as chat_router
import database.chat

@asynccontextmanager
async def lifespan(app):
    path = os.getenv("MODEL_WEIGHTS_PATH", "llm/weights/tinyllm_v5_fp16_weights.pt")
    await asyncio.to_thread(engine.load, path)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)

@app.api_route('/health', methods=["GET", "HEAD"])
def health():
    return {
        "status": "alive"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
