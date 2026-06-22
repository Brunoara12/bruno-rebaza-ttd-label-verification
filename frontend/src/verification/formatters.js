import { FIELD_LABELS } from "./constants";

export function displayValue(value, fallback) {
  if (typeof value !== "string" || value.trim() === "") {
    return fallback;
  }

  return value;
}

export function fieldLabel(fieldName) {
  return FIELD_LABELS[fieldName] ?? "This field";
}

export function plainReviewSummary(failedResults) {
  if (failedResults.some((fieldResult) => fieldResult.reason_code === "MODEL_TIMEOUT")) {
    return "The checker took too long to read the label.";
  }

  if (failedResults.some((fieldResult) => fieldResult.reason_code === "PARSE_ERROR")) {
    return "The checker could not read the label clearly.";
  }

  if (failedResults.length === 1) {
    return `${fieldLabel(failedResults[0].field)} needs review.`;
  }

  return `${failedResults.length} fields need review.`;
}

export function plainReason(fieldResult) {
  switch (fieldResult.reason_code) {
    case "MODEL_TIMEOUT":
      return "The checker took too long to read this field.";
    case "PARSE_ERROR":
      return "The checker could not read this field clearly.";
    case "MISSING_FIELD":
      return "The checker did not find this on the label.";
    case "BELOW_THRESHOLD":
      return "The value on the label does not match the expected value.";
    default:
      return fieldResult.found
        ? "The value on the label does not match the expected value."
        : "The checker did not find this on the label.";
  }
}
