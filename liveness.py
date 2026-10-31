"""Local blink liveness verification for attendance."""

import math
import time

import cv2
import face_recognition


BLINK_THRESHOLD = 0.20
CHALLENGE_TIMEOUT_SECONDS = 12


def _distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _eye_ratio(points):
    if len(points) < 6:
        return None
    width = _distance(points[0], points[3])
    if width < 1:
        return None
    return (_distance(points[1], points[5]) + _distance(points[2], points[4])) / (2 * width)


class LivenessChallenge:
    """Requires one complete blink for a recognised person."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.step = "blink"
        self.eyes_closed = False
        self.started_at = time.time()

    def close(self):
        pass

    def process(self, frame, face_location=None):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Reuse the face box already found by the attendance recogniser when
        # available; running a second face search can miss a valid face.
        locations = [face_location] if face_location is not None else None
        faces = face_recognition.face_landmarks(rgb, locations)
        if len(faces) != 1:
            return {"passed": False, "status": "Liveness: keep exactly one face in view"}

        landmarks = faces[0]
        left = _eye_ratio(landmarks.get("left_eye", []))
        right = _eye_ratio(landmarks.get("right_eye", []))
        if left is None or right is None:
            return {"passed": False, "status": "Liveness: eyes not detected clearly"}
        eye_ratio = (left + right) / 2

        if time.time() - self.started_at > CHALLENGE_TIMEOUT_SECONDS:
            self.reset()
            return {"passed": False, "status": "Liveness timed out. Please blink again."}

        if self.step == "blink":
            if eye_ratio < BLINK_THRESHOLD:
                self.eyes_closed = True
            elif self.eyes_closed:
                self.eyes_closed = False
                self.step = "passed"
                return {"passed": True, "status": "Blink detected. Liveness verified."}
            return {"passed": False, "status": "Liveness: blink once to continue"}

        return {"passed": True, "status": "Liveness verified"}
