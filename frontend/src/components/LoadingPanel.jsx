export function LoadingPanel({ isSubmitting }) {
  if (!isSubmitting) {
    return null;
  }

  return (
    <div className="loading-panel" role="status" aria-live="polite">
      Checking the label... This usually takes a few seconds.
    </div>
  );
}
