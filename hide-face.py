import cv2
import numpy as np
import time
import random
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyvirtualcam
from pyvirtualcam import PixelFormat

# Camera index (0 = built-in)
CAM_INDEX = 0
# MediaPipe model file
MODEL_PATH = "face_landmarker.task"
# Frame resolution
FRAME_W, FRAME_H = 640, 480
# Target FPS
FPS = 30
# Draw current mode name in the corner
SHOW_MODE_OSD = False

# Masking modes, cycled in this order
MODES = ["black", "breakcore"]
# Which mode to start with
START_MODE_INDEX = 0

# Breakcore: distortion strength
BREAKCORE_INTENSITY = 1.0
# Breakcore: padding around the face, in pixels
BREAKCORE_PAD = 25
# Breakcore: pixelation block size
BREAKCORE_PIXEL_BLOCKS = 8
# Breakcore: chance of a full-frame glitch
GLOBAL_GLITCH_CHANCE = 0.05
# Breakcore: chance of spawning random text
BREAKCORE_TEXT_CHANCE = 0.08
# Breakcore: random text glyphs
BREAKCORE_GLYPHS = ["BREAK", "CORE", "ERR", "!!!", "??", "xx", "//", "0x0", ">>>", "###"]

# Enable gesture-based mode switching
GESTURE_ENABLED = True
# Cooldown between switches, in seconds
GESTURE_COOLDOWN_SEC = 1.0
# EAR threshold below which an eye counts as closed
EAR_BLINK_THRESHOLD = 0.18
# How long both eyes must stay closed to switch, in seconds
EYES_CLOSED_SWITCH_SEC = 3.0

# MediaPipe landmark indices used for masking and alignment
LANDMARK_IDX = {
    'face_hull': [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379,
                  378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
                  162, 21, 54, 103, 67, 109],
    'left_eye': [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
    'right_eye': [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
    'mouth': [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13,
              82, 81, 80, 191],
    'nose': [6, 197, 195, 5, 4, 45, 275, 440, 279, 49, 209, 238, 250, 462]
}

# Eye landmarks used for the EAR (eye openness) calculation
LEFT_EYE_EAR = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_EAR = [362, 385, 387, 263, 373, 380]


def mediapipe_to_ndarray(landmarks, w, h):
    # Convert MediaPipe landmarks to (x, y) pixel coordinates
    return np.array([[lm.x * w, lm.y * h] for lm in landmarks], dtype=np.float32)


def make_landmarker(mode, num_faces, det_conf, pres_conf, track_conf=0.5):
    # Build a FaceLandmarker detector with the given parameters
    opts = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mode,
        num_faces=num_faces,
        min_face_detection_confidence=det_conf,
        min_face_presence_confidence=pres_conf,
        min_tracking_confidence=track_conf,
    )
    return vision.FaceLandmarker.create_from_options(opts)


def eye_aspect_ratio(pts, idx):
    # EAR = eye height / eye width. Lower value means the eye is more closed
    p1, p2, p3, p4, p5, p6 = [pts[i] for i in idx]
    v1 = np.linalg.norm(p2 - p6)
    v2 = np.linalg.norm(p3 - p5)
    h = np.linalg.norm(p1 - p4)
    if h < 1e-6:
        return 0.0
    return (v1 + v2) / (2.0 * h)


class GestureController:
    # Tracks how long both eyes stay closed and switches modes accordingly

    def __init__(self, modes, start_idx=0, switch_sec=3.0, cooldown=1.0):
        self.modes = modes
        self.index = start_idx
        self.switch_sec = switch_sec
        self.cooldown = cooldown
        self.last_change = 0.0
        self.eyes_closed_since = None

    def current_mode(self):
        return self.modes[self.index]

    def update(self, pts):
        now = time.time()
        ear_l = eye_aspect_ratio(pts, LEFT_EYE_EAR)
        ear_r = eye_aspect_ratio(pts, RIGHT_EYE_EAR)
        both_closed = (ear_l < EAR_BLINK_THRESHOLD) and (ear_r < EAR_BLINK_THRESHOLD)

        if both_closed:
            if self.eyes_closed_since is None:
                self.eyes_closed_since = now
            elif now - self.eyes_closed_since >= self.switch_sec:
                if now - self.last_change >= self.cooldown:
                    self.index = (self.index + 1) % len(self.modes)
                    self.last_change = now
                    self.eyes_closed_since = None
                    return "next"
        else:
            self.eyes_closed_since = None
        return None


def _bbox(landmarks, pad=0):
    # Bounding box around the face with an optional margin. None if empty
    x, y, w, h = cv2.boundingRect(landmarks.astype(np.int32))
    if w <= 0 or h <= 0:
        return None
    x = max(0, x - pad)
    y = max(0, y - pad)
    x2 = min(FRAME_W, x + w + 2 * pad)
    y2 = min(FRAME_H, y + h + 2 * pad)
    if x2 <= x or y2 <= y:
        return None
    return x, y, x2, y2


def mask_face_black(frame, landmarks):
    # Black mode: fill the face bounding box with solid black
    bb = _bbox(landmarks)
    if bb is None:
        return frame
    x, y, x2, y2 = bb
    frame[y:y2, x:x2] = 0
    return frame


def _rgb_shift(img, shift_px):
    # Split red and blue channels apart. Base for glitch effects
    b, g, r = cv2.split(img)
    M_r = np.float32([[1, 0, shift_px], [0, 1, 0]])
    M_b = np.float32([[1, 0, -shift_px], [0, 1, 0]])
    r_s = cv2.warpAffine(r, M_r, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REFLECT_101)
    b_s = cv2.warpAffine(b, M_b, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REFLECT_101)
    return cv2.merge([b_s, g, r_s])


def mask_face_breakcore(frame, landmarks, intensity=BREAKCORE_INTENSITY, pad=BREAKCORE_PAD):
    # Breakcore mode: pixelation + slice glitch + RGB split + scanlines
    bb = _bbox(landmarks, pad=pad)
    if bb is None:
        return frame
    x, y, x2, y2 = bb
    roi = frame[y:y2, x:x2]
    rh, rw = roi.shape[:2]
    if rh == 0 or rw == 0:
        return frame

    # Hard pixelation: the face stops being readable
    blocks = max(3, BREAKCORE_PIXEL_BLOCKS)
    sw = max(1, min(blocks, rw))
    sh = max(1, int(sw * rh / max(1, rw)))
    small = cv2.resize(roi, (sw, sh), interpolation=cv2.INTER_LINEAR)
    roi[:] = cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)

    # Shift random horizontal bands
    for _ in range(int(random.randint(3, 9) * intensity)):
        sy = random.randint(0, rh - 1)
        se = min(rh, sy + random.randint(2, max(2, rh // 5)))
        if se <= sy:
            continue
        shift = int(random.randint(-rw // 4, rw // 4) * intensity)
        M = np.float32([[1, 0, shift], [0, 1, 0]])
        roi[sy:se] = cv2.warpAffine(roi[sy:se], M, (rw, se - sy), borderMode=cv2.BORDER_REFLECT_101)

    # RGB split
    shift = int(random.randint(2, 10) * intensity)
    b, g, r = cv2.split(roi)
    r_s = cv2.warpAffine(r, np.float32([[1, 0, shift], [0, 1, 0]]), (rw, rh), borderMode=cv2.BORDER_REFLECT_101)
    b_s = cv2.warpAffine(b, np.float32([[1, 0, -shift], [0, 1, 0]]), (rw, rh), borderMode=cv2.BORDER_REFLECT_101)
    roi[:] = cv2.merge([b_s, g, r_s])

    # Darken every second row to mimic scanlines
    roi[::2] = (roi[::2].astype(np.float32) * 0.8).astype(np.uint8)

    # Occasionally invert a random block
    if random.random() < 0.25 * intensity:
        iy = random.randint(0, max(0, rh - 1))
        ih = min(rh, iy + random.randint(2, max(2, rh // 5)))
        roi[iy:ih] = 255 - roi[iy:ih]
    return frame


def global_glitch(frame, chance=GLOBAL_GLITCH_CHANCE):
    # Rare full-frame glitch: RGB split and a few random bands
    if random.random() > chance:
        return frame
    frame = _rgb_shift(frame, random.randint(5, 20))
    h = frame.shape[0]
    for _ in range(random.randint(1, 4)):
        y = random.randint(0, h - 1)
        sh = random.randint(1, 6)
        frame[y:y+sh] = random.choice([0, 255])
    return frame


def breakcore_text(frame, chance=0.2):
    # Draw a random glyph somewhere in the frame
    if random.random() > chance:
        return frame
    txt = random.choice(BREAKCORE_GLYPHS)
    h, w = frame.shape[:2]
    x = random.randint(0, max(0, w - 120))
    y = random.randint(20, max(21, h - 10))
    color = random.choice([(0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255), (0, 255, 0)])
    cv2.putText(frame, txt, (x, y), cv2.FONT_HERSHEY_SIMPLEX, random.uniform(0.5, 1.5), color, 2, cv2.LINE_AA)
    return frame


def apply_mode(mode, frame, f_landmarks):
    # Apply the selected masking mode to the frame
    try:
        if mode == "black":
            return mask_face_black(frame, f_landmarks)
        if mode == "breakcore":
            out = mask_face_breakcore(frame, f_landmarks)
            out = global_glitch(out)
            if random.random() < BREAKCORE_TEXT_CHANCE:
                out = breakcore_text(out, chance=1.0)
            return out
    except Exception as e:
        print(f"[WARN] Error in mode '{mode}': {e}")
        return frame
    return frame


# Face detector for the video stream
face_mesh_live = make_landmarker(
    mode=vision.RunningMode.VIDEO,
    num_faces=1,
    det_conf=0.3,
    pres_conf=0.3,
    track_conf=0.3,
)

# Open the webcam
cap = cv2.VideoCapture(CAM_INDEX, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
cap.set(cv2.CAP_PROP_FPS, FPS)
if not cap.isOpened():
    raise RuntimeError("Camera not accessible")

# Gesture controller for mode switching
gestures = GestureController(MODES, start_idx=START_MODE_INDEX,
                             switch_sec=EYES_CLOSED_SWITCH_SEC,
                             cooldown=GESTURE_COOLDOWN_SEC)

print(f"[hide-face] Modes: {MODES}")
print(f"[hide-face] Gesture: keep both eyes closed for {EYES_CLOSED_SWITCH_SEC}s to switch")
print(f"[hide-face] Starting mode: {gestures.current_mode()}")

frame_count = 0

with pyvirtualcam.Camera(width=FRAME_W, height=FRAME_H, fps=FPS, fmt=PixelFormat.BGR) as cam:
    print(f"[hide-face] Virtual camera started: {cam.device}")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # Run face detection on the current frame
        mp_image_live = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        frame_count += 1
        ts_ms = int(frame_count * 1000 / FPS)
        out = face_mesh_live.detect_for_video(mp_image_live, ts_ms)

        output = frame
        if out.face_landmarks:
            f_landmarks = mediapipe_to_ndarray(out.face_landmarks[0], FRAME_W, FRAME_H)

            # Handle the eye-closed gesture
            if GESTURE_ENABLED:
                event = gestures.update(f_landmarks)
                if event:
                    print(f"[hide-face] {event} -> mode: {gestures.current_mode()}")

            # Apply the current masking mode
            output = apply_mode(gestures.current_mode(), frame, f_landmarks)

        # Mode label in the corner (optional)
        if SHOW_MODE_OSD:
            cv2.putText(output, gestures.current_mode().upper(), (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow("Preview", output)
        cam.send(output)
        cam.sleep_until_next_frame()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
face_mesh_live.close()