"use client";
import { format } from "date-fns";
import type { Incident } from "@/lib/types";

export function RecordsView({ incidents }: { incidents: Incident[] }) {
  function exportCSV() {
    const headers = [
      "Incident ID",
      "Title",
      "Category",
      "Severity",
      "Priority Score",
      "Status",
      "Trust %",
      "Reports Count",
      "Location",
      "Last Updated",
    ];

    const rows = incidents.map((inc) => [
      inc.incident_id,
      `"${inc.title.replace(/"/g, '""')}"`,
      inc.event_category,
      inc.severity,
      inc.priority_score,
      inc.verification_summary?.verification_status ?? "UNVERIFIED",
      Math.round((inc.verification_summary?.overall_confidence ?? 0.8) * 100),
      inc.report_ids.length,
      `"${[inc.city, inc.state_name].filter(Boolean).join(", ")}"`,
      inc.last_updated_at,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `Weather_Intelligence_SITREP_${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function downloadJSON() {
    const dataStr =
      "data:text/json;charset=utf-8," +
      encodeURIComponent(JSON.stringify(incidents, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute(
      "download",
      `National_Weather_Intelligence_Records_${new Date().toISOString().slice(0, 10)}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }

  return (
    <div className="records-view-container">
      <div className="records-header">
        <div>
          <h2>Official Government SITREP & Records Management</h2>
          <p>Export situational reports, audit evidence provenance, and download incident records.</p>
        </div>
        <div className="records-actions">
          <button className="btn-export-csv" onClick={exportCSV}>
            Export SITREP (CSV)
          </button>
          <button className="btn-export-json" onClick={downloadJSON}>
            Backup DB (JSON)
          </button>
        </div>
      </div>

      <div className="records-table-wrapper">
        <table className="records-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Incident Title</th>
              <th>Category</th>
              <th>Severity</th>
              <th>Priority</th>
              <th>Trust %</th>
              <th>Reports</th>
              <th>Location</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => (
              <tr key={inc.incident_id}>
                <td className="font-mono text-xs">{inc.incident_id.slice(0, 14)}...</td>
                <td className="font-semibold">{inc.title}</td>
                <td>
                  <span className="record-category-tag">{inc.event_category}</span>
                </td>
                <td>
                  <span className={`badge badge--${inc.severity.toLowerCase()}`}>
                    {inc.severity}
                  </span>
                </td>
                <td className="font-bold text-purple-700">{(inc.priority_score ?? 0).toFixed(1)}</td>
                <td>
                  {Math.round(
                    (inc.verification_summary?.overall_confidence ?? 0.8) * 100
                  )}
                  %
                </td>
                <td>{inc.report_ids.length}</td>
                <td>{[inc.city, inc.state_name].filter(Boolean).join(", ") || "India"}</td>
                <td className="text-xs text-muted">
                  {format(new Date(inc.last_updated_at), "dd MMM HH:mm")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
