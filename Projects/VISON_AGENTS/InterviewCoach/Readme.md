Flow:
======

       User Webcam (React)
              ↓
       Vision Agents SDK        ← captures live video frames
              ↓
       YOLO / Moondream         ← detects: eye contact, posture, expressions
              ↓
       Gemini Live API          ← analyses: answer quality, confidence, clarity
              ↓
       React UI                 ← shows real-time feedback to user
       


Tech Stack:
===========


# 🚀 Tech Stack

## 🖥 Frontend
- **React + Vite** – UI rendering
- **Webcam (MediaDevices API)** – Live video stream
- **Web Speech API** – Free browser-based speech-to-text

## 🎥 Vision AI
- **Vision Agents SDK** – Real-time video processing
- **YOLO (Ultralytics)** – Pose detection, posture tracking, eye contact estimation

## 🧠 LLM
- **Gemini Live** – Answer quality analysis & scoring



---

# 🔎 What The AI Detects in Real Time

## 🎥 Vision Agent (YOLO)
- 👀 Eye contact %
- 🧍 Posture (straight / slouching)
- 🙂 Facial confidence level
- 🤕 Head movement stability

## 🧠 Gemini (LLM Analysis)
- 📊 Answer relevance score
- 🗣 Clarity of answer
- 🧩 Answer completeness
- 🔁 Filler words detection (um, uh, like...)

---

# 📊 Example Scoring Output

| Category        | Score (1–10) |
|---------------|--------------|
| Relevance     | 8            |
| Clarity       | 7            |
| Confidence    | 9            |
| Posture       | 6            |
| Eye Contact   | 85%          |

---

# 🧠 How It Works

1. 🎥 Webcam streams video to Vision Agent
2. 🤖 YOLO processes posture + facial cues
3. 🎙 Browser converts speech → text
4. 🧠 Gemini analyzes response quality
5. 📊 Scores + feedback shown live
6. 🔁 Next question generated

---

# 🌟 Features

- Real-time feedback loop
- Low-latency video processing
- Free browser speech recognition
- AI-driven scoring system
- Clean modular React architecture

---

# 🛠 Future Enhancements

- Resume-based question generation
- Industry-specific question banks
- Emotion detection
- Downloadable performance report (PDF)
- Multi-language support

---

# 📌 Ideal Use Cases

- Job interview preparation
- Campus placements
- Public speaking training
- Communication skill improvement

---


 Setup:
 ======


Node Modules:
==============


 ```

npm create vite@latest interview-coach -- --template react
cd interview-coach
npm install @stream-io/video-react-sdk
npm install @google/generative-ai


```



# Backend (inside interviewcoach/backend)

```
pip install vision-agent
pip install google-generativeai #ui
```

