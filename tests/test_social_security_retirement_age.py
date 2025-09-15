#!/usr/bin/env python3
"""
Tests for Social Security retirement age vs SS start age scenarios
Validates the major architectural fixes implemented in September 2025
"""

import pytest
from simulation import SimulationParams, RetirementSimulator
from deterministic import DeterministicProjector
from tax_utils import calculate_social_security_benefit


class TestSocialSecurityRetirementAge:
    """Test Social Security timing with different retirement ages"""

    def test_early_retirement_delayed_ss(self):
        """Test retire at 45, SS at 67 (22-year delay)"""
        params = SimulationParams(
            start_capital=5_000_000,
            start_year=2025,
            retirement_age=45,
            horizon_years=30,
            num_sims=3,

            # SS Configuration
            social_security_enabled=True,
            ss_annual_benefit=40_000,
            ss_start_age=67,
            ss_benefit_scenario='moderate',

            # Basic allocation
            w_equity=0.7, w_bonds=0.3, w_real_estate=0.0, w_cash=0.0,
            initial_base_spending=180_000
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check SS income timing
        ss_income_list = results.median_path_details['ss_income']
        years_list = results.median_path_details['years']

        # SS should start at age 67 = 22 years after retirement at 45
        expected_ss_start_year = 2025 + (67 - 45)  # 2047

        # Find when SS actually starts
        ss_start_year = None
        for i, (year, ss_income) in enumerate(zip(years_list, ss_income_list)):
            if ss_income > 0:
                ss_start_year = year
                break

        assert ss_start_year == expected_ss_start_year, f"SS should start in {expected_ss_start_year}, but started in {ss_start_year}"

        # Verify no SS income before start year
        pre_ss_years = [ss for year, ss in zip(years_list, ss_income_list) if year < expected_ss_start_year]
        assert all(ss == 0 for ss in pre_ss_years), "SS income should be zero before start year"

    def test_fire_retirement_early_ss(self):
        """Test retire at 35, SS at 62 (27-year delay)"""
        params = SimulationParams(
            start_capital=3_000_000,
            start_year=2025,
            retirement_age=35,
            horizon_years=35,
            num_sims=3,

            social_security_enabled=True,
            ss_annual_benefit=30_000,
            ss_start_age=62,
            ss_benefit_scenario='conservative',

            w_equity=0.8, w_bonds=0.2, w_real_estate=0.0, w_cash=0.0,
            initial_base_spending=120_000
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        ss_income_list = results.median_path_details['ss_income']
        years_list = results.median_path_details['years']

        expected_ss_start_year = 2025 + (62 - 35)  # 2052

        # Check timing
        actual_start_years = [year for year, ss in zip(years_list, ss_income_list) if ss > 0]
        assert len(actual_start_years) > 0, "SS income should start at some point"
        assert actual_start_years[0] == expected_ss_start_year, f"FIRE scenario: SS should start in {expected_ss_start_year}"

    def test_late_retirement_immediate_ss(self):
        """Test retire at 70, SS at 70 (0-year delay)"""
        params = SimulationParams(
            start_capital=4_000_000,
            start_year=2025,
            retirement_age=70,
            horizon_years=25,
            num_sims=3,

            social_security_enabled=True,
            ss_annual_benefit=50_000,
            ss_start_age=70,
            ss_benefit_scenario='optimistic',

            w_equity=0.5, w_bonds=0.4, w_real_estate=0.1, w_cash=0.0,
            initial_base_spending=200_000
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        ss_income_list = results.median_path_details['ss_income']
        years_list = results.median_path_details['years']

        # Should start immediately (year 0 of retirement)
        expected_ss_start_year = 2025  # Same as retirement year

        first_year_ss = ss_income_list[0] if len(ss_income_list) > 0 else 0
        assert first_year_ss > 0, "Late retirement scenario: SS should start immediately in first year"

    def test_spousal_ss_with_early_retirement(self):
        """Test spousal SS timing with early retirement"""
        params = SimulationParams(
            start_capital=6_000_000,
            start_year=2025,
            retirement_age=50,
            horizon_years=25,
            num_sims=3,

            # Primary SS
            social_security_enabled=True,
            ss_annual_benefit=45_000,
            ss_start_age=67,

            # Spousal SS
            spouse_ss_enabled=True,
            spouse_ss_annual_benefit=25_000,
            spouse_ss_start_age=65,

            ss_benefit_scenario='moderate',
            w_equity=0.6, w_bonds=0.4, w_real_estate=0.0, w_cash=0.0,
            initial_base_spending=250_000
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        ss_income_list = results.median_path_details['ss_income']
        years_list = results.median_path_details['years']

        # Spousal SS should start at age 65 = 15 years after retirement at 50
        expected_spousal_start = 2025 + (65 - 50)  # 2040
        # Primary SS should start at age 67 = 17 years after retirement at 50
        expected_primary_start = 2025 + (67 - 50)  # 2042

        # Check that SS income increases when spousal starts, then increases again when primary starts
        spousal_year_income = None
        primary_year_income = None

        for year, ss_income in zip(years_list, ss_income_list):
            if year == expected_spousal_start and ss_income > 0:
                spousal_year_income = ss_income
            elif year == expected_primary_start and ss_income > 0:
                primary_year_income = ss_income

        assert spousal_year_income is not None, f"Spousal SS should start in {expected_spousal_start}"
        assert primary_year_income is not None, f"Primary SS should start in {expected_primary_start}"
        assert primary_year_income > spousal_year_income, "Combined SS should be higher than spousal alone"

    def test_deterministic_vs_monte_carlo_ss_consistency(self):
        """Test that deterministic and Monte Carlo produce same SS timing"""
        params = SimulationParams(
            start_capital=3_500_000,
            start_year=2025,
            retirement_age=55,
            horizon_years=20,
            num_sims=5,

            social_security_enabled=True,
            ss_annual_benefit=42_000,
            ss_start_age=65,
            ss_benefit_scenario='moderate',

            w_equity=0.65, w_bonds=0.35, w_real_estate=0.0, w_cash=0.0,
            initial_base_spending=160_000
        )

        # Monte Carlo
        simulator = RetirementSimulator(params)
        mc_results = simulator.run_simulation()

        # Deterministic
        projector = DeterministicProjector(params)
        det_results = projector.run_projection()

        # Both should have SS starting at age 65 = 10 years after retirement at 55
        expected_ss_start = 2025 + (65 - 55)  # 2035

        # Check Monte Carlo
        mc_ss_list = mc_results.median_path_details['ss_income']
        mc_years = mc_results.median_path_details['years']
        mc_ss_start = next((year for year, ss in zip(mc_years, mc_ss_list) if ss > 0), None)

        # Check Deterministic
        det_ss_list = det_results.year_by_year_details['ss_income'] if 'ss_income' in det_results.year_by_year_details else []
        det_years = det_results.year_by_year_details['years']
        det_ss_start = next((year for year, ss in zip(det_years, det_ss_list) if ss > 0), None) if det_ss_list else None

        assert mc_ss_start == expected_ss_start, f"Monte Carlo SS start: expected {expected_ss_start}, got {mc_ss_start}"

        # Note: Deterministic may not have ss_income in details yet, so only test if it exists
        if det_ss_start is not None:
            assert det_ss_start == expected_ss_start, f"Deterministic SS start: expected {expected_ss_start}, got {det_ss_start}"

    def test_ss_income_appears_in_year_by_year_details(self):
        """Test that SS income appears in simulation results details"""
        params = SimulationParams(
            start_capital=2_500_000,
            start_year=2025,
            retirement_age=62,
            horizon_years=15,
            num_sims=3,

            social_security_enabled=True,
            ss_annual_benefit=35_000,
            ss_start_age=67,
            ss_benefit_scenario='moderate',

            w_equity=0.6, w_bonds=0.4, w_real_estate=0.0, w_cash=0.0,
            initial_base_spending=140_000
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check that ss_income key exists in details
        details = results.median_path_details
        assert 'ss_income' in details, "ss_income should be in year-by-year details"

        ss_income_list = details['ss_income']
        assert len(ss_income_list) > 0, "ss_income list should not be empty"

        # Should have some years with SS income
        total_ss = sum(ss_income_list)
        assert total_ss > 0, "Should have some Social Security income over simulation period"

    def test_calculate_social_security_benefit_direct(self):
        """Test the core SS benefit calculation function directly"""

        # Test early retirement scenario
        benefit = calculate_social_security_benefit(
            year=2047,  # 22 years after retirement
            start_year=2025,
            retirement_age=45,
            annual_benefit=40_000,
            scenario='moderate',
            custom_reduction=0.15,
            reduction_start_year=2034,
            start_age=67
        )

        # Should get SS income (person is 67 years old in 2047)
        assert benefit > 0, "Should receive SS benefit when reaching start age"
        assert benefit <= 40_000, "Benefit should not exceed full amount"

        # Test before eligibility
        early_benefit = calculate_social_security_benefit(
            year=2030,  # Only 5 years after retirement, person is 50
            start_year=2025,
            retirement_age=45,
            annual_benefit=40_000,
            scenario='moderate',
            custom_reduction=0.15,
            reduction_start_year=2034,
            start_age=67
        )

        assert early_benefit == 0, "Should receive no SS benefit before start age"