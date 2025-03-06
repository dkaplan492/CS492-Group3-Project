from flask import jsonify, Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
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

# Students Access Pages
# Student Dashboard
@main.route('/student_dashboard')
def student_dashboard():
    if verify_role('Student'):
        name = session.get('name', 'Student')
        return render_template('student/student_dashboard.html', name=name)
    return redirect(url_for('auth.home'))

# Student Assignments & Homework
@main.route('/student_assignments_homework')
def student_assignments_homework():
    if verify_role('Student'):
        return render_template('student/student_assignments_homework.html')
    return redirect(url_for('auth.home'))


@main.route('/api/student_classes', methods=['GET'])
def api_student_classes():
    # The logged-in student's username is assumed to be their student_id.
    student_id = session.get('username')
    if not student_id:
        return jsonify({"error": "User not logged in"}), 401

    student = mongo.db["Student Profile"].find_one(
        {"student_id": student_id},
        {"enrolled_classes": 1, "_id": 0}
    )
    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    enrolled = student.get("enrolled_classes", [])
    class_list = [{"id": c.get("class_id"), "subject": c.get("subject", "")} for c in enrolled]
    return jsonify({"classes": class_list})


@main.route('/api/student_assignments_homework', methods=['GET'])
def api_student_assignments_homework():
    student_id = session.get('username')
    if not student_id:
        return jsonify({"error": "User not logged in"}), 401

    class_id = request.args.get('class_id')
    if not class_id:
        return jsonify({"error": "Missing class_id"}), 400

    # Query the assignments_grades collection for assignments for the student and class.
    assignments = list(mongo.db["assignments_grades"].find(
        {"student_id": student_id, "class_number": class_id},
        {"assignment_name": 1, "assigned_date": 1, "due_date": 1, "grade": 1, "graded_date": 1, "_id": 0}
    ))

    graded_assignments = []
    upcoming_assignments = []
    now_date = datetime.now().date()

    for assignment in assignments:
        # Parse and reformat assigned_date
        try:
            try:
                dt_assigned = datetime.strptime(assignment['assigned_date'], "%m/%d/%Y")
            except ValueError:
                dt_assigned = datetime.strptime(assignment['assigned_date'], "%Y-%m-%d")
            assignment['assigned_date'] = dt_assigned.strftime("%m/%d/%Y")
        except Exception as e:
            assignment['assigned_date'] = assignment.get('assigned_date', '')

        # Parse and reformat due_date
        try:
            try:
                dt_due = datetime.strptime(assignment['due_date'], "%m/%d/%Y")
            except ValueError:
                dt_due = datetime.strptime(assignment['due_date'], "%Y-%m-%d")
            assignment['due_date'] = dt_due.strftime("%m/%d/%Y")
        except Exception as e:
            assignment['due_date'] = assignment.get('due_date', '')

        # Parse and reformat graded_date if it exists
        try:
            if assignment.get('graded_date'):
                try:
                    dt_graded = datetime.strptime(assignment['graded_date'], "%m/%d/%Y")
                except ValueError:
                    dt_graded = datetime.strptime(assignment['graded_date'], "%Y-%m-%d")
                assignment['graded_date'] = dt_graded.strftime("%m/%d/%Y")
            else:
                assignment['graded_date'] = ""
        except Exception as e:
            assignment['graded_date'] = assignment.get('graded_date', '')

        # Determine if the due_date has passed (compare only the date part)
        if dt_due.date() <= now_date:
            graded_assignments.append(assignment)
        else:
            upcoming_assignments.append(assignment)

    return jsonify({"graded_assignments": graded_assignments, "upcoming_assignments": upcoming_assignments})


@main.route('/student_class_schedule')
def student_class_schedule():
    if verify_role('Student'):
        return render_template('student/student_class_schedule.html')
    return redirect(url_for('auth.home'))

@main.route('/api/student_class_schedule', methods=['GET'])
def api_student_class_schedule():
    # Get the logged-in student's ID (assumed stored in session as username)
    student_id = session.get("username")
    if not student_id:
        return jsonify({"error": "User not logged in"}), 401

    # Retrieve the student profile to get the enrolled_classes array.
    student = mongo.db["Student Profile"].find_one(
        {"student_id": student_id},
        {"enrolled_classes": 1, "_id": 0}
    )
    if not student:
        return jsonify({"error": "Student profile not found"}), 404

    # Build a mapping from class_id to the student's schedule.
    enrolled_classes = student.get("enrolled_classes", [])
    schedule_mapping = {cls.get("class_id"): cls.get("schedule", "N/A") for cls in enrolled_classes}

    # Find teacher profiles whose assigned_classes contain the student.
    teacher_profiles = list(mongo.db["Teacher Profile"].find(
        {"assigned_classes.students_enrolled": student_id},
        {"name": 1, "email": 1, "phone": 1, "assigned_classes": 1, "_id": 0}
    ))

    # Build the combined schedule list.
    schedule = []
    for teacher in teacher_profiles:
        for cls in teacher.get("assigned_classes", []):
            if student_id in cls.get("students_enrolled", []):
                class_id = cls.get("class_id", "")
                schedule.append({
                    "teacher_name": teacher.get("name", ""),
                    "class_number": class_id,
                    "class_name": cls.get("subject", ""),
                    "schedule": schedule_mapping.get(class_id, "N/A"),
                    "email": teacher.get("email", ""),
                    "phone": teacher.get("phone", "")
                })
    return jsonify({"schedule": schedule})


@main.route('/student_bus_schedule')
def student_bus_schedule():
    if verify_role('Student'):
        return render_template('student/student_bus_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/api/student_bus_schedule', methods=['GET'])
def api_student_bus_schedule():
    # Get the logged-in student's ID from the session.
    student_id = session.get("username")
    if not student_id:
        return jsonify({"error": "User not logged in"}), 401

    # Query the Student Profile collection for the bus_schedule object.
    student = mongo.db["Student Profile"].find_one(
        {"student_id": student_id},
        {"bus_schedule": 1, "_id": 0}
    )
    if not student or "bus_schedule" not in student:
        return jsonify({"error": "Bus schedule not found"}), 404

    return jsonify({"bus_schedule": student["bus_schedule"]})


# Teacher Access Pages
# Teacher Dashboard
@main.route('/teacher_dashboard')
def teacher_dashboard():
    if verify_role('Teacher'):
        name = session.get('name', 'Teacher')
        return render_template('teacher/teacher_dashboard.html', name=name)
    return redirect(url_for('auth.home'))

# Assigning grades to students
@main.route('/teacher_assign_grades')
def teacher_assign_grades():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_assign_grades.html')
    return redirect(url_for('auth.home'))

# Retrieve students assigned to logged-in teacher
@main.route('/grades_get_students', methods=['GET'])
def grades_get_students():

    teacher_id = session.get('username')
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id}) # Matches teacher Username from session to teacher_id in MongoDB Teacher Profile collection
    
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404 # Error if username does not match existing teacher_id
    
    assigned_classes = teacher_profile.get("assigned_classes", []) # Retrieves assigned classes for teacher_id in assigned_classes array 
    student_ids = [student for cls in assigned_classes for student in cls.get("students_enrolled", [])] # Retrieves student_id for students_enrolled array in Teacher Profile
    
    students = mongo.db["Student Profile"].find({"student_id": {"$in": student_ids}}, # Matches retreived student_id from Teacher Profile to student_id in Student Profile
                                                  {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}) 
    student_list = [{"id": s["student_id"], "name": f"{s['first_name']} {s['last_name']}"} for s in students] # Defines student's name as First Name Last Name
    
    return jsonify({"students": student_list})

# Retrieves existing assignments from assignments_grades collection
@main.route('/get_student_grades/<student_id>', methods=['GET'])
def get_student_grades(student_id):

    grades = mongo.db["assignments_grades"].find(
        {"student_id": student_id}, 
        {"_id": 0, "assignment_name": 1, "assigned_date": 1, "grade": 1, "class_number": 1, "due_date": 1}
    )

    # Formats date as MM/DD/YYYY instead of YYYY-MM-DD
    def format_date(date_str):
        if not date_str:
            return ""
        try:
            # Attempt to parse assuming it's already in MM/DD/YYYY
            dt = datetime.strptime(date_str, "%m/%d/%Y")
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            try:
                # Otherwise, try YYYY-MM-DD and convert it to MM/DD/YYYY
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%m/%d/%Y")
            except ValueError:
                # If parsing fails, return the original string
                return date_str

    # Returns assignments per student
    assignments = [
        {
            "id": g["assignment_name"],
            "name": g["assignment_name"],
            "assigned_date": format_date(g.get("assigned_date", "")),
            "due_date": format_date(g.get("due_date", "")),
            "grade": g.get("grade", "")
        }
        for g in grades
    ]
    return jsonify({"assignments": assignments})

# Submit or update grade for each student assignment
@main.route('/submit_grade', methods=['POST'])
def submit_grade():

    try:
        data = request.json
        print("[DEBUG] Received data:", data) # Used for debugging if errors are returned

        student_id = data.get('student_id')
        assignment_name = data.get('assignment_name')
        assigned_date = data.get('assigned_date')
        grade = data.get('grade')

        # Returns error if there is no match on student, assignment, assigned date, or grade
        if not student_id or not assignment_name or not assigned_date or grade is None:
            print("[ERROR] Missing fields:", student_id, assignment_name, assigned_date, grade)
            return jsonify({"error": "Missing required fields"}), 400

        # Convert current date to MM/DD/YYYY format for graded_date upon submission
        formatted_graded_date = datetime.utcnow().strftime("%m/%d/%Y")

        print(f"[DEBUG] Searching MongoDB for: student_id={student_id}, assignment_name={assignment_name}, assigned_date={assigned_date}") # Used for debugging if errors are returned

        # Fetch the actual data from MongoDB and log it
        matching_docs = list(mongo.db["assignments_grades"].find({"student_id": student_id}))
        print(f"[DEBUG] MongoDB Documents for student {student_id}:") # Used for debugging if errors are returned
        for doc in matching_docs:
            print(doc)

        # Check if the document exists before updating
        existing_doc = mongo.db["assignments_grades"].find_one(
            {
                "student_id": student_id,
                "assignment_name": assignment_name,
                "assigned_date": assigned_date
            }
        )

        if not existing_doc:
            print("[ERROR] No matching document found in MongoDB!")
            return jsonify({"error": "Assignment not found. Check student ID, assignment name, and assigned date."}), 400 # Error on page if mongoDB record does not exist

        # Updates the grade in MongoDB
        update_result = mongo.db["assignments_grades"].update_one(
            {
                "student_id": student_id,
                "assignment_name": assignment_name,
                "assigned_date": assigned_date  
            },
            {"$set": {"grade": grade, "graded_date": formatted_graded_date}},
            upsert=False  
        )

        print("[DEBUG] MongoDB Update Result:", update_result.raw_result) # Debugging output for error checks

        if update_result.modified_count > 0:
            return jsonify({"message": "Grade submitted successfully!"}) # Message on page for successful submission
        else:
            return jsonify({"message": "No changes made. Verify data."}), 400 # Message on page if no changes submitted

    except Exception as e:
        print("[ERROR] Exception:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500

# Assigns homework for each student in the enrolled_students for Teacher Profile
@main.route('/assign_homework', methods=['POST'])
def assign_homework():
    
    data = request.json
    assignment_name = data.get('assignment_name')
    assigned_date = data.get('assigned_date')
    due_date = data.get('due_date')
    teacher_id = session.get('username')

    if not assignment_name or not assigned_date or not due_date:
        return jsonify({"error": "All fields are required"}), 400 # Error on page if field is missing

    try:
        # Ensures assigned_date is in MM/DD/YYYY format
        assigned_date = datetime.strptime(assigned_date, "%m/%d/%Y").strftime("%m/%d/%Y")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use MM/DD/YYYY"}), 400 # Error on page if format is incorrect

    # Checks teacher_id in Teacher Profile
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404

    # Checks assigned_classes array in Teacher Profile for classes assigned to user
    assigned_classes = teacher_profile.get("assigned_classes", [])
    
    # Sets assignment information in assignments_grades for class_id and students_enrolled from Teacher Profile
    for cls in assigned_classes:
        class_id = cls["class_id"]
        for student_id in cls.get("students_enrolled", []):
            mongo.db["assignments_grades"].insert_one({
                "class_number": class_id,
                "assignment_name": assignment_name,
                "assigned_date": assigned_date,
                "student_id": student_id,
                "due_date": due_date,
                "grade": None,
                "graded_date": None
            })

    return jsonify({"message": "Homework assigned successfully!"}) # Success message on assignments page

# Attendance for students assigned to teacher
@main.route('/teacher_attendance', methods=['GET', 'POST'])
def teacher_attendance():
    if not verify_role('Teacher'):
        return redirect(url_for('auth.home'))

    teacher_profile = session.get('teacher_profile') # Checks teacher_id in Teacher Profile

    if not teacher_profile:
        flash("Session expired. Please log in again.", "error") # Error message if not a teacher
        return redirect(url_for('auth.home'))

    assigned_classes = teacher_profile.get('assigned_classes', []) # Retrieves classes from assigned_classes array in Teacher Profile

    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d') # Displays past 14 days of data

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
            flash("All fields are required!", "error") # Error message if field is not found
        else:
            # Generate a unique _id for loggingin MongoDB
            attendance_id = str(uuid.uuid4())

            # Insert into MongoDB
            mongo.db.Attendance.insert_one({
                "_id": attendance_id,
                "student_id": student_id,
                "date": date,
                "status": status,
                "class_id": class_id
            })

            flash("Attendance record added successfully!", "success") # Success message on page for successful entry

        # Redirect to refresh the page and show updated records
        return redirect(url_for('main.teacher_attendance', class_id=class_id, student_id=student_id))

    # Get students from the selected class
    student_ids = []
    if selected_class_id:
        selected_class = next((cls for cls in assigned_classes if cls["class_id"] == selected_class_id), None)
        if selected_class:
            student_ids = selected_class.get('students_enrolled', [])

            # Auto-select first student if none is selected
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

# Works with Teacher Attendance to students based on selected class
@main.route('/get_students/<class_id>')
def get_students(class_id):

    teacher_id = session.get('username')

    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id}) # Matches session username to teacher_id in Teacher Profile
    if not teacher_profile:
        return {"error": "Teacher profile not found"}, 404 # Error if teacher_id not located

    # Find the selected class inside assigned_classes array
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

# View Student Profiles
@main.route('/teacher_student_profiles')
def teacher_student_profiles():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_student_profiles.html')
    return redirect(url_for('auth.home'))

# Matches information from Teacher Profile to Student Profile
@main.route('/profile_get_students', methods=['GET'])
def profile_get_students():
    # Matches signed-in Teacher Username to teacher_id in Teacher Profile collection
    teacher_id = session.get('username')
    teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": teacher_id})
    
    if not teacher_profile:
        return jsonify({"error": "Teacher profile not found"}), 404
    
    # Retrieves assigned_classes from the Teacher Profile Collection
    assigned_classes = teacher_profile.get("assigned_classes", [])
    student_ids = [student for cls in assigned_classes for student in cls.get("students_enrolled", [])] # Obtains students enrolled from the students_enrolled array
    
    # Matches students enrolled to student_id in the Student Profile collection
    students = mongo.db["Student Profile"].find({"student_id": {"$in": student_ids}}, 
                                                  {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}) # Gets the student ID, first name, and last name
    student_list = [{"id": s["student_id"], "name": f"{s['first_name']} {s['last_name']}"} for s in students]
    
    return jsonify({"students": student_list})

# Retrieves the student profile information from the Student Profile collection
@main.route('/get_student_profile/<student_id>', methods=['GET'])
def get_student_profile(student_id):
    # Matches student ID obtained to the student_id in the Student Profile collection
    student = mongo.db["Student Profile"].find_one({"student_id": student_id}, {"_id": 0})
    
    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Format Date of Birth from Student Profile collection as MM/DD/YYYY
    if "date_of_birth" in student:
        student["date_of_birth"] = datetime.strptime(student["date_of_birth"], "%Y-%m-%d").strftime("%m-%d-%Y")

    # Populate Emergency Contact from Student Profile collection
    if "emergency_contacts" in student:
        for contact in student["emergency_contacts"]:
            if "relation" not in contact or not contact["relation"]:
                contact["relation"] = "Unknown"

    # Retrieve Bus Schedule from Bus Routes Collection student array
    bus_info = mongo.db["Bus Routes"].find_one({"students": student_id}, {"_id": 0})
    
    if bus_info:
        stops = bus_info.get("stops", [])
        student["bus_schedule"] = "<br>".join(
            [f"Stop: {stop['stop_name']}, Pickup: {stop['pickup_time']}, Dropoff: {stop['dropoff_time']}" for stop in stops] # retrieves stops, pickup, and drop off
        )
    else:
        student["bus_schedule"] = "No bus schedule available"
    
    return jsonify(student)

# Admin Access Pages
# Admin Dashboard
@main.route('/admin_dashboard')
def admin_dashboard():
    if verify_role('Administrator'):
        name = session.get('name', 'Administrator')
        return render_template('admin/admin_dashboard.html', name=name)
    return redirect(url_for('auth.home'))

# Admin update or view users
@main.route('/manage_users_permissions', methods=['GET', 'POST'])
def manage_users_permissions():
    if 'role' not in session or session['role'] != 'Administrator': # Denies access if user is not an Administrator
        flash("Access denied. Only administrators can manage users.", "error")
        return redirect(url_for('auth.home'))

    # Allows Admin user to search for specific user based on username or email address in users collection
    users = []
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        if search_query:
            users = list(mongo.db.users.find({
                "$or": [
                    {"username": {'$regex': search_query, '$options': 'i'}},
                    {"email": {'$regex': search_query, '$options': 'i'}}
                ]
            }))
    
    return render_template('admin/manage_users_permissions.html', users=users)

# Update users information (username, email, role, or password)
@main.route('/update_user', methods=['POST'])
def update_user():
    if 'role' not in session or session['role'] != 'Administrator':
        flash("Access denied.", "error")
        return redirect(url_for('auth.home'))
    
    username = request.form.get('username')
    new_value = request.form.get('new_value')
    update_field = request.form.get('update_field')
    admin_username = session.get('username')
    
    if not username or not new_value or not update_field:
        flash("All fields are required.", "error")
        return redirect(url_for('main.manage_users_permissions'))
    
    # Get the current user record before update.
    user_before = mongo.db.users.find_one({"username": username})
    if not user_before:
        flash("User not found.", "error")
        return redirect(url_for('main.manage_users_permissions'))
    
    # Store the previous value of the field being updated.
    previous_value = "hashed" if update_field == "password" else user_before.get(update_field, "Unknown") # Returns value 'hashed' for Previous Value if updating password
    
    if update_field == "password":
        new_value = generate_password_hash(new_value) # Hashes new password before storing in MongoDB
    
    # Perform the update in MongoDB
    mongo.db.users.update_one({"username": username}, {"$set": {update_field: new_value}})
    
    # If username was updated, query using the new value.
    query = {"username": new_value} if update_field == "username" else {"username": username}
    updated_user = mongo.db.users.find_one(query)
    
    # Create the audit log entry using the updated values.
    audit_entry = {
        "_id": ObjectId(),
        "admin_user": admin_username,
        "users_name": updated_user.get("name"),
        "username": updated_user.get("username"),
        "email": updated_user.get("email"),
        "user_role": updated_user.get("role"),
        "updated_item": update_field,
        "previous_value": previous_value,
        "date_time": datetime.now().strftime('%m/%d/%Y %I:%M %p')
    }
    mongo.db.audit_log.insert_one(audit_entry)
    
    flash("User information updated successfully.", "success")
    return redirect(url_for('main.manage_users_permissions'))

# Audit Log page for updated items
@main.route('/audit_log')
def audit_log():
    if 'role' not in session or session['role'] != 'Administrator':
        flash("Access denied.", "error")
        return redirect(url_for('auth.home'))

    audit_logs = list(mongo.db.audit_log.find({})) # Lists values retained in the audit_log collection
    return render_template('admin/audit_log.html', audit_logs=audit_logs)

# Parent Access Pages
# Parent Dashboard
@main.route('/parent_dashboard')
def parent_dashboard():
    if verify_role('Parent'):
        name = session.get('name', 'Parent')
        return render_template('parent/parent_dashboard.html', name=name)
    return redirect(url_for('auth.home'))

# View linked students attendance records
@main.route('/parent_attendance_records')
def parent_attendance_records():
    if verify_role('Parent'):
        return render_template('parent/parent_attendance_records.html')
    return redirect(url_for('auth.home'))


@main.route('/api/parent_students', methods=['GET'])
def api_parent_students():
    # Ensure the user logged in is a Parent
    parent_id = session.get('username')
    if not parent_id:
        return jsonify({"error": "User not logged in"}), 401

    # Retrieve the Parent Profile using the session's username (matches parent_id)
    parent_profile = mongo.db["Parent Profile"].find_one({"parent_id": parent_id})
    if not parent_profile:
        return jsonify({"error": "Parent profile not found"}), 404

    # Extract linked students from the parent profile
    linked_students = parent_profile.get("linked_students", [])
    student_ids = [student.get("student_id") for student in linked_students]

    # Query the Student Profile collection to get each student's first and last names
    students = list(mongo.db["Student Profile"].find(
        {"student_id": {"$in": student_ids}},
        {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}
    ))

    # Create a list of student objects with id and full name
    student_list = [{
        "id": s["student_id"],
        "name": f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
    } for s in students]

    return jsonify({"students": student_list})


@main.route('/api/attendance_records', methods=['GET'])
def api_attendance_records():
    # Get the student_id from the request parameters
    student_id = request.args.get("student_id")
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    # Calculate the date 30 days ago (assumes Attendance.date is stored as 'YYYY-MM-DD')
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Query the Attendance collection for records of the specified student that are within the last 30 days
    records = list(mongo.db.Attendance.find(
        {
            "student_id": student_id,
            "date": {"$gte": cutoff_date}
        },
        {"class_id": 1, "date": 1, "status": 1, "_id": 0}
    ))

    return jsonify({"records": records})

# View linked students bus schedule
@main.route('/parent_bus_schedule')
def parent_bus_schedule():
    if verify_role('Parent'):
        return render_template('parent/parent_bus_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/api/parent_students_bus', methods=['GET'])
def api_parent_students_bus():
    # Ensure the parent is logged in
    parent_id = session.get('username')
    if not parent_id:
        return jsonify({"error": "User not logged in"}), 401

    # Retrieve the Parent Profile using the parent_id
    parent_profile = mongo.db["Parent Profile"].find_one({"parent_id": parent_id})
    if not parent_profile:
        return jsonify({"error": "Parent profile not found"}), 404

    # Extract linked students and collect student_ids
    linked_students = parent_profile.get("linked_students", [])
    student_ids = [student.get("student_id") for student in linked_students]

    # Query Student Profile collection to get first_name and last_name for each linked student
    students = list(mongo.db["Student Profile"].find(
        {"student_id": {"$in": student_ids}},
        {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}
    ))

    # Build the response list with full names
    student_list = [{
        "id": s["student_id"],
        "name": f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
    } for s in students]

    return jsonify({"students": student_list})


@main.route('/api/parent_bus_schedule', methods=['GET'])
def api_parent_bus_schedule():
    # Get the student_id from query parameters
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    # Query the Student Profile collection for the bus_schedule details
    student = mongo.db["Student Profile"].find_one(
        {"student_id": student_id},
        {"bus_schedule": 1, "_id": 0}
    )

    # If no student or no bus_schedule found, return an empty bus_schedule object
    if not student or "bus_schedule" not in student:
        return jsonify({"bus_schedule": {}}), 200

    # Get the bus_schedule object (which includes stop_name)
    bus_schedule = student["bus_schedule"]

    # Optionally, ensure stop_name exists
    if "stop_name" not in bus_schedule:
        bus_schedule["stop_name"] = "N/A"

    return jsonify({"bus_schedule": bus_schedule})

# Parents view linked students class schedule
@main.route('/parent_view_class_schedule')
def parent_view_class_schedule():
    if verify_role('Parent'):
        return render_template('parent/parent_view_class_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/api/parent_class_schedule', methods=['GET'])
def api_parent_class_schedule():
    # Retrieves linked students
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    # Query Teacher Profile collection for teachers whose assigned_classes include the student_id
    teacher_profiles = list(mongo.db["Teacher Profile"].find(
        {"assigned_classes.students_enrolled": student_id},
        {"teacher_id": 1, "name": 1, "email": 1, "phone": 1, "assigned_classes": 1, "_id": 0}
    ))

    # Query the Student Profile collection to get enrolled_classes for the student
    student = mongo.db["Student Profile"].find_one(
        {"student_id": student_id},
        {"enrolled_classes": 1, "_id": 0}
    )
    enrolled_classes = student.get("enrolled_classes", []) if student else []
    # Build a mapping from class_id to schedule from the student's enrolled_classes
    schedule_mapping = {cls.get("class_id"): cls.get("schedule", "N/A") for cls in enrolled_classes}

    schedule = []
    for teacher in teacher_profiles:
        for cls in teacher.get("assigned_classes", []):
            # Only include the class if the student is enrolled in it
            if student_id in cls.get("students_enrolled", []):
                class_id = cls.get("class_id", "")
                # Ensure the class_id from the teacher's record matches one in the student's enrolled_classes
                class_schedule = schedule_mapping.get(class_id, "N/A")
                schedule.append({
                    "teacher_name": teacher.get("name", ""),
                    "class_number": class_id,
                    "class_name": cls.get("subject", ""),
                    "email": teacher.get("email", ""),
                    "phone": teacher.get("phone", ""),
                    "schedule": class_schedule
                })
    return jsonify({"schedule": schedule})

# View linked students grades
@main.route('/parent_view_student_grades')
def parent_view_student_grades():
    if verify_role('Parent'):
        return render_template('parent/parent_view_student_grades.html')
    return redirect(url_for('auth.home'))


@main.route('/api/parent_students_gradeassignments', methods=['GET'])
def api_parent_students_gradeassignments():
    # Ensure the parent is logged in
    parent_id = session.get('username')
    if not parent_id:
        return jsonify({"error": "User not logged in"}), 401

    # Retrieve the Parent Profile using the parent_id
    parent_profile = mongo.db["Parent Profile"].find_one({"parent_id": parent_id})
    if not parent_profile:
        return jsonify({"error": "Parent profile not found"}), 404

    # Extract linked students and collect student_ids
    linked_students = parent_profile.get("linked_students", [])
    student_ids = [student.get("student_id") for student in linked_students]

    # Query Student Profile collection to get first_name and last_name for each linked student
    students = list(mongo.db["Student Profile"].find(
        {"student_id": {"$in": student_ids}},
        {"student_id": 1, "first_name": 1, "last_name": 1, "_id": 0}
    ))

    # Build the response list with full names
    student_list = [{
        "id": s["student_id"],
        "name": f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
    } for s in students]

    return jsonify({"students": student_list})


@main.route('/api/parent_grades', methods=['GET'])
def api_parent_grades():
    student_id = request.args.get('student_id')
    if not student_id:
        return jsonify({"error": "Missing student_id"}), 400

    # Calculate cutoff date: assignments assigned within the last 30 days
    cutoff_date = (datetime.now() - timedelta(days=30)).date()

    # Get all assignments for the student from assignments_grades collection
    assignments = list(mongo.db["assignments_grades"].find(
        {"student_id": student_id},
        {"class_number": 1, "assignment_name": 1, "assigned_date": 1, "due_date": 1, "grade": 1, "_id": 0}
    ))

    filtered_assignments = []
    for assignment in assignments:
        # Parse assigned_date with fallback
        try:
            dt_assigned = datetime.strptime(assignment['assigned_date'], "%m/%d/%Y")
        except ValueError:
            try:
                dt_assigned = datetime.strptime(assignment['assigned_date'], "%Y-%m-%d")
            except Exception as e:
                print("Error parsing assigned_date for assignment:", assignment, "Error:", e)
                continue

        # Parse due_date with fallback
        try:
            dt_due = datetime.strptime(assignment['due_date'], "%m/%d/%Y")
        except ValueError:
            try:
                dt_due = datetime.strptime(assignment['due_date'], "%Y-%m-%d")
            except Exception as e:
                print("Error parsing due_date for assignment:", assignment, "Error:", e)
                continue

        # Compare only the date parts
        if dt_assigned.date() >= cutoff_date:
            # Reformat both dates to MM/DD/YYYY
            assignment['assigned_date'] = dt_assigned.strftime("%m/%d/%Y")
            assignment['due_date'] = dt_due.strftime("%m/%d/%Y")
            filtered_assignments.append(assignment)

    return jsonify({"assignments": filtered_assignments})