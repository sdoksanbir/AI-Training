"""Configuration contracts describing education contexts, not learner memory."""

from datetime import date
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from educoach.models.learner import ContextType


class SpecialtyProfile(BaseModel):
    """Versioned profile identity with JSON content whose schemas are deferred.

    Content sections default to independent empty objects. Their internal shape
    is intentionally open until the corresponding configuration is specified.
    """

    model_config = ConfigDict(extra="forbid")

    profile_code: str = Field(min_length=1)
    profile_family: ContextType
    display_name: str = Field(min_length=1)
    profile_version: int = Field(gt=0)
    status: Literal["active"] = "active"
    effective_from: date | None = None
    effective_until: date | None = None

    capabilities: JsonValue = Field(default_factory=dict)
    taxonomy: JsonValue = Field(default_factory=dict)
    assessment_schema: JsonValue = Field(default_factory=dict)
    goal_schema: JsonValue = Field(default_factory=dict)
    planning_policy: JsonValue = Field(default_factory=dict)
    rag_policy: JsonValue = Field(default_factory=dict)
    rules: JsonValue = Field(default_factory=dict)
    validators: JsonValue = Field(default_factory=dict)
    prompt_context: JsonValue = Field(default_factory=dict)
    terminology: JsonValue = Field(default_factory=dict)

    @field_validator("profile_code", "display_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("profile_code ve display_name boş olamaz")

        return cleaned

    @model_validator(mode="after")
    def validate_date_range(self) -> "SpecialtyProfile":
        if (
            self.effective_from is not None
            and self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            raise ValueError("effective_until, effective_from tarihinden önce olamaz")

        return self
