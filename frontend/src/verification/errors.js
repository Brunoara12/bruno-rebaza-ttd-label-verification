import { fieldLabel } from "./formatters";

export function readableApiError(payload) {
  const error = payload?.error ?? {};
  const fieldErrors = {};

  if (Array.isArray(error.fields)) {
    error.fields.forEach((fieldError) => {
      const fieldName = fieldError.field ?? "request";
      fieldErrors[fieldName] = readableFieldError(fieldError);
    });
  }

  return {
    message: readableGeneralError(error.code, error.message),
    fields: fieldErrors,
  };
}

function readableGeneralError(code, message) {
  switch (code) {
    case "VALIDATION_ERROR":
      return "Please fix the highlighted items.";
    case "UNSUPPORTED_FILE_TYPE":
      return "Please choose a JPEG, PNG, or WEBP image.";
    case "FILE_TOO_LARGE":
      return message || "Please choose a smaller label photo.";
    case "EMPTY_IMAGE":
      return "The label photo is empty. Please choose another photo.";
    case "INVALID_IMAGE":
      return "The label photo could not be read. Please choose a clear JPEG, PNG, or WEBP image.";
    case "VISION_PROVIDER_ERROR":
      return "The label checker is not available right now. Please try again.";
    default:
      return message || "Something went wrong while checking the label. Please try again.";
  }
}

function readableFieldError(fieldError) {
  const fieldName = fieldError.field ?? "request";
  const label = fieldLabel(fieldName);

  if (fieldName === "image") {
    switch (fieldError.code) {
      case "UNSUPPORTED_FILE_TYPE":
        return "Please choose a JPEG, PNG, or WEBP image.";
      case "FILE_TOO_LARGE":
        return fieldError.message || "Please choose a smaller label photo.";
      case "EMPTY_IMAGE":
        return "The label photo is empty. Please choose another photo.";
      case "INVALID_IMAGE":
        return "The label photo could not be read. Please choose another photo.";
      default:
        return "Please choose a label photo.";
    }
  }

  if (fieldError.code === "MISSING" || fieldError.code === "REQUIRED_FIELD") {
    return `Please fill in ${label}.`;
  }

  return fieldError.message || `Please check ${label}.`;
}
