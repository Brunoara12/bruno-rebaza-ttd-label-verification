import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VerificationForm } from "./VerificationForm";
import { INITIAL_FORM_VALUES } from "../verification/constants";

describe("VerificationForm", () => {
  it("shows exact-match guidance and configures ABV as a constrained number", () => {
    render(
      <VerificationForm
        formValues={{ ...INITIAL_FORM_VALUES, abv: "45", net_contents: "750 mL" }}
        imageFile={null}
        imagePreviewUrl=""
        fieldErrors={{}}
        isSubmitting={false}
        fileInputRef={{ current: null }}
        onFieldChange={vi.fn()}
        onImageChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    const abv = screen.getByLabelText("Alcohol %");
    expect(abv).toHaveAttribute("type", "number");
    expect(abv).toHaveAttribute("min", "0");
    expect(abv).toHaveAttribute("max", "100");
    expect(abv).toHaveAttribute("step", "0.1");
    expect(screen.getByText("This field must match exactly, including punctuation and spacing.")).toBeVisible();
    expect(document.getElementById("image")).toHaveAttribute("accept", "image/*");
  });
});
