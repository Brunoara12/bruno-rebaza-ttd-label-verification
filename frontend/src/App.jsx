import { useEffect, useRef, useState } from "react";

import { BatchResultView } from "./components/BatchResultView";
import { BatchVerificationForm } from "./components/BatchVerificationForm";
import { ErrorAlert } from "./components/ErrorAlert";
import { LoadingPanel } from "./components/LoadingPanel";
import { ProgressPanel } from "./components/ProgressPanel";
import { RemoveBatchItemDialog } from "./components/RemoveBatchItemDialog";
import { StickySubmitAction } from "./components/StickySubmitAction";
import { VerificationForm } from "./components/VerificationForm";
import { VerificationResultView } from "./components/VerificationResultView";
import { verifyBatch, verifyLabel } from "./verification/api";
import { BATCH_PROGRESS_DELAY_MS, INITIAL_FORM_VALUES } from "./verification/constants";
import {
  buildBatchVerificationFormData,
  buildVerificationFormData,
  focusFirstBatchError,
  focusFirstError,
  validateBatchItems,
  validateForm,
  withoutKey,
} from "./verification/form";

function createBatchItem() {
  return {
    clientId: `label-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    formValues: { ...INITIAL_FORM_VALUES },
    imageFile: null,
  };
}

export default function App() {
  const [activeView, setActiveView] = useState("single");
  const [formValues, setFormValues] = useState(INITIAL_FORM_VALUES);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [generalError, setGeneralError] = useState("");
  const [result, setResult] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [singleStartedAt, setSingleStartedAt] = useState(null);
  const [batchItems, setBatchItems] = useState(() => [createBatchItem()]);
  const [batchItemErrors, setBatchItemErrors] = useState({});
  const [batchRequestErrors, setBatchRequestErrors] = useState({});
  const [batchGeneralError, setBatchGeneralError] = useState("");
  const [batchResult, setBatchResult] = useState(null);
  const [isBatchSubmitting, setIsBatchSubmitting] = useState(false);
  const [showBatchProgress, setShowBatchProgress] = useState(false);
  const [batchStartedAt, setBatchStartedAt] = useState(null);
  const [pendingBatchRemoval, setPendingBatchRemoval] = useState(null);
  const fileInputRef = useRef(null);
  const resultRef = useRef(null);
  const removalTriggerRef = useRef(null);

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
    if ((activeView === "single" && result) || (activeView === "batch" && batchResult)) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      resultRef.current?.focus({ preventScroll: true });
    }
  }, [activeView, batchResult, result]);

  useEffect(() => {
    if (!isBatchSubmitting) {
      setShowBatchProgress(false);
      return undefined;
    }

    const timerId = window.setTimeout(() => {
      setShowBatchProgress(true);
    }, BATCH_PROGRESS_DELAY_MS);

    return () => window.clearTimeout(timerId);
  }, [isBatchSubmitting]);

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

    setSingleStartedAt(Date.now());
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
      setSingleStartedAt(null);
    }
  }

  function handleViewChange(nextView) {
    setActiveView(nextView);
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

  function handleBatchFieldChange(clientId, event) {
    const { name, value } = event.target;
    setBatchItems((currentItems) =>
      currentItems.map((item) =>
        item.clientId === clientId
          ? {
              ...item,
              formValues: { ...item.formValues, [name]: value },
            }
          : item,
      ),
    );
    setBatchItemErrors((currentErrors) => withoutBatchFieldError(currentErrors, clientId, name));
    setBatchGeneralError("");
    setBatchRequestErrors({});
    setBatchResult(null);
  }

  function handleBatchImageChange(clientId, event) {
    const selectedFile = event.target.files?.[0] ?? null;
    setBatchItems((currentItems) =>
      currentItems.map((item) =>
        item.clientId === clientId ? { ...item, imageFile: selectedFile } : item,
      ),
    );
    setBatchItemErrors((currentErrors) => withoutBatchFieldError(currentErrors, clientId, "image"));
    setBatchGeneralError("");
    setBatchRequestErrors({});
    setBatchResult(null);
  }

  function addBatchItem() {
    setBatchItems((currentItems) => [...currentItems, createBatchItem()]);
    setBatchGeneralError("");
    setBatchRequestErrors({});
    setBatchResult(null);
  }

  function removeBatchItem(clientId) {
    setBatchItems((currentItems) => currentItems.filter((item) => item.clientId !== clientId));
    setBatchItemErrors((currentErrors) => withoutKey(currentErrors, clientId));
    setBatchGeneralError("");
    setBatchRequestErrors({});
    setBatchResult(null);
  }

  function requestBatchItemRemoval(clientId, labelNumber, triggerElement) {
    const item = batchItems.find((currentItem) => currentItem.clientId === clientId);
    if (!item) {
      return;
    }

    if (!isBatchItemPopulated(item)) {
      removeBatchItem(clientId);
      return;
    }

    removalTriggerRef.current = triggerElement;
    setPendingBatchRemoval({ clientId, labelNumber });
  }

  function cancelBatchItemRemoval() {
    setPendingBatchRemoval(null);
    window.requestAnimationFrame(() => removalTriggerRef.current?.focus());
  }

  function confirmBatchItemRemoval() {
    if (!pendingBatchRemoval) {
      return;
    }

    removeBatchItem(pendingBatchRemoval.clientId);
    setPendingBatchRemoval(null);
  }

  async function handleBatchSubmit(event) {
    event.preventDefault();

    const validationErrors = validateBatchItems(batchItems);
    if (Object.keys(validationErrors).length > 0) {
      setBatchItemErrors(validationErrors);
      setBatchGeneralError("Please fix the highlighted items.");
      setBatchRequestErrors({});
      focusFirstBatchError(validationErrors);
      return;
    }

    setIsBatchSubmitting(true);
    setBatchStartedAt(Date.now());
    setBatchGeneralError("");
    setBatchRequestErrors({});
    setBatchItemErrors({});
    setBatchResult(null);

    try {
      const formData = buildBatchVerificationFormData(batchItems);
      setBatchResult(await verifyBatch(formData));
    } catch (error) {
      if (error?.message && error?.fields) {
        setBatchGeneralError(error.message);
        setBatchRequestErrors(error.fields);
      } else {
        setBatchGeneralError("The label checker is not available right now. Please try again.");
      }
    } finally {
      setIsBatchSubmitting(false);
      setBatchStartedAt(null);
    }
  }

  function resetBatch() {
    setBatchItems([createBatchItem()]);
    setBatchItemErrors({});
    setBatchRequestErrors({});
    setBatchGeneralError("");
    setBatchResult(null);
  }

  const isSingleView = activeView === "single";
  const currentSubmitting = isSingleView ? isSubmitting : isBatchSubmitting;
  const hasCurrentResult = isSingleView ? Boolean(result) : Boolean(batchResult);

  return (
    <main className="page-shell">
      <div className="app-frame">
        <header className="page-header">
          <p className="eyebrow">TTB Label Verification</p>
          <h1>{isSingleView ? "Check One Label" : "Check a Batch"}</h1>
        </header>

        <div className="view-switch" role="group" aria-label="Choose label check type">
          <button
            type="button"
            aria-pressed={isSingleView}
            className={isSingleView ? "active" : ""}
            onClick={() => handleViewChange("single")}
            disabled={currentSubmitting}
          >
            One Label
          </button>
          <button
            type="button"
            aria-pressed={!isSingleView}
            className={!isSingleView ? "active" : ""}
            onClick={() => handleViewChange("batch")}
            disabled={currentSubmitting}
          >
            Batch
          </button>
        </div>

        {isSingleView ? (
          <>
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

            <LoadingPanel isSubmitting={isSubmitting} startedAt={singleStartedAt} />

            {result && (
              <VerificationResultView result={result} onReset={resetForm} resultRef={resultRef} />
            )}
          </>
        ) : (
          <>
            <ErrorAlert generalError={batchGeneralError} fieldErrors={batchRequestErrors} />

            <BatchVerificationForm
              items={batchItems}
              itemErrors={batchItemErrors}
              isSubmitting={isBatchSubmitting}
              onAddItem={addBatchItem}
              onRemoveItem={requestBatchItemRemoval}
              onFieldChange={handleBatchFieldChange}
              onImageChange={handleBatchImageChange}
              onSubmit={handleBatchSubmit}
            />

            <ProgressPanel
              isVisible={showBatchProgress}
              labelCount={batchItems.length}
              startedAt={batchStartedAt}
            />

            {batchResult && (
              <BatchResultView result={batchResult} onReset={resetBatch} resultRef={resultRef} />
            )}
          </>
        )}
      </div>

      <RemoveBatchItemDialog
        item={pendingBatchRemoval}
        onCancel={cancelBatchItemRemoval}
        onConfirm={confirmBatchItemRemoval}
      />

      <StickySubmitAction
        isHidden={hasCurrentResult}
        isSubmitting={currentSubmitting}
        formId={isSingleView ? "verification-form" : "batch-verification-form"}
        label={isSingleView ? "Check Label" : "Check Batch"}
        loadingLabel={isSingleView ? "Checking..." : "Checking Batch..."}
      />
    </main>
  );
}

function isBatchItemPopulated(item) {
  return Boolean(item.imageFile) || Object.keys(INITIAL_FORM_VALUES).some(
    (fieldName) => item.formValues[fieldName] !== INITIAL_FORM_VALUES[fieldName],
  );
}

function withoutBatchFieldError(errorsByItem, clientId, fieldName) {
  const itemErrors = errorsByItem[clientId];
  if (!itemErrors) {
    return errorsByItem;
  }

  const nextItemErrors = withoutKey(itemErrors, fieldName);
  if (Object.keys(nextItemErrors).length === 0) {
    return withoutKey(errorsByItem, clientId);
  }

  return {
    ...errorsByItem,
    [clientId]: nextItemErrors,
  };
}
