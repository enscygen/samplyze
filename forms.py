from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField, MultipleFileField, DateTimeField, TimeField, FileField, SelectMultipleField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError
from flask_wtf.file import FileAllowed
from wtforms.widgets import ListWidget, CheckboxInput
from models import User

# ... (Existing helper function and forms remain the same) ...
def coerce_int_or_none(x):
    if x is None or x == '' or x == 'None':
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None

class LoginForm(FlaskForm):
    username = StringField('Staff ID / Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class StaffForm(FlaskForm):
    name = StringField('Staff Name', validators=[DataRequired(), Length(min=2, max=120)])
    department = SelectField('Department', coerce=int, validators=[DataRequired()])
    staff_id = StringField('Staff ID / Username', validators=[DataRequired(), Length(min=4, max=80)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Add Staff')

    def validate_staff_id(self, staff_id):
        user = User.query.filter_by(username=staff_id.data).first()
        if user:
            raise ValidationError('That Staff ID is already in use. Please choose a different one.')

class EditStaffForm(FlaskForm):
    name = StringField('Staff Name', validators=[DataRequired(), Length(min=2, max=120)])
    department = SelectField('Department', coerce=int, validators=[DataRequired()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password')])
    submit = SubmitField('Update Staff Member')

class ApplicantForm(FlaskForm):
    name = StringField('Applicant Name', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    dob = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email Address', validators=[Optional(), Email()])
    occupation = StringField('Occupation', validators=[Optional()])
    id_card_type = StringField('ID Card Type', validators=[Optional()])
    id_card_number = StringField('ID Card Number', validators=[Optional()])
    
    house_name = StringField('House Name / Number')
    village = StringField('Village / Area')
    city = StringField('City / Town')
    pincode = StringField('PIN Code')
    district = StringField('District')
    state = StringField('State')
    country = StringField('Country', default='India')
    
    remarks = TextAreaField('Remarks')
    overview = TextAreaField('Consultation Overview')
    submit = SubmitField('Save Applicant and Generate UID')

class LabSettingsForm(FlaskForm):
    lab_name = StringField('Laboratory Name', validators=[DataRequired()])
    description = TextAreaField('Description / Slogan')
    address = TextAreaField('Full Address', validators=[DataRequired()])
    contact_number = StringField('Contact Number(s)')
    email = StringField('Public Email Address', validators=[Email()])
    logo = FileField('Upload New Logo', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif'], 'Images only!')])
    submit = SubmitField('Update Settings')

class NSCForm(FlaskForm):
    consultancy_datetime = DateTimeField('Consultancy Date & Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    consultancy_type = StringField('Consultancy Type (e.g., Field Visit, Telephonic)', validators=[DataRequired()])
    problem_issue = TextAreaField('Problem / Issue Description', validators=[DataRequired()], render_kw={'rows': 4})
    problem_with = StringField('Problem related to (e.g., Crop name, Pest name)', validators=[DataRequired()])
    remedy_suggested = TextAreaField('Remedy / Advice Suggested', validators=[DataRequired()], render_kw={'rows': 4})
    remarks = TextAreaField('Additional Remarks', render_kw={'rows': 3})
    submit = SubmitField('Save Consultancy Data')

class SampleForm(FlaskForm):
    sample_name = StringField('Sample Name', validators=[Optional()])
    sample_type = StringField('Sample Type (e.g., Soil, Leaf, Water)', validators=[Optional()])
    collection_date = DateTimeField('Collection Date & Time', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    primary_observations = TextAreaField('Primary Observations', validators=[Optional()])
    
    current_status = SelectField('Sample Status', choices=[
        ('Submitted', 'Submitted'),
        ('In Progress', 'In Progress'),
        ('Analysis Complete', 'Analysis Complete'),
        ('Report Ready', 'Report Ready'),
        ('Disposed', 'Disposed')
    ], validators=[DataRequired()])
    
    recommended_storage = StringField('Recommended Storage (e.g., Refrigerate, Dry)')
    storage_location = StringField('Storage Location in Lab')
    
    allotted_department_id = SelectField('Allot to Department', coerce=coerce_int_or_none, validators=[Optional()])
    assigned_staff_id = SelectField('Assign to Staff/Consultant', coerce=coerce_int_or_none, validators=[Optional()])
    
    diagnostics_needed = TextAreaField('Initial Diagnostics Needed')
    quality_check_data = TextAreaField('Quality Check Data')
    hazard_control = TextAreaField('Hazard Control Measures')
    dispose_before = DateField('Dispose Before Date', format='%Y-%m-%d', validators=[Optional()])
    remarks = TextAreaField('Additional Remarks')
    
    submit = SubmitField('Save Sample and Generate UID')

 
class DiagnosisForm(FlaskForm):
    name = StringField('Diagnosis Name / Test', validators=[Optional()])
    title = StringField('Title', validators=[Optional()])
    description = TextAreaField('Description / Method')
    result = TextAreaField('Result / Observations', validators=[Optional()])
    is_rich_text = BooleanField('Use Rich Text Editor for Result')
    submit = SubmitField('Add Diagnosis') 

class CreateFolderForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Create Folder')

class FolderSettingsForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Optional()], render_kw={'rows': 3})
    submit = SubmitField('Save Changes')

class ComposeMailForm(FlaskForm):
    recipients = SelectMultipleField('To', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=255)])
    body = TextAreaField('Message', validators=[DataRequired()], render_kw={'rows': 10})
    submit = SubmitField('Send Mail')

class KnowledgeBaseForm(FlaskForm):
    category = SelectField('Category', choices=[('Diagnosis', 'Diagnosis'), ('Remedy', 'Remedy')], validators=[DataRequired()])
    name = StringField('Name / Test', validators=[DataRequired()])
    title = StringField('Title (for Diagnosis only)', validators=[Optional()])
    description = TextAreaField('Description / Method / Remedy Details', validators=[DataRequired()], render_kw={'rows': 5})
    submit = SubmitField('Save Entry')

class DBMigrationForm(FlaskForm):
    db_file = FileField('Select Old Database File', validators=[
        DataRequired(), 
        FileAllowed(['db'], 'Only .db database files are allowed!')
    ])
    submit = SubmitField('Migrate Data')
    
class AddEquipmentForm(FlaskForm):
    id_number = StringField('ID Number', validators=[DataRequired()])
    serial_number = StringField('Serial Number', validators=[Optional()])
    name = StringField('Equipment Name', validators=[DataRequired()])
    make_model = StringField('Make & Model', validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    purchase_date = DateField('Purchase Date', format='%Y-%m-%d', validators=[Optional()])
    last_calibration_date = DateField('Last Calibration Date', format='%Y-%m-%d', validators=[Optional()])
    multi_user = BooleanField('Allow Multiple Concurrent Users')
    submit = SubmitField('Add Equipment')

class LogUsageForm(FlaskForm):
    notes = TextAreaField('Notes / Sample ID', render_kw={'rows': 3})
    submit = SubmitField('Confirm Entry')
    
class RestoreForm(FlaskForm):
    backup_file = FileField('Select Backup File (.zip)', validators=[
        DataRequired(),
        FileAllowed(['zip'], 'Only .zip backup files are allowed!')
    ])
    submit = SubmitField('Restore from Backup')

# UPDATED: Changed DataRequired to Optional for permissions
class RoleForm(FlaskForm):
    name = StringField('Role Name', validators=[DataRequired(), Length(min=3, max=80)])
    permissions = SelectMultipleField('Permissions', coerce=int, validators=[Optional()], 
                                      widget=ListWidget(prefix_label=False), 
                                      option_widget=CheckboxInput())
    submit = SubmitField('Save Role')

class VisitorEntryForm(FlaskForm):
    name = StringField('Visitor Name', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[DataRequired()])
    address = TextAreaField('Address', render_kw={'rows': 2})
    id_type = StringField('ID Type (e.g., Aadhar, License)')
    id_number = StringField('ID Number')
    applicant_uid = StringField('Existing Applicant UID (Optional)')
    institution = StringField('Institution / Organization')
    purpose = TextAreaField('Purpose of Visit', validators=[DataRequired()], render_kw={'rows': 3})
    vehicle_type = StringField('Vehicle Type (e.g., Car, Bike)')
    vehicle_number = StringField('Vehicle Registration Number')
    assigned_department_id = SelectField('Assign to Department', coerce=coerce_int_or_none, validators=[Optional()])
    assigned_staff_id = SelectField('Assign to Staff', coerce=coerce_int_or_none, validators=[Optional()])
    
    photo_data = HiddenField()

    submit = SubmitField('Save and Generate Pass')

class TemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    category = SelectField('Template Data Source', choices=[('Sample', 'Sample Data'), ('Applicant', 'Applicant Data')], validators=[DataRequired()])
    subject_template = StringField('Subject Template', validators=[Optional()])
    body_template = TextAreaField('Body Template', validators=[DataRequired()], render_kw={'rows': 15})
    submit = SubmitField('Save Template')
    
    
class CreateArchiveForm(FlaskForm):
    end_date = DateField('Archive All Records Before This Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Create Archive & Clean Database')

class ViewArchiveForm(FlaskForm):
    archive_file = FileField('Select Archive Database File (.db)', validators=[
        DataRequired(),
        FileAllowed(['db'], 'Only .db archive files are allowed!')
    ])
    submit = SubmitField('View Archive')
    

class CreateIssueForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()], render_kw={'rows': 10})
    issue_type = SelectField('Type', choices=[('Bug', 'Bug'), ('Feature Request', 'Feature Request'), ('Task', 'Task')], default='Bug')
    priority = SelectField('Priority', choices=[(f'P{i}', f'P{i}') for i in range(5)], default='P2')
    severity = SelectField('Severity', choices=[(f'S{i}', f'S{i}') for i in range(5)], default='S2')
    assignee_id = SelectField('Assignee', coerce=coerce_int_or_none, validators=[Optional()])
    verifier_id = SelectField('Verifier', coerce=coerce_int_or_none, validators=[Optional()])
    submit = SubmitField('Create Issue')

class CommentForm(FlaskForm):
    comment = TextAreaField('Add a comment...', validators=[DataRequired()], render_kw={'rows': 4})
    submit = SubmitField('Add Comment')