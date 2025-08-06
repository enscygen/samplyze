import os
import sys
from flask import Flask, render_template, redirect, url_for, flash, request, abort, send_from_directory, make_response, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import pytz
from markupsafe import Markup, escape
from jinja2.filters import pass_eval_context
import socket
import csv
import io
from io import BytesIO
import barcode
from barcode.writer import ImageWriter

# Import forms, models, and utility functions from other files
from forms import LoginForm, StaffForm, EditStaffForm, ApplicantForm, NSCForm, SampleForm, DiagnosisForm, LabSettingsForm, ChangePasswordForm, DBMigrationForm, RoleForm
from models import db, User, Department, Applicant, ConsultancyNSC, NSCImage, SampleSC, SampleImage, Diagnosis, LabSettings, DiagnosisAttachment, MailRecipient, AuditLog, Role, Permission, KnowledgeBase, PermissionNames, Visitor
from utils import generate_uid, generate_sample_uid
# Import the blueprints
from fileshare import fileshare_bp
from mail import mail_bp
from knowledge_base import kb_bp
from migrate_data import run_migration
from equipment import equipment_bp
from backup_restore import backup_bp
from roles import roles_bp
from visitors import visitors_bp
# NEW: Import the new decorator
from decorators import permission_required
from templating import templating_bp

# --- PyInstaller Path Correction ---
if getattr(sys, 'frozen', False):
    basedir = sys._MEIPASS
    template_folder = os.path.join(basedir, 'templates')
    static_folder = os.path.join(basedir, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app = Flask(__name__)
 
# --- App Configuration using the new 'basedir' ---
app.config['SECRET_KEY'] = 'a-very-secret-key-that-should-be-changed'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance/laboratory.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'appfiles', 'uploads')
app.config['SHARED_FOLDER'] = os.path.join(basedir, 'appfiles', 'shared_files')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # 50 MB upload limit

# Ensure the necessary data folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['SHARED_FOLDER']):
    os.makedirs(app.config['SHARED_FOLDER'])
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

# --- Extensions Initialization ---
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Register the blueprints
app.register_blueprint(fileshare_bp)
app.register_blueprint(mail_bp)
app.register_blueprint(kb_bp)
app.register_blueprint(equipment_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(visitors_bp)
app.register_blueprint(templating_bp)

# --- Custom Filter for Jinja2 ---
@app.template_filter('nl2br')
def nl2br_filter(s):
    if s is None:
        return ''
    return Markup(escape(s).replace('\n', '<br>\n'))


# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Helper Functions ---
def get_ist_time():
    """Returns the current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def delete_file(filename):
    """Deletes a file from the UPLOAD_FOLDER."""
    if not filename: return
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting file {filename}: {e}") # Log error
        
def log_action(action, user_id=None):
    """Logs an action to the audit trail."""
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id
    
    log_entry = AuditLog(user_id=user_id, action=action)
    db.session.add(log_entry)
    db.session.commit()
     
@app.route('/about')
@login_required
def about():
    return render_template('about.html', title='About Samplyze')

@app.route('/barcode/<data>')
def generate_barcode(data):
    try:
        code128 = barcode.get_barcode_class('code128')
        writer = ImageWriter()
        barcode_image = code128(data, writer=writer)
        
        buffer = BytesIO()
        barcode_image.write(buffer, options={'module_height': 5.0})
        buffer.seek(0)
        
        return send_file(buffer, mimetype='image/png')
    except Exception as e:
        print(f"Error generating barcode: {e}")
        return abort(500)

@app.route('/admin/audit-log')
@admin_required
def audit_log():
    search_query = request.args.get('q', '')
    
    query = AuditLog.query

    if search_query:
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(f'%{search_query}%'),
                AuditLog.action.ilike(f'%{search_query}%')
            )
        )
        
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_log.html', title='Audit Log', logs=logs, search_query=search_query)

@app.route('/admin/audit-log/export')
@admin_required
def audit_log_export():
    search_query = request.args.get('q', '')
    
    query = AuditLog.query

    if search_query:
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(f'%{search_query}%'),
                AuditLog.action.ilike(f'%{search_query}%')
            )
        )
        
    logs = query.order_by(AuditLog.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Timestamp (IST)', 'User', 'Action'])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user.name if log.user else 'System',
            log.action
        ])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=audit_log_export.csv"}
    )

@app.route('/network-info')
@login_required
def network_info():
    try:
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)
    except Exception:
        server_ip = '127.0.0.1'

    client_ip = request.remote_addr
    lan_url = f"http://{server_ip}:8000"

    return render_template('staff/network_info.html', 
                           title='Network Info', 
                           server_ip=server_ip, 
                           client_ip=client_ip, 
                           lan_url=lan_url)


# --- Main Routes ---
# Replace the existing index function in app.py with this one

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        
        # --- NEW: Smart Redirect based on Permissions ---
        # This checks permissions in a specific order and redirects to the first page the user can access.
        permission_map = [
            (PermissionNames.CAN_ACCESS_APPLICANT_SERVICES, 'dashboard'),
            (PermissionNames.CAN_ACCESS_SAMPLING_SERVICES, 'all_samples'),
            (PermissionNames.CAN_ACCESS_VISITOR_MANAGEMENT, 'visitors.dashboard'),
            (PermissionNames.CAN_ACCESS_EQUIPMENT_LOGGING, 'equipment.dashboard'),
            (PermissionNames.CAN_ACCESS_FILE_SHARING, 'fileshare.dashboard'),
            (PermissionNames.CAN_ACCESS_MAIL, 'mail.inbox'),
            (PermissionNames.CAN_ACCESS_KNOWLEDGE_BASE, 'kb.dashboard')
        ]

        for permission, endpoint in permission_map:
            if current_user.can(permission):
                return redirect(url_for(endpoint))
        
        # If the user has no permissions at all, log them out with a message.
        flash("Your role does not have any permissions assigned. Please contact an administrator.", "warning")
        return redirect(url_for('logout'))

    return redirect(url_for('login'))

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            log_action(f"User '{user.username}' logged in.")
            next_page = request.args.get('next')
            flash('Logged in successfully!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    log_action(f"User '{current_user.username}' logged out.")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Admin Routes ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    staff_count = User.query.filter(User.role.has(name='Admin') == False).count()
    applicant_count = Applicant.query.count()
    sample_count = SampleSC.query.count()
    return render_template('admin/dashboard.html', title='Admin Dashboard', staff_count=staff_count, applicant_count=applicant_count, sample_count=sample_count)

@app.route('/admin/staff', methods=['GET', 'POST'])
@admin_required
def manage_staff():
    form = StaffForm()
    form.department.choices = [(d.id, d.name) for d in Department.query.order_by('name').all()]
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by('name').all()]
    
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_staff = User(username=form.staff_id.data, name=form.name.data, password_hash=hashed_password, role_id=form.role_id.data, department_id=form.department.data)
        db.session.add(new_staff)
        db.session.commit()
        log_action(f"Admin created new staff member '{new_staff.name}' (Username: {new_staff.username}).")
        flash('New staff member has been added.', 'success')
        return redirect(url_for('manage_staff'))
    staff_list = User.query.filter(User.role.has(name='Admin') == False).all()
    return render_template('admin/manage_staff.html', title='Manage Staff', form=form, staff_list=staff_list)

@app.route('/admin/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
@admin_required
def edit_staff(staff_id):
    staff = User.query.get_or_404(staff_id)
    form = EditStaffForm(obj=staff)
    form.department.choices = [(d.id, d.name) for d in Department.query.order_by('name').all()]
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by('name').all()]
    
    if form.validate_on_submit():
        staff.name = form.name.data
        staff.department_id = form.department.data
        staff.role_id = form.role_id.data
        if form.password.data:
            staff.password_hash = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        db.session.commit()
        log_action(f"Admin updated details for staff member '{staff.name}'.")
        flash('Staff member has been updated.', 'success')
        return redirect(url_for('manage_staff'))
    elif request.method == 'GET':
        form.department.data = staff.department_id
        form.role_id.data = staff.role_id

    return render_template('admin/edit_staff.html', title='Edit Staff', form=form, staff=staff)

@app.route('/admin/staff/delete/<int:staff_id>', methods=['POST'])
@admin_required
def delete_staff(staff_id):
    staff_to_delete = User.query.get_or_404(staff_id)
    if staff_to_delete.is_admin:
        flash('Admins cannot be deleted from this interface.', 'danger')
        return redirect(url_for('manage_staff'))
    db.session.delete(staff_to_delete)
    db.session.commit()
    log_action(f"Admin deleted staff member '{staff_to_delete.name}'.")
    flash(f'Staff member {staff_to_delete.name} has been deleted.', 'success')
    return redirect(url_for('manage_staff'))


@app.route('/admin/departments', methods=['GET', 'POST'])
@admin_required
def manage_departments():
    if 'name' in request.form:
        dept_name = request.form.get('name')
        if dept_name and not Department.query.filter_by(name=dept_name).first():
            new_dept = Department(name=dept_name)
            db.session.add(new_dept)
            db.session.commit()
            log_action(f"Admin created new department '{new_dept.name}'.")
            flash(f'Department "{dept_name}" added.', 'success')
        else:
            flash('Department name cannot be empty or already exists.', 'danger')
        return redirect(url_for('manage_departments'))
    departments = Department.query.all()
    return render_template('admin/manage_departments.html', title='Manage Departments', departments=departments)

@app.route('/admin/department/delete/<int:dept_id>', methods=['POST'])
@admin_required
def delete_department(dept_id):
    dept_to_delete = Department.query.get_or_404(dept_id)
    db.session.delete(dept_to_delete)
    db.session.commit()
    log_action(f"Admin deleted department '{dept_to_delete.name}'.")
    flash(f'Department "{dept_to_delete.name}" has been deleted. Staff and samples have been unassigned.', 'success')
    return redirect(url_for('manage_departments'))


@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def lab_settings():
    settings = LabSettings.query.first()
    form = LabSettingsForm(obj=settings)
    if form.validate_on_submit():
        settings.lab_name = form.lab_name.data
        settings.description = form.description.data
        settings.address = form.address.data
        settings.contact_number = form.contact_number.data
        settings.email = form.email.data

        if form.logo.data:
            if settings.logo_path:
                delete_file(settings.logo_path)
            
            logo_file = form.logo.data
            filename = secure_filename(logo_file.filename)
            unique_filename = f"logo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            logo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            settings.logo_path = unique_filename

        db.session.commit()
        log_action("Admin updated laboratory settings.")
        flash('Lab settings updated successfully.', 'success')
        return redirect(url_for('lab_settings'))
    return render_template('admin/settings.html', title='Lab Settings', form=form, settings=settings)

@app.route('/admin/change-password', methods=['GET', 'POST'])
@admin_required
def admin_change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if check_password_hash(current_user.password_hash, form.old_password.data):
            current_user.password_hash = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
            db.session.commit()
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect current password.', 'danger')
    return render_template('admin/change_password.html', title='Change Password', form=form)

@app.route('/admin/migrate', methods=['GET', 'POST'])
@admin_required
def migrate_database():
    form = DBMigrationForm()
    if form.validate_on_submit():
        old_db_file = form.db_file.data
        
        temp_path = os.path.join('instance', 'temp_old_db.db')
        old_db_file.save(temp_path)
        
        current_db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')

        success, message = run_migration(new_db_path=current_db_path, old_db_path=temp_path)

        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

        return redirect(url_for('admin_dashboard'))

    return render_template('admin/migrate.html', title='Migrate Database', form=form)


# --- Staff/Consultant Routes ---
@app.route('/dashboard')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def dashboard():
    applicants = Applicant.query.order_by(Applicant.created_at.desc()).all()
    return render_template('staff/dashboard.html', title='OA Dashboard', applicants=applicants)

@app.route('/samples')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def all_samples():
    assigned_to_me = request.args.get('assigned_to_me', 'false').lower() == 'true'
    
    query = SampleSC.query
    
    if assigned_to_me:
        query = query.filter_by(assigned_staff_id=current_user.id)
        
    samples = query.order_by(SampleSC.submission_date.desc()).all()
    
    return render_template('staff/all_samples.html', title='All Samples', samples=samples, assigned_to_me=assigned_to_me)

@app.route('/applicant/add', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def add_applicant():
    form = ApplicantForm()
    if form.validate_on_submit():
        new_applicant = Applicant(uid=generate_uid(), name=form.name.data, gender=form.gender.data, dob=form.dob.data, phone=form.phone.data, email=form.email.data, occupation=form.occupation.data, id_card_type=form.id_card_type.data, id_card_number=form.id_card_number.data, house_name=form.house_name.data, village=form.village.data, city=form.city.data, pincode=form.pincode.data, district=form.district.data, state=form.state.data, country=form.country.data, remarks=form.remarks.data, overview=form.overview.data)
        db.session.add(new_applicant)
        db.session.commit()
        log_action(f"Created new applicant '{new_applicant.name}' (UID: {new_applicant.uid}).")
        flash(f'New applicant {new_applicant.name} added with UID: {new_applicant.uid}', 'success')
        return redirect(url_for('dashboard'))
    return render_template('staff/add_applicant.html', title='Add New Applicant (OA)', form=form)

@app.route('/applicant/edit/<uid>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def edit_applicant(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    form = ApplicantForm(obj=applicant)
    if form.validate_on_submit():
        form.populate_obj(applicant)
        db.session.commit()
        log_action(f"Updated applicant '{applicant.name}' (UID: {applicant.uid}).")
        flash(f'Applicant {applicant.name} has been updated.', 'success')
        return redirect(url_for('view_applicant', uid=applicant.uid))
    return render_template('staff/edit_applicant.html', title='Edit Applicant', form=form, applicant=applicant)


@app.route('/applicant/view/<uid>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def view_applicant(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    return render_template('staff/view_applicant.html', title=f'Applicant: {applicant.name}', applicant=applicant)

@app.route('/applicant/delete/<uid>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def delete_applicant(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    
    for nsc in applicant.consultancies_nsc:
        for image in nsc.images:
            delete_file(image.image_path)
    for sample in applicant.samples_sc:
        for image in sample.images:
            delete_file(image.image_path)
        for diagnosis in sample.diagnoses:
            for attachment in diagnosis.attachments:
                delete_file(attachment.file_path)

    db.session.delete(applicant)
    db.session.commit()
    log_action(f"Deleted applicant '{applicant.name}' and all associated data.")
    flash(f'Applicant {applicant.name} and all associated data have been deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/applicant/<uid>/add_nsc', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def add_nsc(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    form = NSCForm()
    if request.method == 'GET':
        form.consultancy_datetime.data = get_ist_time()

    if form.validate_on_submit():
        dt = form.consultancy_datetime.data
        new_nsc = ConsultancyNSC(
            applicant_id=applicant.id, consultant_id=current_user.id, date=dt.date(),
            time=dt.time(), consultancy_type=form.consultancy_type.data, problem_issue=form.problem_issue.data,
            problem_with=form.problem_with.data, remedy_suggested=form.remedy_suggested.data, remarks=form.remarks.data
        )
        db.session.add(new_nsc)
        db.session.flush()

        i = 0
        while f'images-{i}' in request.files:
            image_file = request.files[f'images-{i}']
            caption_text = request.form.get(f'captions-{i}', '')
            if image_file:
                filename = secure_filename(image_file.filename)
                unique_filename = f"nsc_{new_nsc.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)
                
                nsc_image = NSCImage(consultancy_nsc_id=new_nsc.id, image_path=unique_filename, caption=caption_text)
                db.session.add(nsc_image)
            i += 1
        
        db.session.commit()
        log_action(f"Created new NSC for applicant '{applicant.name}'.")
        flash(f'New NSC record added for {applicant.name}.', 'success')
        return redirect(url_for('view_applicant', uid=applicant.uid))

    return render_template('staff/add_nsc.html', title='Add Non-Sample Consultancy', form=form, applicant=applicant)

@app.route('/nsc/view/<int:nsc_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def view_nsc(nsc_id):
    nsc = ConsultancyNSC.query.get_or_404(nsc_id)
    return render_template('staff/view_nsc.html', title='View NSC', nsc=nsc)

@app.route('/nsc/edit/<int:nsc_id>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def edit_nsc(nsc_id):
    nsc = ConsultancyNSC.query.get_or_404(nsc_id)
    form = NSCForm(obj=nsc, consultancy_datetime=datetime.combine(nsc.date, nsc.time))
    
    if form.validate_on_submit():
        dt = form.consultancy_datetime.data
        nsc.date = dt.date()
        nsc.time = dt.time()
        nsc.consultancy_type = form.consultancy_type.data
        nsc.problem_issue = form.problem_issue.data
        nsc.problem_with = form.problem_with.data
        nsc.remedy_suggested = form.remedy_suggested.data
        nsc.remarks = form.remarks.data

        images_to_delete = request.form.getlist('delete_images')
        for image_id in images_to_delete:
            image = NSCImage.query.get(image_id)
            if image and image.consultancy_nsc_id == nsc.id:
                delete_file(image.image_path)
                db.session.delete(image)

        i = 0
        while f'images-{i}' in request.files:
            image_file = request.files[f'images-{i}']
            caption_text = request.form.get(f'captions-{i}', '')
            if image_file:
                filename = secure_filename(image_file.filename)
                unique_filename = f"nsc_{nsc.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)
                
                nsc_image = NSCImage(consultancy_nsc_id=nsc.id, image_path=unique_filename, caption=caption_text)
                db.session.add(nsc_image)
            i += 1
        
        db.session.commit()
        flash('NSC record has been updated.', 'success')
        return redirect(url_for('view_nsc', nsc_id=nsc.id))
        
    return render_template('staff/edit_nsc.html', title='Edit NSC', form=form, nsc=nsc)

@app.route('/nsc/delete/<int:nsc_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def delete_nsc(nsc_id):
    nsc = ConsultancyNSC.query.get_or_404(nsc_id)
    applicant_uid = nsc.applicant.uid
    
    for image in nsc.images:
        delete_file(image.image_path)
        
    db.session.delete(nsc)
    db.session.commit()
    log_action(f"Deleted NSC (ID: {nsc_id}) for applicant '{nsc.applicant.name}'.")
    flash('NSC record and its images have been deleted.', 'success')
    return redirect(url_for('view_applicant', uid=applicant_uid))

@app.route('/applicant/<uid>/add_sample', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def add_sample(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    form = SampleForm()
    form.allotted_department_id.choices = [('', '--- Select Department ---')] + [(str(d.id), d.name) for d in Department.query.order_by('name').all()]
    form.assigned_staff_id.choices = [('', '--- Select Staff ---')] + [(str(u.id), u.name) for u in User.query.filter(User.role.has(name='Admin') == False).order_by('name').all()]

    if request.method == 'POST':
        form.current_status.data = 'Submitted'

    if form.validate_on_submit():
        new_sample = SampleSC(
            sample_uid=generate_sample_uid(), 
            applicant_id=applicant.id, 
            sample_name=form.sample_name.data,
            sample_type=form.sample_type.data, 
            collection_date=form.collection_date.data,
            primary_observations=form.primary_observations.data, 
            recommended_storage=form.recommended_storage.data,
            storage_location=form.storage_location.data, 
            allotted_department_id=form.allotted_department_id.data,
            assigned_staff_id=form.assigned_staff_id.data, 
            diagnostics_needed=form.diagnostics_needed.data,
            quality_check_data=form.quality_check_data.data, 
            hazard_control=form.hazard_control.data,
            dispose_before=form.dispose_before.data, 
            remarks=form.remarks.data
        )
        db.session.add(new_sample)
        db.session.flush() 

        i = 0
        while f'images-{i}' in request.files:
            image_file = request.files[f'images-{i}']
            caption_text = request.form.get(f'captions-{i}', '')
            if image_file:
                filename = secure_filename(image_file.filename)
                unique_filename = f"sample_{new_sample.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)
                sample_image = SampleImage(sample_sc_id=new_sample.id, image_path=unique_filename, caption=caption_text)
                db.session.add(sample_image)
            i += 1

        db.session.commit()
        log_action(f"Created new sample '{new_sample.sample_uid}' for applicant '{applicant.name}'.")
        flash(f'New sample {new_sample.sample_uid} has been added for {applicant.name}.', 'success')
        return redirect(url_for('view_sample', sample_uid=new_sample.sample_uid))
    return render_template('staff/add_sample.html', title='Add Sample Consultancy', form=form, applicant=applicant)


@app.route('/sample/<sample_uid>/add_diagnosis', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def add_diagnosis(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    form = DiagnosisForm()
    if form.validate_on_submit():
        new_diagnosis = Diagnosis(
            sample_sc_id=sample.id, 
            name=form.name.data, 
            title=form.title.data,
            description=form.description.data, 
            result=form.result.data,
            result_is_rich=form.is_rich_text.data
        )
        db.session.add(new_diagnosis)
        db.session.flush()

        i = 0
        while f'attachments-{i}' in request.files:
            file = request.files[f'attachments-{i}']
            caption_text = request.form.get(f'captions-{i}', '') 
            if file:
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                unique_filename = f"diag_{new_diagnosis.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{original_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                attachment = DiagnosisAttachment(
                    diagnosis_id=new_diagnosis.id, file_path=unique_filename,
                    original_filename=caption_text or original_filename, file_type=file_ext
                )
                db.session.add(attachment)
            i += 1

        db.session.commit()
        log_action(f"Added new diagnosis '{new_diagnosis.title}' to sample '{sample.sample_uid}'.")
        flash('New diagnosis and attachments have been added successfully.', 'success')
        return redirect(url_for('view_sample', sample_uid=sample.sample_uid))
    return render_template('staff/add_diagnosis.html', title='Add Diagnosis', form=form, sample=sample)

@app.route('/diagnosis/edit/<int:diagnosis_id>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def edit_diagnosis(diagnosis_id):
    diagnosis = Diagnosis.query.get_or_404(diagnosis_id)
    sample = diagnosis.sample
    form = DiagnosisForm(obj=diagnosis)
    if form.validate_on_submit():
        form.populate_obj(diagnosis)

        attachments_to_delete = request.form.getlist('delete_attachments')
        for attachment_id in attachments_to_delete:
            attachment = DiagnosisAttachment.query.get(attachment_id)
            if attachment and attachment.diagnosis_id == diagnosis.id:
                delete_file(attachment.file_path)
                db.session.delete(attachment)
        
        i = 0
        while f'attachments-{i}' in request.files:
            file = request.files[f'attachments-{i}']
            caption_text = request.form.get(f'captions-{i}', '') 
            if file:
                original_filename = secure_filename(file.filename)
                file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                unique_filename = f"diag_{diagnosis.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{original_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                attachment = DiagnosisAttachment(
                    diagnosis_id=diagnosis.id, file_path=unique_filename,
                    original_filename=caption_text or original_filename, file_type=file_ext
                )
                db.session.add(attachment)
            i += 1

        db.session.commit()
        flash('Diagnosis has been updated.', 'success')
        return redirect(url_for('view_sample', sample_uid=sample.sample_uid))
    return render_template('staff/edit_diagnosis.html', title='Edit Diagnosis', form=form, diagnosis=diagnosis)

@app.route('/diagnosis/delete/<int:diagnosis_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def delete_diagnosis(diagnosis_id):
    diagnosis = Diagnosis.query.get_or_404(diagnosis_id)
    sample_uid = diagnosis.sample.sample_uid
    
    for attachment in diagnosis.attachments:
        delete_file(attachment.file_path)
        
    db.session.delete(diagnosis)
    db.session.commit()
    log_action(f"Deleted diagnosis '{diagnosis.title}' from sample '{sample_uid}'.")
    flash('Diagnosis and all its attachments have been deleted.', 'success')
    return redirect(url_for('view_sample', sample_uid=sample_uid))


@app.route('/sample/edit/<sample_uid>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def edit_sample(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    form = SampleForm(obj=sample)
    
    form.allotted_department_id.choices = [('', '--- Select Department ---')] + [(str(d.id), d.name) for d in Department.query.order_by('name').all()]
    form.assigned_staff_id.choices = [('', '--- Select Staff ---')] + [(str(u.id), u.name) for u in User.query.filter(User.role.has(name='Admin') == False).order_by('name').all()]

    if form.validate_on_submit():
        form.populate_obj(sample)
        
        images_to_delete = request.form.getlist('delete_images')
        for image_id in images_to_delete:
            image = SampleImage.query.get(image_id)
            if image and image.sample_sc_id == sample.id:
                delete_file(image.image_path)
                db.session.delete(image)
        
        i = 0
        while f'images-{i}' in request.files:
            image_file = request.files[f'images-{i}']
            caption_text = request.form.get(f'captions-{i}', '')
            if image_file:
                filename = secure_filename(image_file.filename)
                unique_filename = f"sample_{sample.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)
                
                sample_image = SampleImage(sample_sc_id=sample.id, image_path=unique_filename, caption=caption_text)
                db.session.add(sample_image)
            i += 1

        db.session.commit()
        log_action(f"Updated sample '{sample.sample_uid}'.")
        flash(f'Sample {sample.sample_uid} has been updated.', 'success')
        return redirect(url_for('view_sample', sample_uid=sample.sample_uid))
    
    elif request.method == 'GET':
        form.allotted_department_id.data = sample.allotted_department_id
        form.assigned_staff_id.data = sample.assigned_staff_id

    return render_template('staff/edit_sample.html', title='Edit Sample', form=form, sample=sample)

@app.route('/sample/delete/<sample_uid>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def delete_sample(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    applicant_uid = sample.applicant.uid

    for image in sample.images:
        delete_file(image.image_path)
    for diagnosis in sample.diagnoses:
        for attachment in diagnosis.attachments:
            delete_file(attachment.file_path)
            
    db.session.delete(sample)
    db.session.commit()
    log_action(f"Deleted sample '{sample.sample_uid}' and all its data.")
    flash(f'Sample {sample.sample_uid} and all its data have been deleted.', 'success')
    return redirect(url_for('view_applicant', uid=applicant_uid))


@app.route('/sample/view/<sample_uid>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_SAMPLING_SERVICES)
def view_sample(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    return render_template('staff/view_sample.html', title=f'Sample: {sample.sample_uid}', sample=sample)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- PDF Report Generation ---
@app.route('/applicant/report/<uid>')
@login_required
def applicant_report(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    return render_template('reports/applicant_report.html', applicant=applicant, generation_time=get_ist_time())


@app.route('/sample/report/<sample_uid>')
@login_required
def sample_report(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    # Get parameters from URL, default to True if not present
    include_images = request.args.get('include_images', 'true').lower() == 'true'
    show_attachments = request.args.get('show_attachments', 'true').lower() == 'true'
    
    return render_template('reports/sample_report.html', 
                           sample=sample, 
                           generation_time=get_ist_time(),
                           include_images=include_images,
                           show_attachments=show_attachments)

@app.route('/nsc/report/<int:nsc_id>')
@login_required
def nsc_report(nsc_id):
    nsc = ConsultancyNSC.query.get_or_404(nsc_id)
    return render_template('reports/nsc_report.html', nsc=nsc, generation_time=get_ist_time())

@app.route('/sample/card/<sample_uid>')
@login_required
def sample_card(sample_uid):
    sample = SampleSC.query.filter_by(sample_uid=sample_uid).first_or_404()
    return render_template('reports/sample_card.html', sample=sample)

@app.route('/applicant/card/<uid>')
@login_required
def applicant_card(uid):
    applicant = Applicant.query.filter_by(uid=uid).first_or_404()
    return render_template('reports/applicant_card.html', applicant=applicant, generation_time=get_ist_time())


# --- Context Processors ---
# Replace the existing context_processor function in app.py with this one

@app.context_processor
def inject_global_variables():
    settings = LabSettings.query.first()
    unread_mail_count = 0
    if current_user.is_authenticated:
        unread_mail_count = MailRecipient.query.filter_by(
            recipient_id=current_user.id, 
            is_read=False, 
            is_deleted=False
        ).count()
    return dict(
        lab_settings=settings,
        current_year=datetime.now(timezone.utc).year,
        unread_mail_count=unread_mail_count,
        Permission=PermissionNames # Make the Permission class available in all templates
    )

# Add this new error handler function anywhere in app.py

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

# --- Create Database and Default Admin ---
with app.app_context():
    db.create_all()
    
    # This function will now robustly seed the database
    def seed_initial_data():
        # --- Seed Permissions ---
        print("Checking and seeding permissions...")
        all_perm_names = [vars(PermissionNames)[p] for p in vars(PermissionNames) if p.startswith('CAN_')]
        all_perms = []
        for name in all_perm_names:
            perm = Permission.query.filter_by(name=name).first()
            if not perm:
                perm = Permission(name=name)
                db.session.add(perm)
            all_perms.append(perm)
        db.session.commit()

        # --- Seed Roles ---
        print("Checking and seeding roles...")
        # Create Admin Role if it doesn't exist
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
        admin_role.permissions = all_perms # Ensure admin has all permissions
        
        # Create Staff Role if it doesn't exist
        staff_role = Role.query.filter_by(name='Staff').first()
        if not staff_role:
            staff_role = Role(name='Staff')
            db.session.add(staff_role)
        # Ensure staff has all permissions except visitor management
        staff_perms = [p for p in all_perms if p.name != PermissionNames.CAN_ACCESS_VISITOR_MANAGEMENT]
        staff_role.permissions = staff_perms
        
        db.session.commit()

        # --- Seed Default User and Settings ---
        if not User.query.filter_by(username='admin').first():
            print("Creating default admin user...")
            admin_role = Role.query.filter_by(name='Admin').first()
            hashed_password = generate_password_hash('password', method='pbkdf2:sha256')
            admin_user = User(username='admin', name='Administrator', password_hash=hashed_password, role=admin_role)
            db.session.add(admin_user)
            db.session.commit()

        if not LabSettings.query.first():
            print("Creating default lab settings...")
            default_settings = LabSettings(lab_name="My Laboratory", description="Default Lab Description", address="123 Lab Street", contact_number="9998887776", email="contact@lab.com")
            db.session.add(default_settings)
            db.session.commit()

    # Run the seeding function
    seed_initial_data()
