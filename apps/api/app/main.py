from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="AI Tech Review API")
app.include_router(health_router)

