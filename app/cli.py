import click
from datetime import date
from flask.cli import AppGroup

from app import db
from app.models.budget_line_item import BudgetLineItem
from app.models.fiscal_year import FiscalYear
from app.models.budget_allocation import BudgetAllocation
from app.services.fiscal_year import compute_fiscal_year_for_date


seed_cli = AppGroup("seed")

DEFAULT_LINE_ITEMS = [
    ("72250 336", "Maintenance and Repair"),
    ("72250 470", "Cabling"),
    ("72250 471", "Software"),
    ("72250 499", "Other Supplies"),
    ("72250 524", "Staff Development"),
    ("72250 599", "Other Charges"),
    ("72250 790", "Equipment"),
    ("Telecom", "Telecom"),
    ("Other", "Other"),
]


@seed_cli.command("run")
def seed_run():
    """Seed the database with default data."""
    _seed_line_items()
    _seed_fiscal_year()
    click.echo("Seed complete.")


def _seed_line_items():
    for code, name in DEFAULT_LINE_ITEMS:
        existing = BudgetLineItem.query.filter_by(code=code).first()
        if not existing:
            is_custom = code == "Other"
            item = BudgetLineItem(code=code, name=name, is_custom=is_custom)
            db.session.add(item)
            click.echo(f"  Created line item: {code} - {name}")
    db.session.commit()


def _seed_fiscal_year():
    today = date.today()
    label = compute_fiscal_year_for_date(today)
    existing = FiscalYear.query.filter_by(label=label).first()
    if not existing:
        if today.month >= 7:
            start = date(today.year, 7, 1)
            end = date(today.year + 1, 6, 30)
        else:
            start = date(today.year - 1, 7, 1)
            end = date(today.year, 6, 30)
        fy = FiscalYear(label=label, start_date=start, end_date=end)
        db.session.add(fy)
        db.session.commit()
        click.echo(f"  Created fiscal year: {label}")

        # Create zero-amount allocations for all line items
        items = BudgetLineItem.query.all()
        for item in items:
            alloc = BudgetAllocation(
                fiscal_year_id=fy.id,
                budget_line_item_id=item.id,
                allocated_amount=0,
            )
            db.session.add(alloc)
        db.session.commit()
        click.echo(f"  Created {len(items)} budget allocations for {label}")
    else:
        click.echo(f"  Fiscal year {label} already exists.")


def register_cli(app):
    app.cli.add_command(seed_cli)
