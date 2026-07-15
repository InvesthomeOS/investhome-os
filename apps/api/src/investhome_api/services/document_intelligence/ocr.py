"""OCR provider abstraction."""

from __future__ import annotations

import io
import logging
from abc import ABC, abstractmethod

from PIL import Image

from investhome_api.config.settings import get_settings
from investhome_api.services.document_intelligence.types import OCRPageResult, SourceReference

logger = logging.getLogger(__name__)


class OCRProvider(ABC):
    name: str

    @abstractmethod
    def ocr_image(self, content: bytes, source: SourceReference) -> OCRPageResult:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError


class LocalTesseractOCR(OCRProvider):
    name = "local_tesseract"

    def is_available(self) -> bool:
        try:
            import pytesseract  # noqa: PLC0415

            _ = pytesseract
            return True
        except ImportError:
            return False

    def ocr_image(self, content: bytes, source: SourceReference) -> OCRPageResult:
        try:
            import pytesseract  # noqa: PLC0415

            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image) or ""
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data.get("conf", []) if str(c).isdigit() and int(c) >= 0]
            confidence = sum(confidences) / len(confidences) / 100 if confidences else None
            return OCRPageResult(text=text.strip(), source=source, confidence=confidence)
        except Exception:
            logger.warning("Tesseract OCR unavailable; returning empty OCR result", exc_info=True)
            return OCRPageResult(text="", source=source, confidence=0.0)


class DevFallbackOCR(OCRProvider):
    """Development OCR that extracts metadata only when tesseract is unavailable."""

    name = "dev_fallback"

    def is_available(self) -> bool:
        return True

    def ocr_image(self, content: bytes, source: SourceReference) -> OCRPageResult:
        try:
            image = Image.open(io.BytesIO(content))
            label = source.label()
            text = (
                f"[OCR placeholder — install Tesseract for full OCR] "
                f"Image {image.size[0]}x{image.size[1]} at {label}"
            )
            return OCRPageResult(text=text, source=source, confidence=0.1)
        except Exception:
            return OCRPageResult(text="", source=source, confidence=0.0)


def get_ocr_provider() -> OCRProvider:
    settings = get_settings()
    if settings.ocr_provider == "local":
        tesseract = LocalTesseractOCR()
        if tesseract.is_available():
            return tesseract
        return DevFallbackOCR()
    return DevFallbackOCR()
