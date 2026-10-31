from database import add_student, get_students, get_student

# Add our test student
add_student(
    student_id="2400234",
    name="Raiyan",
    department="Computer Science",
    email="mdrayyanwahidi786@gmai.com",
    face_image="known_faces/2400234.jpg"
)

# Show all students
print()
print("ALL STUDENTS")
print("--------------------------------")

students = get_students()

for student in students:
    print(student)

# Find our student
print()
print("SEARCHING FOR 2400234")
print("--------------------------------")

student = get_student("2400234")

print(student)