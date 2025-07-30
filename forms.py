from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField, MultipleFileField, DateTimeField, TimeField, FileField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError
from flask_wtf.file import FileAllowed
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
    
# NEW: Form for changing password when logged in
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class StaffForm(FlaskForm):
    name = StringField('Staff Name', validators=[DataRequired(), Length(min=2, max=120)])
    department = SelectField('Department', coerce=int, validators=[DataRequired()])
    staff_id = StringField('Staff ID / Username', validators=[DataRequired(), Length(min=4, max=80)])
    role = SelectField('Role', choices=[('staff', 'Staff'), ('consultant', 'Consultant'), ('both', 'Both')], validators=[DataRequired()])
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
    role = SelectField('Role', choices=[('staff', 'Staff'), ('consultant', 'Consultant'), ('both', 'Both')], validators=[DataRequired()])
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
    
    recommended_storage = StringField('Recommended Storage (e.g., Refrigerate, Dry)')
    storage_location = StringField('Storage Location in Lab')
    
    allotted_department = SelectField('Allot to Department', coerce=coerce_int_or_none, validators=[Optional()])
    assigned_staff = SelectField('Assign to Staff/Consultant', coerce=coerce_int_or_none, validators=[Optional()])
    
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
    submit = SubmitField('Add Diagnosis')

# --- NEW: Forms for File Sharing Feature ---
class CreateFolderForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(min=3, max=100)])
    submit = SubmitField('Create Folder')

class FolderSettingsForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[Optional()], render_kw={'rows': 3})
    submit = SubmitField('Save Changes')

# UPDATED: ComposeMailForm - removed static attachments field
class ComposeMailForm(FlaskForm):
    recipients = SelectMultipleField('To', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=255)])
    body = TextAreaField('Message', validators=[DataRequired()], render_kw={'rows': 10})
    submit = SubmitField('Send Mail')

