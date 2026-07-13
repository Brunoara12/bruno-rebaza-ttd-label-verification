import { render, screen } from "@testing-library/react";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoadingPanel } from "./LoadingPanel";
import { ProgressPanel } from "./ProgressPanel";

describe("cold-start guidance", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("appears for a single label only after five seconds", () => {
    vi.useFakeTimers();
    const startedAt = Date.now();
    render(<LoadingPanel isSubmitting startedAt={startedAt} />);

    expect(screen.queryByText(/first request may take/i)).not.toBeInTheDocument();
    act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByText(/first request may take/i)).toBeVisible();
  });

  it("appears for batch progress after five seconds", () => {
    vi.useFakeTimers();
    const startedAt = Date.now();
    render(<ProgressPanel isVisible labelCount={2} startedAt={startedAt} />);

    act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByText(/first request may take/i)).toBeVisible();
  });
});
