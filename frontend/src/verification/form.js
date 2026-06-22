import { ACCEPTED_IMAGE_TYPES, FIELD_DEFINITIONS } from "./constants";

export function buildVerificationFormData(imageFile, formValues) {
  const formData = new FormData();
  formData.append("image", imageFile);
  FIELD_DEFINITIONS.forEach((field) => {
    formData.append(field.name, formValues[field.name].trim());
  });
  return formData;
}

export function validateForm(imageFile, formValues) {
  const errors = {};

  if (!imageFile) {
    errors.image = "Please choose a label photo.";
  } else if (!ACCEPTED_IMAGE_TYPES.has(imageFile.type)) {
    errors.image = "Please choose a JPEG, PNG, or WEBP image.";
  }

  FIELD_DEFINITIONS.forEach((field) => {
    if (!formValues[field.name].trim()) {
      errors[field.name] = `Please fill in ${field.label}.`;
    }
  });

  return errors;
}

export function focusFirstError(errors) {
  const firstFieldName = Object.keys(errors)[0];
  if (!firstFieldName) {
    return;
  }

  window.requestAnimationFrame(() => {
    const elementId = firstFieldName === "image" ? "image" : `field-${firstFieldName}`;
    document.getElementById(elementId)?.focus();
  });
}

export function withoutKey(objectValue, keyToRemove) {
  const { [keyToRemove]: _removed, ...remaining } = objectValue;
  return remaining;
}
