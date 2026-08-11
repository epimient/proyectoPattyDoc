from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.session_store import SessionStore, get_store
from app.schemas.session import (
    CorrectionResponse,
    ObservationRequest,
    Plan,
    SessionResponse,
    SessionStartRequest,
    SessionStartResponse,
)
from app.services.correction_service import evaluate_correction

router = APIRouter(prefix="/api/session", tags=["session"])

StoreDep = Annotated[SessionStore, Depends(get_store)]


@router.post("/start", response_model=SessionStartResponse)
def start_session(request: SessionStartRequest, store: StoreDep):
    session = store.create_session(request.plan.model_dump())
    return SessionStartResponse(
        session_id=session["session_id"],
        plan=Plan(**session["plan"]),
        status=session["status"],
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, store: StoreDep):
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return SessionResponse(**session)


@router.post("/{session_id}/observation", response_model=CorrectionResponse)
def submit_observation(session_id: str, obs: ObservationRequest, store: StoreDep):
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    correction = evaluate_correction(obs.exercise, obs)
    store.add_observation(session_id, obs.model_dump(), correction.model_dump())
    store.set_current_exercise(session_id, obs.exercise)
    return correction


@router.get("/{session_id}/observations")
def list_observations(session_id: str, store: StoreDep):
    if store.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return store.list_observations(session_id)


@router.post("/{session_id}/complete", response_model=SessionResponse)
def complete_session(session_id: str, store: StoreDep):
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    store.complete_session(session_id)
    return SessionResponse(**store.get_session(session_id))
