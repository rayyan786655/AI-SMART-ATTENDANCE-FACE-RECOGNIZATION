import tkinter as tk
from tkinter import messagebox

import cv2
import face_recognition
import mediapipe as mp
import os
import time

from PIL import Image, ImageTk

from database import (
    get_student,
    has_attendance_today,
    mark_attendance
)

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# SETTINGS
# ============================================================

KNOWN_FACES_FOLDER = "known_faces"

FACE_TOLERANCE = 0.5

BLINK_THRESHOLD = 0.20

MODEL_PATH = "face_landmarker.task"


# ============================================================
# CHECK FOLDERS / MODEL
# ============================================================

if not os.path.exists(KNOWN_FACES_FOLDER):

    os.makedirs(
        KNOWN_FACES_FOLDER,
        exist_ok=True
    )


if not os.path.exists(MODEL_PATH):

    messagebox.showerror(
        "Model Missing",
        "face_landmarker.task was not found.\n\n"
        "Put face_landmarker.task inside your "
        "smart-attendance project folder."
    )

    raise SystemExit


# ============================================================
# LOAD REGISTERED FACES
# ============================================================

known_face_encodings = []

known_face_ids = []


print()
print("========================================")
print(" AI SMART ATTENDANCE")
print("========================================")
print()
print("Loading registered faces...")


for filename in os.listdir(
    KNOWN_FACES_FOLDER
):

    if not filename.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):
        continue


    image_path = os.path.join(
        KNOWN_FACES_FOLDER,
        filename
    )


    try:

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


        known_face_encodings.append(
            encodings[0]
        )


        student_id = os.path.splitext(
            filename
        )[0]


        known_face_ids.append(
            student_id
        )


        print(
            f"Loaded student: {student_id}"
        )


    except Exception as error:

        print(
            f"Could not load {filename}: {error}"
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

print("Loading MediaPipe...")


base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)


options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)


try:

    landmarker = (
        vision.FaceLandmarker.create_from_options(
            options
        )
    )

except Exception as error:

    print()
    print("ERROR: Could not start MediaPipe.")
    print(error)

    raise SystemExit


print("MediaPipe loaded successfully.")


# ============================================================
# MAIN WINDOW
# ============================================================

window = tk.Tk()

window.title(
    "AI Smart Attendance"
)

window.geometry(
    "1100x750"
)

window.configure(
    bg="#08111f"
)


# ============================================================
# VARIABLES
# ============================================================

camera = None

camera_running = False

timestamp_ms = 0

eyes_closed = False

current_student_id = None

current_name = "Unknown"

current_department = ""

current_confidence = 0.0

attendance_message = ""

attendance_message_time = 0


# ============================================================
# TITLE
# ============================================================

title = tk.Label(
    window,
    text="AI SMART ATTENDANCE",
    font=("Arial", 26, "bold"),
    fg="white",
    bg="#08111f"
)

title.pack(
    pady=(15, 5)
)


subtitle = tk.Label(
    window,
    text="Face Recognition + Blink Verification",
    font=("Arial", 12),
    fg="#aab4c3",
    bg="#08111f"
)

subtitle.pack()


# ============================================================
# CAMERA FRAME
# ============================================================

camera_frame = tk.Frame(
    window,
    width=800,
    height=500,
    bg="black"
)

camera_frame.pack(
    pady=15
)

camera_frame.pack_propagate(
    False
)


camera_label = tk.Label(
    camera_frame,
    text="Click START CAMERA",
    font=("Arial", 18),
    fg="white",
    bg="black"
)

camera_label.pack(
    fill="both",
    expand=True
)


# ============================================================
# STUDENT INFORMATION
# ============================================================

info_frame = tk.Frame(
    window,
    bg="#08111f"
)

info_frame.pack()


name_label = tk.Label(
    info_frame,
    text="Name: Unknown",
    font=("Arial", 13, "bold"),
    fg="white",
    bg="#08111f"
)

name_label.pack(
    pady=2
)


id_label = tk.Label(
    info_frame,
    text="Student ID: -",
    font=("Arial", 12),
    fg="white",
    bg="#08111f"
)

id_label.pack(
    pady=2
)


department_label = tk.Label(
    info_frame,
    text="Department: -",
    font=("Arial", 12),
    fg="white",
    bg="#08111f"
)

department_label.pack(
    pady=2
)


status_label = tk.Label(
    info_frame,
    text="Please start the camera",
    font=("Arial", 14, "bold"),
    fg="#f5c542",
    bg="#08111f"
)

status_label.pack(
    pady=8
)


# ============================================================
# ATTENDANCE FUNCTION
# ============================================================

def process_attendance():

    global attendance_message
    global attendance_message_time

    if not current_student_id:

        return


    # Check today's attendance

    already_marked = has_attendance_today(
        current_student_id
    )


    if already_marked:

        attendance_message = (
            "Already marked today"
        )

        attendance_message_time = time.time()

        return


    # Mark attendance

    success = mark_attendance(
        current_student_id,
        current_confidence
    )


    if success:

        attendance_message = (
            "ATTENDANCE MARKED!"
        )

    else:

        attendance_message = (
            "Already marked today"
        )


    attendance_message_time = time.time()


# ============================================================
# CAMERA UPDATE
# ============================================================

def update_camera():

    global timestamp_ms
    global eyes_closed

    global current_student_id
    global current_name
    global current_department
    global current_confidence

    if not camera_running:

        return


    # ========================================================
    # READ CAMERA
    # ========================================================

    success, frame = camera.read()


    if not success:

        status_label.config(
            text="Unable to read camera.",
            fg="#ff4d4d"
        )

        window.after(
            100,
            update_camera
        )

        return


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


    # Reset recognition

    current_student_id = None

    current_name = "Unknown"

    current_department = ""

    current_confidence = 0.0


    # ========================================================
    # PROCESS FACE
    # ========================================================

    for (
        face_encoding,
        face_location
    ) in zip(
        face_encodings,
        face_locations
    ):


        if len(known_face_encodings) > 0:

            face_distances = (
                face_recognition.face_distance(
                    known_face_encodings,
                    face_encoding
                )
            )


            if len(face_distances) > 0:

                best_match_index = (
                    face_distances.argmin()
                )


                matches = (
                    face_recognition.compare_faces(
                        known_face_encodings,
                        face_encoding,
                        tolerance=FACE_TOLERANCE
                    )
                )


                if matches[best_match_index]:

                    current_student_id = (
                        known_face_ids[
                            best_match_index
                        ]
                    )


                    distance = (
                        face_distances[
                            best_match_index
                        ]
                    )


                    current_confidence = max(
                        0.0,
                        min(
                            1.0,
                            1.0 - distance
                        )
                    )


                    student = get_student(
                        current_student_id
                    )


                    if student is not None:

                        current_name = student[1]

                        current_department = (
                            student[2] or ""
                        )


        # ====================================================
        # FACE BOX
        # ====================================================

        top, right, bottom, left = (
            face_location
        )


        top *= 4
        right *= 4
        bottom *= 4
        left *= 4


        if current_student_id:

            box_color = (
                0,
                255,
                0
            )

            box_text = "Recognized"

        else:

            box_color = (
                0,
                0,
                255
            )

            box_text = "Unknown"


        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            box_color,
            3
        )


        cv2.putText(
            frame,
            box_text,
            (left, max(25, top - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            box_color,
            2
        )


    # ========================================================
    # BLINK / LIVENESS DETECTION
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


    try:

        result = (
            landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )
        )

    except Exception as error:

        status_label.config(
            text="Face landmark detection error",
            fg="#ff4d4d"
        )

        print(
            "MediaPipe error:",
            error
        )

        window.after(
            30,
            update_camera
        )

        return


    blink_happened = False


    if result.face_landmarks:

        landmarks = (
            result.face_landmarks[0]
        )


        # ----------------------------------------------------
        # LEFT EYE
        # ----------------------------------------------------

        left_top = landmarks[159]

        left_bottom = landmarks[145]

        left_left = landmarks[33]

        left_right = landmarks[133]


        left_vertical = abs(
            left_top.y -
            left_bottom.y
        )


        left_horizontal = abs(
            left_left.x -
            left_right.x
        )


        # ----------------------------------------------------
        # RIGHT EYE
        # ----------------------------------------------------

        right_top = landmarks[386]

        right_bottom = landmarks[374]

        right_left = landmarks[362]

        right_right = landmarks[263]


        right_vertical = abs(
            right_top.y -
            right_bottom.y
        )


        right_horizontal = abs(
            right_left.x -
            right_right.x
        )


        # ----------------------------------------------------
        # EYE RATIO
        # ----------------------------------------------------

        if (
            left_horizontal > 0
            and
            right_horizontal > 0
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
            # EYES CLOSED
            # ------------------------------------------------

            if eye_ratio < BLINK_THRESHOLD:

                eyes_closed = True


            # ------------------------------------------------
            # EYES OPEN AGAIN
            # ------------------------------------------------

            else:

                if eyes_closed:

                    blink_happened = True

                    eyes_closed = False


    # ========================================================
    # PROCESS BLINK
    # ========================================================

    if blink_happened:

        if current_student_id:

            process_attendance()


    # ========================================================
    # UPDATE STUDENT INFORMATION
    # ========================================================

    name_label.config(
        text=f"Name: {current_name}"
    )


    id_label.config(
        text=(
            f"Student ID: "
            f"{current_student_id or '-'}"
        )
    )


    department_label.config(
        text=(
            f"Department: "
            f"{current_department or '-'}"
        )
    )


    # ========================================================
    # STATUS
    # ========================================================

    if (
        attendance_message
        and
        time.time() - attendance_message_time < 4
    ):

        if "MARKED" in attendance_message:

            status_label.config(
                text=attendance_message,
                fg="#20e070"
            )

        else:

            status_label.config(
                text=attendance_message,
                fg="#f5c542"
            )


    elif current_student_id:

        status_label.config(
            text="Blink to verify attendance",
            fg="#f5c542"
        )


    else:

        status_label.config(
            text="Unknown person",
            fg="#ff4d4d"
        )


    # ========================================================
    # SHOW CAMERA IN TKINTER
    # ========================================================

    display_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )


    image = Image.fromarray(
        display_frame
    )


    image = image.resize(
        (800, 500),
        Image.Resampling.LANCZOS
    )


    photo = ImageTk.PhotoImage(
        image
    )


    camera_label.config(
        image=photo,
        text=""
    )


    camera_label.photo = photo


    # ========================================================
    # RUN AGAIN
    # ========================================================

    window.after(
        30,
        update_camera
    )


# ============================================================
# START CAMERA
# ============================================================

def start_camera():

    global camera
    global camera_running
    global timestamp_ms
    global eyes_closed

    if camera_running:

        return


    timestamp_ms = 0

    eyes_closed = False


    # Try AVFoundation first on macOS

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_AVFOUNDATION
    )


    # Fallback

    if not camera.isOpened():

        camera.release()

        camera = cv2.VideoCapture(
            0
        )


    if not camera.isOpened():

        camera = None

        messagebox.showerror(
            "Camera Error",
            "Could not open camera.\n\n"
            "Check macOS camera permissions."
        )

        return


    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )


    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )


    camera_running = True


    status_label.config(
        text="Looking for your face...",
        fg="white"
    )


    update_camera()


# ============================================================
# STOP CAMERA
# ============================================================

def stop_camera():

    global camera
    global camera_running

    camera_running = False


    if camera is not None:

        camera.release()

        camera = None


    camera_label.config(
        image="",
        text="Camera stopped"
    )


    camera_label.photo = None


    name_label.config(
        text="Name: Unknown"
    )


    id_label.config(
        text="Student ID: -"
    )


    department_label.config(
        text="Department: -"
    )


    status_label.config(
        text="Camera stopped",
        fg="white"
    )


# ============================================================
# BUTTON FRAME
# ============================================================

button_frame = tk.Frame(
    window,
    bg="#08111f"
)

button_frame.pack(
    pady=10
)


# ============================================================
# START BUTTON
# ============================================================

start_button = tk.Button(
    button_frame,
    text="START CAMERA",
    command=start_camera,
    font=("Arial", 11, "bold"),
    bg="#2864e8",
    fg="white",
    activebackground="#1d4fbf",
    activeforeground="white",
    relief="flat",
    padx=25,
    pady=10
)

start_button.pack(
    side="left",
    padx=8
)


# ============================================================
# STOP BUTTON
# ============================================================

stop_button = tk.Button(
    button_frame,
    text="STOP CAMERA",
    command=stop_camera,
    font=("Arial", 11, "bold"),
    bg="#e84949",
    fg="white",
    activebackground="#bd3030",
    activeforeground="white",
    relief="flat",
    padx=25,
    pady=10
)

stop_button.pack(
    side="left",
    padx=8
)


# ============================================================
# CLOSE WINDOW
# ============================================================

def close_window():

    stop_camera()

    try:

        landmarker.close()

    except Exception:

        pass


    cv2.destroyAllWindows()

    window.destroy()


window.protocol(
    "WM_DELETE_WINDOW",
    close_window
)


# ============================================================
# START GUI
# ============================================================

window.mainloop()