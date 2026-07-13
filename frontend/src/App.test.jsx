import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("batch item removal", () => {
  it("removes empty items immediately and confirms populated items", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Batch" }));
    await user.click(screen.getByRole("button", { name: "Add Label" }));
    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryAllByRole("button", { name: "Remove" })).toHaveLength(0);

    await user.type(screen.getByLabelText("Brand Name"), "Acme");
    await user.click(screen.getByRole("button", { name: "Add Label" }));
    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);

    expect(screen.getByRole("dialog")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Keep Label" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(2);

    await user.click(screen.getAllByRole("button", { name: "Remove" })[0]);
    await user.click(screen.getByRole("button", { name: "Remove Label" }));
    expect(screen.queryAllByRole("button", { name: "Remove" })).toHaveLength(0);
  });
});
