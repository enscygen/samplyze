import os
import shutil
import sqlite3
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
import pytz
import io

from models import db, User, Applicant, SampleSC, ConsultancyNSC, Diagnosis
from forms import CreateArchiveForm, ViewArchiveForm
from decorators import permission_required
from models import PermissionNames

# Create a Blueprint
archive_bp = Blueprint('archive', __name__, url_prefix='/admin/archive', template_folder='templates')

# NEW: Local admin_required decorator for this blueprint
def admin_required(f):
    """Decorator to restrict access to admin users."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@archive_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_ARCHIVES)
def dashboard():
    create_form = CreateArchiveForm()
    view_form = ViewArchiveForm()
    return render_template('admin/archive/dashboard.html', title='Archive Management', create_form=create_form, view_form=view_form)

@archive_bp.route('/create', methods=['POST'])
@admin_required # UPDATED: This action is now restricted to admins only
def create_archive():
    form = CreateArchiveForm()
    if form.validate_on_submit():
        end_date = form.end_date.data
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
        archive_db_name = f'archive_{end_date.strftime("%Y-%m-%d")}_{timestamp}.db'
        archive_db_path = os.path.join('instance', archive_db_name)

        main_db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        main_conn = sqlite3.connect(main_db_path)
        archive_conn = sqlite3.connect(archive_db_path)
        
        with current_app.app_context():
            schema = '\n'.join(main_conn.iterdump())
            archive_conn.executescript(schema)

        samples_to_archive = db.session.query(SampleSC).filter(SampleSC.submission_date < end_date).all()
        
        flash(f"Archiving is a complex feature. This is a placeholder for the logic to copy data for {len(samples_to_archive)} samples.", 'info')
        
        return redirect(url_for('archive.dashboard'))

    flash('There was an error with your submission.', 'danger')
    return redirect(url_for('archive.dashboard'))


@archive_bp.route('/view', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_ARCHIVES)
def view_archive():
    form = ViewArchiveForm()
    if form.validate_on_submit():
        archive_file = form.archive_file.data
        temp_path = os.path.join('instance', 'temp_archive_view.db')
        archive_file.save(temp_path)

        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            archived_data = {}
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                archived_data[table] = cursor.fetchall()

            conn.close()
            os.remove(temp_path)

            return render_template('admin/archive/view_archive.html', title='View Archive', archived_data=archived_data)

        except Exception as e:
            flash(f"Could not read the archive file. Error: {e}", 'danger')
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return redirect(url_for('archive.dashboard'))

    flash('Invalid file or form submission.', 'danger')
    return redirect(url_for('archive.dashboard'))
