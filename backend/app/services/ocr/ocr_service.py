"""
Orchestrates the full OCR pipeline: PDF/image → preprocess → OCR → extract fields.
Responsible: MOLLO.
TODO (MOLLO): wire together pdf_converter, image_preprocessor, field_extractor, and tesseract.
"""


async def process_pdf(pdf_path: str) -> dict:
    # TODO (MOLLO): call pdf_to_images → preprocess_image → run_tesseract → extract_fields
    # Returns a dict with standard field names ready for RRV validation
    raise NotImplementedError


async def process_image(image_path: str) -> dict:
    # TODO (MOLLO): same pipeline but starting from a single image (mobile app photo)
    raise NotImplementedError
