import os
import pytest
from app import create_app, db as _db
from app.models.user import User
from app.models.budget_line_item import BudgetLineItem
from app.models.fiscal_year import FiscalYear
from app.models.budget_allocation import BudgetAllocation
from app.models.purchase import Purchase


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    return app.test_client()


@pytest.fixture
def admin_user(db):
    user = User(
        email="admin@test.com",
        display_name="Admin User",
        role="admin",
        auth_provider="dev",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def staff_user(db):
    user = User(
        email="staff@test.com",
        display_name="Staff User",
        role="staff",
        auth_provider="dev",
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_line_items(db):
    items = []
    for code, name in [
        ("72250 336", "Maintenance and Repair"),
        ("72250 471", "Software"),
        ("Other", "Other"),
    ]:
        item = BudgetLineItem(code=code, name=name, is_custom=(code == "Other"))
        db.session.add(item)
        items.append(item)
    db.session.commit()
    return items


@pytest.fixture
def sample_fiscal_year(db):
    from datetime import date

    fy = FiscalYear(
        label="2025-2026",
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
    )
    db.session.add(fy)
    db.session.commit()
    return fy
