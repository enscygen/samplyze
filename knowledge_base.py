import os
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user

from models import db, KnowledgeBase
from forms import KnowledgeBaseForm

# Create a Blueprint
kb_bp = Blueprint('kb', __name__, url_prefix='/kb', template_folder='templates')

@kb_bp.route('/')
@login_required
def dashboard():
    remedies = KnowledgeBase.query.filter_by(category='Remedy').order_by(KnowledgeBase.name).all()
    diagnoses = KnowledgeBase.query.filter_by(category='Diagnosis').order_by(KnowledgeBase.name).all()
    return render_template('kb/dashboard.html', title='Knowledge Base', remedies=remedies, diagnoses=diagnoses)

@kb_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    form = KnowledgeBaseForm()
    if form.validate_on_submit():
        new_entry = KnowledgeBase(
            category=form.category.data,
            name=form.name.data,
            title=form.title.data if form.category.data == 'Diagnosis' else None,
            description=form.description.data
        )
        db.session.add(new_entry)
        db.session.commit()
        flash('New knowledge base entry has been added.', 'success')
        return redirect(url_for('kb.dashboard'))
    return render_template('kb/add_edit_entry.html', title='Add KB Entry', form=form)

@kb_bp.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry = KnowledgeBase.query.get_or_404(entry_id)
    form = KnowledgeBaseForm(obj=entry)
    if form.validate_on_submit():
        entry.category = form.category.data
        entry.name = form.name.data
        entry.title = form.title.data if form.category.data == 'Diagnosis' else None
        entry.description = form.description.data
        db.session.commit()
        flash('Knowledge base entry has been updated.', 'success')
        return redirect(url_for('kb.dashboard'))
    return render_template('kb/add_edit_entry.html', title='Edit KB Entry', form=form)

@kb_bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = KnowledgeBase.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Knowledge base entry has been deleted.', 'success')
    return redirect(url_for('kb.dashboard'))

# NEW: Route to handle CSV file imports
@kb_bp.route('/import', methods=['POST'])
@login_required
def import_csv():
    category = request.form.get('category')
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('kb.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('kb.dashboard'))

    if file and file.filename.endswith('.csv'):
        try:
            # Read the CSV file in memory
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            count = 0
            for row in csv_reader:
                # Normalize headers (lowercase, strip spaces)
                row = {k.lower().strip(): v for k, v in row.items()}

                if category == 'Diagnosis':
                    new_entry = KnowledgeBase(
                        category='Diagnosis',
                        name=row.get('name'),
                        title=row.get('title'),
                        description=row.get('description')
                    )
                elif category == 'Remedy':
                    new_entry = KnowledgeBase(
                        category='Remedy',
                        name=row.get('name'),
                        description=row.get('description')
                    )
                else:
                    continue # Skip if category is invalid
                
                db.session.add(new_entry)
                count += 1
            
            db.session.commit()
            flash(f'Successfully imported {count} entries from the CSV file.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during import: {e}', 'danger')
    else:
        flash('Invalid file type. Please upload a .csv file.', 'danger')

    return redirect(url_for('kb.dashboard'))

@kb_bp.route('/export/<category>')
@login_required
def export_csv(category):
    output = io.StringIO()
    writer = csv.writer(output)
    
    entries = KnowledgeBase.query.filter_by(category=category).all()
    
    # Write headers
    if category == 'Diagnosis':
        writer.writerow(['name', 'title', 'description'])
        for entry in entries:
            writer.writerow([entry.name, entry.title, entry.description])
    elif category == 'Remedy':
        writer.writerow(['name', 'description'])
        for entry in entries:
            writer.writerow([entry.name, entry.description])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=kb_{category.lower()}_export.csv"}
    )

# API endpoint for live search
@kb_bp.route('/api/search/<category>')
@login_required
def search_kb(category):
    entries = KnowledgeBase.query.filter_by(category=category).all()
    return jsonify([{
        'id': entry.id,
        'name': entry.name,
        'title': entry.title,
        'description': entry.description
    } for entry in entries])
