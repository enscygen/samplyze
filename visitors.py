import os
import base64
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime, time
import pytz

from models import db, Visitor, Department, User
from forms import VisitorEntryForm
from utils import generate_uid # We can reuse this for a unique visitor ID

# Create a Blueprint
visitors_bp = Blueprint('visitors', __name__, url_prefix='/visitors', template_folder='templates')

def get_ist_time():
    """Returns the current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

@visitors_bp.route('/')
@login_required
def dashboard():
    # Get filter parameters from the URL
    filter_type = request.args.get('filter', 'today')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    query = Visitor.query
    today = get_ist_time().date()

    if filter_type == 'today':
        start_dt = datetime.combine(today, time.min)
        end_dt = datetime.combine(today, time.max)
        query = query.filter(Visitor.entry_time.between(start_dt, end_dt))
    elif filter_type == 'range' and start_date_str and end_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time.max)
            query = query.filter(Visitor.entry_time.between(start_dt, end_dt))
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('visitors.dashboard'))

    visitors = query.order_by(Visitor.entry_time.desc()).all()
    return render_template('visitors/dashboard.html', title='Visitor Dashboard', visitors=visitors, 
                           filter_type=filter_type, start_date=start_date_str, end_date=end_date_str)

@visitors_bp.route('/entry', methods=['GET', 'POST'])
@login_required
def entry():
    form = VisitorEntryForm()
    form.assigned_department_id.choices = [('', '--- Select Department ---')] + [(d.id, d.name) for d in Department.query.order_by('name').all()]
    form.assigned_staff_id.choices = [('', '--- Select Staff ---')] + [(u.id, u.name) for u in User.query.filter(User.role.has(name='Admin') == False).order_by('name').all()]

    if form.validate_on_submit():
        new_visitor = Visitor(
            visitor_uid=f"VIS-{generate_uid()}",
            name=form.name.data,
            phone=form.phone.data,
            address=form.address.data,
            id_type=form.id_type.data,
            id_number=form.id_number.data,
            applicant_uid=form.applicant_uid.data,
            institution=form.institution.data,
            purpose=form.purpose.data,
            assigned_department_id=form.assigned_department_id.data,
            assigned_staff_id=form.assigned_staff_id.data
        )

        if form.photo_data.data:
            try:
                header, encoded = form.photo_data.data.split(",", 1)
                image_data = base64.b64decode(encoded)
                
                photo_filename = f"visitor_{new_visitor.visitor_uid}.png"
                photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], photo_filename)
                
                with open(photo_path, "wb") as f:
                    f.write(image_data)
                
                new_visitor.photo_filename = photo_filename
            except Exception as e:
                flash(f"Could not save photo: {e}", "danger")

        db.session.add(new_visitor)
        db.session.commit()
        flash('New visitor checked in successfully.', 'success')
        return redirect(url_for('visitors.dashboard'))
        
    return render_template('visitors/entry.html', title='Visitor Entry', form=form)

# NEW: Route to edit a visitor
@visitors_bp.route('/edit/<int:visitor_id>', methods=['GET', 'POST'])
@login_required
def edit_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    form = VisitorEntryForm(obj=visitor)
    form.assigned_department_id.choices = [('', '--- Select Department ---')] + [(d.id, d.name) for d in Department.query.order_by('name').all()]
    form.assigned_staff_id.choices = [('', '--- Select Staff ---')] + [(u.id, u.name) for u in User.query.filter(User.role.has(name='Admin') == False).order_by('name').all()]

    if form.validate_on_submit():
        form.populate_obj(visitor)
        db.session.commit()
        flash('Visitor details have been updated.', 'success')
        return redirect(url_for('visitors.dashboard'))

    elif request.method == 'GET':
        form.assigned_department_id.data = visitor.assigned_department_id
        form.assigned_staff_id.data = visitor.assigned_staff_id

    return render_template('visitors/edit_visitor.html', title='Edit Visitor', form=form, visitor=visitor)

# NEW: Route to delete a visitor
@visitors_bp.route('/delete/<int:visitor_id>', methods=['POST'])
@login_required
def delete_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    # You might want to delete the photo file as well
    if visitor.photo_filename:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], visitor.photo_filename))
        except OSError as e:
            print(f"Error deleting visitor photo: {e}")
    
    db.session.delete(visitor)
    db.session.commit()
    flash(f"Visitor '{visitor.name}' has been deleted.", 'success')
    return redirect(url_for('visitors.dashboard'))

@visitors_bp.route('/mark-out/<int:visitor_id>', methods=['POST'])
@login_required
def mark_out(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    if not visitor.exit_time:
        visitor.exit_time = get_ist_time()
        db.session.commit()
        flash(f"Visitor '{visitor.name}' has been marked as exited.", 'success')
    else:
        flash(f"Visitor '{visitor.name}' has already exited.", 'warning')
    return redirect(request.referrer or url_for('visitors.dashboard'))

@visitors_bp.route('/pass/<int:visitor_id>')
@login_required
def visitor_pass(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    return render_template('reports/visitor_pass.html', visitor=visitor)
