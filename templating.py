import os
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from jinja2 import Environment

from models import db, MessageTemplate, SampleSC, Applicant
from forms import TemplateForm
from decorators import permission_required
from models import PermissionNames

# Create a Blueprint
templating_bp = Blueprint('templating', __name__, url_prefix='/templating', template_folder='templates')

# --- Helper function to get available template parameters ---
def get_template_params(category):
    params = {
        'Applicant': [
            'applicant.uid', 'applicant.name', 'applicant.phone', 'applicant.email', 
            'applicant.full_address', 'applicant.dob'
        ],
        'Sample': [
            'sample.sample_uid', 'sample.sample_name', 'sample.sample_type', 
            'sample.current_status', 'sample.submission_date',
            'applicant.uid', 'applicant.name', 'applicant.phone', 'applicant.email'
        ]
    }
    return params.get(category, [])

@templating_bp.route('/')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def dashboard():
    templates = MessageTemplate.query.order_by(MessageTemplate.name).all()
    return render_template('templating/dashboard.html', title='Message Templates', templates=templates)

# Replace the create_template function in templating.py

@templating_bp.route('/editor', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def create_template():
    form = TemplateForm()
    if form.validate_on_submit():
        new_template = MessageTemplate(
            name=form.name.data,
            category=form.category.data,
            subject_template=form.subject_template.data,
            body_template=form.body_template.data
        )
        db.session.add(new_template)
        db.session.commit()
        flash('New message template created successfully.', 'success')
        return redirect(url_for('templating.dashboard'))
    
    # Get the selected category or default to 'Sample'
    category = request.args.get('category', 'Sample')
    form.category.data = category
    
    return render_template('templating/editor.html', title='Create Template', form=form, params=get_template_params(category))

# Replace the edit_template function in templating.py

@templating_bp.route('/editor/<int:template_id>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def edit_template(template_id):
    template = MessageTemplate.query.get_or_404(template_id)
    form = TemplateForm(obj=template)
    if form.validate_on_submit():
        template.name = form.name.data
        template.category = form.category.data
        template.subject_template = form.subject_template.data
        template.body_template = form.body_template.data
        db.session.commit()
        flash('Message template updated successfully.', 'success')
        return redirect(url_for('templating.dashboard'))

    # Get the selected category from the form or the template object
    category = request.args.get('category', template.category)
    form.category.data = category

    return render_template('templating/editor.html', title='Edit Template', form=form, params=get_template_params(category))

@templating_bp.route('/delete/<int:template_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def delete_template(template_id):
    template = MessageTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash(f"Template '{template.name}' has been deleted.", 'success')
    return redirect(url_for('templating.dashboard'))

@templating_bp.route('/api/params/<category>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def get_params_for_category(category):
    return jsonify(get_template_params(category))

@templating_bp.route('/generate', methods=['GET'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def generate_message():
    templates = MessageTemplate.query.order_by(MessageTemplate.name).all()
    return render_template('templating/generate.html', title='Generate Message', templates=templates)

@templating_bp.route('/api/search/<category>/<term>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def search_data(category, term):
    if category == 'Sample':
        results = SampleSC.query.filter(SampleSC.sample_uid.ilike(f'%{term}%')).limit(10).all()
        return jsonify([{'id': r.id, 'text': f"{r.sample_uid} ({r.applicant.name})"} for r in results])
    elif category == 'Applicant':
        results = Applicant.query.filter(Applicant.uid.ilike(f'%{term}%')).limit(10).all()
        return jsonify([{'id': r.id, 'text': f"{r.uid} ({r.name})"} for r in results])
    return jsonify([])

@templating_bp.route('/render', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def render_message():
    template_id = request.form.get('template_id')
    data_id = request.form.get('data_id')
    
    template = MessageTemplate.query.get_or_404(template_id)
    
    context = {}
    if template.category == 'Sample':
        sample = SampleSC.query.get_or_404(data_id)
        context = {'sample': sample, 'applicant': sample.applicant}
    elif template.category == 'Applicant':
        applicant = Applicant.query.get_or_404(data_id)
        context = {'applicant': applicant}
        
    jinja_env = Environment()
    
    rendered_subject = jinja_env.from_string(template.subject_template or '').render(context)
    rendered_body = jinja_env.from_string(template.body_template or '').render(context)
    
    phone = context.get('applicant').phone if context.get('applicant') else ''
    email = context.get('applicant').email if context.get('applicant') else ''

    return jsonify({
        'subject': rendered_subject,
        'body': rendered_body,
        'phone': phone,
        'email': email
    })

# NEW: Route to import templates from CSV
@templating_bp.route('/import', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def import_csv():
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('templating.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('templating.dashboard'))

    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            count = 0
            for row in csv_reader:
                row = {k.lower().strip(): v for k, v in row.items() if k is not None}
                
                new_template = MessageTemplate(
                    name=row.get('name'),
                    category=row.get('category'),
                    subject_template=row.get('subject_template'),
                    body_template=row.get('body_template')
                )
                db.session.add(new_template)
                count += 1
            
            db.session.commit()
            flash(f'Successfully imported {count} templates from the CSV file.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during import: {e}', 'danger')
    else:
        flash('Invalid file type. Please upload a .csv file.', 'danger')

    return redirect(url_for('templating.dashboard'))

# NEW: Route to export templates to CSV
@templating_bp.route('/export')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_APPLICANT_SERVICES)
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ['name', 'category', 'subject_template', 'body_template']
    writer.writerow(headers)
    
    templates = MessageTemplate.query.all()
    for template in templates:
        writer.writerow([
            template.name,
            template.category,
            template.subject_template,
            template.body_template
        ])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=message_templates_export.csv"}
    )
