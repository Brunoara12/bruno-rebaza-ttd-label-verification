import { fieldLabel, plainReviewSummary } from "../verification/formatters";
import { ResultRow } from "./VerificationResultView";

export function BatchResultView({ result, onReset, resultRef }) {
  return (
    <section
      className="batch-results"
      ref={resultRef}
      aria-labelledby="batch-result-heading"
      tabIndex="-1"
    >
      <div className="batch-summary">
        <div>
          <p className="eyebrow">Batch Result</p>
          <h2 id="batch-result-heading">Summary</h2>
        </div>
        <div className="summary-counts" aria-label="Batch summary counts">
          <SummaryCount label="Passed" value={result.summary.passed} />
          <SummaryCount label="Needs Review" value={result.summary.needs_review} />
          <SummaryCount label="Total" value={result.summary.total} />
        </div>
        <p className="latency">Checked in {result.latency_ms} ms</p>
      </div>

      <div className="batch-result-list">
        {result.items.map((item) => (
          <BatchResultItem key={item.client_id} item={item} />
        ))}
      </div>

      <button className="secondary-action" type="button" onClick={onReset}>
        Check Another Batch
      </button>
    </section>
  );
}

function SummaryCount({ label, value }) {
  return (
    <div className="summary-count">
      <span>{value}</span>
      <strong>{label}</strong>
    </div>
  );
}

function BatchResultItem({ item }) {
  const result = item.result;
  const failedResults = result?.results.filter((fieldResult) => fieldResult.status === "FAIL") ?? [];
  const isApproved = result?.overall_verdict === "APPROVED";
  const needsReview = !isApproved;
  const title = item.filename || `Label ${item.index + 1}`;

  return (
    <details className={needsReview ? "batch-result-item needs-review" : "batch-result-item approved"}>
      <summary>
        <span className="batch-result-title">{title}</span>
        <span className={isApproved ? "badge pass" : "badge fail"}>
          {isApproved ? "APPROVED" : "NEEDS REVIEW"}
        </span>
        <span className="batch-result-note">{result ? itemSummary(result, failedResults) : errorSummary(item)}</span>
      </summary>

      {result ? (
        <div className="batch-result-detail">
          {failedResults.length > 0 && (
            <ul className="failure-list compact" aria-label="Fields that need review">
              {failedResults.map((fieldResult) => (
                <li key={fieldResult.field}>{fieldLabel(fieldResult.field)}</li>
              ))}
            </ul>
          )}
          <div className="result-list">
            {result.results.map((fieldResult) => (
              <ResultRow key={fieldResult.field} fieldResult={fieldResult} />
            ))}
          </div>
        </div>
      ) : (
        <div className="batch-result-detail batch-error-detail">
          <p>{item.error?.message || "This label needs review."}</p>
          {item.error?.fields?.length > 0 && (
            <ul>
              {item.error.fields.map((fieldError) => (
                <li key={`${fieldError.field}-${fieldError.code}`}>{fieldError.message}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </details>
  );
}

function itemSummary(result, failedResults) {
  if (result.overall_verdict === "APPROVED") {
    return `All fields match. Checked in ${result.latency_ms} ms.`;
  }

  return `${plainReviewSummary(failedResults)} Checked in ${result.latency_ms} ms.`;
}

function errorSummary(item) {
  return item.error?.message || "This label could not be checked.";
}
