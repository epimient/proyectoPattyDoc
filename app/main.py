import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_ORIGINS
from app.models.plan_service import get_service
from app.models.session_store import get_store
from app.routers.camera import router as camera_router
from app.routers.plan import router
from app.routers.session import router as session_router
from app.vision.controller import controller as camera_controller

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        get_service()
        logger.info("Modelo y preprocesadores cargados correctamente")
    except Exception as e:
        logger.error("No se pudo cargar el modelo: %s", e)
    get_store()
    logger.info("Almacén de sesiones inicializado")
    yield
    camera_controller.shutdown()
    logger.info("Cámara liberada")


app = FastAPI(
    title="PattyDoc Fitness Plan API",
    description="Generación de planes de acondicionamiento físico personalizados "
    "para personas con discapacidad visual.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(session_router)
app.include_router(camera_router)
