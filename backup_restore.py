import os
import shutil
import zipfile
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file, abort
from flask_login import login_required, current_user
from datetime import datetime
import pytz
import io

from models import db
from forms import RestoreForm

# Create a Blueprint
backup_bp = Blueprint('backup', __name__, url_prefix='/backup', template_folder='templates')

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@backup_bp.route('/')
@admin_required
def index():
    form = RestoreForm()
    return render_template('admin/backup_restore.html', title='Backup & Restore', form=form)

@backup_bp.route('/create')
@admin_required
def create_backup():
    """Creates a zip file containing the database and all uploaded files."""
    try:
        timestamp = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f'samplyze_backup_{timestamp}.zip'
        
        # Paths
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        uploads_path = current_app.config['UPLOAD_FOLDER']
        shared_path = current_app.config['SHARED_FOLDER']
        
        # Create a zip file in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Add database
            zf.write(db_path, arcname='database/laboratory.db')
            
            # 2. Add uploaded files
            for root, _, files in os.walk(uploads_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('uploads', os.path.relpath(file_path, uploads_path))
                    zf.write(file_path, arcname)

            # 3. Add shared files
            for root, _, files in os.walk(shared_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join('shared_files', os.path.relpath(file_path, shared_path))
                    zf.write(file_path, arcname)

        memory_file.seek(0)
        
        flash('Backup created successfully.', 'success')
        return send_file(memory_file, download_name=backup_filename, as_attachment=True)

    except Exception as e:
        flash(f'An error occurred while creating the backup: {e}', 'danger')
        return redirect(url_for('backup.index'))


@backup_bp.route('/restore', methods=['POST'])
@admin_required
def restore_backup():
    form = RestoreForm()
    if form.validate_on_submit():
        backup_file = form.backup_file.data
        
        # Paths
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        uploads_path = current_app.config['UPLOAD_FOLDER']
        shared_path = current_app.config['SHARED_FOLDER']
        
        try:
            with zipfile.ZipFile(backup_file, 'r') as zf:
                # --- Safety Check: Ensure it's a valid backup file ---
                file_list = zf.namelist()
                if 'database/laboratory.db' not in file_list:
                    flash('Invalid backup file. The database is missing.', 'danger')
                    return redirect(url_for('backup.index'))

                # --- Perform Restore ---
                # Close the current database connection to release the file lock
                db.session.close()
                
                # 1. Delete old data
                if os.path.exists(db_path): os.remove(db_path)
                if os.path.exists(uploads_path): shutil.rmtree(uploads_path)
                if os.path.exists(shared_path): shutil.rmtree(shared_path)
                
                # 2. Recreate empty directories
                os.makedirs(uploads_path)
                os.makedirs(shared_path)

                # 3. Extract the backup
                zf.extractall(path=os.path.dirname(db_path)) # Extract to the root project folder
                
                flash('Restore successful! The application has been restored to the backup state. Please log in again.', 'success')
                return redirect(url_for('logout'))

        except Exception as e:
            flash(f'An error occurred during restore: {e}', 'danger')
            return redirect(url_for('backup.index'))
    
    flash('Invalid file or form submission.', 'danger')
    return redirect(url_for('backup.index'))
