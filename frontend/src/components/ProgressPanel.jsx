import { useEffect, useState } from "react";

import { COLD_START_GUIDANCE_DELAY_MS } from "../verification/constants";

export function ProgressPanel({ isVisible, labelCount, startedAt }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!isVisible || !startedAt) {
      setElapsedSeconds(0);
      return undefined;
    }

    const updateElapsed = () => {
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    };
    updateElapsed();
    const timerId = window.setInterval(updateElapsed, 500);
    return () => window.clearInterval(timerId);
  }, [isVisible, startedAt]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="loading-panel progress-panel" role="status" aria-live="polite">
      <p>Checking {labelCount} labels... This may take a few seconds.</p>
      <div className="progress-track" aria-hidden="true">
        <span />
      </div>
      <p className="progress-elapsed">{elapsedSeconds} seconds elapsed</p>
      {elapsedSeconds * 1000 >= COLD_START_GUIDANCE_DELAY_MS && (
        <p className="cold-start-guidance">
          The first request may take up to a minute while the server warms up. Please keep this page open.
        </p>
      )}
    </div>
  );
}
