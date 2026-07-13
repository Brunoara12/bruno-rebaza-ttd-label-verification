import { useEffect, useState } from "react";

import { COLD_START_GUIDANCE_DELAY_MS } from "../verification/constants";

export function LoadingPanel({ isSubmitting, startedAt }) {
  const [showColdStartGuidance, setShowColdStartGuidance] = useState(false);

  useEffect(() => {
    if (!isSubmitting || !startedAt) {
      setShowColdStartGuidance(false);
      return undefined;
    }

    const remainingDelay = Math.max(
      0,
      COLD_START_GUIDANCE_DELAY_MS - (Date.now() - startedAt),
    );
    const timerId = window.setTimeout(() => setShowColdStartGuidance(true), remainingDelay);

    return () => window.clearTimeout(timerId);
  }, [isSubmitting, startedAt]);

  if (!isSubmitting) {
    return null;
  }

  return (
    <div className="loading-panel" role="status" aria-live="polite">
      <p>Checking the label... This usually takes a few seconds.</p>
      {showColdStartGuidance && (
        <p className="cold-start-guidance">
          The first request may take up to a minute while the server warms up. Please keep this page open.
        </p>
      )}
    </div>
  );
}
