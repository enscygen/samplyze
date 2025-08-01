from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import pytz
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()

# Enforce foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_ist_time():
    """Returns the current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

# --- Existing User and Lab Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False) # Staff ID
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    department = db.relationship('Department', backref=db.backref('staff', lazy=True))

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# ... (Applicant, ConsultancyNSC, SampleSC, Diagnosis, etc. models remain the same) ...
class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    occupation = db.Column(db.String(100))
    id_card_type = db.Column(db.String(50))
    id_card_number = db.Column(db.String(50))
    
    house_name = db.Column(db.String(100))
    village = db.Column(db.String(100))
    city = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    district = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    
    remarks = db.Column(db.Text)
    overview = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    
    consultancies_nsc = db.relationship('ConsultancyNSC', back_populates='applicant', cascade="all, delete-orphan")
    samples_sc = db.relationship('SampleSC', back_populates='applicant', cascade="all, delete-orphan")

    @property
    def age(self):
        if not self.dob:
            return None
        today = datetime.today().date()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

    @property
    def full_address(self):
        parts = [self.house_name, self.village, self.city, self.district, self.state, self.country, self.pincode]
        return ', '.join(filter(None, parts))


class ConsultancyNSC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    consultant_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    consultancy_type = db.Column(db.String(100))
    problem_issue = db.Column(db.Text)
    problem_with = db.Column(db.String(200))
    remedy_suggested = db.Column(db.Text)
    remarks = db.Column(db.Text)
    
    applicant = db.relationship('Applicant', back_populates='consultancies_nsc')
    consultant = db.relationship('User')
    images = db.relationship('NSCImage', backref='consultancy', cascade="all, delete-orphan")

class NSCImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultancy_nsc_id = db.Column(db.Integer, db.ForeignKey('consultancy_nsc.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))

class SampleSC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_uid = db.Column(db.String(12), unique=True, nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    allotted_department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    
    sample_name = db.Column(db.String(150))
    sample_type = db.Column(db.String(100))
    collection_date = db.Column(db.DateTime)
    submission_date = db.Column(db.DateTime, default=get_ist_time)
    primary_observations = db.Column(db.Text)
    recommended_storage = db.Column(db.String(200))
    storage_location = db.Column(db.String(100))
    dispose_before = db.Column(db.Date)
    quality_check_data = db.Column(db.Text)
    hazard_control = db.Column(db.Text)
    diagnostics_needed = db.Column(db.Text)
    current_status = db.Column(db.String(100), nullable=False, default='Submitted')
    remarks = db.Column(db.Text)
    
    applicant = db.relationship('Applicant', back_populates='samples_sc')
    assigned_staff = db.relationship('User')
    allotted_department = db.relationship('Department')
    images = db.relationship('SampleImage', backref='sample', cascade="all, delete-orphan")
    diagnoses = db.relationship('Diagnosis', backref='sample', cascade="all, delete-orphan")

class SampleImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_sc_id = db.Column(db.Integer, db.ForeignKey('sample_sc.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))

class Diagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sample_sc_id = db.Column(db.Integer, db.ForeignKey('sample_sc.id'), nullable=False)
    name = db.Column(db.String(150))
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    attachments = db.relationship('DiagnosisAttachment', backref='diagnosis', cascade="all, delete-orphan")

class DiagnosisAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    diagnosis_id = db.Column(db.Integer, db.ForeignKey('diagnosis.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))

class LabSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    address = db.Column(db.String(300))
    contact_number = db.Column(db.String(50))
    email = db.Column(db.String(120))
    logo_path = db.Column(db.String(255), nullable=True)

# --- NEW: Models for File Sharing Feature ---
class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    
    owner = db.relationship('User', backref='owned_folders')
    files = db.relationship('File', backref='folder', cascade="all, delete-orphan")
    permissions = db.relationship('FolderPermission', backref='folder', cascade="all, delete-orphan")

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False) # The unique name on disk
    original_filename = db.Column(db.String(255), nullable=False) # The name the user gave it
    uploaded_at = db.Column(db.DateTime, default=get_ist_time)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    uploader = db.relationship('User')

class FolderPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', backref='folder_permissions')

# --- NEW: Models for Mail Feature ---
class Mail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=get_ist_time)
    
    sender = db.relationship('User', backref='sent_mails')
    recipients = db.relationship('MailRecipient', backref='mail', cascade="all, delete-orphan")
    attachments = db.relationship('MailAttachment', backref='mail', cascade="all, delete-orphan")

class MailRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail_id = db.Column(db.Integer, db.ForeignKey('mail.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False) # Soft delete for inbox

    recipient = db.relationship('User', backref='received_mails')

class MailAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mail_id = db.Column(db.Integer, db.ForeignKey('mail.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)