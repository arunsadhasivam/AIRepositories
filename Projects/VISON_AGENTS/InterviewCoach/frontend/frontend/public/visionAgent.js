// src/agents/visionAgent.js
// Handles webcam capture and sends frames to backend Vision Agent (YOLO + MediaPipe)

/**
 * Start webcam stream and return the video stream object
 * @returns {MediaStream} - Browser webcam stream
 */
export async function startWebcam() {
  try {
    // Request webcam access from browser
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },  // standard resolution for YOLO
      audio: false,                          // audio handled separately by SpeechAPI
    });
    return stream;
  } catch (error) {
    console.error("Webcam access error:", error);
    throw new Error("Could not access webcam. Please allow camera permission.");
  }
}

/**
 * Capture a single frame from the video element as base64 image
 * @param {HTMLVideoElement} videoElement - The video DOM element
 * @returns {string} - Base64 encoded image string
 */
export function captureFrame(videoElement) {
  // Create a canvas to draw the current video frame
  const canvas = document.createElement("canvas");
  canvas.width = videoElement.videoWidth;
  canvas.height = videoElement.videoHeight;

  // Draw current video frame onto canvas
  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoElement, 0, 0);

  // Convert canvas to base64 JPEG image
  return canvas.toDataURL("image/jpeg", 0.8);  // 0.8 = 80% quality, balances size vs clarity
}

/**
 * Send a frame to the Python backend Vision Agent for analysis
 * @param {string} base64Frame - Base64 encoded image
 * @returns {object} - Vision analysis result (eye contact, posture, expression)
 */
export async function analyseFrame(base64Frame) {
  try {
    // Send frame to FastAPI backend running on port 8000
    const response = await fetch("http://localhost:8000/analyse-frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frame: base64Frame }),  // send base64 image in request body
    });

    if (!response.ok) throw new Error("Backend analysis failed");

    // Return the vision analysis result
    return await response.json();
  } catch (error) {
    console.error("Frame analysis error:", error);
    // Return default values if backend is not running
    return {
      eyeContact: false,
      posture: "unknown",
      expression: "neutral",
      confidence: 0,
    };
  }
}

/**
 * Start continuous frame analysis every 2 seconds
 * @param {HTMLVideoElement} videoElement - The video DOM element
 * @param {function} onResult - Callback function called with each analysis result
 * @returns {function} - Stop function to cancel the interval
 */
export function startContinuousAnalysis(videoElement, onResult) {
  // Analyse frame every 2000ms (2 seconds) — balances performance vs responsiveness
  const intervalId = setInterval(async () => {
    const frame = captureFrame(videoElement);      // capture current frame
    const result = await analyseFrame(frame);       // send to backend
    onResult(result);                               // pass result to React component
  }, 2000);

  // Return a stop function so React can clear interval on unmount
  return () => clearInterval(intervalId);
}
