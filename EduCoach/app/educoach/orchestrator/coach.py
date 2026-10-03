from dataclasses import dataclass
from uuid import UUID

from educoach.llm import LLMProvider, LLMRequest
from educoach.services import LearnerMemoryService
from educoach.validators import validate_response


@dataclass(frozen=True)
class CoachResult:
    text: str
    model: str


class CoachOrchestrator:
    def __init__(self, memory: LearnerMemoryService, provider: LLMProvider) -> None:
        self.memory = memory
        self.provider = provider

    def respond(self, learner_id: UUID, message: str) -> CoachResult:
        summary = self.memory.get_learner_memory_summary(learner_id)
        request = LLMRequest(
            system_prompt=(
                "Sen EduCoach'sun. Yalnızca verilen öğrenci hafızasındaki "
                "gerçek bilgileri kullan; bilinmeyenleri uydurma."
            ),
            user_message=message,
            memory_context=repr(summary),
        )
        response = self.provider.generate(request)
        return CoachResult(validate_response(response.text), response.model)
