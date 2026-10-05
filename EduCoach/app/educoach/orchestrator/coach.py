from dataclasses import dataclass
from uuid import UUID

from educoach.llm import LLMProvider, LLMRequest
from educoach.rag import Retriever
from educoach.services import LearnerMemoryService
from educoach.specialties import SpecialtyProfileRegistry
from educoach.validators import validate_response, validate_user_message

from .context_resolution import ActiveContextResolutionStatus
from .context_routing import resolve_request_context
from .intent_detection import detect_intents
from .rag_gating import RAGNeedStatus, decide_rag_need


_AMBIGUOUS_CONTEXT_CLARIFICATION = (
    "Birden fazla aktif çalışma bağlamın var. "
    "Hangi bağlamı kastettiğini belirtir misin?"
)
_DETERMINISTIC_MODEL = "deterministic"


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

    def respond(
        self,
        learner_id: UUID,
        message: str,
        *,
        context_id: UUID | None = None,
    ) -> CoachResult:
        message = validate_user_message(message)
        snapshot = self.memory.get_learner_memory_snapshot(learner_id)
        active_context = resolve_request_context(
            snapshot,
            message,
            self.specialty_registry,
            requested_context_id=context_id,
        )
        if (
            context_id is not None
            and active_context.status == ActiveContextResolutionStatus.UNAVAILABLE
        ):
            raise ValueError("requested context does not belong to the learner snapshot")
        if active_context.status == ActiveContextResolutionStatus.AMBIGUOUS:
            return CoachResult(
                text=_AMBIGUOUS_CONTEXT_CLARIFICATION,
                model=_DETERMINISTIC_MODEL,
            )
        intent_resolution = detect_intents(message)
        rag_need = decide_rag_need(message, intent_resolution)
        knowledge = ""
        if (
            self.retriever is not None
            and rag_need.status != RAGNeedStatus.NOT_REQUIRED
        ):
            programs = {"global"}
            if active_context.status == ActiveContextResolutionStatus.RESOLVED:
                assert active_context.context is not None
                programs.add(active_context.context.program_code)
            filters = {"program": programs}
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
