from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import pytz
from sqlalchemy import event, Table
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

# --- NEW: Models for Role-Based Permission System ---

# Association table for the many-to-many relationship between roles and permissions
role_permissions = Table('role_permissions', db.metadata,
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

# UPDATED: Renamed this class to avoid a name conflict
class PermissionNames:
    # These are the static permissions available in the system
    CAN_ACCESS_APPLICANT_SERVICES = 'can_access_applicant_services'
    CAN_ACCESS_SAMPLING_SERVICES = 'can_access_sampling_services'
    CAN_ACCESS_MAIL = 'can_access_mail'
    CAN_ACCESS_VISITOR_MANAGEMENT = 'can_access_visitor_management'
    CAN_ACCESS_KNOWLEDGE_BASE = 'can_access_knowledge_base'
    CAN_ACCESS_FILE_SHARING = 'can_access_file_sharing'
    CAN_ACCESS_EQUIPMENT_LOGGING = 'can_access_equipment_logging'
    CAN_MANAGE_ARCHIVES = 'can_manage_archives'
    CAN_VIEW_ALL_SAMPLES = 'can_view_all_samples'
    CAN_ACCESS_ISSUE_TRACKER = 'can_access_issue_tracker'
    CAN_MANAGE_INVENTORY = 'can_manage_inventory'

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    permissions = db.relationship('Permission', secondary=role_permissions, backref=db.backref('roles', lazy='dynamic'))

    def has_permission(self, perm):
        return any(p.name == perm for p in self.permissions)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)


# --- UPDATED: User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # The 'role' text field is replaced with a foreign key to the Role table
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    
    department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    department = db.relationship('Department', backref=db.backref('staff', lazy=True))

    def can(self, perm):
        """Check if the user has a specific permission."""
        return self.role is not None and self.role.has_permission(perm)

    @property
    def is_admin(self):
        """Property to check if the user has the admin role."""
        return self.role is not None and self.role.name == 'Admin'


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# ... (All other models: Applicant, SampleSC, Mail, etc. remain the same) ...
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
    result_is_rich = db.Column(db.Boolean, default=False)
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
    nav_logo_path = db.Column(db.String(255), nullable=True)
    show_name_in_navbar = db.Column(db.Boolean, default=True)
    show_name_in_reports = db.Column(db.Boolean, default=True)
    website_url = db.Column(db.String(300))
    verification_url = db.Column(db.String(300))

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

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_number = db.Column(db.String(100), unique=True, nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=True)
    name = db.Column(db.String(150), nullable=False)
    make_model = db.Column(db.String(200))
    purchase_date = db.Column(db.Date)
    last_calibration_date = db.Column(db.Date)
    multi_user = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(150))
    
    logs = db.relationship('EquipmentLog', backref='equipment', cascade="all, delete-orphan")

class EquipmentLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=get_ist_time, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text)

    user = db.relationship('User')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=get_ist_time, nullable=False)
    
    user = db.relationship('User')

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_uid = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text)
    id_type = db.Column(db.String(100))
    id_number = db.Column(db.String(100))
    applicant_uid = db.Column(db.String(10), nullable=True) # Link to an existing applicant
    institution = db.Column(db.String(200))
    purpose = db.Column(db.Text)
    entry_time = db.Column(db.DateTime, default=get_ist_time, nullable=False)
    exit_time = db.Column(db.DateTime, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    vehicle_type = db.Column(db.String(100))
    vehicle_number = db.Column(db.String(50))
    assigned_department_id = db.Column(db.Integer, db.ForeignKey('department.id', ondelete='SET NULL'), nullable=True)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    assigned_department = db.relationship('Department')
    assigned_staff = db.relationship('User')

class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) # 'Diagnosis' or 'Remedy'
    name = db.Column(db.String(150), nullable=False)    # e.g., "Fungal Test" or "Pest Infestation"
    title = db.Column(db.String(150), nullable=True)     # Only for Diagnosis
    description = db.Column(db.Text, nullable=True)    # For Diagnosis Method or Remedy Details

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Sample' or 'Applicant'
    subject_template = db.Column(db.Text)
    body_template = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_time)


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_uid = db.Column(db.String(15), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    verifier_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    issue_type = db.Column(db.String(50), default='Bug')
    priority = db.Column(db.String(10), default='P2')
    severity = db.Column(db.String(10), default='S2')
    status = db.Column(db.String(50), default='New')
    
    created_at = db.Column(db.DateTime, default=get_ist_time)
    updated_at = db.Column(db.DateTime, default=get_ist_time, onupdate=get_ist_time)

    reporter = db.relationship('User', foreign_keys=[reporter_id])
    assignee = db.relationship('User', foreign_keys=[assignee_id])
    verifier = db.relationship('User', foreign_keys=[verifier_id])
    
    comments = db.relationship('IssueComment', backref='issue', cascade="all, delete-orphan")
    attachments = db.relationship('IssueAttachment', backref='issue', cascade="all, delete-orphan")

class IssueComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=get_ist_time)
    
    author = db.relationship('User')

class IssueAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=get_ist_time)
    
    uploader = db.relationship('User')
    
class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_uid = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    make = db.Column(db.String(100))
    model = db.Column(db.String(100))
    total_quantity = db.Column(db.String(100)) # Changed to String
    current_quantity = db.Column(db.Integer, nullable=False) # Is a percentage
    block_code = db.Column(db.String(50))
    lab_code = db.Column(db.String(50))
    location_code = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    remarks = db.Column(db.Text)