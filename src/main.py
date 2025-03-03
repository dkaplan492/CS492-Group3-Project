from flask import jsonify, Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from bson.json_util import dumps
from datetime import datetime, timedelta
from src import mongo
import uuid

main = Blueprint('main', __name__)

# Database connection
db = mongo.db

# Defined database collections
bus_schedule_collection = db["Bus_Schedule"]
assignments_collection = db["Assignments"]
attendance_collection = db["Attendance"]
students_collection = db["Student_Profile"]
parents_collection = db["Parent_Profile"]


# Helper function to verify user role
def verify_role(required_role):
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
@main.route("/student_assignments_homework")
def student_assignments_homework():
    student_id = session.get('student_id')
    assignments = list(assignments_collection.find({"student_id": student_id}))
    return render_template("student/student_assignments_homework.html", assignments=assignments)

# Student Bus Schedule
@main.route("/student_bus_schedule")
def student_bus_schedule():
    student_id = session.get('student_id')
    bus_schedule = list(bus_schedule_collection.find({"student_id": student_id}))
    return render_template("student/student_bus_schedule.html", bus_schedule=bus_schedule)

# Student class schedule
@main.route('/student_classes_and_grades')
def student_classes_and_grades():
    if verify_role('Student'):
        return render_template('student/student_classes_and_grades.html')
    return redirect(url_for('auth.home'))

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

# Helper function to get student_id from the Parent Profile collection
def get_student_id(parent_id):
    parent = parents_collection.find_one({"parent_id": parent_id})
    return parent.get("student_id") if parent else None

# Parents view attendance for their linked children
@main.route("/parent_attendance_records")
def parent_attendance_records():
    parent_id = session.get('parent_id')
    student_id = get_student_id(parent_id)
    if not student_id:
        flash("Student not found for this parent!", "danger")

        return render_template("parent/parent_attendance_records.html", attendance_records=[])
    
    attendance_records = list(attendance_collection.find({"student_id": student_id}))
    return render_template("parent/parent_attendance_records.html", attendance_records=attendance_records)

# Parents view Bus Schedule for their linked children
@main.route("/parent_bus_schedule")
def parent_bus_schedule():
    parent_id = session.get('parent_id')
    student_id = get_student_id(parent_id)
    if not student_id:
        flash("Student not found for this parent!", "danger")
        
        return render_template("parent/parent_bus_schedule.html", bus_schedule=[])
    
    bus_schedule = list(bus_schedule_collection.find({"student_id": student_id}))
    return render_template("parent/parent_bus_schedule.html", bus_schedule=bus_schedule)

# Parents view Class Schedule for their linked children
@main.route('/parent_view_class_schedule')
def parent_view_class_schedule():
    if verify_role('Parent'):
        return render_template('parent/parent_view_class_schedule.html')
    return redirect(url_for('auth.home'))

# Parents view grades for their linked children
@main.route('/parent_view_student_grades')
def parent_view_student_grades():
    if verify_role('Parent'):
        return render_template('parent/parent_view_student_grades.html')
    return redirect(url_for('auth.home'))