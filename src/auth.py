from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from werkzeug.security import check_password_hash
from src import mongo

auth = Blueprint('auth', __name__)

@auth.route('/')
def home():
    # Use the active_tab parameter from the query string; default to 'home'
    active_tab = request.args.get('active_tab', 'home')
    return render_template('home.html', active_tab=active_tab)

# Login route with role validation
@auth.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    # Map form roles to the corresponding tab id in home.html
    role_to_tab = {
        "Student": "students",
        "Parent": "parents",
        "Teacher": "teachers",
        "Administrator": "administrators"
    }
    active_tab = role_to_tab.get(role, "home")

    # Query the user from the MongoDB users collection
    user = mongo.db.users.find_one({"username": username})

    if user and check_password_hash(user['password'], password):
        if user['role'] == role:
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user.get('name', role.capitalize())
            print(f"[DEBUG] Login successful - Username: {user['username']}, Role: {user['role']}") # Debugging output for error checking

            # Redirect to appropriate dashboard depending on user role
            if role == 'Student':
                return redirect(url_for('main.student_dashboard'))
            elif role == 'Parent':
                return redirect(url_for('main.parent_dashboard'))
            elif role == 'Teacher':
                teacher_profile = mongo.db["Teacher Profile"].find_one({"teacher_id": username})
                session['teacher_profile'] = {
                    "teacher_id": teacher_profile["teacher_id"],
                    "name": teacher_profile["name"],
                    "assigned_classes": teacher_profile["assigned_classes"]
                }
                return redirect(url_for('main.teacher_dashboard'))
            elif role == 'Administrator':
                return redirect(url_for('main.admin_dashboard'))
            else:
                flash("Incorrect credentials. Please try again.", category="error") # Error message on tab if credentials do not match role, or username/password do not match
        else:
            print(f"[DEBUG] Role mismatch - Username: {username}")
            flash("Incorrect credentials. Please try again.", category="error")
    else:
        print(f"[DEBUG] Invalid login - Username: {username}")
        flash("Incorrect credentials. Please try again.", category="error")

    # Redirect back to the home page with the current tab active so the error message shows only there
    return redirect(url_for('auth.home', active_tab=active_tab))

# Logout route
@auth.route('/logout')
def logout():
    """Logout route for all users."""
    print(f"[DEBUG] Logging out - Username: {session.get('username', 'Unknown')}")
    session.clear()
    return redirect(url_for('auth.home'))
