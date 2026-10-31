from database import mark_attendance
from database import has_attendance_today
from database import get_attendance


student_id = "2400234"


print("Checking attendance...")


# Check before marking
if has_attendance_today(student_id):

    print("Student is already marked present today.")

else:

    print("Student has not been marked today.")

    success = mark_attendance(
        student_id,
        confidence=0.95
    )

    if success:
        print("Attendance marked successfully!")
    else:
        print("Attendance was already marked.")


print()
print("ATTENDANCE RECORDS")
print("----------------------------")


records = get_attendance()

for record in records:

    print(record)