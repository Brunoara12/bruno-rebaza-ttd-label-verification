import pytest
from pydantic import ValidationError

from backend.app.comparison import (
    compare_abv,
    compare_brand_name,
    compare_country_of_origin,
    compare_government_warning,
    compare_label,
    compare_net_contents,
)
from backend.app.schemas import ApplicationData, ExtractedLabel


CANONICAL_WARNING = (
    "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN "
    "SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF "
    "THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES "
    "IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY "
    "CAUSE HEALTH PROBLEMS."
)


def application_data(**overrides: str) -> ApplicationData:
    values = {
        "brand_name": "Acme Reserve",
        "class_type": "Straight Bourbon Whiskey",
        "abv": "45%",
        "net_contents": "750 mL",
        "producer": "Acme Distilling Co.",
        "country_of_origin": "United States",
        "government_warning": CANONICAL_WARNING,
    }
    values.update(overrides)
    return ApplicationData(**values)


def extracted_label(**overrides: object) -> ExtractedLabel:
    values = {
        "brand_name": "Acme Reserve",
        "class_type": "Straight Bourbon Whiskey",
        "abv": "45% Alc./Vol. (90 Proof)",
        "net_contents": "750ml",
        "producer": "Acme Distilling Co.",
        "country_of_origin": "USA",
        "government_warning": CANONICAL_WARNING,
        "raw_text": "sample label text",
        "extraction_confidence": 0.97,
    }
    values.update(overrides)
    return ExtractedLabel(**values)


def assert_pass(result) -> None:
    assert result.status == "PASS"
    assert result.reason_code is None


def assert_fail(result, reason_code: str) -> None:
    assert result.status == "FAIL"
    assert result.reason_code == reason_code


def test_application_data_requires_expected_fields_and_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ApplicationData(brand_name="Only one field")

    with pytest.raises(ValidationError):
        application_data(unexpected_field="not allowed")


def test_extracted_label_accepts_nullable_fields_and_bounds_confidence() -> None:
    label = ExtractedLabel(
        brand_name=None,
        class_type=None,
        abv=None,
        net_contents=None,
        producer=None,
        country_of_origin=None,
        government_warning=None,
        extraction_confidence=0.0,
    )

    assert label.brand_name is None
    assert label.extraction_confidence == 0.0

    with pytest.raises(ValidationError):
        extracted_label(extraction_confidence=1.01)


def test_case_only_brand_difference_passes() -> None:
    result = compare_brand_name("ACME RESERVE", "acme reserve")

    assert_pass(result)


def test_fuzzy_brand_punctuation_whitespace_and_token_order_passes() -> None:
    result = compare_brand_name("Acme Reserve", "Reserve,   Acme")

    assert_pass(result)


def test_fuzzy_brand_short_near_miss_fails() -> None:
    result = compare_brand_name("AB", "AC")

    assert_fail(result, "BELOW_THRESHOLD")


def test_fuzzy_brand_missing_found_value_fails() -> None:
    result = compare_brand_name("Acme Reserve", None)

    assert_fail(result, "MISSING_FIELD")


def test_usa_country_synonym_matches_united_states() -> None:
    result = compare_country_of_origin("United States", "USA")

    assert_pass(result)


def test_country_unrelated_value_fails() -> None:
    result = compare_country_of_origin("United States", "Canada")

    assert_fail(result, "BELOW_THRESHOLD")


@pytest.mark.parametrize(
    "found",
    [
        "45",
        "45%",
        "45.0% Alc./Vol.",
        "45% Alc./Vol. (90 Proof)",
        "45.09%",
    ],
)
def test_abv_normalized_formats_pass(found: str) -> None:
    result = compare_abv("45%", found)

    assert_pass(result)


@pytest.mark.parametrize("found", ["44.8%", "not listed"])
def test_abv_outside_tolerance_or_unparseable_fails(found: str) -> None:
    result = compare_abv("45%", found)

    assert result.status == "FAIL"
    assert result.reason_code in {"BELOW_THRESHOLD", "PARSE_ERROR"}


@pytest.mark.parametrize("found", ["750ml", "750 ML", "0.75 L", "75 cL", "25.36 fl oz"])
def test_net_contents_unit_normalized_formats_pass(found: str) -> None:
    result = compare_net_contents("750 mL", found)

    assert_pass(result)


@pytest.mark.parametrize("found", ["700 mL", "750 grams", "not listed"])
def test_net_contents_outside_tolerance_or_unparseable_fails(found: str) -> None:
    result = compare_net_contents("750 mL", found)

    assert result.status == "FAIL"
    assert result.reason_code in {"BELOW_THRESHOLD", "PARSE_ERROR"}


def test_correct_all_caps_government_warning_passes() -> None:
    result = compare_government_warning(CANONICAL_WARNING, CANONICAL_WARNING)

    assert_pass(result)


def test_government_warning_title_case_fails() -> None:
    title_case_warning = CANONICAL_WARNING.title()

    result = compare_government_warning(CANONICAL_WARNING, title_case_warning)

    assert_fail(result, "BELOW_THRESHOLD")
    assert result.found == title_case_warning


def test_government_warning_missing_colon_fails() -> None:
    missing_colon_warning = CANONICAL_WARNING.replace("WARNING:", "WARNING", 1)

    result = compare_government_warning(CANONICAL_WARNING, missing_colon_warning)

    assert_fail(result, "BELOW_THRESHOLD")
    assert result.found == missing_colon_warning


def test_government_warning_whitespace_only_difference_passes() -> None:
    wrapped_warning = CANONICAL_WARNING.replace(" ", "\n  ", 3)

    result = compare_government_warning(CANONICAL_WARNING, wrapped_warning)

    assert_pass(result)


def test_misread_government_warning_returns_extracted_text() -> None:
    misread_warning = CANONICAL_WARNING.replace("SURGEON", "SUREON", 1)

    result = compare_government_warning(CANONICAL_WARNING, misread_warning)

    assert_fail(result, "BELOW_THRESHOLD")
    assert result.found == misread_warning


def test_compare_label_returns_ordered_results_and_approved_when_all_pass() -> None:
    result = compare_label(application_data(), extracted_label(), latency_ms=123)

    assert result.overall_verdict == "APPROVED"
    assert result.latency_ms == 123
    assert [field_result.field for field_result in result.results] == [
        "brand_name",
        "class_type",
        "abv",
        "net_contents",
        "producer",
        "country_of_origin",
        "government_warning",
    ]
    assert {field_result.status for field_result in result.results} == {"PASS"}


def test_compare_label_returns_needs_review_when_any_field_fails() -> None:
    result = compare_label(
        application_data(),
        extracted_label(government_warning=CANONICAL_WARNING.title()),
    )

    assert result.overall_verdict == "NEEDS_REVIEW"
    warning_result = result.results[-1]
    assert warning_result.field == "government_warning"
    assert warning_result.status == "FAIL"
    assert warning_result.found == CANONICAL_WARNING.title()
