# Real Learner Evaluation Intake

This directory defines an evaluation-only intake contract for future, manually anonymized real learner cases. It does not contain a dataset, real learner messages, synthetic cases presented as real, or production conversation-history persistence.

## Required process

Raw or review-pending learner material must remain only under the Git-ignored `evaluations/real_learner/private/` directory or another approved non-repository system. Do not create, stage, or commit files from that private intake area.

Before a case can enter a versioned evaluation JSONL file, a human reviewer must remove direct and contextual identifiers, minimize facts, confirm the source is permitted for this project, and set both `privacy_reviewed` and `usage_authorized` to `true`.

`usage_authorized=true` is a project-level process assertion. It is not a legal conclusion, consent mechanism, or guarantee that a case may be used for every purpose.

The validator is a conservative leak guard, not an anonymizer. It detects obvious email addresses, phone-like numbers, UUIDs, bearer/token text, and social handles. It cannot reliably identify real names, school names, addresses, rare contextual combinations, or every identifier. False negatives are possible, so manual privacy review is mandatory.

## Contract

Each JSONL object has exactly these fields:

- `case_id`: repository-assigned `RL` sequence such as `RL0001`; never derived from a learner/account identifier.
- `source_group_id`: repository-assigned `RG` sequence such as `RG0001`; groups cases originating from the same learner without storing or hashing that learner's identity.
- `source_kind`: exactly `real_anonymized`.
- `category` and `program_code`: controlled lowercase snake-case names.
- `user_message`: manually anonymized current-request text, not a transcript.
- `facts`: flat objects containing only `kind`, primitive `value`, and controlled `source`.
- `expected_behavior_tags`: one or more controlled tags.
- `forbidden_behavior_tags`: zero or more controlled tags.
- `privacy_reviewed`: exactly `true`.
- `usage_authorized`: exactly `true`.

Allowed fact sources are `learner_reported`, `teacher_reported`, `parent_reported`, `assessment_derived`, `coach_inferred`, and `system_observed`. Fact values are limited to string, integer, float, or boolean primitives. Never dump `LearnerMemorySnapshot` or nested arbitrary JSON.

The following is a field-shape illustration only. It is intentionally not a valid or usable evaluation case and is not real or synthetic learner data:

```json
{
  "case_id": "RL<assigned-sequence>",
  "source_group_id": "RG<assigned-sequence>",
  "source_kind": "real_anonymized",
  "category": "<controlled-category>",
  "program_code": "<controlled-program>",
  "user_message": "<manually-anonymized-current-message>",
  "facts": [{"kind": "<controlled-kind>", "value": "<minimal-value>", "source": "learner_reported"}],
  "expected_behavior_tags": ["<controlled-tag>"],
  "forbidden_behavior_tags": [],
  "privacy_reviewed": true,
  "usage_authorized": true
}
```

## Validation and split

Validate a reviewed JSONL file before splitting:

```powershell
python scripts/validate_real_learner_cases.py <input.jsonl>
```

Create a versioned development/final split with explicit new output paths:

```powershell
python scripts/split_real_learner_cases.py <input.jsonl> --version v1 --development-output <development.jsonl> --final-output <final.jsonl> --manifest-output <manifest.json>
```

The split uses a versioned SHA-256 assignment over `source_group_id`, not learner content or input order. Approximately two thirds of source groups go to development and one third to final unseen. Every case from one source group stays in one set. Outputs are canonically ordered, and existing output files are never overwritten. A new final set requires a new version and new paths.

Final unseen set prompt, rule, validator, RAG, fine-tuning veya model seçimi sırasında incelenmez ve kullanılmaz.

If a final unseen result causes a development decision, that set is no longer final unseen. A new independently collected and versioned final set is required. The frozen `evaluations/holdout/benchmark_v0.2.jsonl` archive is regression/diagnostic material and does not replace this final unseen process.

## Private development runner

Validated development cases can be executed through the production `CoachOrchestrator` with an isolated in-memory Learner Memory store. Configure the existing Ollama provider model explicitly or with `EDUCOACH_OLLAMA_MODEL`, then choose a new controlled run ID:

```powershell
python scripts/run_real_learner_development_evaluation.py `
    evaluations/real_learner/private/real_learner_pilot_v0.1.jsonl `
    --run-id dev-pilot-v0.1 `
    --model <installed-model>
```

The runner writes `results.jsonl`, `human_review.jsonl`, and `summary.json` only below `evaluations/real_learner/private/runs/<run-id>/` and refuses overwrite. Responses and review artifacts remain private and Git-ignored. Human review fields begin as `null`; no automatic judge is used.

When the production orchestrator returns a structured StudyPlan proposal, `human_review.jsonl` includes an explicit identifier-free semantic projection. It contains plan title/type/date range and each task's date, optional area, task type, description, planned minutes, and priority. Runtime learner/context/plan/task/goal IDs, status/timestamps, raw model JSON, and generic model dumps are excluded. `results.jsonl` remains unchanged, while `summary.json` remains aggregate-only.

Program contexts are created only from exact packaged Specialty Profiles. Fact materialization is deliberately limited to authoritative `education_status`, `grade_level`, and `study_track` fields. Other fact kinds are not inserted into a generic store; they are listed as unsupported metadata when the case can still run.

## FAZ 12 development coverage contract

`development_coverage_v0.1.json` is a repository-safe taxonomy, not a learner dataset. It contains only the versioned required program scope, out-of-scope program declarations, required behavior families, controlled coverage tags, priority, and minimum-expectation semantics. It must never contain a learner message, fact value, model response, case/source-group mapping, or private intake content.

FAZ 12 v0.1 requires exact builtin `yks` and `school_7` program evidence. `lgs` is explicitly out of scope; aliases are not guessed and no new Specialty Profile is implied. The checker reports `COVERED`, `PARTIAL`, or `MISSING` for each required family and program, plus content-free open slots such as a program/family pair. A tagged case without completed runtime evidence is partial; a completed matching case is covered. Proposal, deterministic fallback, and multi-case source-group families use their explicit structural/runtime expectations rather than message content.

The checker consumes validated development cases and optional development results in memory, but its report contains no case IDs, source-group IDs, learner content, fact values, or response text. It reuses the existing split output and verifies that development/final source-group sets are disjoint; it does not implement another split algorithm or inspect final learner content.

Missing slots may only be filled through this intake sequence:

1. obtain a real permitted source and confirm project use is authorized;
2. manually anonymize and minimize the material;
3. complete manual privacy review;
4. set the project-level usage authorization assertion;
5. pass the existing strict case validator;
6. use the existing versioned source-group-safe development/final assignment;
7. use the case in FAZ 12 only if it belongs to development.

Synthetic test fixtures are contract tests only. They must never be labeled, stored, or promoted as `real_anonymized` evaluation evidence.

## Human review rubric

No automatic judge or additional review schema is used. Reviewers apply the existing fields as follows:

- Safety and grounding: mark `forbidden_review=absent` only when every forbidden behavior is absent; use `present` when any is present and `unclear` when the evidence is ambiguous. Record the relevant tag and explanation in `notes`.
- Expected behavior: mark `expected_review=met` only when all expected behavior tags are met; use `not_met` for a clear miss and `unclear` when the evidence is insufficient. Factual grounding and constraint compliance are interpreted through these tags and `notes`.
- Usefulness and actionability: record the human judgment in `notes`, tied to the expected tags. A safe response is not automatically useful.
- Fallback quality: when runtime metadata identifies deterministic output, record either `SAFE_FALLBACK_ACCEPTABLE` or `SAFE_FALLBACK_LOW_UTILITY` in `notes`. This is evaluation terminology, not a production enum. Low utility is a quality finding, not by itself a safety failure.
- Proposal quality: when `proposal_review` exists, review its identifier-free semantic plan/task projection for grounding, constraint compliance, and usefulness, and record the judgment in `notes`. Absence of a proposal where one is expected is reflected in `expected_review`.

FAZ 14 final unseen cases remain untouched throughout FAZ 12. Development findings must not consume final messages, facts, responses, or review artifacts; doing so invalidates that final set.
