"""Public HTTP request and response contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from educoach.models import StudyPlan, StudyTask


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"] = "ok"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    login_identifier: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


class CoachRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str = Field(min_length=1)
    context_id: UUID | None = None


class StudyPlanProposalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: StudyPlan
    tasks: tuple[StudyTask, ...]


class CoachResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    study_plan_proposal: StudyPlanProposalResponse | None = None
