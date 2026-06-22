export function StickySubmitAction({
  isHidden,
  isSubmitting,
  formId = "verification-form",
  label = "Check Label",
  loadingLabel = "Checking...",
}) {
  if (isHidden) {
    return null;
  }

  return (
    <div className="sticky-action">
      <button type="submit" form={formId} disabled={isSubmitting}>
        {isSubmitting ? loadingLabel : label}
      </button>
    </div>
  );
}
