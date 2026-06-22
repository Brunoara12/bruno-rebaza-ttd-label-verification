export function ErrorAlert({ generalError, fieldErrors }) {
  if (!generalError) {
    return null;
  }

  return (
    <div className="alert error-alert" role="alert" aria-live="assertive">
      <strong>{generalError}</strong>
      {Object.keys(fieldErrors).length > 0 && (
        <ul>
          {Object.entries(fieldErrors).map(([fieldName, message]) => (
            <li key={fieldName}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
