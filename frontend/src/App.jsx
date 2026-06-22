import { useEffect, useRef, useState } from "react";

import { ErrorAlert } from "./components/ErrorAlert";
import { LoadingPanel } from "./components/LoadingPanel";
import { StickySubmitAction } from "./components/StickySubmitAction";
import { VerificationForm } from "./components/VerificationForm";
import { VerificationResultView } from "./components/VerificationResultView";
import { verifyLabel } from "./verification/api";
import { INITIAL_FORM_VALUES } from "./verification/constants";
import {
  buildVerificationFormData,
  focusFirstError,
  validateForm,
  withoutKey,
} from "./verification/form";

export default function App() {
  const [formValues, setFormValues] = useState(INITIAL_FORM_VALUES);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [generalError, setGeneralError] = useState("");
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef(null);
  const resultRef = useRef(null);

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl("");
      return undefined;
    }

    const previewUrl = URL.createObjectURL(imageFile);
    setImagePreviewUrl(previewUrl);

    return () => URL.revokeObjectURL(previewUrl);
  }, [imageFile]);

  useEffect(() => {
    if (result) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  function handleFieldChange(event) {
    const { name, value } = event.target;
    setFormValues((currentValues) => ({ ...currentValues, [name]: value }));
    setFieldErrors((currentErrors) => withoutKey(currentErrors, name));
    setGeneralError("");
    setResult(null);
  }

  function handleImageChange(event) {
    const selectedFile = event.target.files?.[0] ?? null;
    setImageFile(selectedFile);
    setFieldErrors((currentErrors) => withoutKey(currentErrors, "image"));
    setGeneralError("");
    setResult(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const validationErrors = validateForm(imageFile, formValues);
    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      setGeneralError("Please fix the highlighted items.");
      focusFirstError(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setGeneralError("");
    setFieldErrors({});
    setResult(null);

    try {
      const formData = buildVerificationFormData(imageFile, formValues);
      setResult(await verifyLabel(formData));
    } catch (error) {
      if (error?.message && error?.fields) {
        setGeneralError(error.message);
        setFieldErrors(error.fields);
        focusFirstError(error.fields);
      } else {
        setGeneralError("The label checker is not available right now. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetForm() {
    setFormValues(INITIAL_FORM_VALUES);
    setImageFile(null);
    setImagePreviewUrl("");
    setFieldErrors({});
    setGeneralError("");
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.focus();
    }
  }

  return (
    <main className="page-shell">
      <div className="app-frame">
        <header className="page-header">
          <p className="eyebrow">TTB Label Verification</p>
          <h1>Check One Label</h1>
        </header>

        <ErrorAlert generalError={generalError} fieldErrors={fieldErrors} />

        <VerificationForm
          formValues={formValues}
          imageFile={imageFile}
          imagePreviewUrl={imagePreviewUrl}
          fieldErrors={fieldErrors}
          isSubmitting={isSubmitting}
          fileInputRef={fileInputRef}
          onFieldChange={handleFieldChange}
          onImageChange={handleImageChange}
          onSubmit={handleSubmit}
        />

        <LoadingPanel isSubmitting={isSubmitting} />

        {result && (
          <VerificationResultView result={result} onReset={resetForm} resultRef={resultRef} />
        )}
      </div>

      <StickySubmitAction isHidden={Boolean(result)} isSubmitting={isSubmitting} />
    </main>
  );
}
