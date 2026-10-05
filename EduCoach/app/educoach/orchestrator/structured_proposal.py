"""Strict LLM-side StudyPlan proposal parsing and system materialization."""

from datetime import date
import json

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from educoach.models import (
    ContextStatus,
    LearningContext,
    PlanType,
    StudyPlan,
    StudyTask,
    TaskPriority,
    TaskType,
)
from educoach.services import LearnerMemorySnapshot
from educoach.writeback import StudyPlanWriteProposal


class StructuredLLMOutputError(ValueError):
    """Raised when an LLM response is not a valid structured envelope."""


class StudyPlanTaskProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_date: date
    task_type: TaskType
    description: str = Field(min_length=1)
    planned_minutes: int = Field(ge=1)
    area_type: str | None = None
    area_code: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("description cannot be blank")
        return cleaned

    @field_validator("area_type", "area_code")
    @classmethod
    def normalize_optional_area(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_area_pair(self) -> "StudyPlanTaskProposal":
        if (self.area_type is None) != (self.area_code is None):
            raise ValueError("area_type and area_code must be supplied together")
        return self


class StudyPlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field(min_length=1)
    plan_type: PlanType
    start_date: date
    end_date: date
    tasks: tuple[StudyPlanTaskProposal, ...] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title cannot be blank")
        return cleaned

    @model_validator(mode="after")
    def validate_date_range(self) -> "StudyPlanProposal":
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class StructuredCoachOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_text: str = Field(min_length=1)
    proposal: StudyPlanProposal | None

    @field_validator("response_text")
    @classmethod
    def normalize_response_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("response_text cannot be blank")
        return cleaned


def parse_structured_coach_output(raw_text: str) -> StructuredCoachOutput:
    """Parse exactly one strict JSON object into the semantic output schema."""

    if not isinstance(raw_text, str):
        raise StructuredLLMOutputError("structured LLM output must be a string")
    try:
        value = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError) as error:
        raise StructuredLLMOutputError("structured LLM output is not valid JSON") from error
    if not isinstance(value, dict):
        raise StructuredLLMOutputError("structured LLM output must be a JSON object")
    try:
        return StructuredCoachOutput.model_validate(value)
    except ValidationError as error:
        raise StructuredLLMOutputError(
            "structured LLM output does not match the StudyPlan schema"
        ) from error


def materialize_study_plan_write_proposal(
    proposal: StudyPlanProposal,
    snapshot: LearnerMemorySnapshot,
    context: LearningContext,
) -> StudyPlanWriteProposal:
    """Bind semantic plan fields to authoritative learner/context ownership."""

    learner_id = snapshot.learner.learner_id
    matching_contexts = tuple(
        item for item in snapshot.contexts if item.context_id == context.context_id
    )
    if (
        context.status != ContextStatus.ACTIVE
        or context.learner_id != learner_id
        or len(matching_contexts) != 1
        or matching_contexts[0] != context
    ):
        raise ValueError("context must be the active authoritative snapshot context")

    plan = StudyPlan(
        learner_id=learner_id,
        context_id=context.context_id,
        title=proposal.title,
        plan_type=proposal.plan_type,
        start_date=proposal.start_date,
        end_date=proposal.end_date,
    )
    tasks = tuple(
        StudyTask(
            plan_id=plan.plan_id,
            context_id=context.context_id,
            task_date=task.task_date,
            task_type=task.task_type,
            description=task.description,
            planned_minutes=task.planned_minutes,
            area_type=task.area_type,
            area_code=task.area_code,
            priority=task.priority,
        )
        for task in proposal.tasks
    )
    return StudyPlanWriteProposal(plan=plan, tasks=tasks)


def _build_structured_study_plan_prompt(base_prompt: str) -> str:
    plan_types = [item.value for item in PlanType]
    task_types = [item.value for item in TaskType]
    priorities = [item.value for item in TaskPriority]
    shape = {
        "response_text": "Kullanıcıya gösterilecek Türkçe cevap",
        "proposal": {
            "title": "Çalışma planı başlığı",
            "plan_type": plan_types[0],
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "tasks": [
                {
                    "task_date": "YYYY-MM-DD",
                    "task_type": task_types[0],
                    "description": "Çalışma görevi",
                    "planned_minutes": 60,
                    "priority": TaskPriority.MEDIUM.value,
                    "area_type": None,
                    "area_code": None,
                }
            ],
        },
    }
    forbidden_fields = (
        "learner_id, context_id, goal_id, plan_id, task_id, status, created_at, "
        "updated_at, completed_at"
    )
    return (
        base_prompt
        + "\n\nBu planning isteği için ONLY valid JSON object döndür. "
        "Markdown/code fence veya JSON dışında metin kullanma. "
        "Bilinmeyen learner bilgisini uydurma. Yeterli bilgi yoksa proposal null "
        "olsun. Şu system-owned alanları üretme: "
        + forbidden_fields
        + ". Allowed plan_type values: "
        + json.dumps(plan_types, ensure_ascii=False)
        + ". Allowed task_type values: "
        + json.dumps(task_types, ensure_ascii=False)
        + ". Allowed priority values: "
        + json.dumps(priorities, ensure_ascii=False)
        + ". Exact JSON shape: "
        + json.dumps(shape, ensure_ascii=False)
    )
