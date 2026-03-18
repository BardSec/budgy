from datetime import date
from app import db
from app.models.fiscal_year import FiscalYear


def compute_fiscal_year_for_date(d: date) -> str:
    """Return the fiscal year label (e.g. '2025-2026') for a given date.

    Fiscal year runs July 1 through June 30.
    A date in July 2025 through June 2026 belongs to FY 2025-2026.
    """
    if d.month >= 7:
        return f"{d.year}-{d.year + 1}"
    else:
        return f"{d.year - 1}-{d.year}"


def get_or_create_fiscal_year(d: date) -> FiscalYear:
    """Get or create the FiscalYear record for a given date."""
    label = compute_fiscal_year_for_date(d)
    fy = FiscalYear.query.filter_by(label=label).first()
    if fy is None:
        if d.month >= 7:
            start = date(d.year, 7, 1)
            end = date(d.year + 1, 6, 30)
        else:
            start = date(d.year - 1, 7, 1)
            end = date(d.year, 6, 30)
        fy = FiscalYear(label=label, start_date=start, end_date=end, is_active=True)
        db.session.add(fy)
        db.session.commit()
    return fy


def get_current_fiscal_year_label() -> str:
    """Return the label for the current fiscal year."""
    return compute_fiscal_year_for_date(date.today())


def get_all_fiscal_years():
    """Return all fiscal years ordered by start date descending."""
    return FiscalYear.query.order_by(FiscalYear.start_date.desc()).all()
