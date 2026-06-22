import { FIELD_DEFINITIONS } from "../verification/constants";
import { FieldInput } from "./FieldInput";
import { ImagePicker } from "./ImagePicker";

export function VerificationForm({
  formValues,
  imageFile,
  imagePreviewUrl,
  fieldErrors,
  isSubmitting,
  fileInputRef,
  onFieldChange,
  onImageChange,
  onSubmit,
}) {
  return (
    <form
      id="verification-form"
      className="verification-form"
      onSubmit={onSubmit}
      noValidate
      aria-busy={isSubmitting}
    >
      <ImagePicker
        imageFile={imageFile}
        imagePreviewUrl={imagePreviewUrl}
        imageError={fieldErrors.image}
        isSubmitting={isSubmitting}
        fileInputRef={fileInputRef}
        onImageChange={onImageChange}
      />

      <section className="form-section" aria-labelledby="expected-heading">
        <h2 id="expected-heading">Expected Label Information</h2>
        <div className="field-grid">
          {FIELD_DEFINITIONS.map((field) => (
            <FieldInput
              key={field.name}
              field={field}
              value={formValues[field.name]}
              error={fieldErrors[field.name]}
              isSubmitting={isSubmitting}
              onChange={onFieldChange}
            />
          ))}
        </div>
      </section>

      <button className="primary-action" type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Checking..." : "Check Label"}
      </button>
    </form>
  );
}
