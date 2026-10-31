import sqlite3
import os

# --------------------------------
# DATABASE LOCATION
# --------------------------------

DATABASE_FOLDER = "database"
DATABASE_FILE = os.path.join(
    DATABASE_FOLDER,
    "attendance.db"
)

# Create database folder if needed
os.makedirs(DATABASE_FOLDER, exist_ok=True)


# --------------------------------
# CONNECT TO DATABASE
# --------------------------------

def get_connection():
    return sqlite3.connect(DATABASE_FILE)


# --------------------------------
# CREATE TABLES
# --------------------------------

def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT,
            email TEXT,
            face_image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL
        )
    """)

    connection.commit()
    connection.close()


# --------------------------------
# ADD STUDENT
# --------------------------------

def add_student(
    student_id,
    name,
    department,
    email,
    face_image
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO students
            (student_id, name, department, email, face_image)
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            name,
            department,
            email,
            face_image
        ))

        connection.commit()

        print("Student added successfully!")

    except sqlite3.IntegrityError:

        print("Student ID already exists.")

    finally:

        connection.close()


# --------------------------------
# GET ALL STUDENTS
# --------------------------------

def get_students():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            department,
            email,
            face_image
        FROM students
        ORDER BY name
    """)

    students = cursor.fetchall()

    connection.close()

    return students


# --------------------------------
# FIND STUDENT
# --------------------------------

def get_student(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            name,
            department,
            email,
            face_image
        FROM students
        WHERE student_id = ?
    """, (student_id,))

    student = cursor.fetchone()

    connection.close()

    return student






from datetime import datetime


# --------------------------------
# CHECK TODAY'S ATTENDANCE
# --------------------------------

def has_attendance_today(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE student_id = ?
        AND date = ?
    """, (
        student_id,
        today
    ))

    record = cursor.fetchone()

    connection.close()

    return record is not None


# --------------------------------
# MARK ATTENDANCE
# --------------------------------

def mark_attendance(student_id, confidence=0.0):

    connection = get_connection()
    cursor = connection.cursor()

    now = datetime.now()

    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    # Don't mark twice on the same day
    if has_attendance_today(student_id):

        connection.close()

        return False

    cursor.execute("""
        INSERT INTO attendance
        (student_id, date, time, status, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (
        student_id,
        date,
        time,
        "Present",
        confidence
    ))

    connection.commit()

    connection.close()

    return True


# --------------------------------
# GET ATTENDANCE
# --------------------------------

def get_attendance():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            date,
            time,
            status,
            confidence
        FROM attendance
        ORDER BY date DESC, time DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records


# --------------------------------
# RUN WHEN FILE IS EXECUTED
# --------------------------------

if __name__ == "__main__":

    create_tables()

    print("Database created successfully!")
    print(f"Database location: {DATABASE_FILE}")