import { useEffect, useRef } from "react";

export function RemoveBatchItemDialog({ item, onCancel, onConfirm }) {
  const cancelButtonRef = useRef(null);
  const confirmButtonRef = useRef(null);

  useEffect(() => {
    if (!item) {
      return undefined;
    }

    cancelButtonRef.current?.focus();
    return undefined;
  }, [item]);

  if (!item) {
    return null;
  }

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const firstButton = cancelButtonRef.current;
    const lastButton = confirmButtonRef.current;
    if (event.shiftKey && document.activeElement === firstButton) {
      event.preventDefault();
      lastButton?.focus();
    } else if (!event.shiftKey && document.activeElement === lastButton) {
      event.preventDefault();
      firstButton?.focus();
    }
  }

  return (
    <div className="confirmation-backdrop" role="presentation">
      <section
        className="confirmation-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-label-dialog-title"
        aria-describedby="remove-label-dialog-description"
        onKeyDown={handleKeyDown}
      >
        <h2 id="remove-label-dialog-title">Remove Label {item.labelNumber}?</h2>
        <p id="remove-label-dialog-description">
          This label has a photo or entered details. Removing it will discard that information.
        </p>
        <div className="confirmation-actions">
          <button ref={cancelButtonRef} className="secondary-action" type="button" onClick={onCancel}>
            Keep Label
          </button>
          <button ref={confirmButtonRef} className="remove-label-action" type="button" onClick={onConfirm}>
            Remove Label
          </button>
        </div>
      </section>
    </div>
  );
}
