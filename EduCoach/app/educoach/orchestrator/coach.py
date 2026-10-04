from dataclasses import dataclass
from uuid import UUID

from educoach.llm import LLMProvider, LLMRequest
from educoach.rag import Retriever
from educoach.services import LearnerMemoryService
from educoach.specialties import SpecialtyProfileRegistry
from educoach.validators import validate_response, validate_user_message


@dataclass(frozen=True)
class CoachResult:
    text: str
    model: str


class CoachOrchestrator:
    def __init__(
        self,
        memory: LearnerMemoryService,
        provider: LLMProvider,
        retriever: Retriever | None = None,
        specialty_registry: SpecialtyProfileRegistry | None = None,
    ) -> None:
        self.memory = memory
        self.provider = provider
        self.retriever = retriever
        self.specialty_registry = specialty_registry

    def health(self) -> bool:
        return self.provider.health()

    def respond(self, learner_id: UUID, message: str) -> CoachResult:
        message = validate_user_message(message)
        snapshot = self.memory.get_learner_memory_snapshot(learner_id)
        knowledge = ""
        if self.retriever is not None:
            contexts = snapshot.contexts
            filters = None
            if contexts:
                filters = {"program": {context.program_code for context in contexts}}
            chunks = self.retriever.search(message, filters=filters)
            knowledge = "\n".join(
                f"[{chunk.title} | {chunk.source}] {chunk.text}" for chunk in chunks
            )
        request = LLMRequest(
            system_prompt=(
                "Sen EduCoach'sun. Yalnızca verilen öğrenci hafızasındaki "
                "gerçek bilgileri kullan; bilinmeyenleri uydurma."
            ),
            user_message=message,
            memory_context=repr(snapshot) + ("\nKnowledge:\n" + knowledge if knowledge else ""),
        )
        response = self.provider.generate(request)
        return CoachResult(
            validate_response(
                response.text,
                snapshot=snapshot,
                specialty_registry=self.specialty_registry,
            ),
            response.model,
        )
