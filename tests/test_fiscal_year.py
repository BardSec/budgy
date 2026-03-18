from datetime import date
from app.services.fiscal_year import compute_fiscal_year_for_date, get_or_create_fiscal_year


class TestFiscalYearCalculation:
    def test_july_first_belongs_to_new_fy(self):
        assert compute_fiscal_year_for_date(date(2025, 7, 1)) == "2025-2026"

    def test_june_thirtieth_belongs_to_old_fy(self):
        assert compute_fiscal_year_for_date(date(2026, 6, 30)) == "2025-2026"

    def test_january_belongs_to_prior_start_year(self):
        assert compute_fiscal_year_for_date(date(2026, 1, 15)) == "2025-2026"

    def test_december_belongs_to_current_start_year(self):
        assert compute_fiscal_year_for_date(date(2025, 12, 1)) == "2025-2026"

    def test_june_first(self):
        assert compute_fiscal_year_for_date(date(2025, 6, 1)) == "2024-2025"

    def test_july_second(self):
        assert compute_fiscal_year_for_date(date(2024, 7, 2)) == "2024-2025"

    def test_get_or_create_creates_new(self, app, db):
        with app.app_context():
            fy = get_or_create_fiscal_year(date(2025, 8, 15))
            assert fy.label == "2025-2026"
            assert fy.start_date == date(2025, 7, 1)
            assert fy.end_date == date(2026, 6, 30)

    def test_get_or_create_returns_existing(self, app, db, sample_fiscal_year):
        with app.app_context():
            fy = get_or_create_fiscal_year(date(2025, 10, 1))
            assert fy.id == sample_fiscal_year.id
