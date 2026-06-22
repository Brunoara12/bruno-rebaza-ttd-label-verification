export function ImagePicker({
  imageFile,
  imagePreviewUrl,
  imageError,
  isSubmitting,
  fileInputRef,
  onImageChange,
}) {
  return (
    <section className="form-section image-section" aria-labelledby="image-heading">
      <h2 id="image-heading">Label Photo</h2>
      <label className="file-picker" htmlFor="image">
        <span className="file-picker-title">Choose Label Photo</span>
        <span className="file-picker-detail">
          {imageFile ? imageFile.name : "JPEG, PNG, or WEBP"}
        </span>
        <input
          ref={fileInputRef}
          id="image"
          name="image"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={onImageChange}
          disabled={isSubmitting}
          aria-invalid={Boolean(imageError)}
          aria-describedby={imageError ? "image-error" : undefined}
        />
      </label>
      {imageError && (
        <p className="field-error" id="image-error">
          {imageError}
        </p>
      )}
      {imagePreviewUrl && (
        <div className="image-preview">
          <img src={imagePreviewUrl} alt="Selected label preview" />
        </div>
      )}
    </section>
  );
}
