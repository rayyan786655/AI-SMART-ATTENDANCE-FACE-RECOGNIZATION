import cv2
import face_recognition
import mediapipe as mp
import os
import time

from database import get_student
from database import has_attendance_today
from database import mark_attendance


# ============================================================
# SETTINGS
# ============================================================

KNOWN_FACES_FOLDER = "known_faces"

FACE_TOLERANCE = 0.5

BLINK_THRESHOLD = 0.20

BLINK_REQUIRED = 1


# ============================================================
# LOAD REGISTERED FACES
# ============================================================

known_face_encodings = []
known_face_ids = []

print()
print("========================================")
print(" SMART ATTENDANCE SYSTEM")
print("========================================")
print()

print("Loading registered faces...")


for filename in os.listdir(KNOWN_FACES_FOLDER):

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):
        continue

    image_path = os.path.join(
        KNOWN_FACES_FOLDER,
        filename
    )

    image = face_recognition.load_image_file(
        image_path
    )

    encodings = face_recognition.face_encodings(
        image
    )

    if len(encodings) == 0:

        print(
            f"No face found in {filename}"
        )

        continue

    encoding = encodings[0]

    student_id = os.path.splitext(
        filename
    )[0]

    known_face_encodings.append(
        encoding
    )

    known_face_ids.append(
        student_id
    )

    print(
        f"Loaded student: {student_id}"
    )


print()
print(
    f"Total registered students: "
    f"{len(known_face_ids)}"
)
print()


# ============================================================
# MEDIAPIPE FACE LANDMARKER
# ============================================================

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MODEL_PATH = "face_landmarker.task"


if not os.path.exists(MODEL_PATH):

    print(
        "ERROR: face_landmarker.task "
        "was not found."
    )

    exit()


base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)


options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)


landmarker = (
    vision.FaceLandmarker.create_from_options(
        options
    )
)


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(0)


if not camera.isOpened():

    print("Could not open camera.")

    exit()


print("Camera started.")
print()
print("Look at the camera.")
print("The system will recognize you.")
print("Then blink to confirm that you are live.")
print()
print("Press Q to quit.")
print()


# ============================================================
# VARIABLES
# ============================================================

timestamp_ms = 0

recognized_student_id = None

recognized_student_name = "Unknown"

recognized_department = ""

face_confidence = 0.0

eyes_closed = False

blink_detected = False

last_blink_time = 0

attendance_message = ""

attendance_message_time = 0


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()


    if not success:

        print(
            "Could not read camera frame."
        )

        break


    height, width, _ = frame.shape


    # ========================================================
    # FACE RECOGNITION
    # ========================================================

    small_frame = cv2.resize(
        frame,
        (0, 0),
        fx=0.25,
        fy=0.25
    )


    rgb_small_frame = cv2.cvtColor(
        small_frame,
        cv2.COLOR_BGR2RGB
    )


    face_locations = (
        face_recognition.face_locations(
            rgb_small_frame
        )
    )


    face_encodings = (
        face_recognition.face_encodings(
            rgb_small_frame,
            face_locations
        )
    )


    # Reset current recognition
    recognized_student_id = None
    recognized_student_name = "Unknown"
    recognized_department = ""
    face_confidence = 0.0


    # ========================================================
    # PROCESS DETECTED FACE
    # ========================================================

    for face_encoding, face_location in zip(
        face_encodings,
        face_locations
    ):


        if len(known_face_encodings) > 0:

            matches = (
                face_recognition.compare_faces(
                    known_face_encodings,
                    face_encoding,
                    tolerance=FACE_TOLERANCE
                )
            )


            face_distances = (
                face_recognition.face_distance(
                    known_face_encodings,
                    face_encoding
                )
            )


            best_match_index = (
                face_distances.argmin()
            )


            if matches[best_match_index]:

                recognized_student_id = (
                    known_face_ids[
                        best_match_index
                    ]
                )


                # Convert distance into a simple
                # confidence-like value
                distance = (
                    face_distances[
                        best_match_index
                    ]
                )

                face_confidence = max(
                    0.0,
                    min(
                        1.0,
                        1.0 - distance
                    )
                )


                # Look up student in database
                student = get_student(
                    recognized_student_id
                )


                if student is not None:

                    recognized_student_name = (
                        student[1]
                    )

                    recognized_department = (
                        student[2] or ""
                    )


        # Scale coordinates back up
        top, right, bottom, left = (
            face_location
        )

        top *= 4
        right *= 4
        bottom *= 4
        left *= 4


        # Draw face rectangle
        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            2
        )


    # ========================================================
    # LIVENESS / BLINK DETECTION
    # ========================================================

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb_frame
    )


    timestamp_ms += 33


    result = landmarker.detect_for_video(
        mp_image,
        timestamp_ms
    )


    if result.face_landmarks:

        landmarks = result.face_landmarks[0]


        # ----------------------------------------------------
        # LEFT EYE
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # RIGHT EYE
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # CALCULATE EYE RATIO
        # ----------------------------------------------------

        if (
            left_horizontal > 0
            and right_horizontal > 0
        ):

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


            # ------------------------------------------------
            # BLINK START
            # ------------------------------------------------

            if eye_ratio < BLINK_THRESHOLD:

                eyes_closed = True


            # ------------------------------------------------
            # BLINK FINISHED
            # ------------------------------------------------

            else:

                if eyes_closed:

                    blink_detected = True

                    last_blink_time = (
                        time.time()
                    )

                    eyes_closed = False


# ============================================================
# ATTENDANCE LOGIC
# ============================================================

    if blink_detected:

        if (
            time.time() - last_blink_time
            < 2
        ):

            if recognized_student_id:

                # Check today's attendance
                already_marked = (
                    has_attendance_today(
                        recognized_student_id
                    )
                )


                if already_marked:

                    attendance_message = (
                        "Already marked today"
                    )


                else:

                    success = mark_attendance(
                        recognized_student_id,
                        face_confidence
                    )


                    if success:

                        attendance_message = (
                            "ATTENDANCE MARKED!"
                        )

                    else:

                        attendance_message = (
                            "Already marked today"
                        )


                attendance_message_time = (
                    time.time()
                )


        else:

            blink_detected = False


    # ========================================================
    # DISPLAY INFORMATION
    # ========================================================

    # Student name
    cv2.putText(
        frame,
        f"Name: {recognized_student_name}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )


    # Student ID
    if recognized_student_id:

        cv2.putText(
            frame,
            f"Student ID: {recognized_student_id}",
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # Department
        cv2.putText(
            frame,
            f"Department: {recognized_department}",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # Liveness instruction
        if not blink_detected:

            cv2.putText(
                frame,
                "Blink to verify",
                (20, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )


    else:

        cv2.putText(
            frame,
            "Unknown person",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


    # ========================================================
    # ATTENDANCE MESSAGE
    # ========================================================

    if (
        attendance_message
        and
        time.time() - attendance_message_time
        < 4
    ):

        cv2.putText(
            frame,
            attendance_message,
            (20, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            3
        )


    # ========================================================
    # SHOW CAMERA
    # ========================================================

    cv2.imshow(
        "SMART ATTENDANCE SYSTEM",
        frame
    )


    # ========================================================
    # QUIT
    # ========================================================

    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


# ============================================================
# CLEANUP
# ============================================================

camera.release()

cv2.destroyAllWindows()

print()
print("Smart Attendance System stopped.")