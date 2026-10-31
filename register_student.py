import cv2
import os
import face_recognition

from database import create_tables, add_student


# ============================================================
# SMART ATTENDANCE SYSTEM
# STUDENT REGISTRATION
# ============================================================


# ============================================================
# SETTINGS
# ============================================================

SAVE_FOLDER = "known_faces"

os.makedirs(
    SAVE_FOLDER,
    exist_ok=True
)

# Make sure database exists
create_tables()


# ============================================================
# STUDENT INFORMATION
# ============================================================

print()
print("========================================")
print(" SMART ATTENDANCE SYSTEM")
print(" STUDENT REGISTRATION")
print("========================================")
print()


student_id = input(
    "Enter Student ID: "
).strip()

student_name = input(
    "Enter Student Name: "
).strip()

department = input(
    "Enter Department: "
).strip()

email = input(
    "Enter Email: "
).strip()


# ============================================================
# VALIDATION
# ============================================================

if not student_id:

    print("Student ID is required.")
    exit()


if not student_name:

    print("Student Name is required.")
    exit()


if not department:

    print("Department is required.")
    exit()


# ============================================================
# FACE IMAGE PATH
# ============================================================

filename = f"{student_id}.jpg"

filepath = os.path.join(
    SAVE_FOLDER,
    filename
)


# ============================================================
# CHECK EXISTING FACE
# ============================================================

if os.path.exists(filepath):

    print()
    print(
        "A face image already exists for this Student ID."
    )

    choice = input(
        "Replace it? (y/n): "
    ).strip().lower()

    if choice != "y":

        print("Registration cancelled.")
        exit()


# ============================================================
# OPEN CAMERA
# ============================================================

camera = cv2.VideoCapture(
    0,
    cv2.CAP_AVFOUNDATION
)


if not camera.isOpened():

    camera = cv2.VideoCapture(0)


if not camera.isOpened():

    print()
    print("ERROR: Could not open camera.")
    exit()


print()
print("Camera started.")
print()
print("Look directly at the camera.")
print()
print("Press SPACE to capture.")
print("Press Q to cancel.")
print()


# ============================================================
# CAMERA LOOP
# ============================================================

registration_successful = False


while True:

    success, frame = camera.read()


    if not success:

        print(
            "Could not read camera frame."
        )

        break


    # ========================================================
    # RESIZE FOR FACE RECOGNITION
    # ========================================================

    small_frame = cv2.resize(
        frame,
        (0, 0),
        fx=0.25,
        fy=0.25
    )


    # ========================================================
    # BGR -> RGB
    # ========================================================

    rgb_small_frame = cv2.cvtColor(
        small_frame,
        cv2.COLOR_BGR2RGB
    )


    # ========================================================
    # FIND FACES
    # ========================================================

    face_locations = (
        face_recognition.face_locations(
            rgb_small_frame
        )
    )


    # ========================================================
    # DRAW FACE BOXES
    # ========================================================

    for (
        top,
        right,
        bottom,
        left
    ) in face_locations:

        # Convert coordinates back
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4


        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            2
        )


        cv2.putText(
            frame,
            "Face detected",
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    cv2.putText(
        frame,
        "SPACE = Capture | Q = Cancel",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SHOW CAMERA
    # ========================================================

    cv2.imshow(
        "Student Registration",
        frame
    )


    key = cv2.waitKey(1) & 0xFF


    # ========================================================
    # CAPTURE
    # ========================================================

    if key == ord(" "):


        # ----------------------------------------------------
        # No face
        # ----------------------------------------------------

        if len(face_locations) == 0:

            print()
            print(
                "No face detected."
            )

            print(
                "Please look directly at the camera."
            )

            continue


        # ----------------------------------------------------
        # Multiple faces
        # ----------------------------------------------------

        if len(face_locations) > 1:

            print()
            print(
                "Multiple faces detected."
            )

            print(
                "Only one person should be visible."
            )

            continue


        # ====================================================
        # GET FACE COORDINATES
        # ====================================================

        top, right, bottom, left = (
            face_locations[0]
        )


        top *= 4
        right *= 4
        bottom *= 4
        left *= 4


        # ====================================================
        # ADD MARGIN
        # ====================================================

        margin = 30


        x1 = max(
            0,
            left - margin
        )

        y1 = max(
            0,
            top - margin
        )

        x2 = min(
            frame.shape[1],
            right + margin
        )

        y2 = min(
            frame.shape[0],
            bottom + margin
        )


        # ====================================================
        # CROP FACE
        # ====================================================

        face_image = frame[
            y1:y2,
            x1:x2
        ]


        # ====================================================
        # SAVE IMAGE
        # ====================================================

        saved = cv2.imwrite(
            filepath,
            face_image
        )


        if not saved:

            print()
            print(
                "ERROR: Could not save face image."
            )

            break


        # ====================================================
        # SAVE STUDENT IN DATABASE
        # ====================================================

        add_student(
            student_id,
            student_name,
            department,
            email,
            filepath
        )


        registration_successful = True


        print()
        print("========================================")
        print(" STUDENT REGISTERED SUCCESSFULLY")
        print("========================================")
        print()

        print(
            f"Student ID : {student_id}"
        )

        print(
            f"Name       : {student_name}"
        )

        print(
            f"Department : {department}"
        )

        print(
            f"Email      : {email}"
        )

        print(
            f"Face image : {filepath}"
        )

        print()
        print(
            "Face saved successfully."
        )

        print(
            "Student information saved to database."
        )

        print()

        break


    # ========================================================
    # CANCEL
    # ========================================================

    elif key == ord("q"):

        print()
        print(
            "Registration cancelled."
        )

        break


# ============================================================
# CLOSE CAMERA
# ============================================================

camera.release()

cv2.destroyAllWindows()


# ============================================================
# FINAL RESULT
# ============================================================

if registration_successful:

    print(
        "Registration completed successfully."
    )

else:

    print(
        "Registration was not completed."
    )