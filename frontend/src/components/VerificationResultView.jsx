import { displayValue, fieldLabel, plainReason, plainReviewSummary } from "../verification/formatters";

export function VerificationResultView({ result, onReset, resultRef }) {
  const failedResults = result.results.filter((fieldResult) => fieldResult.status === "FAIL");
  const isApproved = result.overall_verdict === "APPROVED";

  return (
    <section
      className={isApproved ? "results approved" : "results needs-review"}
      ref={resultRef}
      aria-labelledby="result-heading"
    >
      <div className="verdict-panel">
        <p className="eyebrow">Result</p>
        <h2 id="result-heading">{isApproved ? "APPROVED" : "NEEDS REVIEW"}</h2>
        <p>{isApproved ? "All fields match." : plainReviewSummary(failedResults)}</p>
        <p className="latency">Checked in {result.latency_ms} ms</p>
      </div>

      {!isApproved && failedResults.length > 0 && (
        <section className="failure-summary" aria-labelledby="failure-heading">
          <h3 id="failure-heading">Needs review</h3>
          <ul className="failure-list" aria-label="Fields that need review">
            {failedResults.map((fieldResult) => (
              <li key={fieldResult.field}>{fieldLabel(fieldResult.field)}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="field-results" aria-labelledby="all-fields-heading">
        <h3 id="all-fields-heading">All fields</h3>
        <div className="result-list">
          {result.results.map((fieldResult) => (
            <ResultRow key={fieldResult.field} fieldResult={fieldResult} />
          ))}
        </div>
      </section>

      <button className="secondary-action" type="button" onClick={onReset}>
        Check Another Label
      </button>
    </section>
  );
}

function ResultRow({ fieldResult }) {
  const isPass = fieldResult.status === "PASS";

  return (
    <article className="result-row">
      <div className="result-row-heading">
        <h4>{fieldLabel(fieldResult.field)}</h4>
        <span className={isPass ? "badge pass" : "badge fail"}>{isPass ? "PASS" : "FAIL"}</span>
      </div>
      {isPass ? (
        <p className="match-note">Found on label: {displayValue(fieldResult.found, "Not found")}</p>
      ) : (
        <>
          <p className="match-note">{plainReason(fieldResult)}</p>
          <dl>
            <div>
              <dt>Expected</dt>
              <dd>{displayValue(fieldResult.expected, "Not provided")}</dd>
            </div>
            <div>
              <dt>Found on label</dt>
              <dd>{displayValue(fieldResult.found, "Not found")}</dd>
            </div>
          </dl>
        </>
      )}
    </article>
  );
}
