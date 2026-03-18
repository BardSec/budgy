from datetime import datetime, timezone
from app import db


class FiscalYear(db.Model):
    __tablename__ = "fiscal_years"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "2025-2026"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    allocations = db.relationship(
        "BudgetAllocation", backref="fiscal_year", lazy="dynamic"
    )
    purchases = db.relationship("Purchase", backref="fiscal_year", lazy="dynamic")

    def __repr__(self):
        return f"<FiscalYear {self.label}>"
