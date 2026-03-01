// src/components/FeedbackPanel.jsx
// Displays Gemini's real-time feedback after each answer

export default function FeedbackPanel({ feedback }) {
  // Don't render if no feedback yet
  if (!feedback) return null;

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>📊 Gemini Feedback</h3>

      {/* Score grid — shows individual scores */}
      <div style={styles.scoreGrid}>
        <ScoreItem label="Relevance" score={feedback.relevanceScore} />
        <ScoreItem label="Clarity" score={feedback.clarityScore} />
        <ScoreItem label="Confidence" score={feedback.confidenceScore} />
        <ScoreItem label="Overall" score={feedback.overallScore} highlight />
      </div>

      {/* Filler words count */}
      <div style={styles.fillerBox}>
        <span>🗣️ Filler Words Detected: </span>
        <strong style={{ color: feedback.fillerWords > 3 ? "#f87171" : "#4ade80" }}>
          {feedback.fillerWords}
        </strong>
        {/* Red if more than 3 filler words, green otherwise */}
      </div>

      {/* Strengths */}
      <div style={styles.infoBox}>
        <p style={styles.label}>✅ Strengths</p>
        <p style={styles.text}>{feedback.strengths}</p>
      </div>

      {/* Improvement */}
      <div style={styles.infoBox}>
        <p style={styles.label}>💡 Improve</p>
        <p style={styles.text}>{feedback.improvement}</p>
      </div>
    </div>
  );
}

// Individual score item component
function ScoreItem({ label, score, highlight }) {
  // Determine color based on score range
  const color = score >= 7 ? "#4ade80" : score >= 4 ? "#facc15" : "#f87171";

  return (
    <div style={{ ...styles.scoreItem, border: highlight ? "2px solid #6366f1" : "1px solid #334155" }}>
      <p style={styles.scoreLabel}>{label}</p>
      <p style={{ ...styles.scoreValue, color }}>{score}/10</p>
    </div>
  );
}

const styles = {
  container: { background: "#1e293b", padding: "16px", borderRadius: "12px" },
  title: { margin: "0 0 12px 0", color: "#e2e8f0" },
  scoreGrid: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", marginBottom: "12px" },
  scoreItem: { background: "#0f172a", padding: "10px", borderRadius: "8px", textAlign: "center" },
  scoreLabel: { margin: "0 0 4px 0", fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" },
  scoreValue: { margin: 0, fontSize: "20px", fontWeight: "bold" },
  fillerBox: { background: "#0f172a", padding: "10px 14px", borderRadius: "8px", marginBottom: "10px", fontSize: "14px" },
  infoBox: { background: "#0f172a", padding: "12px", borderRadius: "8px", marginBottom: "8px" },
  label: { margin: "0 0 4px 0", fontSize: "12px", color: "#94a3b8", textTransform: "uppercase" },
  text: { margin: 0, fontSize: "14px", lineHeight: "1.6", color: "#e2e8f0" },
};
