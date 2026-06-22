export function StickySubmitAction({ isHidden, isSubmitting }) {
  if (isHidden) {
    return null;
  }

  return (
    <div className="sticky-action">
      <button type="submit" form="verification-form" disabled={isSubmitting}>
        {isSubmitting ? "Checking..." : "Check Label"}
      </button>
    </div>
  );
}
