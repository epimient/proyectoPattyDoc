"""Endpoints de cámara para el flujo web.

El video se entrega como MJPEG (`GET /api/camera/stream`) y el estado se
consulta por polling (`GET /api/camera/state`). Los comandos son POST.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.schemas.session import SessionStartRequest
from app.vision.controller import CameraController, controller as _default_controller

router = APIRouter(prefix="/api/camera", tags=["camera"])


def get_controller() -> CameraController:
    return _default_controller


def _resolve_source(source: str | None) -> int | str | None:
    if source is None:
        return None
    return int(source) if source.isdigit() else source


@router.get("/stream")
def stream(controller: CameraController = Depends(get_controller)):
    def _mjpeg():
        while True:
            frame = controller.get_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(0.03)

    return StreamingResponse(
        _mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/state")
def state(controller: CameraController = Depends(get_controller)):
    return controller.state


@router.post("/start")
def start(
    request: SessionStartRequest,
    source: str | None = Query(default=None, description="0 (webcam) o ruta a un video"),
    controller: CameraController = Depends(get_controller),
):
    try:
        return controller.start(request.plan.model_dump(), source=_resolve_source(source))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/calibrate")
def calibrate(controller: CameraController = Depends(get_controller)):
    try:
        return controller.calibrate()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/next")
def next_step(controller: CameraController = Depends(get_controller)):
    try:
        return controller.next()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post("/stop")
def stop(controller: CameraController = Depends(get_controller)):
    try:
        return controller.stop()
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
