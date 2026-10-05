"""Minimal authenticated HTTP adapter for EduCoach."""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from educoach.llm import OllamaProviderError
from educoach.orchestrator import (
    CoachOrchestrator,
    StructuredLLMOutputError,
)
from educoach.validators import ResponseValidationError

from .auth import (
    AuthenticatedPrincipal,
    AuthenticationError,
    AuthResolver,
)
from .schemas import (
    CoachRequest,
    CoachResponse,
    HealthResponse,
    StudyPlanProposalResponse,
)


_INTERNAL_ERROR_DETAIL = "internal server error"
_SERVICE_UNAVAILABLE_DETAIL = "coach service unavailable"


def create_app(
    orchestrator: CoachOrchestrator,
    auth_resolver: AuthResolver,
) -> FastAPI:
    """Create an API instance with explicit runtime dependencies."""

    app = FastAPI()

    def resolve_principal(
        authorization: Annotated[
            str | None,
            Header(alias="Authorization"),
        ] = None,
    ) -> AuthenticatedPrincipal:
        try:
            principal = auth_resolver.resolve(authorization)
        except AuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        if not isinstance(principal, AuthenticatedPrincipal):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return principal

    @app.exception_handler(Exception)
    async def sanitize_unhandled_error(request, error):
        del request, error
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": _INTERNAL_ERROR_DETAIL},
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        try:
            healthy = orchestrator.health()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="service unavailable",
            ) from None
        if not healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="service unavailable",
            )
        return HealthResponse()

    @app.post("/v1/coach/respond", response_model=CoachResponse)
    def respond(
        request: CoachRequest,
        principal: Annotated[
            AuthenticatedPrincipal,
            Depends(resolve_principal),
        ],
    ) -> CoachResponse:
        try:
            result = orchestrator.respond(
                principal.learner_id,
                request.message,
                context_id=request.context_id,
            )
        except (OllamaProviderError, StructuredLLMOutputError, ResponseValidationError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=_SERVICE_UNAVAILABLE_DETAIL,
            ) from None
        except ValueError as error:
            if str(error) == "Learner bulunamadı":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="learner not found",
                ) from None
            if str(error) == "requested context does not belong to the learner snapshot":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="context is not available",
                ) from None
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid request",
            ) from None
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=_INTERNAL_ERROR_DETAIL,
            ) from None

        proposal = result.study_plan_proposal
        proposal_response = (
            StudyPlanProposalResponse(
                plan=proposal.plan,
                tasks=proposal.tasks,
            )
            if proposal is not None
            else None
        )
        return CoachResponse(
            text=result.text,
            study_plan_proposal=proposal_response,
        )

    return app
