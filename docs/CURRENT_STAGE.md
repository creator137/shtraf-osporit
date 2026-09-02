# Stage 4 - DeepSeek Legal Analysis and Document Generation

This file defines the currently paid/development scope.

## Included In Stage 4

- DeepSeek analysis of a completed Stage 3 case using structured OCR fields,
  questionnaire answers, Legal Rules Engine results, and existing legal sources.
- Structured Pydantic validation of AI output.
- Storage of AI analysis input summary, proposed grounds, missing evidence, and
  user confirmation status.
- Telegram confirmation/rejection flow for proposed grounds.
- Generation of an individual complaint and, when relevant, a petition to
  request missing evidence.
- DOCX and PDF output saved as case files and sent to the user.
- Minimal read-only admin visibility for AI analysis and generated documents.

## Result Of This Stage

The system proposes potential legal arguments for the specific case, lets the
user confirm or reject them, and generates documents only from confirmed
arguments and known facts.

AI output must not introduce new legal sources, case facts, camera properties,
or user answers. Unknown data must stay marked as missing or requiring request.

## Excluded From Stage 4

- Cancellation probability or commercial scoring.
- Payment flow.
- Lawyer workflow.
- Automatic filing to government systems.
- ESIA, GIS GMP, courts, or Госуслуги integrations.
- Automatic external registry checks, web scraping, vector search, or RAG.
- Automatic image comparison of vehicles or plates.
- Automatic verification of cameras, calibration, signs, or external registries.

> Stage 4 generates draft documents for user review. It does not guarantee
> cancellation of a fine and does not replace legal review.
