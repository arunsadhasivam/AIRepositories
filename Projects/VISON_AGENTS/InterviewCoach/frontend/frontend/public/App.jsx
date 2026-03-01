// src/App.jsx
// Entry point — role selection screen before interview starts

import { useState } from "react";
import InterviewRoom from "./components/InterviewRoom";

export default function App() {
  const [role, setRole] = useState("");            // selected job role
  const [started, setStarted] = useState(false);  // has interview started

  // Show InterviewRoom once user clicks Start
  if (started) {
    return <InterviewRoom role={role} />;
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>

        {/* Header */}
        <h1 style={styles.title}>🎯 AI Interview Coach</h1>
        <p style={styles.subtitle}>
          Powered by Vision Agents + Gemini + YOLO
        </p>

        {/* Role input */}
        <label style={styles.label}>Select Job Role</label>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={styles.select}
        >
          <option value="">-- Select Role --</option>
          <option value="Software Engineer">Software Engineer</option>
          <option value="Data Scientist">Data Scientist</option>
          <option value="Product Manager">Product Manager</option>
          <option value="DevOps Engineer">DevOps Engineer</option>
          <option value="Java Developer">Java Developer</option>
          <option value="Frontend Developer">Frontend Developer</option>
        </select>

        {/* Feature list */}
        <div style={styles.features}>
          <p style={styles.feature}>📷 Real-time eye contact & posture detection</p>
          <p style={styles.feature}>🎤 Speech-to-text answer capture</p>
          <p style={styles.feature}>🤖 Gemini AI answer analysis</p>
          <p style={styles.feature}>📊 Instant feedback & scoring</p>
        </div>

        {/* Start button */}
        <button
          onClick={() => role && setStarted(true)}  // only start if role is selected
          style={{ ...styles.btn, opacity: role ? 1 : 0.5 }}
          disabled={!role}
        >
          🚀 Start Interview
        </button>

        {!role && (
          <p style={styles.hint}>Please select a job role to continue</p>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: "100vh", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" },
  card: { background: "#1e293b", padding: "40px", borderRadius: "16px", width: "420px", textAlign: "center", boxShadow: "0 25px 50px rgba(0,0,0,0.5)" },
  title: { color: "#e2e8f0", fontSize: "28px", margin: "0 0 8px 0" },
  subtitle: { color: "#64748b", fontSize: "14px", marginBottom: "32px" },
  label: { display: "block", textAlign: "left", color: "#94a3b8", fontSize: "13px", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "1px" },
  select: { width: "100%", padding: "12px", background: "#0f172a", color: "#e2e8f0", border: "1px solid #334155", borderRadius: "8px", fontSize: "15px", marginBottom: "24px", cursor: "pointer" },
  features: { background: "#0f172a", borderRadius: "10px", padding: "16px", marginBottom: "24px", textAlign: "left" },
  feature: { margin: "8px 0", fontSize: "14px", color: "#94a3b8" },
  btn: { width: "100%", padding: "14px", background: "#6366f1", color: "#fff", border: "none", borderRadius: "10px", fontSize: "16px", cursor: "pointer", fontWeight: "600" },
  hint: { color: "#475569", fontSize: "13px", marginTop: "12px" },
};
