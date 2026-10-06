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

Program contexts are created only from exact packaged Specialty Profiles. Fact materialization is deliberately limited to authoritative `education_status`, `grade_level`, and `study_track` fields. Other fact kinds are not inserted into a generic store; they are listed as unsupported metadata when the case can still run.
