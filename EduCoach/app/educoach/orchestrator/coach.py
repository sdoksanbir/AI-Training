from dataclasses import dataclass
from uuid import UUID

from educoach.llm import LLMProvider, LLMRequest
from educoach.models import LearningContext
from educoach.rag import Retriever
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfileRegistry
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationReport,
    evaluate_response,
    validate_user_message,
)
from educoach.writeback import (
    StudyPlanWriteProposal,
    StudyPlanWriteValidationReport,
    WriteValidationStatus,
    validate_study_plan_write,
)

from .auto_fix import apply_response_auto_fix
from .context_resolution import ActiveContextResolutionStatus
from .context_routing import resolve_request_context
from .intent_detection import detect_intents
from .intent import IntentType
from .rag_gating import RAGNeedStatus, decide_rag_need
from .regeneration import (
    MAX_REGENERATION_ATTEMPTS,
    ResponseRegenerationExhausted,
    build_regeneration_request,
)
from .response_actions import handle_response_validation_action
from .structured_proposal import (
    _build_structured_study_plan_prompt,
    materialize_study_plan_write_proposal,
    parse_structured_coach_output,
)


_AMBIGUOUS_CONTEXT_CLARIFICATION = (
    "Birden fazla aktif çalışma bağlamın var. "
    "Hangi bağlamı kastettiğini belirtir misin?"
)
_DETERMINISTIC_MODEL = "deterministic"
_BASE_SYSTEM_PROMPT = (
    "Sen EduCoach'sun. Yalnızca verilen öğrenci hafızasındaki "
    "ve seçili bağlamdaki doğrulanmış gerçek bilgileri kullan; bilinmeyenleri "
    "uydurma. Availability bilinmiyorsa belirli boş saatler veya kesin günlük "
    "müsaitlik varsayma. Kanıtlanmamış bir konuyu öğrencinin gerçek zayıflığı "
    "gibi sunma; gerekirse önce tanılayıcı kontrol öner. Kullanıcının açık süre, "
    "yük, ders-gün veya tolerans sınırlarını aşma. Eğitim hedefi ya da sınav "
    "sonucu için garanti, kesin başarı veya bu planla belirli bir seviyeye çıkma "
    "vaadi verme. Sağlık belirtisinde teşhis, tedavi, ilaç dozu, sıvı veya "
    "beslenme kısıtlaması ve fizyolojik müdahale önerme; konu eğitim koçluğunu "
    "aşıyorsa ilgili profesyonele veya güvenilir bir yetişkine yönlendir. "
    "Yanıtlarında harici URL, web adresi veya www bağlantısı kullanma."
)


@dataclass(frozen=True)
class CoachResult:
    text: str
    model: str
    study_plan_proposal: StudyPlanWriteProposal | None = None


@dataclass(frozen=True)
class _GenerationAttempt:
    response_text: str
    model: str
    study_plan_proposal: StudyPlanWriteProposal | None
    validation_report: ResponseValidationReport


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
        structured_planning = (
            IntentType.PLANNING in intent_resolution.intents
            and active_context.status == ActiveContextResolutionStatus.RESOLVED
        )
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
        system_prompt = (
            _build_structured_study_plan_prompt(_BASE_SYSTEM_PROMPT)
            if structured_planning
            else _BASE_SYSTEM_PROMPT
        )
        request = LLMRequest(
            system_prompt=system_prompt,
            user_message=message,
            memory_context=repr(snapshot) + ("\nKnowledge:\n" + knowledge if knowledge else ""),
        )
        current_request = request
        for regeneration_attempt in range(MAX_REGENERATION_ATTEMPTS + 1):
            attempt = self._generate_attempt(
                current_request,
                structured_planning=structured_planning,
                snapshot=snapshot,
                context=active_context.context,
            )
            if (
                attempt.validation_report.action
                is ResponseValidationAction.AUTO_FIX
            ):
                attempt = self._apply_auto_fix_once(attempt, snapshot)
            if (
                attempt.validation_report.action
                is ResponseValidationAction.REGENERATE
            ):
                if regeneration_attempt == MAX_REGENERATION_ATTEMPTS:
                    raise ResponseRegenerationExhausted(
                        attempt.validation_report
                    )
                current_request = build_regeneration_request(
                    request,
                    attempt.validation_report,
                )
                continue
            validated_text = handle_response_validation_action(
                attempt.response_text,
                attempt.validation_report,
            )
            return CoachResult(
                validated_text,
                attempt.model,
                attempt.study_plan_proposal,
            )
        raise RuntimeError("controlled regeneration loop terminated unexpectedly")

    def _apply_auto_fix_once(
        self,
        attempt: _GenerationAttempt,
        snapshot: LearnerMemorySnapshot,
    ) -> _GenerationAttempt:
        fixed_text = apply_response_auto_fix(
            attempt.response_text,
            attempt.validation_report,
        )
        final_report = evaluate_response(
            fixed_text,
            snapshot=snapshot,
            specialty_registry=self.specialty_registry,
        )
        return _GenerationAttempt(
            response_text=fixed_text,
            model=attempt.model,
            study_plan_proposal=attempt.study_plan_proposal,
            validation_report=final_report,
        )

    def _generate_attempt(
        self,
        request: LLMRequest,
        *,
        structured_planning: bool,
        snapshot: LearnerMemorySnapshot,
        context: LearningContext | None,
    ) -> _GenerationAttempt:
        response = self.provider.generate(request)
        response_text = response.text
        study_plan_proposal = None
        if structured_planning:
            output = parse_structured_coach_output(response.text)
            response_text = output.response_text
            if output.proposal is not None:
                assert context is not None
                study_plan_proposal = materialize_study_plan_write_proposal(
                    output.proposal,
                    snapshot,
                    context,
                )
        validation_report = evaluate_response(
            response_text,
            snapshot=snapshot,
            specialty_registry=self.specialty_registry,
        )
        if study_plan_proposal is not None:
            proposal_report = validate_study_plan_write(
                snapshot,
                study_plan_proposal,
            )
            validation_report = _apply_study_plan_safety_boundary(
                validation_report,
                proposal_report,
            )
        return _GenerationAttempt(
            response_text=response_text,
            model=response.model,
            study_plan_proposal=study_plan_proposal,
            validation_report=validation_report,
        )


def _apply_study_plan_safety_boundary(
    response_report: ResponseValidationReport,
    proposal_report: StudyPlanWriteValidationReport,
) -> ResponseValidationReport:
    if proposal_report.status is not WriteValidationStatus.REJECTED:
        # Missing or ambiguous learner facts cannot be repaired by asking the
        # provider to regenerate from the same snapshot.
        return response_report

    violations = response_report.violations + tuple(
        violation
        for violation in proposal_report.violations
        if all(
            existing.rule_id != violation.rule_id
            for existing in response_report.violations
        )
    )
    action = (
        ResponseValidationAction.BLOCK
        if response_report.action is ResponseValidationAction.BLOCK
        else ResponseValidationAction.REGENERATE
    )
    return ResponseValidationReport(action=action, violations=violations)
