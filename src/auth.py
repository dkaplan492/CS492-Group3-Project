from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from werkzeug.security import check_password_hash
from src import mongo

auth = Blueprint('auth', __name__)

@auth.route('/')
def home():
    """Welcome homepage."""
    return render_template('home.html', active_tab='home')


@auth.route('/login', methods=['POST'])
def login():
    """Login route with role validation."""
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    # Query the user from the MongoDB collection
    user = mongo.db.users.find_one({"username": username})

    if user and check_password_hash(user['password'], password):
        if user['role'] == role:
            session['username'] = user['username']
            session['role'] = user['role']
            session['first_name'] = user.get('first_name', role.capitalize())
            print(f"[DEBUG] Login successful - Username: {user['username']}, Role: {user['role']}")

            # Redirect to the appropriate dashboard based on role
            if role == 'Student':
                return redirect(url_for('main.student_dashboard'))
            elif role == 'Parent':
                return redirect(url_for('main.parent_dashboard'))
            elif role == 'Teacher':
                return redirect(url_for('main.teacher_dashboard'))
            elif role == 'Administrator':
                return redirect(url_for('main.admin_dashboard'))
        else:
            print(f"[DEBUG] Role mismatch - Username: {username}")
            flash("Invalid username or password.", category="error")
    else:
        print(f"[DEBUG] Invalid login - Username: {username}")
        flash("Invalid username or password.", category="error")

    # Render the login page with the active tab set to the role
    return render_template('home.html', active_tab=role.lower())


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset requests."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')

        # Query the user from the MongoDB collection
        user = mongo.db.users.find_one({"username": username, "role": role})

        if user and user['email'] == email:  # Assuming an 'email' field exists in the MongoDB document
            # Handle password reset logic (e.g., send reset link via email)
            print(f"[DEBUG] Password reset initiated for {username}, Role: {role}")
            flash(f"A password reset link has been sent to {email}.")
            return redirect(url_for('auth.home'))
        else:
            print(f"[DEBUG] Invalid reset attempt for {username}, Role: {role}")
            flash("Invalid username, email, or role.")
            return render_template('reset_password.html')

    return render_template('reset_password.html')


@auth.route('/reset_password_page')
def reset_password_page():
    """Redirect to the reset password page."""
    return render_template('reset_password.html')


@auth.route('/logout')
def logout():
    """Logout route for all users."""
    print(f"[DEBUG] Logging out - Username: {session.get('username', 'Unknown')}")
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('auth.home'))