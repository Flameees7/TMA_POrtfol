import io
import logging
from pathlib import Path
from PIL import Image, ImageOps

logger = logging.getLogger("image_service")


class ImageService:
    """Utility service for optimizing and converting product images to high efficiency WebP."""

    @staticmethod
    def process_and_save_webp(
        image_bytes: bytes,
        destination_path: Path,
        max_dimension: int = 1600,
        quality: int = 85
    ) -> Path:
        """
        Converts raw image bytes to an optimized .webp file:
        1. Corrects EXIF rotation (especially from smartphone cameras).
        2. Converts color mode (RGB / RGBA).
        3. Scales down if exceeding max_dimension while preserving aspect ratio.
        4. Saves as lightweight WebP with high visual fidelity.
        """
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure .webp extension
        if destination_path.suffix.lower() != ".webp":
            destination_path = destination_path.with_suffix(".webp")

        with Image.open(io.BytesIO(image_bytes)) as img:
            # 1. Correct smartphone EXIF orientation
            try:
                img = ImageOps.exif_transpose(img)
            except Exception as e:
                logger.debug(f"Could not apply exif_transpose: {e}")

            # 2. Color mode handling
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                processed_img = img.convert("RGBA")
            else:
                processed_img = img.convert("RGB")

            # 3. Scale down if necessary
            if max(processed_img.width, processed_img.height) > max_dimension:
                processed_img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            # 4. Save as WebP
            processed_img.save(
                destination_path,
                format="WEBP",
                quality=quality,
                method=6,
                optimize=True
            )

        logger.info(f"Saved optimized WebP image: {destination_path} (Quality: {quality})")
        return destination_path
