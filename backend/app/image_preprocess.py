from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


DEFAULT_MAX_IMAGE_EDGE_PX = 1280
DEFAULT_JPEG_QUALITY = 76
JPEG_MIME_TYPE = "image/jpeg"


class ImagePreprocessError(ValueError):
    """Raised when an uploaded image cannot be decoded or normalized."""


@dataclass(frozen=True)
class PreprocessedImage:
    data: bytes
    mime_type: str
    width: int
    height: int


def preprocess_image(
    image_bytes: bytes,
    *,
    max_edge_px: int = DEFAULT_MAX_IMAGE_EDGE_PX,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY,
) -> PreprocessedImage:
    if not image_bytes:
        raise ImagePreprocessError("Image file is empty.")
    if max_edge_px < 1:
        raise ImagePreprocessError("Maximum image edge must be at least 1 pixel.")
    if not 1 <= jpeg_quality <= 95:
        raise ImagePreprocessError("JPEG quality must be between 1 and 95.")

    try:
        with Image.open(BytesIO(image_bytes)) as source_image:
            source_image.load()
            image = ImageOps.exif_transpose(source_image)

            if image.mode != "RGB":
                image = image.convert("RGB")

            width, height = image.size
            if width < 1 or height < 1:
                raise ImagePreprocessError("Image dimensions are invalid.")

            resized = _resize_to_max_edge(image, max_edge_px)
            output = BytesIO()
            resized.save(output, format="JPEG", quality=jpeg_quality, optimize=True)

            return PreprocessedImage(
                data=output.getvalue(),
                mime_type=JPEG_MIME_TYPE,
                width=resized.width,
                height=resized.height,
            )
    except ImagePreprocessError:
        raise
    except (OSError, UnidentifiedImageError) as exc:
        raise ImagePreprocessError("Image file is corrupt or unsupported.") from exc


def _resize_to_max_edge(image: Image.Image, max_edge_px: int) -> Image.Image:
    longest_edge = max(image.size)
    if longest_edge <= max_edge_px:
        return image.copy()

    scale = max_edge_px / longest_edge
    new_size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    return image.resize(new_size, Image.Resampling.LANCZOS)
