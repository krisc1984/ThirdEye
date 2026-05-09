import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.model_providers import router as model_providers_router
from app.api.playbooks import router as playbooks_router
from app.api.projects import router as projects_router
from app.api.reviews import router as reviews_router
from app.api.skills import router as skills_router

app = FastAPI(title="AI Tech Review API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(playbooks_router)
app.include_router(model_providers_router)
app.include_router(reviews_router)
app.include_router(skills_router)

logging.basicConfig(level=logging.INFO)
