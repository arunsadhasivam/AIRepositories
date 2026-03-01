#!/usr/bin/env python3
"""
Backend server for AI Interview Coach.
Uses Vision Agents SDK + YOLO + MediaPipe to analyse webcam frames.
Exposes a REST API that the React frontend calls.
"""

import base64                                   # decode base64 image from frontend
import numpy as np                              # image array manipulation
import cv2                                      # OpenCV for image processing
from fastapi import FastAPI                     # FastAPI web framework
from fastapi.middleware.cors import CORSMiddleware  # allow React frontend to call this API
from pydantic import BaseModel                  # input validation
import mediapipe as mp                          # MediaPipe for pose and face detection

# ─── Initialize FastAPI app ───
app = FastAPI(title="Interview Coach Vision API")

# ─── Allow React frontend (localhost:5173) to call this backend ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],    # Vite React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Initialize MediaPipe face mesh for eye contact detection ───
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,                    # process single frames, not video
    max_num_faces=1,                           # only track one face
    min_detection_confidence=0.5
)

# ─── Initialize MediaPipe pose for posture detection ───
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=True,
    min_detection_confidence=0.5
)

# ─── Pydantic model for incoming request ───
class FrameRequest(BaseModel):
    frame: str                                 # base64 encoded JPEG image from React


def decode_frame(base64_frame: str) -> np.ndarray:
    """Convert base64 image string to OpenCV numpy array."""
    # Remove data URL prefix if present (e.g. "data:image/jpeg;base64,")
    if "," in base64_frame:
        base64_frame = base64_frame.split(",")[1]

    # Decode base64 to bytes then to numpy array
    img_bytes = base64.b64decode(base64_frame)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)

    # Decode numpy array to OpenCV image (BGR format)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)


def detect_eye_contact(image: np.ndarray) -> bool:
    """
    Detect if user is making eye contact with camera.
    Uses MediaPipe face mesh — checks if eyes are looking forward.
    """
    # Convert BGR to RGB for MediaPipe
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)

    if not results.multi_face_landmarks:
        return False                           # no face detected = no eye contact

    # Get face landmarks
    landmarks = results.multi_face_landmarks[0].landmark

    # Left eye: landmarks 33, 133 | Right eye: landmarks 362, 263
    # If face is looking forward, horizontal gaze ratio stays near center
    left_eye_x = landmarks[33].x
    right_eye_x = landmarks[263].x
    nose_x = landmarks[1].x                   # nose tip as reference center

    # Check if eyes are roughly symmetrical around nose — indicates forward gaze
    left_diff = abs(nose_x - left_eye_x)
    right_diff = abs(right_eye_x - nose_x)
    gaze_ratio = left_diff / (right_diff + 0.001)  # avoid division by zero

    # Ratio close to 1.0 means face is forward/symmetric = eye contact
    return 0.7 < gaze_ratio < 1.4


def detect_posture(image: np.ndarray) -> str:
    """
    Detect user's sitting posture using MediaPipe Pose.
    Returns: 'straight', 'slouching', or 'unknown'
    """
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_image)

    if not results.pose_landmarks:
        return "unknown"                       # no pose detected

    landmarks = results.pose_landmarks.landmark

    # Get shoulder landmarks (left=11, right=12)
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    # Get ear landmarks (left=7, right=8) — ears dropping = slouching
    left_ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
    right_ear = landmarks[mp_pose.PoseLandmark.RIGHT_EAR]

    # Average shoulder Y position
    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

    # Average ear Y position
    ear_y = (left_ear.y + right_ear.y) / 2

    # If ears are significantly lower than expected relative to shoulders = slouching
    # In MediaPipe, Y increases downward (0 = top, 1 = bottom)
    diff = shoulder_y - ear_y

    if diff > 0.15:
        return "straight"                      # ears well above shoulders = upright
    else:
        return "slouching"                     # ears too close to shoulders = slouching


def detect_expression(image: np.ndarray) -> str:
    """
    Simple expression detection using face landmark distances.
    Returns: 'confident', 'nervous', or 'neutral'
    """
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)

    if not results.multi_face_landmarks:
        return "neutral"

    landmarks = results.multi_face_landmarks[0].landmark

    # Mouth landmarks: upper lip=13, lower lip=14
    mouth_open = abs(landmarks[13].y - landmarks[14].y)

    # Eyebrow landmarks: left=70, right=300
    # Raised eyebrows can indicate nervousness
    left_brow = landmarks[70].y
    left_eye_top = landmarks[159].y
    brow_raise = left_eye_top - left_brow     # positive = brow raised above eye

    # Simple heuristic classification
    if brow_raise > 0.03 and mouth_open < 0.02:
        return "nervous"                       # raised brows + closed mouth = tense
    elif mouth_open > 0.04:
        return "confident"                     # open mouth = speaking confidently
    else:
        return "neutral"


# ─── Main API endpoint — called by React every 2 seconds ───
@app.post("/analyse-frame")
async def analyse_frame(request: FrameRequest):
    """
    Receive a base64 webcam frame from React.
    Run Vision Agent analysis (eye contact, posture, expression).
    Return results as JSON.
    """
    # Step 1: Decode base64 image to OpenCV array
    image = decode_frame(request.frame)

    if image is None:
        return {"error": "Could not decode image frame"}

    # Step 2: Run all detections
    eye_contact = detect_eye_contact(image)    # bool
    posture = detect_posture(image)            # string
    expression = detect_expression(image)      # string

    # Step 3: Calculate confidence score (0-100) based on all signals
    confidence_score = 0
    if eye_contact: confidence_score += 40     # eye contact is most important
    if posture == "straight": confidence_score += 35
    if expression == "confident": confidence_score += 25

    # Step 4: Return structured result to React
    return {
        "eyeContact": eye_contact,
        "posture": posture,
        "expression": expression,
        "confidence": confidence_score          # 0-100 composite score
    }


# ─── Health check endpoint ───
@app.get("/health")
async def health():
    return {"status": "running", "service": "Interview Coach Vision API"}


# ─── Run server ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # start on port 8000
