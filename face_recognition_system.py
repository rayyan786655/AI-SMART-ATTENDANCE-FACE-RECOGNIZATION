import cv2
import face_recognition
import os

# --------------------------------
# SETTINGS
# --------------------------------

KNOWN_FACES_FOLDER = "known_faces"

# --------------------------------
# LOAD KNOWN FACES
# --------------------------------

known_face_encodings = []
known_face_names = []

for filename in os.listdir(KNOWN_FACES_FOLDER):

    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        continue

    image_path = os.path.join(
        KNOWN_FACES_FOLDER,
        filename
    )

    # Load image
    image = face_recognition.load_image_file(image_path)

    # Generate face encoding
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        print(f"No face found in {filename}")
        continue

    # Use the first detected face
    encoding = encodings[0]

    # Store encoding
    known_face_encodings.append(encoding)

    # Use filename as student ID
    student_id = os.path.splitext(filename)[0]

    known_face_names.append(student_id)

    print(f"Loaded student: {student_id}")


print()
print(f"Total registered students: {len(known_face_names)}")
print()

# --------------------------------
# OPEN CAMERA
# --------------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Could not open camera.")
    exit()

print("Face recognition started.")
print("Press Q to quit.")

# --------------------------------
# RECOGNITION LOOP
# --------------------------------

while True:

    success, frame = camera.read()

    if not success:
        print("Could not read camera frame.")
        break

    # Resize frame to make processing faster
    small_frame = cv2.resize(
        frame,
        (0, 0),
        fx=0.25,
        fy=0.25
    )

    # OpenCV uses BGR
    # face_recognition uses RGB
    rgb_small_frame = cv2.cvtColor(
        small_frame,
        cv2.COLOR_BGR2RGB
    )

    # Detect faces
    face_locations = face_recognition.face_locations(
        rgb_small_frame
    )

    # Generate encodings
    face_encodings = face_recognition.face_encodings(
        rgb_small_frame,
        face_locations
    )

    # --------------------------------
    # CHECK EACH FACE
    # --------------------------------

    for face_encoding, face_location in zip(
        face_encodings,
        face_locations
    ):

        # Compare with known faces
        matches = face_recognition.compare_faces(
            known_face_encodings,
            face_encoding,
            tolerance=0.5
        )

        name = "Unknown"

        # Calculate face distances
        face_distances = face_recognition.face_distance(
            known_face_encodings,
            face_encoding
        )

        if len(face_distances) > 0:

            best_match_index = face_distances.argmin()

            if matches[best_match_index]:
                name = known_face_names[best_match_index]

        # --------------------------------
        # GET FACE LOCATION
        # --------------------------------

        top, right, bottom, left = face_location

        # Scale back up because we resized the frame
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw rectangle
        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            (0, 255, 0),
            2
        )

        # Display name
        cv2.rectangle(
            frame,
            (left, bottom - 35),
            (right, bottom),
            (0, 255, 0),
            cv2.FILLED
        )

        cv2.putText(
            frame,
            name,
            (left + 6, bottom - 6),
            cv2.FONT_HERSHEY_DUPLEX,
            0.8,
            (0, 0, 0),
            1
        )

    # Show camera
    cv2.imshow(
        "Smart Attendance - Face Recognition",
        frame
    )

    # Quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# --------------------------------
# CLEAN UP
# --------------------------------

camera.release()
cv2.destroyAllWindows()