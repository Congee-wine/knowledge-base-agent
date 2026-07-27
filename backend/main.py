import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from routers import agents, auth, chat, conversations, knowledge
from database import close_connection_pool, initialize_connection_pool
from services.errors import DomainError


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_connection_pool()
    try:
        yield
    finally:
        close_connection_pool()


app = FastAPI(title="软小助 AI 管家 API", lifespan=lifespan)


@app.exception_handler(DomainError)
def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message, "requestId": str(uuid.uuid4())},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(conversations.router)
app.include_router(knowledge.router)
