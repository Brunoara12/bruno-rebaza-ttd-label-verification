from io import BytesIO

import pytest
from PIL import Image

from backend.app.image_preprocess import ImagePreprocessError, preprocess_image


def make_image_bytes(width: int, height: int, image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (width, height), color=(160, 40, 40))
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def test_preprocess_downscales_and_reencodes_to_jpeg() -> None:
    result = preprocess_image(make_image_bytes(400, 200), max_edge_px=100, jpeg_quality=80)

    assert result.mime_type == "image/jpeg"
    assert result.width == 100
    assert result.height == 50
    assert result.data.startswith(b"\xff\xd8")

    with Image.open(BytesIO(result.data)) as image:
        assert image.format == "JPEG"
        assert image.size == (100, 50)


def test_preprocess_keeps_smaller_image_dimensions() -> None:
    result = preprocess_image(make_image_bytes(80, 60), max_edge_px=100, jpeg_quality=80)

    assert result.width == 80
    assert result.height == 60


def test_preprocess_rejects_corrupt_image() -> None:
    with pytest.raises(ImagePreprocessError):
        preprocess_image(b"not an image")


def test_preprocess_rejects_invalid_options() -> None:
    with pytest.raises(ImagePreprocessError):
        preprocess_image(make_image_bytes(10, 10), max_edge_px=0)

    result = preprocess_image(make_image_bytes(10, 10), jpeg_quality=100)
    assert result.mime_type == "image/jpeg"

    with pytest.raises(ImagePreprocessError):
        preprocess_image(make_image_bytes(10, 10), jpeg_quality=101)
