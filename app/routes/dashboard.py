from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.fiscal_year import FiscalYear
from app.models.purchase import Purchase
from app.services.budget import get_budget_summary, get_budget_totals
from app.services.fiscal_year import get_or_create_fiscal_year, get_all_fiscal_years
from app.utils.decorators import manager_required
from datetime import date

dashboard_bp = Blueprint(
    "dashboard", __name__, template_folder="../templates/dashboard"
)


@dashboard_bp.route("/")
@login_required
@manager_required
def index():
    fiscal_years = get_all_fiscal_years()

    # Get selected fiscal year
    fy_id = request.args.get("fy", type=int)
    if fy_id:
        fiscal_year = FiscalYear.query.get(fy_id)
    else:
        fiscal_year = get_or_create_fiscal_year(date.today())

    if not fiscal_year:
        fiscal_year = get_or_create_fiscal_year(date.today())

    summary = get_budget_summary(fiscal_year.id)
    totals = get_budget_totals(summary)

    # Recent purchases for this FY
    recent_purchases = (
        Purchase.query.filter_by(fiscal_year_id=fiscal_year.id)
        .filter(Purchase.status != "rejected")
        .order_by(Purchase.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard/index.html",
        fiscal_year=fiscal_year,
        fiscal_years=fiscal_years,
        summary=summary,
        totals=totals,
        recent_purchases=recent_purchases,
    )
