"""Deterministic, source-group-safe development/final split tooling."""

from hashlib import sha256
import json
from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr

from .contracts import RealLearnerEvaluationCase


SPLIT_POLICY_VERSION = "source-group-sha256-modulo-3-v1"
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class SplitManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: StrictStr
    split_policy_version: StrictStr
    input_case_count: StrictInt
    source_group_count: StrictInt
    development_case_count: StrictInt
    final_case_count: StrictInt
    development_sha256: StrictStr
    final_sha256: StrictStr


def split_cases(
    cases: tuple[RealLearnerEvaluationCase, ...],
    *,
    version: str,
) -> tuple[
    tuple[RealLearnerEvaluationCase, ...],
    tuple[RealLearnerEvaluationCase, ...],
]:
    """Assign complete source groups using a stable 2:1 hash policy."""

    _validate_version(version)
    development: list[RealLearnerEvaluationCase] = []
    final: list[RealLearnerEvaluationCase] = []
    for case in cases:
        target = (
            final
            if _source_group_bucket(case.source_group_id, version) == 0
            else development
        )
        target.append(case)
    return (
        tuple(sorted(development, key=lambda case: case.case_id)),
        tuple(sorted(final, key=lambda case: case.case_id)),
    )


def write_split(
    cases: tuple[RealLearnerEvaluationCase, ...],
    *,
    version: str,
    development_path: Path,
    final_path: Path,
    manifest_path: Path,
) -> SplitManifest:
    """Write new canonical outputs while refusing every overwrite."""

    paths = (development_path, final_path, manifest_path)
    resolved_paths = {path.resolve(strict=False) for path in paths}
    if len(resolved_paths) != len(paths):
        raise ValueError("split output paths must be distinct")
    if any(path.exists() for path in paths):
        raise FileExistsError(
            "split output already exists; use a new dataset version"
        )

    development, final = split_cases(cases, version=version)
    development_content = _canonical_jsonl(development)
    final_content = _canonical_jsonl(final)
    manifest = SplitManifest(
        version=version,
        split_policy_version=SPLIT_POLICY_VERSION,
        input_case_count=len(cases),
        source_group_count=len({case.source_group_id for case in cases}),
        development_case_count=len(development),
        final_case_count=len(final),
        development_sha256=_content_hash(development_content),
        final_sha256=_content_hash(final_content),
    )
    manifest_content = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(development_path, development_content)
    _write_new(final_path, final_content)
    _write_new(manifest_path, manifest_content)
    return manifest


def _source_group_bucket(source_group_id: str, version: str) -> int:
    material = (
        f"{SPLIT_POLICY_VERSION}\0{version}\0{source_group_id}"
    ).encode("utf-8")
    return int.from_bytes(sha256(material).digest()[:8], "big") % 3


def _canonical_jsonl(
    cases: tuple[RealLearnerEvaluationCase, ...],
) -> str:
    return "".join(
        json.dumps(
            case.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
        for case in cases
    )


def _content_hash(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _write_new(path: Path, content: str) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)


def _validate_version(version: str) -> None:
    if not isinstance(version, str) or not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("version must be a controlled non-empty identifier")
