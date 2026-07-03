"""FastAPI entrypoint for the research agent backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .routers.articles import router as articles_router
from .routers.chat import router as chat_router
from .routers.sources import router as sources_router

app = FastAPI(title="AI Research Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(sources_router)
app.include_router(articles_router)


@app.get("/")
def root():
    return RedirectResponse("http://127.0.0.1:5174")


@app.get("/health")
def health():
    return {"status": "ok"}

