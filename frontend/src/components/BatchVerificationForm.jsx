import { useEffect, useState } from "react";

import { FIELD_DEFINITIONS, MAX_BATCH_ITEMS } from "../verification/constants";

export function BatchVerificationForm({
  items,
  itemErrors,
  isSubmitting,
  onAddItem,
  onRemoveItem,
  onFieldChange,
  onImageChange,
  onSubmit,
}) {
  return (
    <form id="batch-verification-form" className="verification-form" onSubmit={onSubmit} noValidate>
      <section className="form-section batch-intro" aria-labelledby="batch-heading">
        <h2 id="batch-heading">Batch Labels</h2>
        <p>{items.length} label{items.length === 1 ? "" : "s"} ready to check.</p>
      </section>

      <div className="batch-items">
        {items.map((item, index) => (
          <BatchItemFields
            key={item.clientId}
            item={item}
            index={index}
            errors={itemErrors[item.clientId] ?? {}}
            canRemove={items.length > 1}
            isSubmitting={isSubmitting}
            onRemoveItem={onRemoveItem}
            onFieldChange={onFieldChange}
            onImageChange={onImageChange}
          />
        ))}
      </div>

      <div className="batch-actions">
        <button
          className="secondary-action add-label-action"
          type="button"
          onClick={onAddItem}
          disabled={isSubmitting || items.length >= MAX_BATCH_ITEMS}
        >
          Add Label
        </button>
        <button className="primary-action" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Checking Batch..." : "Check Batch"}
        </button>
      </div>
    </form>
  );
}

function BatchItemFields({
  item,
  index,
  errors,
  canRemove,
  isSubmitting,
  onRemoveItem,
  onFieldChange,
  onImageChange,
}) {
  const imageInputId = `batch-${item.clientId}-image`;
  const imageErrorId = `${imageInputId}-error`;

  return (
    <section className="form-section batch-item" aria-labelledby={`batch-${item.clientId}-heading`}>
      <div className="batch-item-heading">
        <h2 id={`batch-${item.clientId}-heading`}>Label {index + 1}</h2>
        {canRemove && (
          <button
            className="remove-label-action"
            type="button"
            onClick={() => onRemoveItem(item.clientId)}
            disabled={isSubmitting}
          >
            Remove
          </button>
        )}
      </div>

      <div className="batch-image-field">
        <label className="file-picker" htmlFor={imageInputId}>
          <span className="file-picker-title">Choose Label Photo</span>
          <span className="file-picker-detail">
            {item.imageFile ? item.imageFile.name : "JPEG, PNG, or WEBP"}
          </span>
          <input
            id={imageInputId}
            name="image"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(event) => onImageChange(item.clientId, event)}
            disabled={isSubmitting}
            aria-describedby={errors.image ? imageErrorId : undefined}
          />
        </label>
        {errors.image && (
          <p className="field-error" id={imageErrorId}>
            {errors.image}
          </p>
        )}
        <BatchImagePreview file={item.imageFile} />
      </div>

      <div className="field-grid">
        {FIELD_DEFINITIONS.map((field) => {
          const inputId = `batch-${item.clientId}-${field.name}`;
          const errorId = `${inputId}-error`;
          const commonProps = {
            id: inputId,
            name: field.name,
            value: item.formValues[field.name],
            placeholder: field.placeholder,
            onChange: (event) => onFieldChange(item.clientId, event),
            disabled: isSubmitting,
            "aria-invalid": Boolean(errors[field.name]),
            "aria-describedby": errors[field.name] ? errorId : undefined,
          };

          return (
            <div key={field.name} className={field.multiline ? "field full-width" : "field"}>
              <label htmlFor={inputId}>{field.label}</label>
              {field.multiline ? (
                <textarea {...commonProps} rows="7" />
              ) : (
                <input {...commonProps} type="text" inputMode={field.inputMode} />
              )}
              {errors[field.name] && (
                <p className="field-error" id={errorId}>
                  {errors[field.name]}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function BatchImagePreview({ file }) {
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!file) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  if (!previewUrl) {
    return null;
  }

  return (
    <div className="image-preview batch-preview">
      <img src={previewUrl} alt="Selected label preview" />
    </div>
  );
}
