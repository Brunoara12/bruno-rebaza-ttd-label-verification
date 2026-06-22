export const DEPLOYED_API_BASE_URL = "https://bruno-rebaza-ttd-label-verification.onrender.com";

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? DEPLOYED_API_BASE_URL
).replace(/\/$/, "");

export const CANONICAL_GOVERNMENT_WARNING =
  "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS. (2) CONSUMPTION OF ALCOHOLIC BEVERAGES IMPAIRS YOUR ABILITY TO DRIVE A CAR OR OPERATE MACHINERY, AND MAY CAUSE HEALTH PROBLEMS.";

export const ACCEPTED_IMAGE_TYPES = new Set([
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
]);

export const BATCH_PROGRESS_DELAY_MS = 700;
export const MAX_BATCH_ITEMS = 10;
export const MAX_UPLOAD_BYTES = 10485760;
export const MAX_UPLOAD_MB = 10;

export const FIELD_DEFINITIONS = [
  {
    name: "brand_name",
    label: "Brand Name",
    placeholder: "Example: Acme Reserve",
    inputMode: "text",
  },
  {
    name: "class_type",
    label: "Type of Product",
    placeholder: "Example: Straight Bourbon Whiskey",
    inputMode: "text",
  },
  {
    name: "abv",
    label: "Alcohol %",
    placeholder: "Example: 45%",
    inputMode: "decimal",
  },
  {
    name: "net_contents",
    label: "Bottle Size",
    placeholder: "Example: 750 mL",
    inputMode: "text",
  },
  {
    name: "producer",
    label: "Producer",
    placeholder: "Example: Acme Distilling Co.",
    inputMode: "text",
  },
  {
    name: "country_of_origin",
    label: "Country",
    placeholder: "Example: United States",
    inputMode: "text",
  },
  {
    name: "government_warning",
    label: "Government Warning",
    placeholder: "Paste the full warning text",
    multiline: true,
  },
];

export const FIELD_LABELS = FIELD_DEFINITIONS.reduce((labels, field) => {
  labels[field.name] = field.label;
  return labels;
}, {});

export const INITIAL_FORM_VALUES = FIELD_DEFINITIONS.reduce((values, field) => {
  values[field.name] =
    field.name === "government_warning" ? CANONICAL_GOVERNMENT_WARNING : "";
  return values;
}, {});
