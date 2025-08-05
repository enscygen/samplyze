from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import db, Role, Permission, User
from forms import RoleForm

# Create a Blueprint
roles_bp = Blueprint('roles', __name__, url_prefix='/admin/roles', template_folder='templates')

def admin_required(f):
    """Decorator to restrict access to admin users."""
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@roles_bp.route('/')
@admin_required
def manage_roles():
    roles = Role.query.order_by(Role.name).all()
    return render_template('admin/manage_roles.html', title='Manage Roles', roles=roles)

@roles_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_role():
    form = RoleForm()
    # Populate the checkboxes with all available permissions
    form.permissions.choices = [(p.id, p.name.replace('_', ' ').title()) for p in Permission.query.all()]
    
    if form.validate_on_submit():
        new_role = Role(name=form.name.data)
        # Add the selected permissions to the new role
        for perm_id in form.permissions.data:
            perm = Permission.query.get(perm_id)
            new_role.permissions.append(perm)
        
        db.session.add(new_role)
        db.session.commit()
        flash(f"Role '{new_role.name}' has been created.", 'success')
        return redirect(url_for('roles.manage_roles'))
        
    return render_template('admin/add_edit_role.html', title='Add New Role', form=form)

@roles_bp.route('/edit/<int:role_id>', methods=['GET', 'POST'])
@admin_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    form.permissions.choices = [(p.id, p.name.replace('_', ' ').title()) for p in Permission.query.all()]

    if form.validate_on_submit():
        role.name = form.name.data
        # Clear existing permissions and add the newly selected ones
        role.permissions.clear()
        for perm_id in form.permissions.data:
            perm = Permission.query.get(perm_id)
            role.permissions.append(perm)
            
        db.session.commit()
        flash(f"Role '{role.name}' has been updated.", 'success')
        return redirect(url_for('roles.manage_roles'))

    elif request.method == 'GET':
        # Pre-select the checkboxes for the role's current permissions
        form.permissions.data = [p.id for p in role.permissions]

    return render_template('admin/add_edit_role.html', title='Edit Role', form=form, role=role)

@roles_bp.route('/delete/<int:role_id>', methods=['POST'])
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    if role.name == 'Admin':
        flash('The Admin role cannot be deleted.', 'danger')
        return redirect(url_for('roles.manage_roles'))
    
    # Before deleting, unassign users from this role (or handle as needed)
    User.query.filter_by(role_id=role.id).update({'role_id': None})
    
    db.session.delete(role)
    db.session.commit()
    flash(f"Role '{role.name}' has been deleted.", 'success')
    return redirect(url_for('roles.manage_roles'))
