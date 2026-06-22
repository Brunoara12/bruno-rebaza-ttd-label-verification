import { API_BASE_URL } from "./constants";
import { readableApiError } from "./errors";

export async function verifyLabel(formData) {
  const response = await fetch(`${API_BASE_URL}/verify`, {
    method: "POST",
    body: formData,
  });
  const payload = await readJsonSafely(response);

  if (!response.ok) {
    throw readableApiError(payload);
  }

  return payload;
}

async function readJsonSafely(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}
