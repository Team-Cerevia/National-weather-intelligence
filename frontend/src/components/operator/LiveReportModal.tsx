"use client";
import { useState } from "react";

interface LiveReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function LiveReportModal({
  isOpen,
  onClose,
  onSuccess,
}: LiveReportModalProps) {
  const [city, setCity] = useState("");
  const [stateName, setStateName] = useState("");
  const [category, setCategory] = useState("WATERLOGGING");
  const [severity, setSeverity] = useState("HIGH");
  const [text, setText] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || !city.trim()) return;

    setIsSubmitting(true);
    try {
      const payload = {
        source: "field_operator",
        source_type: "citizen_app",
        source_id: `op_${Date.now()}`,
        timestamp: new Date().toISOString(),
        text: text.trim(),
        city: city.trim(),
        state: stateName.trim() || undefined,
        media_urls: mediaUrl.trim() ? [mediaUrl.trim()] : [],
        country: "India",
      };

      const res = await fetch("http://localhost:8000/api/v1/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        onSuccess();
        onClose();
        setText("");
        setCity("");
        setMediaUrl("");
      }
    } catch (err) {
      console.error("Failed to submit field report", err);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>➕ Report Ground Incident (Operator Entry)</h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-group">
            <label>Location City / District *</label>
            <input
              type="text"
              required
              placeholder="e.g. Mumbai / Dadar West"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Event Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="WATERLOGGING">Waterlogging</option>
                <option value="FLOOD">Flood</option>
                <option value="RAIN">Heavy Rain</option>
                <option value="THUNDERSTORM">Thunderstorm</option>
                <option value="CYCLONE">Cyclone Alert</option>
                <option value="HEATWAVE">Heatwave</option>
              </select>
            </div>

            <div className="form-group">
              <label>Initial Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                <option value="LOW">Low</option>
                <option value="MODERATE">Moderate</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Field Report Description *</label>
            <textarea
              required
              rows={3}
              placeholder="Describe ground situation (e.g., 3 feet waterlogging near railway station, traffic diverted by police)..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Ground Photo / Video Proof URL (Optional)</label>
            <input
              type="url"
              placeholder="https://..."
              value={mediaUrl}
              onChange={(e) => setMediaUrl(e.target.value)}
            />
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary"
            >
              {isSubmitting ? "Processing NLP & Pipeline..." : "Broadcast Incident Live"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
