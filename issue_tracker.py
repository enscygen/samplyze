import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
import pytz

from models import db, Issue, IssueComment, IssueAttachment, User, PermissionNames
from forms import CreateIssueForm, CommentForm
from decorators import permission_required
from utils import generate_uid

# Create a Blueprint
issue_tracker_bp = Blueprint('issue_tracker', __name__, url_prefix='/issue-tracker', template_folder='templates')

def get_ist_time():
    """Returns the current time in IST."""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

@issue_tracker_bp.route('/')
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def dashboard():
    filter_by = request.args.get('filter', 'home') # Default to 'home' view
    
    query = Issue.query
    
    if filter_by == 'assigned':
        query = query.filter_by(assignee_id=current_user.id)
    elif filter_by == 'reported':
        query = query.filter_by(reporter_id=current_user.id)
    # UPDATED: New logic for the "Home" view
    elif filter_by == 'home':
        # Show issues where the verifier is not set (NULL) OR is the current user.
        # This creates a "to be verified" queue for everyone.
        query = query.filter(db.or_(Issue.verifier_id == None, Issue.verifier_id == current_user.id))
    
    issues = query.order_by(Issue.updated_at.desc()).all()
    
    return render_template('issue_tracker/dashboard.html', title='Issue Tracker', issues=issues, filter_by=filter_by)

@issue_tracker_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def create_issue():
    form = CreateIssueForm()
    users = User.query.order_by(User.name).all()
    form.assignee_id.choices = [('', '--')] + [(u.id, u.name) for u in users]
    form.verifier_id.choices = [('', '--')] + [(u.id, u.name) for u in users]

    if form.validate_on_submit():
        new_issue = Issue(
            issue_uid=f"ISS-{generate_uid()}",
            title=form.title.data,
            description=form.description.data,
            reporter_id=current_user.id,
            assignee_id=form.assignee_id.data,
            verifier_id=form.verifier_id.data,
            issue_type=form.issue_type.data,
            priority=form.priority.data,
            severity=form.severity.data
        )
        db.session.add(new_issue)
        db.session.commit()
        flash('New issue has been created.', 'success')
        return redirect(url_for('issue_tracker.view_issue', issue_id=new_issue.id))
        
    return render_template('issue_tracker/create_issue.html', title='Create New Issue', form=form)

@issue_tracker_bp.route('/<int:issue_id>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def view_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    comment_form = CommentForm()
    
    if comment_form.validate_on_submit():
        new_comment = IssueComment(
            issue_id=issue.id,
            author_id=current_user.id,
            comment=comment_form.comment.data
        )
        db.session.add(new_comment)
        issue.updated_at = get_ist_time()
        db.session.commit()
        flash('Your comment has been added.', 'success')
        return redirect(url_for('issue_tracker.view_issue', issue_id=issue.id))

    users = User.query.order_by(User.name).all()
    return render_template('issue_tracker/view_issue.html', title=f"Issue: {issue.title}", issue=issue, comment_form=comment_form, users=users)

@issue_tracker_bp.route('/delete/<int:issue_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def delete_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    if issue.reporter_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(issue)
    db.session.commit()
    flash(f"Issue #{issue.issue_uid} has been deleted.", 'success')
    return redirect(url_for('issue_tracker.dashboard'))

@issue_tracker_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def delete_comment(comment_id):
    comment = IssueComment.query.get_or_404(comment_id)
    issue_id = comment.issue_id
    if comment.author_id != current_user.id and not current_user.is_admin:
        abort(403)
        
    db.session.delete(comment)
    db.session.commit()
    flash("Comment has been deleted.", 'success')
    return redirect(url_for('issue_tracker.view_issue', issue_id=issue_id))

@issue_tracker_bp.route('/update_field/<int:issue_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_ACCESS_ISSUE_TRACKER)
def update_issue_field(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    field = request.form.get('field')
    value = request.form.get('value')

    if field and value is not None:
        try:
            if value == '':
                value = None
            setattr(issue, field, value)
            issue.updated_at = get_ist_time()
            db.session.commit()
            return jsonify({'success': True, 'message': f'{field.replace("_", " ").title()} updated.'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'Invalid field or value.'})
