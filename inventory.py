import os
import csv
import io
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from wtforms.validators import DataRequired

from models import db, InventoryItem, PermissionNames
from forms import InventoryItemForm
from decorators import permission_required
from utils import generate_uid

# Create a Blueprint
inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory', template_folder='templates')

@inventory_bp.route('/')
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def dashboard():
    form = InventoryItemForm()
    
    # Get filter parameters from the URL
    search = request.args.get('search', '')
    category = request.args.get('category', 'all')
    expiry_filter = request.args.get('expiry', 'all')
    quantity_filter = request.args.get('quantity', 'all')

    query = InventoryItem.query

    if search:
        search_term = f"%{search}%"
        query = query.filter(db.or_(
            InventoryItem.name.ilike(search_term),
            InventoryItem.item_uid.ilike(search_term),
            InventoryItem.block_code.ilike(search_term),
            InventoryItem.lab_code.ilike(search_term),
            InventoryItem.location_code.ilike(search_term)
        ))
    
    if category != 'all':
        query = query.filter_by(category=category)
        
    if expiry_filter == 'expired':
        query = query.filter(InventoryItem.expiry_date < date.today())
    elif expiry_filter == 'near_expiry':
        # Nearing expiry is within the next 30 days
        query = query.filter(InventoryItem.expiry_date.between(date.today(), date.today() + timedelta(days=30)))

    if quantity_filter == 'low_stock':
        # Low stock is 20% or less
        query = query.filter(InventoryItem.current_quantity <= 20)

    items = query.order_by(InventoryItem.name).all()
    
    # Pass filter values back to the template to keep them selected
    filters = {
        'search': search,
        'category': category,
        'expiry': expiry_filter,
        'quantity': quantity_filter
    }
    
    return render_template('inventory/dashboard.html', title='Inventory Management', form=form, items=items, filters=filters)

@inventory_bp.route('/add', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def add_item():
    form = InventoryItemForm()
    if form.validate_on_submit():
        new_item = InventoryItem(
            item_uid=form.item_uid.data,
            name=form.name.data,
            category=form.category.data,
            make=form.make.data,
            model=form.model.data,
            total_quantity=form.total_quantity.data,
            current_quantity=form.current_quantity.data,
            block_code=form.block_code.data,
            lab_code=form.lab_code.data,
            location_code=form.location_code.data,
            purchase_date=form.purchase_date.data,
            expiry_date=form.expiry_date.data,
            remarks=form.remarks.data
        )
        db.session.add(new_item)
        db.session.commit()
        flash(f"Item '{new_item.name}' has been added to the inventory.", 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
    return redirect(url_for('inventory.dashboard'))

@inventory_bp.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def edit_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    # Pass the original UID to the form to handle the uniqueness check correctly
    form = InventoryItemForm(obj=item, original_item_uid=item.item_uid)
    
    if form.validate_on_submit():
        # The UID is not changed, so we can't use populate_obj
        item.name = form.name.data
        item.category = form.category.data
        item.make = form.make.data
        item.model = form.model.data
        item.total_quantity = form.total_quantity.data
        item.current_quantity = form.current_quantity.data
        item.block_code = form.block_code.data
        item.lab_code = form.lab_code.data
        item.location_code = form.location_code.data
        item.purchase_date = form.purchase_date.data
        item.expiry_date = form.expiry_date.data
        item.remarks = form.remarks.data
        db.session.commit()
        flash(f"Item '{item.name}' has been updated.", 'success')
        return redirect(url_for('inventory.dashboard'))
    return render_template('inventory/add_edit_item.html', title='Edit Item', form=form, item=item)


@inventory_bp.route('/delete/<int:item_id>', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def delete_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash(f"Item '{item.name}' has been deleted.", 'success')
    return redirect(url_for('inventory.dashboard'))

@inventory_bp.route('/view/<int:item_id>')
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def view_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    return render_template('inventory/view_item.html', title=f"View Item: {item.name}", item=item)

@inventory_bp.route('/import', methods=['POST'])
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def import_csv():
    if 'file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('inventory.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return redirect(url_for('inventory.dashboard'))

    if file and file.filename.endswith('.csv'):
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            count = 0
            for row in csv_reader:
                row = {k.lower().strip(): v for k, v in row.items() if k is not None}
                
                purchase_date = datetime.strptime(row.get('purchase_date'), '%Y-%m-%d').date() if row.get('purchase_date') else None
                expiry_date = datetime.strptime(row.get('expiry_date'), '%Y-%m-%d').date() if row.get('expiry_date') else None

                new_item = InventoryItem(
                    item_uid=row.get('item_uid'),
                    name=row.get('name'),
                    category=row.get('category'),
                    make=row.get('make'),
                    model=row.get('model'),
                    total_quantity=row.get('total_quantity'),
                    current_quantity=int(row.get('current_quantity', 100)),
                    block_code=row.get('block_code'),
                    lab_code=row.get('lab_code'),
                    location_code=row.get('location_code'),
                    purchase_date=purchase_date,
                    expiry_date=expiry_date,
                    remarks=row.get('remarks')
                )
                db.session.add(new_item)
                count += 1
            
            db.session.commit()
            flash(f'Successfully imported {count} inventory items from the CSV file.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during import: {e}', 'danger')
    else:
        flash('Invalid file type. Please upload a .csv file.', 'danger')

    return redirect(url_for('inventory.dashboard'))

@inventory_bp.route('/export')
@login_required
@permission_required(PermissionNames.CAN_MANAGE_INVENTORY)
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ['item_uid', 'name', 'category', 'make', 'model', 'total_quantity', 'current_quantity', 'block_code', 'lab_code', 'location_code', 'purchase_date', 'expiry_date', 'remarks']
    writer.writerow(headers)
    
    items = InventoryItem.query.all()
    for item in items:
        writer.writerow([
            item.item_uid,
            item.name,
            item.category,
            item.make,
            item.model,
            item.total_quantity,
            item.current_quantity,
            item.block_code,
            item.lab_code,
            item.location_code,
            item.purchase_date.strftime('%Y-%m-%d') if item.purchase_date else '',
            item.expiry_date.strftime('%Y-%m-%d') if item.expiry_date else '',
            item.remarks
        ])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=inventory_export.csv"}
    )
