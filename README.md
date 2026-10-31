# AI Smart Attendance (Face Recognition)

An attendance system that uses a webcam and face recognition to identify people and mark their attendance automatically, with no manual roll calls.

## Features

- Real-time face detection and recognition from a webcam
- Automatic attendance marking with date and time
- Simple desktop GUI
- Register new people by capturing their face
- Attendance records saved locally (CSV or database)

## Tech Stack

- Python 3.11
- OpenCV for camera access and image processing
- MediaPipe Face Landmarker (`face_landmarker.task`) for face detection and landmarks
- GUI: Tkinter / PyQt (update to match your project)

## Project Structure

```
smart-attendance/
├── main.py                  # Entry point (update to your actual file name)
├── face_landmarker.task     # MediaPipe face landmark model
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rayyan786655/AI-SMART-ATTENDANCE-FACE-RECOGNIZATION.git
   cd AI-SMART-ATTENDANCE-FACE-RECOGNIZATION
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```bash
python main.py
```

1. Allow the app to access your camera.
2. Register a new person by entering their name and capturing their face.
3. Start attendance. Recognised faces are marked present automatically.
4. View or export the attendance records.

> On macOS, grant camera permission to Terminal or VS Code under **System Settings → Privacy & Security → Camera**.

## How It Works

1. The webcam captures frames in real time.
2. The face detector locates faces and extracts facial landmarks.
3. Each detected face is compared with the registered faces.
4. On a match, the person's name and timestamp are saved to the attendance record.

## Troubleshooting

- **Camera not opening:** check camera permissions and make sure no other app is using it.
- **Face not recognised:** improve lighting, face the camera directly, and re-register with a clear photo.
- **Missing model error:** make sure `face_landmarker.task` is in the project root.

## Future Improvements

- Cloud or database storage for attendance
- Admin dashboard and attendance reports
- Anti-spoofing (liveness detection)
- Email or SMS notifications

## Author

**Md Raiyan Wahidi**
GitHub: [@rayyan786655](https://github.com/rayyan786655)

## License

This project is licensed under the MIT License. Add a `LICENSE` file if you want to use this.
