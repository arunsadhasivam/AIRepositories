// src/components/ScoreCard.jsx
// Final scorecard shown after interview ends — summarises performance

export default function ScoreCard({ feedback, visionData }) {
  // Calculate overall performance message based on score
  function getPerformanceMessage(score) {
    if (score >= 8) return { msg: "Excellent! You are ready for the interview. 🎉", color: "#4ade80" };
    if (score >= 6) return { msg: "Good performance! A little more practice and you're set. 💪", color: "#facc15" };
    return { msg: "Keep practising. Focus on clarity and confidence. 📚", color: "#f87171" };
  }

  const score = feedback?.overallScore || 0;
  const { msg, color } = getPerformanceMessage(score);

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🏁 Interview Complete</h2>

      {/* Overall score circle */}
      <div style={styles.scoreCircle}>
        <p style={styles.scoreNumber}>{score}</p>
        <p style={styles.scoreLabel}>out of 10</p>
      </div>

      {/* Performance message */}
      <p style={{ ...styles.message, color }}>{msg}</p>

      {/* Breakdown table */}
      <div style={styles.breakdown}>
        <h3 style={styles.sectionTitle}>📋 Score Breakdown</h3>

        <Row label="Answer Relevance" value={`${feedback?.relevanceScore || 0}/10`} />
        <Row label="Answer Clarity" value={`${feedback?.clarityScore || 0}/10`} />
        <Row label="Confidence Level" value={`${feedback?.confidenceScore || 0}/10`} />
        <Row label="Filler Words Used" value={feedback?.fillerWords || 0} />
      </div>

      {/* Vision summary */}
      {visionData && (
        <div style={styles.breakdown}>
          <h3 style={styles.sectionTitle}>👁️ Body Language Summary</h3>
          <Row label="Eye Contact" value={visionData.eyeContact ? "✅ Good" : "❌ Needs work"} />
          <Row label="Posture" value={visionData.posture || "N/A"} />
          <Row label="Expression" value={visionData.expression || "N/A"} />
        </div>
      )}

      {/* Tips */}
      <div style={styles.tipsBox}>
        <h3 style={styles.sectionTitle}>💡 Key Tips</h3>
        <p style={styles.tip}>• {feedback?.improvement || "Practice speaking clearly and concisely."}</p>
        <p style={styles.tip}>• Maintain eye contact with the camera at all times.</p>
        <p style={styles.tip}>• Reduce filler words like "um", "uh", "like".</p>
        <p style={styles.tip}>• Sit straight — good posture projects confidence.</p>
      </div>

      {/* Restart button */}
      <button onClick={() => window.location.reload()} style={styles.restartBtn}>
        🔄 Practice Again
      </button>
    </div>
  );
}

// Reusable row component for breakdown table
function Row({ label, value }) {
  return (
    <div style={styles.row}>
      <span style={styles.rowLabel}>{label}</span>
      <span style={styles.rowValue}>{value}</span>
    </div>
  );
}

const styles = {
  container: { maxWidth: "600px", margin: "40px auto", padding: "32px", background: "#1e293b", borderRadius: "16px", color: "#fff", textAlign: "center" },
  title: { fontSize: "28px", marginBottom: "24px" },
  scoreCircle: { width: "120px", height: "120px", borderRadius: "50%", background: "#0f172a", border: "4px solid #6366f1", margin: "0 auto 20px", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" },
  scoreNumber: { margin: 0, fontSize: "36px", fontWeight: "bold", color: "#6366f1" },
  scoreLabel: { margin: 0, fontSize: "12px", color: "#94a3b8" },
  message: { fontSize: "16px", marginBottom: "24px", fontWeight: "500" },
  breakdown: { background: "#0f172a", borderRadius: "12px", padding: "16px", marginBottom: "16px", textAlign: "left" },
  sectionTitle: { margin: "0 0 12px 0", fontSize: "14px", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "1px" },
  row: { display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #1e293b" },
  rowLabel: { color: "#94a3b8", fontSize: "14px" },
  rowValue: { color: "#e2e8f0", fontSize: "14px", fontWeight: "500" },
  tipsBox: { background: "#0f172a", borderRadius: "12px", padding: "16px", marginBottom: "24px", textAlign: "left" },
  tip: { margin: "6px 0", fontSize: "14px", color: "#e2e8f0", lineHeight: "1.6" },
  restartBtn: { padding: "12px 32px", background: "#6366f1", color: "#fff", border: "none", borderRadius: "10px", cursor: "pointer", fontSize: "16px" },
};
