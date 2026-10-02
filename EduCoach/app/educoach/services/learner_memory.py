"""Learner Memory application service."""

from collections.abc import Iterable

from sqlalchemy.orm import Session, sessionmaker

from educoach.models import Learner, LearningContext
from educoach.repositories import LearnerRepository


class LearnerMemoryService:
    """Coordinates transactional Learner Memory operations."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.session_factory = session_factory

    def register_learner(
        self,
        learner: Learner,
        contexts: Iterable[LearningContext] = (),
    ) -> Learner:
        context_items = tuple(contexts)

        for context in context_items:
            if context.learner_id != learner.learner_id:
                raise ValueError(
                    "LearningContext learner_id, kayıt edilen "
                    "Learner ile aynı olmalıdır"
                )

        with self.session_factory() as session:
            repository = LearnerRepository(session)

            with session.begin():
                repository.add_learner(learner)

                for context in context_items:
                    repository.add_context(context)

        return learner
