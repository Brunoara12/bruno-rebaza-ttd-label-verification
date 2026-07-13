import { describe, expect, it } from "vitest";

import { INITIAL_FORM_VALUES } from "./constants";
import { isValidAbv, isValidNetContents, validateForm } from "./form";

describe("ABV validation", () => {
  it.each(["0", "45", "45.5", "100"])('accepts "%s"', (value) => {
    expect(isValidAbv(value)).toBe(true);
  });

  it.each(["-0.1", "45.55", "100.1", "forty five"])('rejects "%s"', (value) => {
    expect(isValidAbv(value)).toBe(false);
  });
});

describe("net contents validation", () => {
  it.each(["750 mL", "0.75 L", "75 cL", "25.4 fl oz", "12 ounces"])('accepts "%s"', (value) => {
    expect(isValidNetContents(value)).toBe(true);
  });

  it.each(["0 mL", "-750 mL", "750", "750 grams", "size: 750 mL"])('rejects "%s"', (value) => {
    expect(isValidNetContents(value)).toBe(false);
  });
});

it("leaves image MIME validation to the backend", () => {
  const errors = validateForm(
    { name: "label.gif", size: 1024, type: "image/gif" },
    { ...INITIAL_FORM_VALUES, abv: "45", net_contents: "750 mL" },
  );

  expect(errors.image).toBeUndefined();
});
