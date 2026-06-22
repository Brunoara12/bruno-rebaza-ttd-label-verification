export function FieldInput({ field, value, error, isSubmitting, onChange }) {
  const inputId = `field-${field.name}`;
  const errorId = `${inputId}-error`;
  const commonProps = {
    id: inputId,
    name: field.name,
    value,
    placeholder: field.placeholder,
    onChange,
    disabled: isSubmitting,
    "aria-invalid": Boolean(error),
    "aria-describedby": error ? errorId : undefined,
  };

  return (
    <div className={field.multiline ? "field full-width" : "field"}>
      <label htmlFor={inputId}>{field.label}</label>
      {field.multiline ? (
        <textarea {...commonProps} rows="7" />
      ) : (
        <input {...commonProps} type="text" inputMode={field.inputMode} />
      )}
      {error && (
        <p className="field-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}
