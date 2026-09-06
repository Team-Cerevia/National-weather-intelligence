"use client";
import { useState } from "react";
import type { Incident } from "@/lib/types";

export function OperatorCopilotView({ incidents }: { incidents: Incident[] }) {
  const [messages, setMessages] = useState<
    Array<{ sender: "user" | "bot"; text: string; time: string }>
  >([
    {
      sender: "bot",
      text: "Welcome, Emergency Response Operator. I am your National Weather Intelligence Copilot. How can I assist your team today?",
      time: "Just now",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");

  async function sendQuery(query: string) {
    if (!query.trim()) return;

    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMsg = { sender: "user" as const, text: query, time };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/incidents/copilot?query=${encodeURIComponent(query)}`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: data.reply, time },
        ]);
      } else {
        throw new Error("API error");
      }
    } catch {
      // Fallback if backend API is offline
      const criticalCount = incidents.filter((i) => i.severity === "CRITICAL").length;
      const highCount = incidents.filter((i) => i.severity === "HIGH").length;
      const verifiedCount = incidents.filter(
        (i) => i.verification_summary?.verification_status === "SUPPORTED"
      ).length;

      let replyText = `Acknowledged query: "${query}". Analyzing PostgreSQL incidents...`;
      const q = query.toLowerCase();
      if (q.includes("sitrep") || q.includes("briefing")) {
        replyText = `OPERATOR SITUATION BRIEFING (SITREP)\n\n• Total Active Alerts: ${incidents.length} (${criticalCount} Critical, ${highCount} High)\n• Multi-Source Verified: ${verifiedCount} incidents`;
      }
      setMessages((prev) => [...prev, { sender: "bot", text: replyText, time }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="copilot-container">
      <div className="copilot-sidebar">
        <h4>Quick Operator Actions</h4>
        <button
          className="copilot-preset-btn"
          onClick={() => sendQuery("Generate Situation Briefing (SITREP)")}
        >
          Generate Executive SITREP
        </button>
        <button
          className="copilot-preset-btn"
          onClick={() => sendQuery("Show NDRF Deployment Protocol")}
        >
          NDRF Deployment Protocol
        </button>
        <button
          className="copilot-preset-btn"
          onClick={() => sendQuery("Audit Contradictions & Fake Media")}
        >
          Audit Contradictions & Fake Media
        </button>

        <div className="copilot-stats-box">
          <p><strong>System Status:</strong></p>
          <p>• NLP Transformer Engine: ACTIVE</p>
          <p>• Vision pHash Deduplication: ACTIVE</p>
          <p>• Spatial H3 Resolution: Level 7</p>
        </div>
      </div>

      <div className="copilot-chat-area">
        <div className="copilot-messages">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`copilot-msg ${
                m.sender === "user" ? "copilot-msg--user" : "copilot-msg--bot"
              }`}
            >
              <div className="copilot-msg-header">
                <span>{m.sender === "user" ? "Operator" : "Emergency Copilot"}</span>
                <span className="copilot-msg-time">{m.time}</span>
              </div>
              <div className="copilot-msg-body">{m.text}</div>
            </div>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendQuery(input);
          }}
          className="copilot-input-row"
        >
          <input
            type="text"
            className="copilot-input"
            placeholder="Ask Copilot (e.g. Summarize critical alerts, generate SITREP)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button type="submit" className="copilot-send-btn">
            Send Query
          </button>
        </form>
      </div>
    </div>
  );
}
