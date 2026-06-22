from difflib import SequenceMatcher
import re
import string

from backend.app.schemas import ApplicationData, ExtractedLabel, FieldResult, VerificationResult

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - exercised only in bare local environments
    # Keep local no-network development usable; deployed/test environments should use RapidFuzz.
    fuzz = None


FUZZY_THRESHOLD = 90.0
COUNTRY_THRESHOLD = 95.0
ABV_TOLERANCE_PERCENTAGE_POINTS = 0.1
NET_CONTENTS_TOLERANCE_ML = 1.0
SHORT_TEXT_EXACT_LENGTH = 3

COUNTRY_SYNONYMS = {
    "us": "united states",
    "u s": "united states",
    "usa": "united states",
    "u s a": "united states",
    "united states": "united states",
    "united states of america": "united states",
}

US_STATE_ABBREVIATIONS = {
    "al",
    "ak",
    "az",
    "ar",
    "ca",
    "co",
    "ct",
    "dc",
    "de",
    "fl",
    "ga",
    "hi",
    "ia",
    "id",
    "il",
    "ks",
    "ky",
    "la",
    "ma",
    "md",
    "mi",
    "mn",
    "mo",
    "ms",
    "mt",
    "nc",
    "nd",
    "ne",
    "nh",
    "nj",
    "nm",
    "nv",
    "ny",
    "oh",
    "ok",
    "pa",
    "ri",
    "sc",
    "sd",
    "tn",
    "tx",
    "ut",
    "va",
    "vt",
    "wa",
    "wi",
    "wv",
    "wy",
}
AMBIGUOUS_US_STATE_ABBREVIATIONS = {"in", "me", "or"}
US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "district of columbia",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}


def compare_brand_name(expected: str, found: str | None) -> FieldResult:
    return _compare_fuzzy("brand_name", "fuzzy", expected, found, FUZZY_THRESHOLD)


def compare_class_type(expected: str, found: str | None) -> FieldResult:
    return _compare_fuzzy("class_type", "fuzzy", expected, found, FUZZY_THRESHOLD)


def compare_producer(expected: str, found: str | None) -> FieldResult:
    return _compare_fuzzy(
        "producer",
        "fuzzy",
        expected,
        found,
        FUZZY_THRESHOLD,
        normalizer=_normalize_producer_text,
    )


def compare_country_of_origin(expected: str, found: str | None) -> FieldResult:
    if _is_missing(found):
        return _fail("country_of_origin", "country-synonym", expected, found, "MISSING_FIELD")

    expected_normalized = _canonical_country(expected)
    found_normalized = _canonical_country(found)
    score = _token_sort_ratio(expected_normalized, found_normalized)

    if score >= COUNTRY_THRESHOLD:
        return _pass("country_of_origin", "country-synonym", expected, found)

    return _fail("country_of_origin", "country-synonym", expected, found, "BELOW_THRESHOLD")


def compare_abv(expected: str, found: str | None) -> FieldResult:
    if _is_missing(found):
        return _fail("abv", "numeric-normalized", expected, found, "MISSING_FIELD")

    expected_percent = _parse_abv_percent(expected)
    found_percent = _parse_abv_percent(found)

    if expected_percent is None or found_percent is None:
        return _fail("abv", "numeric-normalized", expected, found, "PARSE_ERROR")

    if abs(expected_percent - found_percent) <= ABV_TOLERANCE_PERCENTAGE_POINTS:
        return _pass("abv", "numeric-normalized", expected, found)

    return _fail("abv", "numeric-normalized", expected, found, "BELOW_THRESHOLD")


def compare_net_contents(expected: str, found: str | None) -> FieldResult:
    if _is_missing(found):
        return _fail("net_contents", "unit-normalized", expected, found, "MISSING_FIELD")

    expected_ml = _parse_net_contents_ml(expected)
    found_ml = _parse_net_contents_ml(found)

    if expected_ml is None or found_ml is None:
        return _fail("net_contents", "unit-normalized", expected, found, "PARSE_ERROR")

    if abs(expected_ml - found_ml) <= NET_CONTENTS_TOLERANCE_ML:
        return _pass("net_contents", "unit-normalized", expected, found)

    return _fail("net_contents", "unit-normalized", expected, found, "BELOW_THRESHOLD")


def compare_government_warning(expected: str, found: str | None) -> FieldResult:
    if _is_missing(found):
        return _fail("government_warning", "exact", expected, found, "MISSING_FIELD")

    # TTB warning text is intentionally strict: whitespace can vary, but case and punctuation cannot.
    if _collapse_whitespace(expected) == _collapse_whitespace(found):
        return _pass("government_warning", "exact", expected, found)

    return _fail("government_warning", "exact", expected, found, "BELOW_THRESHOLD")


def compare_label(
    application: ApplicationData,
    extracted: ExtractedLabel,
    latency_ms: int = 0,
) -> VerificationResult:
    results = [
        compare_brand_name(application.brand_name, extracted.brand_name),
        compare_class_type(application.class_type, extracted.class_type),
        compare_abv(application.abv, extracted.abv),
        compare_net_contents(application.net_contents, extracted.net_contents),
        compare_producer(application.producer, extracted.producer),
        compare_country_of_origin(application.country_of_origin, extracted.country_of_origin),
        compare_government_warning(
            application.government_warning,
            extracted.government_warning,
        ),
    ]
    verdict = "NEEDS_REVIEW" if any(result.status == "FAIL" for result in results) else "APPROVED"

    return VerificationResult(
        results=results,
        overall_verdict=verdict,
        latency_ms=latency_ms,
    )


def _compare_fuzzy(
    field: str,
    match_type: str,
    expected: str,
    found: str | None,
    threshold: float,
    normalizer=None,
) -> FieldResult:
    if _is_missing(found):
        return _fail(field, match_type, expected, found, "MISSING_FIELD")

    normalizer = normalizer or _normalize_fuzzy_text
    expected_normalized = normalizer(expected)
    found_normalized = normalizer(found)

    # Fuzzy scores are too forgiving for very short strings, so short values must match exactly.
    if _requires_exact_short_match(expected_normalized, found_normalized):
        if expected_normalized == found_normalized:
            return _pass(field, match_type, expected, found)
        return _fail(field, match_type, expected, found, "BELOW_THRESHOLD")

    if _token_sort_ratio(expected_normalized, found_normalized) >= threshold:
        return _pass(field, match_type, expected, found)

    return _fail(field, match_type, expected, found, "BELOW_THRESHOLD")


def _pass(field: str, match_type: str, expected: str | None, found: str | None) -> FieldResult:
    return FieldResult(
        field=field,
        match_type=match_type,
        expected=expected,
        found=found,
        status="PASS",
    )


def _fail(
    field: str,
    match_type: str,
    expected: str | None,
    found: str | None,
    reason_code: str,
) -> FieldResult:
    return FieldResult(
        field=field,
        match_type=match_type,
        expected=expected,
        found=found,
        status="FAIL",
        reason_code=reason_code,
    )


def _is_missing(value: str | None) -> bool:
    return value is None or not value.strip()


def _normalize_fuzzy_text(value: str | None) -> str:
    without_punctuation = (value or "").lower().translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    return _collapse_whitespace(without_punctuation)


def _normalize_producer_text(value: str | None) -> str:
    normalized = _normalize_fuzzy_text(value)
    role_words = (
        "produced|distilled|bottled|imported|vinted|cellared|blended|brewed|"
        "fermented|prepared|manufactured|made|packed|selected"
    )
    return re.sub(
        rf"^(?:(?:{role_words})(?:\s+and\s+(?:{role_words}))*\s+by\s+)+",
        "",
        normalized,
    )


def _collapse_whitespace(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _requires_exact_short_match(expected: str, found: str) -> bool:
    expected_length = len(expected.replace(" ", ""))
    found_length = len(found.replace(" ", ""))
    return min(expected_length, found_length) <= SHORT_TEXT_EXACT_LENGTH


def _token_sort_ratio(expected: str, found: str) -> float:
    if fuzz is not None:
        return float(fuzz.token_sort_ratio(expected, found))

    expected_sorted = " ".join(sorted(expected.split()))
    found_sorted = " ".join(sorted(found.split()))
    return SequenceMatcher(None, expected_sorted, found_sorted).ratio() * 100


def _canonical_country(value: str | None) -> str:
    normalized = _normalize_fuzzy_text(value or "")
    if normalized in COUNTRY_SYNONYMS:
        return COUNTRY_SYNONYMS[normalized]
    if _mentions_us_location(value or "", normalized):
        return "united states"
    return normalized


def _mentions_us_location(raw_value: str, normalized: str) -> bool:
    state_pattern = "|".join(sorted(US_STATE_ABBREVIATIONS | AMBIGUOUS_US_STATE_ABBREVIATIONS))
    if re.search(rf",\s*(?:{state_pattern})\.?\b", raw_value, flags=re.IGNORECASE):
        return True

    normalized_tokens = set(normalized.split())
    if normalized_tokens & US_STATE_ABBREVIATIONS:
        return True

    padded_normalized = f" {normalized} "
    return any(f" {state} " in padded_normalized for state in US_STATE_NAMES)


def _parse_abv_percent(value: str | None) -> float | None:
    # Prefer explicit percent/ABV text before proof; labels often include both, e.g. "45% ... (90 Proof)".
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", value or "")
    if percent_match:
        return float(percent_match.group(1))

    abv_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:abv|alc(?:ohol)?\.?\s*/?\s*vol)",
        value or "",
        flags=re.IGNORECASE,
    )
    if abv_match:
        return float(abv_match.group(1))

    proof_match = re.search(r"(\d+(?:\.\d+)?)\s*proof", value or "", flags=re.IGNORECASE)
    if proof_match:
        return float(proof_match.group(1)) / 2

    number_match = re.search(r"\d+(?:\.\d+)?", value or "")
    if number_match:
        return float(number_match.group(0))

    return None


def _parse_net_contents_ml(value: str | None) -> float | None:
    # Accept both spaced and compact units, then convert everything to mL for comparison.
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(milliliters?|ml|liters?|litres?|l|centiliters?|cl|"
        r"fluid\s*ounces?|fl\.?\s*oz\.?|ounces?|oz)\b",
        value or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    quantity = float(match.group(1))
    unit = re.sub(r"[\s.]", "", match.group(2).lower())

    if unit in {"ml", "milliliter", "milliliters"}:
        return quantity
    if unit in {"l", "liter", "liters", "litre", "litres"}:
        return quantity * 1000
    if unit in {"cl", "centiliter", "centiliters"}:
        return quantity * 10
    if unit in {"floz", "fluidounce", "fluidounces", "oz", "ounce", "ounces"}:
        return quantity * 29.5735295625

    return None
