import argparse
import json
from io import BytesIO
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont


DEFAULT_BACKEND_URL = "https://bruno-rebaza-ttd-label-verification-ej1c.onrender.com"

CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC "
    "BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF "
    "ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY "
    "CAUSE HEALTH PROBLEMS."
)

LABEL_FIELDS = {
    "brand_name": "Acme Reserve",
    "class_type": "Straight Bourbon Whiskey",
    "abv": "45%",
    "net_contents": "750 mL",
    "producer": "Acme Distilling Co.",
    "country_of_origin": "United States",
    "government_warning": CANONICAL_WARNING,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 6 verification checklist and latency benchmark against a backend URL."
    )
    parser.add_argument("--base-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Optional image path. By default the checklist uses a generated high-contrast label.",
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")
    parser.add_argument(
        "--write-sample",
        type=Path,
        help="Write the deterministic Acme Reserve sample image and exit without calling a backend.",
    )
    args = parser.parse_args()

    if args.write_sample:
        args.write_sample.parent.mkdir(parents=True, exist_ok=True)
        args.write_sample.write_bytes(generate_label_jpeg(with_warning=True))
        print(f"Wrote sample image: {args.write_sample}")
        return

    base_url = args.base_url.rstrip("/")
    image_bytes = args.image.read_bytes() if args.image else generate_label_jpeg(with_warning=True)
    no_warning_bytes = (
        crop_left_half_jpeg(image_bytes) if args.image else generate_label_jpeg(with_warning=False)
    )
    imperfect_bytes = degrade_image_jpeg(image_bytes)

    with httpx.Client(timeout=args.timeout) as client:
        report = run_checklist(
            client=client,
            base_url=base_url,
            image_bytes=image_bytes,
            no_warning_bytes=no_warning_bytes,
            imperfect_bytes=imperfect_bytes,
            repeats=max(1, args.repeats),
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


def run_checklist(
    *,
    client: httpx.Client,
    base_url: str,
    image_bytes: bytes,
    no_warning_bytes: bytes,
    imperfect_bytes: bytes,
    repeats: int,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    latency_samples: list[int] = []

    checks.append(check_health(client, base_url))
    checks.append(check_empty_submit(client, base_url))
    checks.append(check_wrong_file_type(client, base_url))

    valid_runs = [
        post_verify(client, base_url, image_bytes, "phase-6-label.jpg", LABEL_FIELDS)
        for _ in range(repeats)
    ]
    latency_samples.extend(server_latency_ms(run) for run in valid_runs if run["status_code"] == 200)
    checks.append(
        check_result(
            "valid_label",
            valid_runs[-1],
            lambda payload: payload.get("overall_verdict") == "APPROVED"
            and all(field.get("status") == "PASS" for field in payload.get("results", [])),
        )
    )
    checks.append(
        check_result(
            "correct_warning",
            valid_runs[-1],
            lambda payload: field_status(payload, "government_warning") == "PASS",
        )
    )

    mismatch = post_verify(
        client,
        base_url,
        image_bytes,
        "phase-6-label.jpg",
        {**LABEL_FIELDS, "brand_name": "Wrong Brand"},
    )
    latency_samples.append(server_latency_ms(mismatch))
    checks.append(
        check_result(
            "mismatches",
            mismatch,
            lambda payload: payload.get("overall_verdict") == "NEEDS_REVIEW"
            and field_status(payload, "brand_name") == "FAIL",
        )
    )

    case_only = post_verify(
        client,
        base_url,
        image_bytes,
        "phase-6-label.jpg",
        {
            **LABEL_FIELDS,
            "brand_name": LABEL_FIELDS["brand_name"].lower(),
            "class_type": LABEL_FIELDS["class_type"].lower(),
            "producer": LABEL_FIELDS["producer"].lower(),
            "country_of_origin": LABEL_FIELDS["country_of_origin"].lower(),
        },
    )
    latency_samples.append(server_latency_ms(case_only))
    checks.append(
        check_result(
            "case_only",
            case_only,
            lambda payload: field_status(payload, "brand_name") == "PASS"
            and field_status(payload, "class_type") == "PASS"
            and field_status(payload, "producer") == "PASS",
        )
    )

    normalized = post_verify(
        client,
        base_url,
        image_bytes,
        "phase-6-label.jpg",
        {**LABEL_FIELDS, "abv": "90 Proof", "net_contents": "0.75 L"},
    )
    latency_samples.append(server_latency_ms(normalized))
    checks.append(
        check_result(
            "abv_units_normalization",
            normalized,
            lambda payload: field_status(payload, "abv") == "PASS"
            and field_status(payload, "net_contents") == "PASS",
        )
    )

    missing_warning = post_verify(
        client,
        base_url,
        no_warning_bytes,
        "front-label-no-warning.jpg",
        LABEL_FIELDS,
    )
    latency_samples.append(server_latency_ms(missing_warning))
    checks.append(
        check_result(
            "missing_warning",
            missing_warning,
            lambda payload: payload.get("overall_verdict") == "NEEDS_REVIEW"
            and field_status(payload, "government_warning") == "FAIL",
        )
    )

    wrong_caps = post_verify(
        client,
        base_url,
        image_bytes,
        "phase-6-label.jpg",
        {**LABEL_FIELDS, "government_warning": CANONICAL_WARNING.title()},
    )
    latency_samples.append(server_latency_ms(wrong_caps))
    checks.append(
        check_result(
            "wrong_caps_warning",
            wrong_caps,
            lambda payload: payload.get("overall_verdict") == "NEEDS_REVIEW"
            and field_status(payload, "government_warning") == "FAIL",
        )
    )

    imperfect = post_verify(
        client,
        base_url,
        imperfect_bytes,
        "imperfect-label.jpg",
        LABEL_FIELDS,
    )
    latency_samples.append(server_latency_ms(imperfect))
    checks.append(
        check_result(
            "imperfect_image",
            imperfect,
            lambda payload: payload.get("overall_verdict") in {"APPROVED", "NEEDS_REVIEW"}
            and "results" in payload,
        )
    )

    batch = post_batch(
        client,
        base_url,
        [
            ("phase-6-label.jpg", image_bytes, LABEL_FIELDS),
            ("brand-mismatch.jpg", image_bytes, {**LABEL_FIELDS, "brand_name": "Wrong Brand"}),
            ("front-label-no-warning.jpg", no_warning_bytes, LABEL_FIELDS),
        ],
    )
    checks.append(check_batch_summary(batch))

    speed = summarize_latency(latency_samples)
    checks.append(
        {
            "name": "single_label_speed",
            "passed": bool(speed["samples"]) and speed["max_ms"] < 5000,
            "details": speed,
        }
    )

    return {
        "base_url": base_url,
        "checks": checks,
        "single_label_latency": speed,
        "all_passed": all(check["passed"] for check in checks),
    }


def check_health(client: httpx.Client, base_url: str) -> dict[str, Any]:
    response = timed_request(lambda: client.get(f"{base_url}/health"))
    passed = response["status_code"] == 200 and response["payload"].get("status") == "ok"
    return {"name": "health", "passed": passed, "details": compact_response(response)}


def check_empty_submit(client: httpx.Client, base_url: str) -> dict[str, Any]:
    response = timed_request(lambda: client.post(f"{base_url}/verify"))
    return {
        "name": "empty_submit",
        "passed": response["status_code"] == 422
        and response["payload"].get("error", {}).get("code") == "VALIDATION_ERROR",
        "details": compact_response(response),
    }


def check_wrong_file_type(client: httpx.Client, base_url: str) -> dict[str, Any]:
    response = timed_request(
        lambda: client.post(
            f"{base_url}/verify",
            data=LABEL_FIELDS,
            files={"image": ("label.txt", b"plain text", "text/plain")},
        )
    )
    return {
        "name": "wrong_file_type",
        "passed": response["status_code"] == 422
        and response["payload"].get("error", {}).get("code") == "UNSUPPORTED_FILE_TYPE",
        "details": compact_response(response),
    }


def post_verify(
    client: httpx.Client,
    base_url: str,
    image_bytes: bytes,
    filename: str,
    fields: dict[str, str],
) -> dict[str, Any]:
    return timed_request(
        lambda: client.post(
            f"{base_url}/verify",
            data=fields,
            files={"image": (filename, image_bytes, "image/jpeg")},
        )
    )


def post_batch(
    client: httpx.Client,
    base_url: str,
    items: list[tuple[str, bytes, dict[str, str]]],
) -> dict[str, Any]:
    payload_items = []
    files = []
    for index, (filename, image_bytes, fields) in enumerate(items, start=1):
        payload_items.append({"client_id": f"label-{index}", **fields})
        files.append(("images", (filename, image_bytes, "image/jpeg")))

    return timed_request(
        lambda: client.post(
            f"{base_url}/verify/batch",
            data={"items_json": json.dumps(payload_items)},
            files=files,
        )
    )


def check_result(name: str, response: dict[str, Any], predicate) -> dict[str, Any]:
    payload = response["payload"]
    passed = response["status_code"] == 200 and predicate(payload)
    return {"name": name, "passed": passed, "details": compact_verification(response)}


def check_batch_summary(response: dict[str, Any]) -> dict[str, Any]:
    payload = response["payload"]
    summary = payload.get("summary", {})
    counts_add_up = summary.get("passed", -1) + summary.get("needs_review", -1) == summary.get("total")
    passed = (
        response["status_code"] == 200
        and summary.get("total") == 3
        and counts_add_up
        and len(payload.get("items", [])) == 3
    )
    return {"name": "batch_summary", "passed": passed, "details": compact_batch(response)}


def timed_request(callable_request) -> dict[str, Any]:
    started_at = perf_counter()
    response = callable_request()
    client_latency_ms = round((perf_counter() - started_at) * 1000)
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return {
        "status_code": response.status_code,
        "client_latency_ms": client_latency_ms,
        "server_latency_ms": read_latency_header(response, payload),
        "payload": payload,
    }


def read_latency_header(response: httpx.Response, payload: dict[str, Any]) -> int | None:
    raw_value = (
        response.headers.get("x-verification-latency-ms")
        or response.headers.get("x-batch-verification-latency-ms")
        or payload.get("latency_ms")
    )
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def field_status(payload: dict[str, Any], field_name: str) -> str | None:
    for result in payload.get("results", []):
        if result.get("field") == field_name:
            return result.get("status")
    return None


def server_latency_ms(response: dict[str, Any]) -> int:
    return int(response.get("server_latency_ms") or response.get("client_latency_ms") or 0)


def summarize_latency(samples: list[int]) -> dict[str, Any]:
    clean_samples = [sample for sample in samples if sample > 0]
    if not clean_samples:
        return {"samples": [], "p50_ms": None, "p95_ms": None, "max_ms": None}
    sorted_samples = sorted(clean_samples)
    p95_index = min(len(sorted_samples) - 1, round((len(sorted_samples) - 1) * 0.95))
    return {
        "samples": clean_samples,
        "p50_ms": round(median(clean_samples)),
        "p95_ms": sorted_samples[p95_index],
        "max_ms": max(clean_samples),
    }


def compact_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status_code": response["status_code"],
        "client_latency_ms": response["client_latency_ms"],
        "server_latency_ms": response["server_latency_ms"],
        "error": response["payload"].get("error"),
    }


def compact_verification(response: dict[str, Any]) -> dict[str, Any]:
    payload = response["payload"]
    return {
        "status_code": response["status_code"],
        "client_latency_ms": response["client_latency_ms"],
        "server_latency_ms": response["server_latency_ms"],
        "overall_verdict": payload.get("overall_verdict"),
        "fields": [
            {
                "field": result.get("field"),
                "status": result.get("status"),
                "reason_code": result.get("reason_code"),
                "found": result.get("found"),
            }
            for result in payload.get("results", [])
        ],
        "error": payload.get("error"),
    }


def compact_batch(response: dict[str, Any]) -> dict[str, Any]:
    payload = response["payload"]
    return {
        "status_code": response["status_code"],
        "client_latency_ms": response["client_latency_ms"],
        "server_latency_ms": response["server_latency_ms"],
        "summary": payload.get("summary"),
        "items": [
            {
                "client_id": item.get("client_id"),
                "status": item.get("status"),
                "verdict": (item.get("result") or {}).get("overall_verdict"),
                "error": item.get("error"),
            }
            for item in payload.get("items", [])
        ],
        "error": payload.get("error"),
    }


def generate_label_jpeg(*, with_warning: bool) -> bytes:
    image = Image.new("RGB", (1500, 1900), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(82)
    heading_font = load_font(52)
    body_font = load_font(42)
    small_font = load_font(34)

    y = 90
    draw.text((90, y), "ACME RESERVE", fill="black", font=title_font)
    y += 120
    draw.text((90, y), "STRAIGHT BOURBON WHISKEY", fill="black", font=heading_font)
    y += 95
    draw.text((90, y), "ALC 45% BY VOL", fill="black", font=body_font)
    y += 75
    draw.text((90, y), "750 ML", fill="black", font=body_font)
    y += 105
    draw.text((90, y), "PRODUCED AND BOTTLED BY", fill="black", font=small_font)
    y += 58
    draw.text((90, y), "ACME DISTILLING CO.", fill="black", font=body_font)
    y += 78
    draw.text((90, y), "COUNTRY OF ORIGIN: UNITED STATES", fill="black", font=body_font)
    y += 110

    if with_warning:
        draw.rectangle((70, y - 25, 1430, 1760), outline="black", width=5)
        warning_lines = [
            "GOVERNMENT WARNING:",
            "(1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK",
            "ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF",
            "BIRTH DEFECTS.",
            "(2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY",
            "TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS.",
        ]
        for line in warning_lines:
            draw.text((100, y), line, fill="black", font=small_font)
            y += 58
    else:
        draw.text((90, y), "RESPONSIBLY PRODUCED SAMPLE LABEL", fill="black", font=body_font)

    return encode_jpeg(image, quality=88)


def load_font(size: int) -> ImageFont.ImageFont:
    for font_name in (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def crop_left_half_jpeg(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        cropped = rgb.crop((0, 0, max(1, width // 2), height))
        return encode_jpeg(cropped, quality=82)


def degrade_image_jpeg(image_bytes: bytes) -> bytes:
    with Image.open(BytesIO(image_bytes)) as image:
        rgb = image.convert("RGB")
        tiny = rgb.resize((max(1, rgb.width // 10), max(1, rgb.height // 10)))
        blurred = tiny.filter(ImageFilter.GaussianBlur(radius=2.0))
        enlarged = blurred.resize(rgb.size)
        return encode_jpeg(enlarged, quality=45)


def encode_jpeg(image: Image.Image, *, quality: int) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


def print_report(report: dict[str, Any]) -> None:
    print(f"Base URL: {report['base_url']}")
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{status} {check['name']}: {json.dumps(check['details'], ensure_ascii=True)}")
    print(f"Single-label latency: {json.dumps(report['single_label_latency'])}")
    print(f"All passed: {report['all_passed']}")


if __name__ == "__main__":
    main()
