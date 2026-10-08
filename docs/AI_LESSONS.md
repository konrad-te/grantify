# From matching to preparation

The forest-fire demo turns an understandable idea into a funding preparation conversation.

1. A local LLM extracts company and project facts with exact evidence quotes. The user reviews them.
2. Deterministic code shortlists programmes using country, activities, amount and recorded dates.
3. For EIC Accelerator, instant rules check explicit evidence features in five preparation areas. An optional second LLM call interprets the evidence more deeply.
4. The server validates the response schema, complete area coverage and exact supporting quotes.
5. Weak or missing evidence produces targeted questions and a preparation task. New answers can update the review.

## What changed

Semantic overlap was useful for finding leads, but a high score was misleading. A project can match a topic while failing a crucial requirement.

The first questionnaire also failed: enough characters in a text box did not mean useful evidence. The current review distinguishes an interested customer from a paid pilot and explains why controlled tests do not establish field reliability. The instant mode detects explicit evidence features with transparent rules; the optional AI mode interprets richer statements.

The overall recommendation comes from the reviewed area states, with possible problems prioritised. The AI does not choose a success percentage.

## What is tested

Automated tests exercise validation, quote grounding, duplicate or omitted areas, failure recovery, safe rendering and deterministic matching.

Preparation scenarios cover the initial wildfire story, stronger follow-up evidence, and a vague story containing an instruction to approve it. Run instant checks with:

    python -m tools.evaluate_readiness --case initial
    python -m tools.evaluate_readiness --case improved
    python -m tools.evaluate_readiness --case vague

These checks are a small regression set, not a measurement of real funding decisions.

Add `--engine ai` to check the actual local model separately. Automated tests use controlled model responses to test grounding and failure handling; they do not establish model accuracy.

## Limits

An exact quote proves where a statement came from; it does not prove the statement is true or the interpretation correct. Self-reported evidence is not an independently reviewed document. The local model can still misjudge it.

The instant rules can miss paraphrases and contradictions; their findings are explicitly preliminary. Live AI testing on this machine hit memory exhaustion with qwen3:8b and a two-minute timeout with qwen3.5:4b. The main demonstration therefore uses instant checks. Successful model-quality evaluation remains outstanding.

The catalogue is manually maintained. Call availability, legal eligibility, eligible spending and funding component still need official review. EIC-specific deeper assessment is implemented; other programme questionnaires collect evidence without the same semantic review.

The rules come from the [2026 EIC work programme](https://eic.ec.europa.eu/system/files/2025-11/EIC-Work-Programme-2026.pdf), Accelerator award criteria, reviewed 8 October 2026. These are an explicitly limited preparation rubric, not a complete rulebook.
