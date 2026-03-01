// src/components/InterviewRoom.jsx
// Main interview screen — shows webcam, question, speech input, real-time feedback

import { useEffect, useRef, useState } from "react";
import { startWebcam, startContinuousAnalysis } from "../agents/visionAgent";
import { analyseAnswer, generateQuestion } from "../agents/geminiAgent";
import FeedbackPanel from "./FeedbackPanel";
import ScoreCard from "./ScoreCard";

export default function InterviewRoom({ role }) {
  // Refs
  const videoRef = useRef(null);                    // reference to <video> DOM element
  const stopVisionRef = useRef(null);               // stores stop function for vision interval

  // State
  const [question, setQuestion] = useState("");                    // current interview question
  const [transcript, setTranscript] = useState("");               // user's spoken answer
  const [isListening, setIsListening] = useState(false);          // is mic recording
  const [visionData, setVisionData] = useState(null);             // real-time vision results
  const [feedback, setFeedback] = useState(null);                 // Gemini answer feedback
  const [showScore, setShowScore] = useState(false);              // show final scorecard
  const [isLoading, setIsLoading] = useState(false);              // loading state for Gemini

  // ─── On mount: start webcam + vision analysis + generate first question ───
  useEffect(() => {
    async function init() {
      // Step 1: Start webcam and attach stream to video element
      const stream = await startWebcam();
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // Step 2: Start continuous vision analysis every 2 seconds
      const stopFn = startContinuousAnalysis(videoRef.current, (result) => {
        setVisionData(result);                      // update vision state with each result
      });
      stopVisionRef.current = stopFn;              // save stop function for cleanup

      // Step 3: Generate first interview question using Gemini
      const q = await generateQuestion(role || "Software Engineer");
      setQuestion(q);
    }

    init();

    // Cleanup on unmount — stop vision analysis interval
    return () => {
      if (stopVisionRef.current) stopVisionRef.current();
    };
  }, []);

  // ─── Speech Recognition (Web Speech API — free, built into browser) ───
  function startListening() {
    // Check browser support for Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support speech recognition. Try Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;                 // keep recording until stopped
    recognition.interimResults = true;             // show partial results while speaking
    recognition.lang = "en-US";

    // Update transcript as user speaks
    recognition.onresult = (event) => {
      let fullTranscript = "";
      for (let i = 0; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript;  // build full transcript
      }
      setTranscript(fullTranscript);
    };

    recognition.start();
    setIsListening(true);

    // Save recognition instance to stop later
    window._recognition = recognition;
  }

  function stopListening() {
    if (window._recognition) {
      window._recognition.stop();                  // stop recording
      setIsListening(false);
    }
  }

  // ─── Submit answer to Gemini for analysis ───
  async function submitAnswer() {
    if (!transcript.trim()) {
      alert("Please speak your answer first.");
      return;
    }

    setIsLoading(true);
    stopListening();                               // stop mic before submitting

    // Send question + transcript to Gemini for analysis
    const result = await analyseAnswer(question, transcript);
    setFeedback(result);
    setIsLoading(false);
  }

  // ─── Move to next question ───
  async function nextQuestion() {
    setFeedback(null);                             // clear previous feedback
    setTranscript("");                             // clear transcript
    const q = await generateQuestion(role || "Software Engineer");
    setQuestion(q);                                // generate new question
  }

  // ─── Finish interview and show scorecard ───
  function finishInterview() {
    if (stopVisionRef.current) stopVisionRef.current();  // stop vision analysis
    setShowScore(true);
  }

  // Show final scorecard if interview is done
  if (showScore) {
    return <ScoreCard feedback={feedback} visionData={visionData} />;
  }

  return (
    <div style={styles.container}>

      {/* ── Left Panel: Webcam ── */}
      <div style={styles.leftPanel}>
        <h3 style={styles.sectionTitle}>📷 Live Feed</h3>

        {/* Webcam video element */}
        <video
          ref={videoRef}
          autoPlay
          muted
          style={styles.video}
        />

        {/* Real-time vision indicators */}
        {visionData && (
          <div style={styles.visionBadges}>
            <span style={visionData.eyeContact ? styles.badgeGreen : styles.badgeRed}>
              {visionData.eyeContact ? "✅ Eye Contact" : "❌ No Eye Contact"}
            </span>
            <span style={styles.badgeBlue}>
              🧍 Posture: {visionData.posture}
            </span>
            <span style={styles.badgeBlue}>
              😊 Expression: {visionData.expression}
            </span>
          </div>
        )}
      </div>

      {/* ── Right Panel: Question + Answer + Feedback ── */}
      <div style={styles.rightPanel}>

        {/* Interview question */}
        <div style={styles.questionBox}>
          <h3 style={styles.sectionTitle}>❓ Question</h3>
          <p style={styles.questionText}>{question || "Loading question..."}</p>
        </div>

        {/* Transcript display */}
        <div style={styles.transcriptBox}>
          <h3 style={styles.sectionTitle}>🎤 Your Answer</h3>
          <p style={styles.transcriptText}>
            {transcript || "Click 'Start Speaking' and answer the question..."}
          </p>
        </div>

        {/* Controls */}
        <div style={styles.controls}>
          {!isListening ? (
            <button onClick={startListening} style={styles.btnGreen}>
              🎙️ Start Speaking
            </button>
          ) : (
            <button onClick={stopListening} style={styles.btnRed}>
              ⏹️ Stop Speaking
            </button>
          )}

          <button onClick={submitAnswer} style={styles.btnBlue} disabled={isLoading}>
            {isLoading ? "Analysing..." : "📊 Analyse Answer"}
          </button>

          <button onClick={nextQuestion} style={styles.btnGrey}>
            ⏭️ Next Question
          </button>

          <button onClick={finishInterview} style={styles.btnOrange}>
            🏁 Finish
          </button>
        </div>

        {/* Gemini feedback panel */}
        {feedback && <FeedbackPanel feedback={feedback} />}
      </div>
    </div>
  );
}

// ─── Inline Styles ───
const styles = {
  container: { display: "flex", gap: "20px", padding: "20px", minHeight: "100vh", backgroundColor: "#0f172a", color: "#fff" },
  leftPanel: { flex: 1, display: "flex", flexDirection: "column", gap: "12px" },
  rightPanel: { flex: 1.2, display: "flex", flexDirection: "column", gap: "16px" },
  sectionTitle: { margin: "0 0 8px 0", color: "#94a3b8", fontSize: "14px", textTransform: "uppercase", letterSpacing: "1px" },
  video: { width: "100%", borderRadius: "12px", border: "2px solid #334155" },
  visionBadges: { display: "flex", flexDirection: "column", gap: "8px" },
  badgeGreen: { background: "#166534", padding: "8px 12px", borderRadius: "8px", fontSize: "14px" },
  badgeRed: { background: "#7f1d1d", padding: "8px 12px", borderRadius: "8px", fontSize: "14px" },
  badgeBlue: { background: "#1e3a5f", padding: "8px 12px", borderRadius: "8px", fontSize: "14px" },
  questionBox: { background: "#1e293b", padding: "16px", borderRadius: "12px" },
  questionText: { fontSize: "18px", lineHeight: "1.6", margin: 0 },
  transcriptBox: { background: "#1e293b", padding: "16px", borderRadius: "12px", minHeight: "100px" },
  transcriptText: { fontSize: "15px", color: "#94a3b8", margin: 0, lineHeight: "1.6" },
  controls: { display: "flex", gap: "10px", flexWrap: "wrap" },
  btnGreen: { padding: "10px 16px", background: "#16a34a", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" },
  btnRed: { padding: "10px 16px", background: "#dc2626", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" },
  btnBlue: { padding: "10px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" },
  btnGrey: { padding: "10px 16px", background: "#475569", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" },
  btnOrange: { padding: "10px 16px", background: "#ea580c", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer", fontSize: "14px" },
};
