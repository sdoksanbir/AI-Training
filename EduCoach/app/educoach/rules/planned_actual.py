"""Pure planned-versus-actual fact projection for learner study records."""

from dataclasses import dataclass
from uuid import UUID

from educoach.models import StudySession, StudyTask
from educoach.services.snapshot import LearnerMemorySnapshot


def _validate_minutes(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _validate_id_tuple(values: tuple[UUID, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{field_name} must be a tuple")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} cannot contain duplicates")


@dataclass(frozen=True)
class TaskStudyActualFact:
    task_id: UUID
    planned_minutes: int
    actual_minutes: int
    session_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, UUID):
            raise ValueError("task_id must be a UUID")
        _validate_minutes(self.planned_minutes, "planned_minutes")
        _validate_minutes(self.actual_minutes, "actual_minutes")
        _validate_id_tuple(self.session_ids, "session_ids")


@dataclass(frozen=True)
class PlannedActualFacts:
    task_facts: tuple[TaskStudyActualFact, ...]
    unassigned_actual_minutes: int
    unassigned_session_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.task_facts, tuple):
            raise ValueError("task_facts must be a tuple")
        task_ids = tuple(fact.task_id for fact in self.task_facts)
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("task_facts cannot contain duplicate task_id values")
        _validate_minutes(
            self.unassigned_actual_minutes,
            "unassigned_actual_minutes",
        )
        _validate_id_tuple(
            self.unassigned_session_ids,
            "unassigned_session_ids",
        )


def project_planned_actual_facts(
    snapshot: LearnerMemorySnapshot,
) -> PlannedActualFacts:
    """Project recorded planned and actual facts without inventing dates."""

    tasks = _index_tasks(snapshot.study_tasks)
    sessions = _index_sessions(snapshot.study_sessions)
    sessions_by_task: dict[UUID, list[StudySession]] = {
        task_id: [] for task_id in tasks
    }
    unassigned_sessions: list[StudySession] = []

    for session in sessions.values():
        if session.learner_id != snapshot.learner.learner_id:
            raise ValueError("study session must belong to the snapshot learner")
        if session.task_id is None:
            unassigned_sessions.append(session)
            continue

        task = tasks.get(session.task_id)
        if task is None:
            raise ValueError("linked study session must reference a snapshot task")
        if session.context_id != task.context_id:
            raise ValueError("linked study session must match the task context")
        sessions_by_task[task.task_id].append(session)

    task_facts = tuple(
        _project_task_fact(task, sessions_by_task[task.task_id])
        for task in sorted(tasks.values(), key=lambda item: str(item.task_id))
    )
    ordered_unassigned = sorted(
        unassigned_sessions,
        key=lambda item: str(item.session_id),
    )
    return PlannedActualFacts(
        task_facts=task_facts,
        unassigned_actual_minutes=sum(
            session.duration_minutes for session in ordered_unassigned
        ),
        unassigned_session_ids=tuple(
            session.session_id for session in ordered_unassigned
        ),
    )


def _index_tasks(tasks: tuple[StudyTask, ...]) -> dict[UUID, StudyTask]:
    indexed: dict[UUID, StudyTask] = {}
    for task in tasks:
        if task.task_id in indexed:
            raise ValueError("snapshot cannot contain duplicate task_id values")
        indexed[task.task_id] = task
    return indexed


def _index_sessions(
    sessions: tuple[StudySession, ...],
) -> dict[UUID, StudySession]:
    indexed: dict[UUID, StudySession] = {}
    for session in sessions:
        if session.session_id in indexed:
            raise ValueError("snapshot cannot contain duplicate session_id values")
        indexed[session.session_id] = session
    return indexed


def _project_task_fact(
    task: StudyTask,
    sessions: list[StudySession],
) -> TaskStudyActualFact:
    ordered_sessions = sorted(sessions, key=lambda item: str(item.session_id))
    return TaskStudyActualFact(
        task_id=task.task_id,
        planned_minutes=task.planned_minutes,
        actual_minutes=sum(session.duration_minutes for session in ordered_sessions),
        session_ids=tuple(session.session_id for session in ordered_sessions),
    )
