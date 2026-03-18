import csv
import io
from datetime import date

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    abort,
)
from flask_login import login_required, current_user

from app import db
from app.models.user import User
from app.models.budget_line_item import BudgetLineItem
from app.models.budget_allocation import BudgetAllocation
from app.models.fiscal_year import FiscalYear
from app.models.purchase import Purchase
from app.models.document import Document
from app.models.activity_log import ActivityLog
from app.services.activity import log_activity
from app.services.storage import get_storage_backend
from app.utils.decorators import admin_required
from app.utils.forms import (
    BudgetAllocationForm,
    FiscalYearForm,
    BudgetLineItemForm,
    UserEditForm,
    PurchaseStatusForm,
)

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_request
def check_admin():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if not current_user.is_admin:
        abort(403)


# ── Dashboard ──────────────────────────────────────────────────
@admin_bp.route("/")
def index():
    user_count = User.query.count()
    purchase_count = Purchase.query.count()
    fy_count = FiscalYear.query.count()
    recent_logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    return render_template(
        "admin/index.html",
        user_count=user_count,
        purchase_count=purchase_count,
        fy_count=fy_count,
        recent_logs=recent_logs,
    )


# ── Users ──────────────────────────────────────────────────────
@admin_bp.route("/users")
def users():
    users = User.query.order_by(User.display_name).all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
def user_edit(id):
    user = User.query.get_or_404(id)
    form = UserEditForm(obj=user)

    if request.method == "GET":
        form.is_active.data = "1" if user.is_active else "0"

    if form.validate_on_submit():
        user.display_name = form.display_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data == "1"
        db.session.commit()
        log_activity(current_user.id, "user_updated", "user", user.id)
        flash(f"User {user.email} updated.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_edit.html", form=form, user=user)


# ── Fiscal Years ───────────────────────────────────────────────
@admin_bp.route("/fiscal-years")
def fiscal_years():
    fys = FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    return render_template("admin/fiscal_years.html", fiscal_years=fys)


@admin_bp.route("/fiscal-years/new", methods=["GET", "POST"])
def fiscal_year_create():
    form = FiscalYearForm()
    if form.validate_on_submit():
        fy = FiscalYear(
            label=form.label.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
        )
        db.session.add(fy)
        db.session.commit()
        log_activity(current_user.id, "fiscal_year_created", "fiscal_year", fy.id)
        flash("Fiscal year created.", "success")
        return redirect(url_for("admin.fiscal_years"))
    return render_template("admin/fiscal_year_form.html", form=form, edit=False)


@admin_bp.route("/fiscal-years/<int:id>/edit", methods=["GET", "POST"])
def fiscal_year_edit(id):
    fy = FiscalYear.query.get_or_404(id)
    form = FiscalYearForm(obj=fy)
    if form.validate_on_submit():
        fy.label = form.label.data
        fy.start_date = form.start_date.data
        fy.end_date = form.end_date.data
        db.session.commit()
        log_activity(current_user.id, "fiscal_year_updated", "fiscal_year", fy.id)
        flash("Fiscal year updated.", "success")
        return redirect(url_for("admin.fiscal_years"))
    return render_template("admin/fiscal_year_form.html", form=form, edit=True, fy=fy)


# ── Budget Line Items ─────────────────────────────────────────
@admin_bp.route("/line-items")
def line_items():
    items = BudgetLineItem.query.order_by(BudgetLineItem.code).all()
    return render_template("admin/line_items.html", items=items)


@admin_bp.route("/line-items/new", methods=["GET", "POST"])
def line_item_create():
    form = BudgetLineItemForm()
    if form.validate_on_submit():
        item = BudgetLineItem(code=form.code.data, name=form.name.data)
        db.session.add(item)
        db.session.commit()
        log_activity(current_user.id, "line_item_created", "budget_line_item", item.id)
        flash("Line item created.", "success")
        return redirect(url_for("admin.line_items"))
    return render_template("admin/line_item_form.html", form=form, edit=False)


@admin_bp.route("/line-items/<int:id>/edit", methods=["GET", "POST"])
def line_item_edit(id):
    item = BudgetLineItem.query.get_or_404(id)
    form = BudgetLineItemForm(obj=item)
    if form.validate_on_submit():
        item.code = form.code.data
        item.name = form.name.data
        db.session.commit()
        log_activity(current_user.id, "line_item_updated", "budget_line_item", item.id)
        flash("Line item updated.", "success")
        return redirect(url_for("admin.line_items"))
    return render_template("admin/line_item_form.html", form=form, edit=True, item=item)


# ── Budget Allocations ─────────────────────────────────────────
@admin_bp.route("/allocations")
def allocations():
    fy_id = request.args.get("fy", type=int)
    query = BudgetAllocation.query

    if fy_id:
        query = query.filter_by(fiscal_year_id=fy_id)

    allocs = (
        query.join(BudgetLineItem)
        .join(FiscalYear)
        .order_by(FiscalYear.start_date.desc(), BudgetLineItem.code)
        .all()
    )
    fiscal_years = FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    return render_template(
        "admin/allocations.html", allocations=allocs, fiscal_years=fiscal_years
    )


@admin_bp.route("/allocations/new", methods=["GET", "POST"])
def allocation_create():
    form = BudgetAllocationForm()
    form.fiscal_year_id.choices = [
        (fy.id, fy.label)
        for fy in FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    ]
    form.budget_line_item_id.choices = [
        (i.id, i.display_label)
        for i in BudgetLineItem.query.filter_by(is_active=True).order_by(BudgetLineItem.code).all()
    ]

    if form.validate_on_submit():
        existing = BudgetAllocation.query.filter_by(
            fiscal_year_id=form.fiscal_year_id.data,
            budget_line_item_id=form.budget_line_item_id.data,
        ).first()
        if existing:
            flash("An allocation for this line item and fiscal year already exists. Edit it instead.", "warning")
            return redirect(url_for("admin.allocation_edit", id=existing.id))

        alloc = BudgetAllocation(
            fiscal_year_id=form.fiscal_year_id.data,
            budget_line_item_id=form.budget_line_item_id.data,
            allocated_amount=form.allocated_amount.data,
        )
        db.session.add(alloc)
        db.session.commit()
        log_activity(current_user.id, "allocation_created", "budget_allocation", alloc.id)
        flash("Budget allocation created.", "success")
        return redirect(url_for("admin.allocations"))

    return render_template("admin/allocation_form.html", form=form, edit=False)


@admin_bp.route("/allocations/<int:id>/edit", methods=["GET", "POST"])
def allocation_edit(id):
    alloc = BudgetAllocation.query.get_or_404(id)
    form = BudgetAllocationForm(obj=alloc)
    form.fiscal_year_id.choices = [
        (fy.id, fy.label)
        for fy in FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    ]
    form.budget_line_item_id.choices = [
        (i.id, i.display_label)
        for i in BudgetLineItem.query.filter_by(is_active=True).order_by(BudgetLineItem.code).all()
    ]

    if form.validate_on_submit():
        alloc.fiscal_year_id = form.fiscal_year_id.data
        alloc.budget_line_item_id = form.budget_line_item_id.data
        alloc.allocated_amount = form.allocated_amount.data
        db.session.commit()
        log_activity(current_user.id, "allocation_updated", "budget_allocation", alloc.id)
        flash("Budget allocation updated.", "success")
        return redirect(url_for("admin.allocations"))

    return render_template("admin/allocation_form.html", form=form, edit=True, alloc=alloc)


# ── Allocation CSV Import ──────────────────────────────────────
@admin_bp.route("/allocations/import", methods=["GET", "POST"])
def allocation_import():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or not file.filename.endswith(".csv"):
            flash("Please upload a CSV file.", "danger")
            return redirect(url_for("admin.allocation_import"))

        fy_id = request.form.get("fiscal_year_id", type=int)
        if not fy_id:
            flash("Please select a fiscal year.", "danger")
            return redirect(url_for("admin.allocation_import"))

        reader = csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig"))
        count = 0
        for row in reader:
            code = row.get("code", "").strip()
            amount = row.get("amount", "0").strip().replace(",", "")
            if not code or not amount:
                continue

            item = BudgetLineItem.query.filter_by(code=code).first()
            if not item:
                flash(f"Line item code '{code}' not found, skipping.", "warning")
                continue

            try:
                amount_val = float(amount)
            except ValueError:
                flash(f"Invalid amount for code '{code}', skipping.", "warning")
                continue

            existing = BudgetAllocation.query.filter_by(
                fiscal_year_id=fy_id, budget_line_item_id=item.id
            ).first()
            if existing:
                existing.allocated_amount = amount_val
            else:
                alloc = BudgetAllocation(
                    fiscal_year_id=fy_id,
                    budget_line_item_id=item.id,
                    allocated_amount=amount_val,
                )
                db.session.add(alloc)
            count += 1

        db.session.commit()
        flash(f"Imported/updated {count} allocations.", "success")
        return redirect(url_for("admin.allocations"))

    fiscal_years = FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
    return render_template("admin/allocation_import.html", fiscal_years=fiscal_years)


# ── Purchases Admin ────────────────────────────────────────────
@admin_bp.route("/purchases")
def purchases():
    page = request.args.get("page", 1, type=int)
    query = Purchase.query.order_by(Purchase.created_at.desc())
    pagination = query.paginate(page=page, per_page=50, error_out=False)
    return render_template("admin/purchases.html", purchases=pagination.items, pagination=pagination)


@admin_bp.route("/purchases/<int:id>/delete", methods=["POST"])
def purchase_delete(id):
    purchase = Purchase.query.get_or_404(id)

    # Delete associated documents from storage
    storage = get_storage_backend()
    for doc in purchase.documents.all():
        try:
            storage.delete(doc.object_key)
        except Exception:
            pass

    db.session.delete(purchase)
    db.session.commit()
    log_activity(current_user.id, "purchase_deleted", "purchase", id)
    flash("Purchase deleted.", "success")
    return redirect(url_for("admin.purchases"))


# ── Documents Admin ────────────────────────────────────────────
@admin_bp.route("/documents")
def documents():
    page = request.args.get("page", 1, type=int)
    pagination = Document.query.order_by(Document.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/documents.html", documents=pagination.items, pagination=pagination)


@admin_bp.route("/documents/<int:id>/delete", methods=["POST"])
def document_delete(id):
    doc = Document.query.get_or_404(id)
    storage = get_storage_backend()
    try:
        storage.delete(doc.object_key)
    except Exception:
        pass
    db.session.delete(doc)
    db.session.commit()
    log_activity(current_user.id, "document_deleted", "document", id)
    flash("Document deleted.", "success")
    return redirect(url_for("admin.documents"))


# ── Activity Log ───────────────────────────────────────────────
@admin_bp.route("/activity")
def activity():
    page = request.args.get("page", 1, type=int)
    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template("admin/activity.html", logs=pagination.items, pagination=pagination)
