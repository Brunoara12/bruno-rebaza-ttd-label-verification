import { useEffect, useState } from "react";

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
    </div>
  );
}
