import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent_configs import router as agent_configs_router
from app.api.health import router as health_router
from app.api.knowledge_workspace import router as knowledge_workspace_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.model_providers import router as model_providers_router
from app.api.observability import router as observability_router
from app.api.playbooks import router as playbooks_router
from app.api.projects import router as projects_router
from app.api.reviews import router as reviews_router
from app.api.skills_manage import router as skills_manage_router
from app.api.skills import router as skills_router
from app.api.skill_graph import router as skill_graph_router
from app.api.tavily_settings import router as tavily_settings_router
from app.core.config import settings


def _configure_logging() -> None:
    log_dir = settings.data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "api.log"
    access_log_path = log_dir / "access.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    access_formatter = logging.Formatter(
        fmt="%(asctime)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    has_stream = any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers)
    has_file = any(
        isinstance(handler, RotatingFileHandler) and Path(getattr(handler, "baseFilename", "")) == log_path
        for handler in root_logger.handlers
    )

    if not has_stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    if not has_file:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    has_access_file = any(
        isinstance(handler, RotatingFileHandler) and Path(getattr(handler, "baseFilename", "")) == access_log_path
        for handler in access_logger.handlers
    )
    if not has_access_file:
        access_file_handler = RotatingFileHandler(
            access_log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        access_file_handler.setLevel(logging.INFO)
        access_file_handler.setFormatter(access_formatter)
        access_logger.addHandler(access_file_handler)
    has_access_stream = any(isinstance(handler, logging.StreamHandler) for handler in access_logger.handlers)
    if not has_access_stream:
        access_stream_handler = logging.StreamHandler()
        access_stream_handler.setLevel(logging.INFO)
        access_stream_handler.setFormatter(access_formatter)
        access_logger.addHandler(access_stream_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "httpx", "app", "openai.agents"):
        logging.getLogger(logger_name).setLevel(logging.INFO)


_configure_logging()

app = FastAPI(title="AI Tech Review API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(agent_configs_router)
app.include_router(knowledge_workspace_router)
app.include_router(mcp_servers_router)
app.include_router(projects_router)
app.include_router(playbooks_router)
app.include_router(model_providers_router)
app.include_router(observability_router)
app.include_router(reviews_router)
app.include_router(skills_manage_router)
app.include_router(skills_router)
app.include_router(skill_graph_router)
app.include_router(tavily_settings_router)
