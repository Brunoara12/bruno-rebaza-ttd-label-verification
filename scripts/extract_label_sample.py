import argparse
import json
from pathlib import Path

from backend.app.config import get_settings
from backend.app.image_preprocess import preprocess_image
from backend.app.vision_service import OpenAIVisionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured label fields from one image.")
    parser.add_argument("image_path", help="Path to a readable beverage alcohol label image.")
    args = parser.parse_args()

    settings = get_settings()
    image_path = Path(args.image_path)
    image = preprocess_image(
        image_path.read_bytes(),
        max_edge_px=settings.vision_max_image_edge_px,
        jpeg_quality=settings.vision_jpeg_quality,
    )

    service = OpenAIVisionService(
        api_key=settings.openai_api_key,
        model=settings.vision_model,
        timeout_seconds=settings.vision_timeout_seconds,
    )
    extracted_label = service.extract_label(image)
    print(json.dumps(extracted_label.model_dump(), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
