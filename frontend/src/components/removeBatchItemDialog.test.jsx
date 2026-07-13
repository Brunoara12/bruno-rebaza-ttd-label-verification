import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoveBatchItemDialog } from "./RemoveBatchItemDialog";

describe("RemoveBatchItemDialog", () => {
  it("focuses the safe action and supports Escape", () => {
    const onCancel = vi.fn();
    render(
      <RemoveBatchItemDialog
        item={{ clientId: "label-1", labelNumber: 1 }}
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Keep Label" })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
