# Defensa Individual - Team Assignments

This document outlines what each team member is responsible for and what they need to be able to explain during the individual defense.

---

## MOLLO — OCR RRV + Image Processing

**Module:** `backend/app/services/ocr/`

**Responsibilities:**
- Convert PDF electoral acts to images (`pdf_converter.py`).
- Preprocess images for OCR (grayscale, thresholding, deskew) (`image_preprocessor.py`).
- Run Tesseract OCR and extract standard field values (`field_extractor.py`, `ocr_service.py`).
- Mark act as `OBSERVADA` when OCR confidence is below threshold.

**Defense questions to prepare:**
- How does the OCR pipeline handle low-quality or rotated images?
- How do you map raw OCR text to the standard field names?
- What happens when OCR confidence is below the threshold?

---

## Ferrufino — Mobile App + SMS + Receiver

**Module:** `backend/app/services/sms/`, `mobile-app/`

**Responsibilities:**
- Implement the mobile app for capturing act photos.
- Implement the SMS receiver and gateway integration (`sms_receiver.py`).
- Parse SMS into standard fields (`sms_parser.py`).
- Validate sender PIN (`sms_security.py`).
- Mark act as `RECHAZADA` when SMS format is invalid.

**Defense questions to prepare:**
- What is the agreed SMS format? How is it parsed?
- How is the sender authenticated (PIN validation)?
- How does the mobile app send the photo to the backend?

---

## Sanabria — Validator + Logs + OEP Rules

**Module:** `backend/app/services/validation/`, `backend/app/services/logging/`

**Responsibilities:**
- Implement all OEP validation rules from `docs/reglas_validacion.md`.
- Assign `estado` to each act based on validation results.
- Write functional logs and events to MongoDB (`functional_log_service.py`).
- Orchestrate the RRV service flow (`rrv_service.py`).

**Defense questions to prepare:**
- Explain each validation rule and its failure consequence.
- How are duplicate acts detected and handled?
- What is the difference between a functional log and a technical metric?

---

## Escobar — Clusters + Persistence + Fault Tolerance

**Module:** `backend/app/core/database.py`, `backend/app/repositories/`, `infra/`

**Responsibilities:**
- Configure MongoDB Replica Set (Cluster 1 - RRV).
- Configure PostgreSQL replication (Cluster 2 - Official).
- Implement all repository CRUD operations.
- Configure Docker Compose infrastructure.
- Implement health check routes.

**Defense questions to prepare:**
- How does the MongoDB replica set handle primary failure?
- How does PostgreSQL streaming replication ensure consistency?
- What happens to data integrity if one cluster node goes down?

---

## Erick Diaz — Official Automation + Comparative Dashboard

**Module:** `automatizador-oficial/`, `backend/app/services/oficial/`, `dashboard/`

**Responsibilities:**
- Implement the CSV automatizador that reads official data and sends it to the API.
- Implement the official act processing service (`oficial_service.py`).
- Implement dashboard API routes (`dashboard_routes.py`).
- Implement the comparative dashboard frontend.

**Defense questions to prepare:**
- How does the CSV automatizador handle errors or missing rows?
- How is the RRV vs official comparison computed?
- What does the dashboard show and how is it updated in near real-time?
