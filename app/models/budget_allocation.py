from datetime import datetime, timezone
from app import db


class BudgetAllocation(db.Model):
    __tablename__ = "budget_allocations"
    __table_args__ = (
        db.UniqueConstraint(
            "fiscal_year_id", "budget_line_item_id", name="uq_fy_line_item"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    fiscal_year_id = db.Column(
        db.Integer, db.ForeignKey("fiscal_years.id"), nullable=False
    )
    budget_line_item_id = db.Column(
        db.Integer, db.ForeignKey("budget_line_items.id"), nullable=False
    )
    allocated_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<BudgetAllocation FY:{self.fiscal_year_id} Line:{self.budget_line_item_id}>"
