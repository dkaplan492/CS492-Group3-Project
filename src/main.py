from flask import Blueprint, render_template, session, redirect, url_for, flash
from src import mongo

main = Blueprint('main', __name__)

# Helper function to check role
def verify_role(required_role):
    """Verify if the logged-in user has the required role."""
    if 'role' in session and session['role'] == required_role:
        return True
    flash(f'Unauthorized access. Please log in as a {required_role.lower()}.')
    return False

# Student Dashboard
@main.route('/student_dashboard')
def student_dashboard():
    if verify_role('Student'):
        first_name = session.get('first_name', 'Student')
        return render_template('student/student_dashboard.html', name=first_name)
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


@main.route('/student_class_announcements')
def student_class_announcements():
    if verify_role('Student'):
        return render_template('student/student_class_announcements.html')
    return redirect(url_for('auth.home'))


@main.route('/student_classes_and_grades')
def student_classes_and_grades():
    if verify_role('Student'):
        return render_template('student/student_classes_and_grades.html')
    return redirect(url_for('auth.home'))


@main.route('/student_profile_settings')
def student_profile_settings():
    if verify_role('Student'):
        return render_template('student/student_profile_settings.html')
    return redirect(url_for('auth.home'))


@main.route('/student_teacher_communication')
def student_teacher_communication():
    if verify_role('Student'):
        return render_template('student/student_teacher_communication.html')
    return redirect(url_for('auth.home'))


# Teacher Dashboard
@main.route('/teacher_dashboard')
def teacher_dashboard():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_dashboard.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_assign_grades')
def teacher_assign_grades():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_assign_grades.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_attendance')
def teacher_attendance():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_attendance.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_bus_schedule_lookup')
def teacher_bus_schedule_lookup():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_bus_schedule_lookup.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_class_announcements')
def teacher_class_announcements():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_class_announcements.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_received_messages')
def teacher_received_messages():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_received_messages.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_reporting')
def teacher_reporting():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_reporting.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_student_profiles')
def teacher_student_profiles():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_student_profiles.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_view_schedule')
def teacher_view_schedule():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_view_schedule.html')
    return redirect(url_for('auth.home'))


@main.route('/teacher_manage_student_records')
def teacher_manage_student_records():
    if verify_role('Teacher'):
        return render_template('teacher/teacher_manage_student_records.html')
    return redirect(url_for('auth.home'))


# Admin Dashboard
@main.route('/admin_dashboard')
def admin_dashboard():
    if verify_role('Administrator'):
        return render_template('admin/admin_dashboard.html')
    return redirect(url_for('auth.home'))


@main.route('/manage_users_permissions')
def manage_users_permissions():
    if verify_role('Administrator'):
        return render_template('admin/manage_users_permissions.html')
    return redirect(url_for('auth.home'))


# Parent Dashboard
@main.route('/parent_dashboard')
def parent_dashboard():
    if verify_role('Parent'):
        return render_template('parent/parent_dashboard.html')
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


@main.route('/parent_school_announcements')
def parent_school_announcements():
    if verify_role('Parent'):
        return render_template('parent/parent_school_announcements.html')
    return redirect(url_for('auth.home'))


@main.route('/parent_teacher_communication')
def parent_teacher_communication():
    if verify_role('Parent'):
        return render_template('parent/parent_teacher_communication.html')
    return redirect(url_for('auth.home'))


@main.route('/parent_update_student_info')
def parent_update_student_info():
    if verify_role('Parent'):
        return render_template('parent/parent_update_student_info.html')
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