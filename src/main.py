from flask import jsonify, Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from bson.objectid import ObjectId
from bson.json_util import dumps
from datetime import datetime, timedelta
from src import mongo
import uuid

main = Blueprint('main', __name__)

# Helper function to check role
def verify_role(required_role):
    """Verify if the logged-in user has the required role."""
    if 'role' in session and session['role'] == required_role:
        return True
    flash(f"Incorrect User: You must be a {required_role} to access this page.", "error")
    return False


# Student Dashboard
@main.route('/student_dashboard')
def student_dashboard():
    if verify_role('Student'):
        name = session.get('name', 'Student')
        return render_template('student/student_dashboard.html', name=name)
    return redirect(url_for('auth.home'))


@main.route('/student_assignments_homework')
def student_assignments_homework():
    if verify_role('Student'):
        return render_template('student/student_assignments_homework.html')
    return redirect(url_for('auth.home'))


@main.route('/student_bus_schedule')
def student_bus_schedule():
    if verify_role('Student'):
        return render_template('student/student_bus_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/student_classes_and_grades')
def student_classes_and_grades():
    if verify_role('Student'):
        return render_template('student/student_classes_and_grades.html')
    return redirect(url_for('auth.home'))


# Teacher Dashboard
@main.route('/teacher_dashboard')
def teacher_dashboard():
    if verify_role('Teacher'):
        name = session.get('name', 'Teacher')
        return render_template('teacher/teacher_dashboard.html', name=name)
    return redirect(url_for('auth.home'))


@main.route('/teacher_assign_grades')
def teacher_assign_grades():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_assign_grades.html')
    return redirect(url_for('auth.home'))


@main.route('/grades_get_students', methods=['GET'])
def grades_get_students():
    """Fetch students assigned to the logged-in teacher for grading."""
    teacher_id = session.get('username')
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404
    
    assigned_classes = teacher_profile.get("assigned_classes", [])
    student_ids = [student for cls in assigned_classes for student in cls.get("students_enrolled", [])]
    
    students = mongo.db["Student Profile"].find({"student_id": {"$in": student_ids}}, 
                                                  {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0})
    student_list = [{"id": s["student_id"], "name": f"{s['first_name']} {s['last_name']}"} for s in students]
    
    return jsonify({"students": student_list})


@main.route('/get_student_grades/<student_id>', methods=['GET'])
def get_student_grades(student_id):
    """Retrieve assignments that need grading for a student."""
    grades = mongo.db["Grades"].find({"student_id": student_id}, {"_id": 0})
    assignments = [{"id": g["assignment_name"], "name": g["assignment_name"], "grade": g.get("grade", "")} for g in grades]
    
    return jsonify({"assignments": assignments})


@main.route('/submit_grade', methods=['POST'])
def submit_grade():
    """Submit or update a student's grade for an assignment."""
    data = request.json
    student_id = data.get('student_id')
    assignment_name = data.get('assignment_id')
    grade = data.get('grade')
    
    mongo.db["Grades"].update_one(
        {"student_id": student_id, "assignment_name": assignment_name},
        {"$set": {"grade": grade, "entered_date": datetime.utcnow()}},
        upsert=True
    )
    return jsonify({"message": "Grade submitted successfully!"})

@main.route('/assign_homework', methods=['POST'])
def assign_homework():
    """Assign homework to all students in a teacher's class."""
    data = request.json
    assignment_name = data.get('assignment_name')
    due_date = data.get('due_date')
    teacher_id = session.get('username')
    
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404
    
    assigned_classes = teacher_profile.get("assigned_classes", [])
    for cls in assigned_classes:
        class_id = cls["class_id"]
        for student_id in cls.get("students_enrolled", []):
            mongo.db["Assignments"].insert_one({
                "class_number": class_id,
                "assignment_name": assignment_name,
                "student_id": student_id,
                "entered_date": datetime.utcnow(),
                "due_date": due_date
            })
    
    return jsonify({"message": "Homework assigned successfully!"})


@main.route('/teacher_attendance', methods=['GET', 'POST'])
def teacher_attendance():
    if not verify_role('Teacher'):
        return redirect(url_for('auth.home'))

    teacher_profile = session.get('teacher_profile')

    if not teacher_profile:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('auth.home'))

    assigned_classes = teacher_profile.get('assigned_classes', [])

    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

    # Get selected class and student from request
    selected_class_id = request.args.get('class_id') or (assigned_classes[0]['class_id'] if assigned_classes else None)
    selected_student_id = request.args.get('student_id')

    # Handle POST request to submit new attendance
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        date = request.form.get('date')
        status = request.form.get('status')
        class_id = request.form.get('class_id')

        if not (student_id and date and status and class_id):
            flash("All fields are required!", "error")
        else:
            # Generate a unique _id
            attendance_id = str(uuid.uuid4())

            # Insert into MongoDB
            mongo.db.Attendance.insert_one({
                "_id": attendance_id,
                "student_id": student_id,
                "date": date,
                "status": status,
                "class_id": class_id
            })

            flash("Attendance record added successfully!", "success")

        # Redirect to refresh the page and show updated records
        return redirect(url_for('main.teacher_attendance', class_id=class_id, student_id=student_id))

    # Get students from the selected class
    student_ids = []
    if selected_class_id:
        selected_class = next((cls for cls in assigned_classes if cls["class_id"] == selected_class_id), None)
        if selected_class:
            student_ids = selected_class.get('students_enrolled', [])

            # ✅ Auto-select first student if none is selected
            if not selected_student_id and student_ids:
                selected_student_id = student_ids[0]

    # Retrieve student names from "Student Profile"
    student_data = {s['student_id']: f"{s['first_name']} {s['last_name']}" for s in mongo.db["Student Profile"].find(
        {"student_id": {"$in": student_ids}}, {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}
    )}

    # Filter attendance records by class and selected student
    filter_query = {
        'class_id': selected_class_id,
        'date': {'$gte': fourteen_days_ago}
    }
    if selected_student_id:
        filter_query['student_id'] = selected_student_id

    records = list(mongo.db.Attendance.find(filter_query))

    # Attach student names to records
    for record in records:
        record['student_name'] = student_data.get(record['student_id'], record['student_id'])

    return render_template(
        'teacher/teacher_attendance.html',
        assigned_classes=assigned_classes,
        selected_class_id=selected_class_id,
        selected_student_id=selected_student_id,
        student_data=student_data,
        records=records
    )

# Works with Teacher Attendance to obtain records
@main.route('/get_students/<class_id>')
def get_students(class_id):
    """Fetch students based on selected class."""
    teacher_id = session.get('username')

    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    if not teacher_profile:
        return {"error": "Teacher profile not found"}, 404

    # Find the selected class inside assigned_classes
    selected_class = next(
        (cls for cls in teacher_profile.get('assigned_classes', []) if cls['class_id'] == class_id),
        None
    )

    if not selected_class:
        return {"error": "Class not found"}, 404

    # Extract student IDs from the selected class
    student_ids = selected_class.get('students_enrolled', [])

    # Fetch student details from "Student Profile"
    students = list(mongo.db["Student Profile"].find({"student_id": {"$in": student_ids}}, 
                                                      {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}))

    return {"students": [{"id": s['student_id'], "name": f"{s['first_name']} {s['last_name']}"} for s in students]}


@main.route('/teacher_student_profiles')
def teacher_student_profiles():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_student_profiles.html')
    return redirect(url_for('auth.home'))


@main.route('/profile_get_students', methods=['GET'])
def profile_get_students():
    """Fetch students assigned to the logged-in teacher."""
    teacher_id = session.get('username')
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404
    
    assigned_classes = teacher_profile.get("assigned_classes", [])
    student_ids = [student for cls in assigned_classes for student in cls.get("students_enrolled", [])]
    
    students = mongo.db["Student Profile"].find({"student_id": {"$in": student_ids}}, 
                                                  {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0})
    student_list = [{"id": s["student_id"], "name": f"{s['first_name']} {s['last_name']}"} for s in students]
    
    return jsonify({"students": student_list})


@main.route('/get_student_profile/<student_id>', methods=['GET'])
def get_student_profile(student_id):
    """Retrieve detailed student profile based on student_id."""
    student = mongo.db["Student Profile"].find_one({"student_id": student_id}, {"_id": 0})
    
    if not student:
        return jsonify({"error": "Student not found"}), 404
    
    from datetime import datetime

    # Format Date of Birth
    if "date_of_birth" in student:
        student["date_of_birth"] = datetime.strptime(student["date_of_birth"], "%Y-%m-%d").strftime("%m-%d-%Y")

    # Populate Emergency Contact
    if "emergency_contacts" in student:
        for contact in student["emergency_contacts"]:
            if "relation" not in contact or not contact["relation"]:
                contact["relation"] = "Unknown"

    # Retrieve Bus Schedule from Bus Routes Collection
    bus_info = mongo.db["Bus Routes"].find_one({"students": student_id}, {"_id": 0})
    
    if bus_info:
        stops = bus_info.get("stops", [])
        student["bus_schedule"] = "<br>".join(
            [f"Stop: {stop['stop_name']}, Pickup: {stop['pickup_time']}, Dropoff: {stop['dropoff_time']}" for stop in stops]
        )
    else:
        student["bus_schedule"] = "No bus schedule available"
    
    return jsonify(student)


# Admin Dashboard
@main.route('/admin_dashboard')
def admin_dashboard():
    if verify_role('Administrator'):
        name = session.get('name', 'Administrator')
        return render_template('admin/admin_dashboard.html', name=name)
    return redirect(url_for('auth.home'))


@main.route('/manage_users_permissions')
def manage_users_permissions():
    if verify_role('Administrator'):
        return render_template('admin/manage_users_permissions.html')
    return redirect(url_for('auth.home'))


@main.route('/audit_log')
def audit_log():
    if verify_role('Administrator'):
        return render_template('admin/audit_log.html')
    return redirect(url_for('auth.home'))


# Parent Dashboard
@main.route('/parent_dashboard')
def parent_dashboard():
    if verify_role('Parent'):
        name = session.get('name', 'Parent')
        return render_template('parent/parent_dashboard.html', name=name)
    return redirect(url_for('auth.home'))


@main.route('/parent_attendance_records')
def parent_attendance_records():
    if verify_role('Parent'):
        return render_template('parent/parent_attendance_records.html')
    return redirect(url_for('auth.home'))


@main.route('/parent_bus_schedule')
def parent_bus_schedule():
    if verify_role('Parent'):
        return render_template('parent/parent_bus_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/parent_view_class_schedule')
def parent_view_class_schedule():
    if verify_role('Parent'):
        return render_template('parent/parent_view_class_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/parent_view_student_grades')
def parent_view_student_grades():
    if verify_role('Parent'):
        return render_template('parent/parent_view_student_grades.html')
    return redirect(url_for('auth.home'))