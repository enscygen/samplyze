import os
import shutil
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from models import db, Folder, File, FolderPermission, User, PermissionNames
from forms import CreateFolderForm, FolderSettingsForm
from decorators import permission_required

# Create a Blueprint
fileshare_bp = Blueprint('fileshare', __name__, url_prefix='/fileshare', template_folder='templates')

# --- Helper Functions ---
def has_permission(folder, user):
    """Check if a user has permission to access a folder."""
    if user.role == 'admin' or folder.owner_id == user.id:
        return True
    return FolderPermission.query.filter_by(folder_id=folder.id, user_id=user.id).first() is not None

# --- Routes ---
@fileshare_bp.route('/', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def dashboard():
    form = CreateFolderForm()
    if form.validate_on_submit():
        folder_name = form.name.data
        # Create physical folder
        folder_path = os.path.join(current_app.config['SHARED_FOLDER'], folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            # Create DB record
            new_folder = Folder(name=folder_name, owner_id=current_user.id)
            db.session.add(new_folder)
            db.session.commit()
            flash(f'Folder "{folder_name}" created successfully.', 'success')
        else:
            flash(f'A folder with the name "{folder_name}" already exists.', 'danger')
        return redirect(url_for('fileshare.dashboard'))

    # Get folders owned by the user or shared with the user
    owned_folders = Folder.query.filter_by(owner_id=current_user.id).all()
    shared_permissions = FolderPermission.query.filter_by(user_id=current_user.id).all()
    shared_folders = [p.folder for p in shared_permissions]
    
    # Combine and remove duplicates
    all_folders = list(set(owned_folders + shared_folders))
    all_folders.sort(key=lambda x: x.created_at, reverse=True)

    return render_template('fileshare/dashboard.html', title='File Sharing', form=form, folders=all_folders)

@fileshare_bp.route('/folder/<int:folder_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def view_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if not has_permission(folder, current_user):
        abort(403)
    
    files = File.query.filter_by(folder_id=folder.id).order_by(File.uploaded_at.desc()).all()
    return render_template('fileshare/view_folder.html', title=folder.name, folder=folder, files=files)

@fileshare_bp.route('/folder/<int:folder_id>/upload', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def upload_file(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if not has_permission(folder, current_user):
        abort(403)

    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    if file:
        original_filename = secure_filename(file.filename)
        # Create a unique filename to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_filename = f"{timestamp}_{original_filename}"
        
        # Save file to the physical folder
        folder_path = os.path.join(current_app.config['SHARED_FOLDER'], folder.name)
        file.save(os.path.join(folder_path, unique_filename))

        # Create DB record
        new_file = File(
            folder_id=folder.id,
            filename=unique_filename,
            original_filename=original_filename,
            uploader_id=current_user.id
        )
        db.session.add(new_file)
        db.session.commit()
        return 'File uploaded successfully', 200
    return 'Error uploading file', 500

@fileshare_bp.route('/file/delete/<int:file_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def delete_file_from_folder(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    if not has_permission(folder, current_user):
        abort(403)
        
    # Delete physical file
    file_path = os.path.join(current_app.config['SHARED_FOLDER'], folder.name, file.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
    # Delete DB record
    db.session.delete(file)
    db.session.commit()
    flash(f'File "{file.original_filename}" has been deleted.', 'success')
    return redirect(url_for('fileshare.view_folder', folder_id=folder.id))

@fileshare_bp.route('/file/download/<int:file_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    if not has_permission(folder, current_user):
        abort(403)
    
    directory = os.path.join(current_app.config['SHARED_FOLDER'], folder.name)
    return send_from_directory(directory, file.filename, as_attachment=True, download_name=file.original_filename)

@fileshare_bp.route('/folder/<int:folder_id>/settings', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def folder_settings(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.owner_id != current_user.id and current_user.role != 'admin':
        abort(403) # Only owner or admin can change settings

    form = FolderSettingsForm(obj=folder)
    
    if form.validate_on_submit():
        # Handle folder rename
        new_name = form.name.data
        if new_name != folder.name:
            old_path = os.path.join(current_app.config['SHARED_FOLDER'], folder.name)
            new_path = os.path.join(current_app.config['SHARED_FOLDER'], new_name)
            if os.path.exists(new_path):
                flash(f'A folder with the name "{new_name}" already exists.', 'danger')
                return redirect(url_for('fileshare.folder_settings', folder_id=folder.id))
            shutil.move(old_path, new_path)
            folder.name = new_name
            
        folder.description = form.description.data
        
        # Handle permissions
        new_permissions = [int(uid) for uid in request.form.getlist('permissions')]
        # Remove old permissions
        FolderPermission.query.filter_by(folder_id=folder.id).delete()
        # Add new permissions
        for user_id in new_permissions:
            permission = FolderPermission(folder_id=folder.id, user_id=user_id)
            db.session.add(permission)
            
        db.session.commit()
        flash('Folder settings updated successfully.', 'success')
        return redirect(url_for('fileshare.view_folder', folder_id=folder.id))
        
    all_users = User.query.filter(User.id != current_user.id).order_by(User.name).all()
    current_permissions = [p.user_id for p in folder.permissions]
    
    return render_template('fileshare/folder_settings.html', title='Folder Settings', form=form, folder=folder, all_users=all_users, current_permissions=current_permissions)

@fileshare_bp.route('/folder/delete/<int:folder_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    if folder.owner_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    # Delete physical folder and its contents
    folder_path = os.path.join(current_app.config['SHARED_FOLDER'], folder.name)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        
    # Delete DB record (cascades will delete files and permissions)
    db.session.delete(folder)
    db.session.commit()
    flash(f'Folder "{folder.name}" and all its contents have been deleted.', 'success')
    return redirect(url_for('fileshare.dashboard'))

@fileshare_bp.route('/file/view/<int:file_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_FILE_SHARING)
def view_file(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    if not has_permission(folder, current_user):
        abort(403)
    
    directory = os.path.join(current_app.config['SHARED_FOLDER'], folder.name)
    # 'as_attachment=False' tells the browser to try and display the file inline
    return send_from_directory(directory, file.filename, as_attachment=False, download_name=file.original_filename)