import { format } from "date-fns";
import type { VerificationSummary } from "@/lib/types";

const REL_CONFIG = {
  SUPPORTING: { label: "Supporting", dot: "dot-supporting" },
  CORROBORATING: { label: "Corroborating", dot: "dot-supporting" },
  CONTRADICTING: { label: "Contradicting", dot: "dot-contradicting" },
  NEUTRAL: { label: "Neutral", dot: "dot-neutral" },
};

export function EvidencePanel({
  summary,
}: {
  summary: VerificationSummary;
}) {
  const { evidence_items, explanation, supporting_count, contradicting_count } =
    summary;

  return (
    <div className="evidence-panel">
      <div className="evidence-summary-box">
        <p className="evidence-explanation">{explanation}</p>
        <div className="evidence-counts">
          <span className="evidence-count evidence-count--supporting">
            ✓ {supporting_count} supporting
          </span>
          <span className="evidence-count evidence-count--contradicting">
            ✗ {contradicting_count} contradicting
          </span>
        </div>
      </div>

      {evidence_items.length === 0 ? (
        <p className="detail-empty-sub">No evidence items recorded.</p>
      ) : (
        <ul className="evidence-list">
          {evidence_items.map((ev) => {
            const rel =
              REL_CONFIG[ev.relationship] ?? REL_CONFIG.NEUTRAL;
            const confidence = ev.confidence_score;

            return (
              <li key={ev.evidence_id} className="evidence-item">
                <div className="evidence-item-header">
                  <span className={`evidence-dot ${rel.dot}`} />
                  <span className="evidence-source">{ev.source}</span>
                  <span className="evidence-source-type">{ev.source_type}</span>
                  <span className={`badge evidence-rel-badge`}>{rel.label}</span>
                  {confidence !== null && confidence !== undefined && (
                    <span className="evidence-confidence">
                      {Math.round(confidence * 100)}%
                    </span>
                  )}
                  <time className="evidence-time">
                    {format(new Date(ev.timestamp), "dd MMM HH:mm")}
                  </time>
                </div>
                <p className="evidence-reasoning">{ev.reasoning}</p>
                {ev.extracted_location && (
                  <p className="evidence-loc">Location: {ev.extracted_location}</p>
                )}
                {ev.media_proof_urls.length > 0 && (
                  <div className="evidence-media">
                    <div className="evidence-media-grid">
                      {ev.media_proof_urls.map((url, i) => (
                        <div key={i} className="evidence-media-item">
                          {/\.(png|jpe?g|webp|gif)($|\?)/i.test(url) ? (
                            <img
                              src={url}
                              alt={`Evidence photo ${i + 1}`}
                              className="evidence-thumbnail"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = "none";
                              }}
                            />
                          ) : null}
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="evidence-media-link"
                          >
                            Source Media {i + 1}
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
