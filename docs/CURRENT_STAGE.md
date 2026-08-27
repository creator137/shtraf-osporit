# Stage 2 - Document Processing + Manual Correction

Client price for this stage must be agreed separately. This file defines scope only.

## Included In Stage 2

The following work is expected in Stage 2 tasks:

- OCR processing for uploaded fine documents.
- Storage of raw OCR text.
- Extraction of basic постановление fields from OCR text.
- Admin view of recognized text and extracted fields.
- Manual correction of extracted fields in the admin panel.
- Case processing status updates for recognition flow.
- Basic error state when document processing fails.
- Tests for OCR service boundaries, extraction, API, and admin form behavior.

## Basic Fields For Stage 2

- постановление number;
- постановление date;
- UIN;
- fine amount;
- article / КоАП reference when visible;
- vehicle plate number when visible;
- violation date/time when visible;
- violation place when visible;
- issuing authority when visible.

## Excluded From Stage 2

- Legal Rules Engine.
- Legal knowledge base.
- LLM-based legal reasoning.
- OpenAI, Claude, or Gemini integration.
- Probability of cancellation.
- Automatic legal grounds.
- Complaint generation.
- DOCX or PDF generation.
- Payments.
- ESIA, GIS GMP, or partner API integration.
- Automatic filing of complaints.
- Lawyer workflow.
- Complex roles.
- Complex analytics.

> Keep Stage 2 focused on reading the uploaded document and letting the operator correct recognized data.
