import os
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response, abort
from flask_login import login_required, current_user
from datetime import datetime
import pytz

from models import db, Equipment, EquipmentLog, User
from forms import AddEquipmentForm, LogUsageForm

# Create a Blueprint
equipment_bp = Blueprint('equipment', __name__, url_prefix='/equipment', template_folder='templates')

@equipment_bp.route('/')
@login_required
def dashboard():
    form = AddEquipmentForm()
    all_equipment = Equipment.query.order_by(Equipment.name).all()
    
    active_logs = EquipmentLog.query.filter_by(end_time=None).all()
    active_log_map = {log.equipment_id: [] for log in active_logs}
    for log in active_logs:
        active_log_map[log.equipment_id].append(log)

    return render_template('equipment/dashboard.html', title='Equipment Logging', 
                           form=form, all_equipment=all_equipment, active_log_map=active_log_map)

@equipment_bp.route('/add', methods=['POST'])
@login_required
def add_equipment():
    form = AddEquipmentForm()
    if form.validate_on_submit():
        new_equipment = Equipment(
            id_number=form.id_number.data,
            serial_number=form.serial_number.data,
            name=form.name.data,
            make_model=form.make_model.data,
            purchase_date=form.purchase_date.data,
            last_calibration_date=form.last_calibration_date.data,
            multi_user=form.multi_user.data,
            location=form.location.data
        )
        db.session.add(new_equipment)
        db.session.commit()
        flash(f"Equipment '{new_equipment.name}' has been added.", 'success')
    else:
        flash('Error adding equipment. Please check the form.', 'danger')
    return redirect(url_for('equipment.dashboard'))

@equipment_bp.route('/edit/<int:equipment_id>', methods=['GET', 'POST'])
@login_required
def edit_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    form = AddEquipmentForm(obj=equipment)
    if form.validate_on_submit():
        form.populate_obj(equipment)
        db.session.commit()
        flash(f"Equipment '{equipment.name}' has been updated.", 'success')
        return redirect(url_for('equipment.dashboard'))
    return render_template('equipment/add_edit.html', title='Edit Equipment', form=form)

@equipment_bp.route('/delete/<int:equipment_id>', methods=['POST'])
@login_required
def delete_equipment(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    db.session.delete(equipment)
    db.session.commit()
    flash(f"Equipment '{equipment.name}' has been deleted.", 'success')
    return redirect(url_for('equipment.dashboard'))

@equipment_bp.route('/log/start/<int:equipment_id>', methods=['POST'])
@login_required
def start_log(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    notes = request.form.get('notes', '')
    
    if not equipment.multi_user:
        existing_log = EquipmentLog.query.filter_by(equipment_id=equipment.id, user_id=current_user.id, end_time=None).first()
        if existing_log:
            flash(f"You are already using '{equipment.name}'.", 'warning')
            return redirect(url_for('equipment.dashboard'))

    new_log = EquipmentLog(
        equipment_id=equipment.id,
        user_id=current_user.id,
        notes=notes
    )
    db.session.add(new_log)
    db.session.commit()
    flash(f"You have started using '{equipment.name}'.", 'success')
    return redirect(url_for('equipment.dashboard'))

@equipment_bp.route('/log/end/<int:log_id>', methods=['POST'])
@login_required
def end_log(log_id):
    log = EquipmentLog.query.get_or_404(log_id)
    if log.user_id != current_user.id:
        abort(403)
    
    log.end_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    db.session.commit()
    flash(f"You have finished using '{log.equipment.name}'.", 'success')
    return redirect(url_for('equipment.dashboard'))

@equipment_bp.route('/logs/<int:equipment_id>')
@login_required
def view_logs(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    logs = EquipmentLog.query.filter_by(equipment_id=equipment.id).order_by(EquipmentLog.start_time.desc()).all()
    return render_template('equipment/view_logs.html', title=f"Logs for {equipment.name}", equipment=equipment, logs=logs)

# NEW: Route to export a specific equipment's log as CSV
@equipment_bp.route('/logs/export/<int:equipment_id>')
@login_required
def export_logs_csv(equipment_id):
    equipment = Equipment.query.get_or_404(equipment_id)
    logs = EquipmentLog.query.filter_by(equipment_id=equipment.id).order_by(EquipmentLog.start_time.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ['User', 'Start Time', 'End Time', 'Duration (Minutes)', 'Notes']
    writer.writerow(headers)
    
    for log in logs:
        duration = (log.end_time - log.start_time).total_seconds() // 60 if log.end_time else ''
        writer.writerow([
            log.user.name,
            log.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            log.end_time.strftime('%Y-%m-%d %H:%M:%S') if log.end_time else 'In Use',
            duration,
            log.notes
        ])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=log_{equipment.id_number}.csv"}
    )

@equipment_bp.route('/import', methods=['POST'])
@login_required
def import_csv():
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('equipment.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('equipment.dashboard'))

    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            count = 0
            for row in csv_reader:
                row = {k.lower().strip(): v for k, v in row.items() if k is not None}
                
                purchase_date = datetime.strptime(row.get('purchase_date'), '%Y-%m-%d').date() if row.get('purchase_date') else None
                last_calibration_date = datetime.strptime(row.get('last_calibration_date'), '%Y-%m-%d').date() if row.get('last_calibration_date') else None

                new_equipment = Equipment(
                    id_number=row.get('id_number'),
                    serial_number=row.get('serial_number'),
                    name=row.get('name'),
                    make_model=row.get('make_and_model'),
                    purchase_date=purchase_date,
                    last_calibration_date=last_calibration_date,
                    multi_user=row.get('multi_user', 'false').lower() in ['true', '1', 'yes'],
                    location=row.get('location')
                )
                db.session.add(new_equipment)
                count += 1
            
            db.session.commit()
            flash(f'Successfully imported {count} equipment entries from the CSV file.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during import: {e}', 'danger')
    else:
        flash('Invalid file type. Please upload a .csv file.', 'danger')

    return redirect(url_for('equipment.dashboard'))

@equipment_bp.route('/export')
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ['id_number', 'serial_number', 'name', 'make_and_model', 'purchase_date', 'last_calibration_date', 'multi_user', 'location']
    writer.writerow(headers)
    
    all_equipment = Equipment.query.all()
    for eq in all_equipment:
        writer.writerow([
            eq.id_number,
            eq.serial_number,
            eq.name,
            eq.make_model,
            eq.purchase_date.strftime('%Y-%m-%d') if eq.purchase_date else '',
            eq.last_calibration_date.strftime('%Y-%m-%d') if eq.last_calibration_date else '',
            eq.multi_user,
            eq.location
        ])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=equipment_export.csv"}
    )
