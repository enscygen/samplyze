import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from models import db, Mail, MailRecipient, MailAttachment, User, PermissionNames
from forms import ComposeMailForm
from decorators import permission_required

# Create a Blueprint
mail_bp = Blueprint('mail', __name__, url_prefix='/mail', template_folder='templates')

# --- Helper Function ---
def delete_mail_file(filename):
    """Deletes a file from the mail attachments folder."""
    if not filename: return
    try:
        # Mail attachments are stored in the main UPLOAD_FOLDER
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error deleting mail attachment {filename}: {e}")

# --- Routes ---
@mail_bp.route('/')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def inbox():
    received_mails = MailRecipient.query.join(Mail).filter(
        MailRecipient.recipient_id == current_user.id, 
        MailRecipient.is_deleted == False
    ).order_by(MailRecipient.is_read.asc(), Mail.sent_at.desc()).all()
    
    return render_template('mail/inbox.html', title='Inbox', mails=received_mails)

@mail_bp.route('/sent')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def sent():
    sent_mails = Mail.query.filter_by(sender_id=current_user.id).order_by(Mail.sent_at.desc()).all()
    return render_template('mail/sent.html', title='Sent Mail', mails=sent_mails)

@mail_bp.route('/compose', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def compose():
    form = ComposeMailForm()
    form.recipients.choices = [(u.id, u.name) for u in User.query.filter(User.id != current_user.id).order_by(User.name).all()]

    if form.validate_on_submit():
        new_mail = Mail(
            sender_id=current_user.id,
            subject=form.subject.data,
            body=form.body.data
        )
        db.session.add(new_mail)
        db.session.flush()

        for user_id in form.recipients.data:
            recipient = MailRecipient(mail_id=new_mail.id, recipient_id=user_id)
            db.session.add(recipient)

        i = 0
        while f'attachments-{i}' in request.files:
            attachment_file = request.files[f'attachments-{i}']
            if attachment_file:
                original_filename = secure_filename(attachment_file.filename)
                unique_filename = f"mail_{new_mail.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{original_filename}"
                attachment_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename))
                
                attachment = MailAttachment(
                    mail_id=new_mail.id,
                    filename=unique_filename,
                    original_filename=original_filename
                )
                db.session.add(attachment)
            i += 1

        db.session.commit()
        flash('Your mail has been sent.', 'success')
        return redirect(url_for('mail.inbox'))

    return render_template('mail/compose.html', title='Compose Mail', form=form)

@mail_bp.route('/view/<int:recipient_mail_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def view_mail(recipient_mail_id):
    recipient_mail = MailRecipient.query.get_or_404(recipient_mail_id)
    
    if recipient_mail.recipient_id != current_user.id:
        abort(403)
        
    if not recipient_mail.is_read:
        recipient_mail.is_read = True
        db.session.commit()
        
    mail = recipient_mail.mail
    return render_template('mail/view_mail.html', title=mail.subject, mail=mail, recipient_mail=recipient_mail)

@mail_bp.route('/view_sent/<int:mail_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def view_sent_mail(mail_id):
    mail = Mail.query.get_or_404(mail_id)
    if mail.sender_id != current_user.id:
        abort(403)
    return render_template('mail/view_sent_mail.html', title=mail.subject, mail=mail)

@mail_bp.route('/delete/<int:recipient_mail_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def delete_mail(recipient_mail_id):
    recipient_mail = MailRecipient.query.get_or_404(recipient_mail_id)
    if recipient_mail.recipient_id != current_user.id:
        abort(403)
        
    recipient_mail.is_deleted = True
    db.session.commit()
    flash('Mail moved to trash.', 'success')
    return redirect(url_for('mail.inbox'))

# NEW: Route to permanently delete a sent mail
@mail_bp.route('/delete_sent/<int:mail_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def delete_sent_mail(mail_id):
    mail = Mail.query.get_or_404(mail_id)
    if mail.sender_id != current_user.id:
        abort(403)
    
    # Delete all associated attachment files from the server
    for attachment in mail.attachments:
        delete_mail_file(attachment.filename)
        
    # Delete the mail record from the database
    # The cascade will handle deleting recipients and attachments records
    db.session.delete(mail)
    db.session.commit()
    flash('Mail has been permanently deleted for all recipients.', 'success')
    return redirect(url_for('mail.sent'))


@mail_bp.route('/attachment/<int:attachment_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def download_attachment(attachment_id):
    attachment = MailAttachment.query.get_or_404(attachment_id)
    mail = attachment.mail
    
    is_recipient = MailRecipient.query.filter_by(mail_id=mail.id, recipient_id=current_user.id).first()
    if mail.sender_id != current_user.id and not is_recipient:
        abort(403)
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], attachment.filename, as_attachment=True, download_name=attachment.original_filename)

@mail_bp.route('/attachment/view/<int:attachment_id>')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_MAIL)
def view_attachment(attachment_id):
    attachment = MailAttachment.query.get_or_404(attachment_id)
    mail = attachment.mail
    
    is_recipient = MailRecipient.query.filter_by(mail_id=mail.id, recipient_id=current_user.id).first()
    if mail.sender_id != current_user.id and not is_recipient:
        abort(403)
        
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], attachment.filename, as_attachment=False, download_name=attachment.original_filename)
