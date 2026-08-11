from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.models.plan_service import PlanService, get_service
from app.schemas.plan import FeedbackRequest, FeedbackResponse, PlanResponse, UserProfile

router = APIRouter(prefix="/api", tags=["plan"])

ServiceDep = Annotated[PlanService, Depends(get_service)]


@router.post("/plan", response_model=PlanResponse)
def generate_plan(profile: UserProfile, service: ServiceDep):
    try:
        return service.generate_plan(profile)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error generando plan: {e}") from e


@router.get("/exercises")
def list_exercises(service: ServiceDep):
    try:
        return service.list_exercises()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest, service: ServiceDep):
    try:
        result = service.apply_feedback(request)
        return FeedbackResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error aplicando feedback: {e}") from e


@router.get("/health")
def health(service: ServiceDep):
    return service.health()
