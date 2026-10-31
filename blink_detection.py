import cv2
import mediapipe as mp
import time


# --------------------------------
# MEDIAPIPE TASKS
# --------------------------------

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# --------------------------------
# FACE LANDMARK MODEL
# --------------------------------

MODEL_PATH = "face_landmarker.task"


# --------------------------------
# CHECK MODEL EXISTS
# --------------------------------

import os

if not os.path.exists(MODEL_PATH):
    print("ERROR: face_landmarker.task was not found.")
    print()
    print("We need to download the Face Landmarker model first.")
    exit()


# --------------------------------
# CREATE FACE LANDMARKER
# --------------------------------

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)

landmarker = vision.FaceLandmarker.create_from_options(
    options
)


# --------------------------------
# CAMERA
# --------------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Could not open camera.")
    exit()


print("Blink detection started.")
print("Look at the camera.")
print("Blink your eyes.")
print("Press Q to quit.")


# --------------------------------
# BLINK SETTINGS
# --------------------------------

BLINK_THRESHOLD = 0.20

eyes_closed = False
blink_detected = False
last_blink_time = 0

timestamp_ms = 0


# --------------------------------
# MAIN LOOP
# --------------------------------

while True:

    success, frame = camera.read()

    if not success:
        print("Could not read camera.")
        break


    # Convert BGR → RGB
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    # Create MediaPipe image
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )


    # Increase timestamp
    timestamp_ms += 33


    # Run face landmark detection
    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )


    # --------------------------------
    # PROCESS FACE
    # --------------------------------

    if result.face_landmarks:

        landmarks = result.face_landmarks[0]


        height, width, _ = frame.shape


        # --------------------------------
        # LEFT EYE
        # --------------------------------

        left_top = landmarks[159]
        left_bottom = landmarks[145]

        left_left = landmarks[33]
        left_right = landmarks[133]


        left_vertical = abs(
            left_top.y - left_bottom.y
        )

        left_horizontal = abs(
            left_left.x - left_right.x
        )


        # --------------------------------
        # RIGHT EYE
        # --------------------------------

        right_top = landmarks[386]
        right_bottom = landmarks[374]

        right_left = landmarks[362]
        right_right = landmarks[263]


        right_vertical = abs(
            right_top.y - right_bottom.y
        )

        right_horizontal = abs(
            right_left.x - right_right.x
        )


        # --------------------------------
        # CALCULATE EYE RATIOS
        # --------------------------------

        if left_horizontal > 0 and right_horizontal > 0:

            left_ratio = (
                left_vertical /
                left_horizontal
            )

            right_ratio = (
                right_vertical /
                right_horizontal
            )


            eye_ratio = (
                left_ratio +
                right_ratio
            ) / 2


            # --------------------------------
            # DISPLAY EYE RATIO
            # --------------------------------

            cv2.putText(
                frame,
                f"Eye Ratio: {eye_ratio:.3f}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )


            # --------------------------------
            # BLINK DETECTION
            # --------------------------------

            if eye_ratio < BLINK_THRESHOLD:

                if not eyes_closed:
                    eyes_closed = True


            else:

                if eyes_closed:

                    blink_detected = True

                    last_blink_time = time.time()

                    eyes_closed = False


    # --------------------------------
    # DISPLAY STATUS
    # --------------------------------

    if blink_detected:

        if time.time() - last_blink_time < 2:

            cv2.putText(
                frame,
                "BLINK DETECTED!",
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                3
            )

        else:

            blink_detected = False

    else:

        cv2.putText(
            frame,
            "Please blink",
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2
        )


    # --------------------------------
    # SHOW CAMERA
    # --------------------------------

    cv2.imshow(
        "Blink / Liveness Detection",
        frame
    )


    # --------------------------------
    # QUIT
    # --------------------------------

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# --------------------------------
# CLEAN UP
# --------------------------------

camera.release()

cv2.destroyAllWindows()