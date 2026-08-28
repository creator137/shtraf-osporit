# Stage 3 - Legal Questionnaire + Rules Engine

Client price for this stage: **5 000 RUB**. This information defines the agreed scope.

## Included In Stage 3

- A Telegram questionnaire that asks factual questions one at a time.
- Deterministic selection of possible verification directions from user answers.
- The first ten MVP situations provided by the client representative.
- Versioned legal rule definitions and references to the provided legal sources.
- Storage of questionnaire answers and the resulting rule matches per case.
- Admin view of the legal rule catalogue, sources, answers, and results.
- Tests for question branching, rule evaluation, persistence, and API output.

## Result Of This Stage

The system uses the recognized fine notice and the user's factual answers to
identify possible directions for further legal verification and the evidence
that is available, missing, or must be requested.

The user does not choose a legal code. The rules engine derives matching codes
from the answers.

## Excluded From Stage 3

- LLM-based legal reasoning.
- A legal conclusion or guarantee that a fine will be cancelled.
- Cancellation probability or commercial scoring.
- Complaint, petition, DOCX, or PDF generation.
- Automatic image comparison of vehicles or plates.
- Automatic verification of cameras, calibration, signs, or external registries.
- Payments, lawyer workflow, ESIA, GIS GMP, and automatic filing.
- Implementing the full catalogue of 25-50 future scenarios.

> Stage 3 returns possible directions for verification. It does not generate a complaint or replace legal review.
