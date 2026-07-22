"""Unit tests for LAU date calculations and IRAV rent-increase math."""
from datetime import date

from app.models import (
    Contract, add_months, add_years, calculate_rent_increase, compute_contract_dates,
)


def test_add_years_leap_day():
    assert add_years(date(2024, 2, 29), 5) == date(2029, 2, 28)


def test_add_months_clamps_day():
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert add_months(date(2025, 7, 15), -4) == date(2025, 3, 15)


def test_contract_individual_landlord_5_years():
    c = Contract(property_id=1, start_date=date(2024, 3, 1), landlord_is_company=False)
    compute_contract_dates(c, today=date(2024, 3, 1))
    assert c.mandatory_end_date == date(2029, 3, 1)
    assert c.notice_deadline_date == date(2028, 11, 1)
    assert c.tacit_renewal_end_date == date(2032, 3, 1)


def test_contract_company_landlord_7_years():
    c = Contract(property_id=1, start_date=date(2024, 3, 1), landlord_is_company=True)
    compute_contract_dates(c, today=date(2024, 3, 1))
    assert c.mandatory_end_date == date(2031, 3, 1)
    assert c.notice_deadline_date == date(2030, 11, 1)
    assert c.tacit_renewal_end_date == date(2034, 3, 1)


def test_next_rent_update_rolls_forward():
    c = Contract(
        property_id=1, start_date=date(2024, 3, 1),
        has_rent_update_clause=True, rent_update_date=date(2024, 3, 1),
    )
    compute_contract_dates(c, today=date(2026, 7, 22))
    assert c.next_rent_update_date == date(2027, 3, 1)


def test_no_rent_update_clause_means_no_update_date():
    c = Contract(property_id=1, start_date=date(2024, 3, 1), has_rent_update_clause=False)
    compute_contract_dates(c, today=date(2026, 7, 22))
    assert c.next_rent_update_date is None


def test_rent_increase_irav():
    increase, new_rent = calculate_rent_increase(850.0, 0.0214)
    assert increase == 18.19
    assert new_rent == 868.19


def test_rent_increase_zero():
    increase, new_rent = calculate_rent_increase(0.0, 0.0214)
    assert increase == 0.0
    assert new_rent == 0.0
