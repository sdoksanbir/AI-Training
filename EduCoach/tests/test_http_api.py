from datetime import date
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from educoach.api import (
    AuthenticatedPrincipal,
    AuthenticationRequired,
    create_app,
)
from educoach.models import PlanType, StudyPlan, StudyTask, TaskType
from educoach.orchestrator import CoachResult
from educoach.writeback import StudyPlanWriteProposal


class StubAuthResolver:
    def __init__(self, principal: AuthenticatedPrincipal | None = None) -> None:
        self.principal = principal
        self.credentials: list[str | None] = []

    def resolve(self, credential: str | None) -> AuthenticatedPrincipal:
        self.credentials.append(credential)
        if self.principal is None:
            raise AuthenticationRequired
        return self.principal


class StubOrchestrator:
    def __init__(self, result: CoachResult | None = None) -> None:
        self.result = result or CoachResult("Hazırım.", "stub")
        self.calls: list[tuple[UUID, str, UUID | None]] = []
        self.error: Exception | None = None

    def health(self) -> bool:
        return True

    def respond(
        self,
        learner_id: UUID,
        message: str,
        *,
        context_id: UUID | None = None,
    ) -> CoachResult:
        self.calls.append((learner_id, message, context_id))
        if self.error is not None:
            raise self.error
        return self.result


def _principal(learner_id: UUID | None = None) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject_id="test-subject",
        learner_id=learner_id or uuid4(),
    )


def _client(
    orchestrator: StubOrchestrator,
    resolver: StubAuthResolver,
) -> TestClient:
    return TestClient(
        create_app(orchestrator, resolver),
        raise_server_exceptions=False,
    )


def test_health_is_public() -> None:
    resolver = StubAuthResolver()
    response = _client(StubOrchestrator(), resolver).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert resolver.credentials == []


def test_coach_response_requires_authentication() -> None:
    orchestrator = StubOrchestrator()
    response = _client(orchestrator, StubAuthResolver()).post(
        "/v1/coach/respond",
        json={"message": "Merhaba"},
    )

    assert response.status_code == 401
    assert orchestrator.calls == []


def test_request_rejects_client_supplied_learner_id() -> None:
    orchestrator = StubOrchestrator()
    response = _client(orchestrator, StubAuthResolver(_principal())).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={
            "learner_id": str(uuid4()),
            "message": "Merhaba",
        },
    )

    assert response.status_code == 422
    assert orchestrator.calls == []


def test_principal_learner_and_optional_context_reach_orchestrator() -> None:
    learner_id = uuid4()
    context_id = uuid4()
    orchestrator = StubOrchestrator()
    response = _client(
        orchestrator,
        StubAuthResolver(_principal(learner_id)),
    ).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={"message": "Planımı göster", "context_id": str(context_id)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Hazırım.",
        "study_plan_proposal": None,
    }
    assert orchestrator.calls == [(learner_id, "Planımı göster", context_id)]


def test_unknown_principal_learner_maps_to_not_found() -> None:
    orchestrator = StubOrchestrator()
    orchestrator.error = ValueError("Learner bulunamadı")
    response = _client(orchestrator, StubAuthResolver(_principal())).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={"message": "Merhaba"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "learner not found"}


def test_context_outside_principal_learner_fails_closed() -> None:
    orchestrator = StubOrchestrator()
    orchestrator.error = ValueError(
        "requested context does not belong to the learner snapshot"
    )
    response = _client(orchestrator, StubAuthResolver(_principal())).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={"message": "Merhaba", "context_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "context is not available"}


def test_internal_error_detail_is_sanitized() -> None:
    orchestrator = StubOrchestrator()
    orchestrator.error = RuntimeError("secret provider endpoint detail")
    response = _client(orchestrator, StubAuthResolver(_principal())).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={"message": "Merhaba"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}
    assert "secret provider" not in response.text


def test_study_plan_proposal_is_serialized_without_writeback() -> None:
    learner_id = uuid4()
    context_id = uuid4()
    plan = StudyPlan(
        learner_id=learner_id,
        context_id=context_id,
        title="Haftalık plan",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 6),
        end_date=date(2026, 10, 12),
    )
    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context_id,
        task_date=date(2026, 10, 6),
        task_type=TaskType.STUDY,
        description="Matematik çalış",
        planned_minutes=45,
    )
    proposal = StudyPlanWriteProposal(plan=plan, tasks=(task,))
    orchestrator = StubOrchestrator(
        CoachResult("Plan adayı hazır.", "stub", proposal)
    )
    response = _client(
        orchestrator,
        StubAuthResolver(_principal(learner_id)),
    ).post(
        "/v1/coach/respond",
        headers={"Authorization": "Bearer test"},
        json={"message": "Plan yap", "context_id": str(context_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Plan adayı hazır."
    assert body["study_plan_proposal"]["plan"]["learner_id"] == str(learner_id)
    assert body["study_plan_proposal"]["plan"]["context_id"] == str(context_id)
    assert len(body["study_plan_proposal"]["tasks"]) == 1
