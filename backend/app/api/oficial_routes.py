"""
Official Computation (CO) API routes: CSV ingestion and transcription.
Responsible: Erick Diaz.
TODO: implement endpoints once automatizador-oficial is ready.
"""
from fastapi import APIRouter

router = APIRouter()

# TODO (Erick Diaz): POST /acta — receive official act from CSV automatizador
# TODO (Erick Diaz): GET /actas — list official acts with filters
# TODO (Erick Diaz): GET /acta/{mesa_codigo} — get official act by mesa_codigo
