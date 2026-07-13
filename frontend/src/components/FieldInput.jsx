export function FieldInput({ field, value, error, isSubmitting, onChange }) {
  const inputId = `field-${field.name}`;
  const errorId = `${inputId}-error`;
  const helpId = field.helpText ? `${inputId}-help` : undefined;
  const describedBy = [helpId, error ? errorId : undefined].filter(Boolean).join(" ") || undefined;
  const commonProps = {
    id: inputId,
    name: field.name,
    value,
    placeholder: field.placeholder,
    onChange,
    disabled: isSubmitting,
    "aria-invalid": Boolean(error),
    "aria-describedby": describedBy,
  };

  return (
    <div className={field.multiline ? "field full-width" : "field"}>
      <label htmlFor={inputId}>{field.label}</label>
      {field.helpText && (
        <p className="field-help" id={helpId}>
          {field.helpText}
        </p>
      )}
      {field.multiline ? (
        <textarea {...commonProps} rows="7" />
      ) : (
        <input
          {...commonProps}
          type={field.inputType ?? "text"}
          inputMode={field.inputMode}
          min={field.min}
          max={field.max}
          step={field.step}
        />
      )}
      {error && (
        <p className="field-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  );
}
