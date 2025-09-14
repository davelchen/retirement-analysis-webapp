"""
Unit tests for Monte Carlo simulation engine.
"""
import pytest
import numpy as np
from simulation import SimulationParams, RetirementSimulator, calculate_percentiles, calculate_summary_stats


class TestSimulationParams:
    """Test SimulationParams validation and initialization"""
    
    def test_default_params_valid(self):
        """Test that default parameters are valid"""
        params = SimulationParams()
        simulator = RetirementSimulator(params)
        # Should not raise an exception
        assert simulator.params.start_capital == 7_550_000
    
    def test_allocation_weights_validation(self):
        """Test allocation weights sum to 1.0"""
        params = SimulationParams(w_equity=0.5, w_bonds=0.3, w_real_estate=0.1, w_cash=0.05)
        with pytest.raises(ValueError, match="Allocation weights must sum to 1.0"):
            RetirementSimulator(params)
    
    def test_allocation_weights_valid(self):
        """Test valid allocation weights"""
        params = SimulationParams(w_equity=0.6, w_bonds=0.2, w_real_estate=0.15, w_cash=0.05)
        simulator = RetirementSimulator(params)
        assert abs(sum([params.w_equity, params.w_bonds, params.w_real_estate, params.w_cash]) - 1.0) < 1e-6
    
    def test_tax_brackets_default_mjf(self):
        """Test default tax brackets for MFJ"""
        params = SimulationParams(filing_status="MFJ")
        expected = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
        assert params.tax_brackets == expected
    
    def test_tax_brackets_default_single(self):
        """Test default tax brackets for Single"""
        params = SimulationParams(filing_status="Single")
        expected = [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        assert params.tax_brackets == expected

    def test_social_security_default_params(self):
        """Test Social Security default parameters"""
        params = SimulationParams()
        assert params.social_security_enabled == True
        assert params.ss_annual_benefit == 40_000
        assert params.ss_start_age == 67
        assert params.ss_benefit_scenario == "moderate"
        assert params.ss_custom_reduction == 0.10
        assert params.ss_reduction_start_year == 2034

    def test_social_security_custom_params(self):
        """Test Social Security custom parameters"""
        params = SimulationParams(
            social_security_enabled=False,
            ss_annual_benefit=55_000,
            ss_start_age=70,
            ss_benefit_scenario="conservative",
            ss_custom_reduction=0.15,
            ss_reduction_start_year=2035
        )
        assert params.social_security_enabled == False
        assert params.ss_annual_benefit == 55_000
        assert params.ss_start_age == 70
        assert params.ss_benefit_scenario == "conservative"
        assert params.ss_custom_reduction == 0.15
        assert params.ss_reduction_start_year == 2035

    def test_social_security_scenarios_valid(self):
        """Test valid Social Security scenarios"""
        valid_scenarios = ['conservative', 'moderate', 'optimistic', 'custom']
        for scenario in valid_scenarios:
            params = SimulationParams(ss_benefit_scenario=scenario)
            assert params.ss_benefit_scenario == scenario

    def test_social_security_age_range_valid(self):
        """Test valid Social Security start ages"""
        for age in [62, 65, 67, 70]:
            params = SimulationParams(ss_start_age=age)
            assert params.ss_start_age == age


class TestRetirementSimulator:
    """Test retirement simulation logic"""
    
    def test_cape_withdrawal_rate(self):
        """Test CAPE-based withdrawal rate calculation"""
        params = SimulationParams(cape_now=25.0)
        simulator = RetirementSimulator(params)
        base_wr = simulator._get_base_withdrawal_rate()
        expected = 0.0175 + 0.5 * (1.0 / 25.0)
        assert abs(base_wr - expected) < 1e-10
    
    def test_re_income_ramp_preset(self):
        """Test real estate income for ramp preset"""
        params = SimulationParams(re_flow_preset="ramp", start_year=2026)
        simulator = RetirementSimulator(params)
        
        assert simulator._get_re_income(2026) == 50_000
        assert simulator._get_re_income(2027) == 60_000
        assert simulator._get_re_income(2028) == 75_000
        assert simulator._get_re_income(2030) == 75_000
    
    def test_re_income_delayed_preset(self):
        """Test real estate income for delayed preset"""
        params = SimulationParams(re_flow_preset="delayed", start_year=2026)
        simulator = RetirementSimulator(params)
        
        assert simulator._get_re_income(2030) == 0
        assert simulator._get_re_income(2031) == 50_000
        assert simulator._get_re_income(2032) == 60_000
        assert simulator._get_re_income(2033) == 75_000
    
    def test_college_topup(self):
        """Test college top-up calculation"""
        params = SimulationParams(college_growth_real=0.013)
        simulator = RetirementSimulator(params)
        
        # Should be zero outside 2032-2041
        assert simulator._get_college_topup(2031) == 0
        assert simulator._get_college_topup(2042) == 0
        
        # Should be 100k in 2032
        assert abs(simulator._get_college_topup(2032) - 100_000) < 1
        
        # Should grow by 1.3% annually
        topup_2033 = simulator._get_college_topup(2033)
        expected_2033 = 100_000 * (1.013)
        assert abs(topup_2033 - expected_2033) < 1
    
    def test_onetime_expenses(self):
        """Test expense streams"""
        params = SimulationParams(
            expense_streams=[
                {'amount': 50_000, 'start_year': 2033, 'years': 1, 'description': '2033 expense'},
                {'amount': 75_000, 'start_year': 2040, 'years': 1, 'description': '2040 expense'}
            ]
        )
        simulator = RetirementSimulator(params)
        
        assert simulator._get_onetime_expense(2032) == 0
        assert simulator._get_onetime_expense(2033) == 50_000
        assert simulator._get_onetime_expense(2040) == 75_000
        assert simulator._get_onetime_expense(2041) == 0
    
    def test_multiyear_expense_streams(self):
        """Test multi-year expense streams (e.g., college expenses)"""
        params = SimulationParams(
            expense_streams=[
                {'amount': 50_000, 'start_year': 2032, 'years': 4, 'description': 'Kid 1 college'},
                {'amount': 50_000, 'start_year': 2034, 'years': 4, 'description': 'Kid 2 college'}
            ]
        )
        simulator = RetirementSimulator(params)
        
        # Test individual years
        assert simulator._get_onetime_expense(2031) == 0
        assert simulator._get_onetime_expense(2032) == 50_000  # Kid 1 only
        assert simulator._get_onetime_expense(2033) == 50_000  # Kid 1 only
        assert simulator._get_onetime_expense(2034) == 100_000  # Both kids
        assert simulator._get_onetime_expense(2035) == 100_000  # Both kids
        assert simulator._get_onetime_expense(2036) == 50_000  # Kid 2 only
        assert simulator._get_onetime_expense(2037) == 50_000  # Kid 2 only
        assert simulator._get_onetime_expense(2038) == 0       # Neither
    
    def test_other_income(self):
        """Test other income calculation"""
        params = SimulationParams(
            other_income_amount=50_000,
            other_income_start_year=2030,
            other_income_years=5
        )
        simulator = RetirementSimulator(params)
        
        assert simulator._get_other_income(2029) == 0
        assert simulator._get_other_income(2030) == 50_000
        assert simulator._get_other_income(2034) == 50_000
        assert simulator._get_other_income(2035) == 0
    
    def test_spending_guardrails(self):
        """Test Guyton-Klinger guardrails"""
        params = SimulationParams(lower_wr=0.03, upper_wr=0.05, adjustment_pct=0.10)
        simulator = RetirementSimulator(params)
        
        # Test upper guardrail trigger
        portfolio_value = 1_000_000
        current_spend = 60_000  # 6% WR
        new_spend, action = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert action == "down"
        assert abs(new_spend - 54_000) < 1  # 60k * 0.9
        
        # Test lower guardrail trigger  
        current_spend = 25_000  # 2.5% WR
        new_spend, action = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert action == "up"
        assert abs(new_spend - 27_500) < 1  # 25k * 1.1
        
        # Test no guardrail trigger
        current_spend = 40_000  # 4% WR
        new_spend, action = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert action == "none"
        assert new_spend == current_spend
    
    def test_spending_bounds(self):
        """Test spending floor and ceiling"""
        params = SimulationParams(
            spending_floor_real=100_000,
            spending_ceiling_real=300_000,
            floor_end_year=2040
        )
        simulator = RetirementSimulator(params)
        
        # Test floor applied (within floor period)
        spending, floor_applied, ceiling_applied = simulator._apply_spending_bounds(80_000, 2035)
        assert spending == 100_000
        assert floor_applied == True
        assert ceiling_applied == False
        
        # Test floor not applied (after floor period)
        spending, floor_applied, ceiling_applied = simulator._apply_spending_bounds(80_000, 2045)
        assert spending == 80_000
        assert floor_applied == False
        assert ceiling_applied == False
        
        # Test ceiling applied
        spending, floor_applied, ceiling_applied = simulator._apply_spending_bounds(350_000, 2035)
        assert spending == 300_000
        assert floor_applied == False
        assert ceiling_applied == True
    
    def test_return_means_baseline(self):
        """Test return means for baseline regime"""
        params = SimulationParams(regime="baseline")
        simulator = RetirementSimulator(params)
        
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(0)
        assert eq_mean == params.equity_mean
        assert bond_mean == params.bonds_mean
        assert re_mean == params.real_estate_mean
        assert cash_mean == params.cash_mean
    
    def test_return_means_recession_recover(self):
        """Test return means for recession_recover regime"""
        params = SimulationParams(regime="recession_recover")
        simulator = RetirementSimulator(params)
        
        # Year 0: recession
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(0)
        assert eq_mean == -0.15
        
        # Year 1: recovery
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(1)
        assert eq_mean == 0.00
        
        # Year 2+: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(2)
        assert eq_mean == params.equity_mean
    
    def test_return_means_grind_lower(self):
        """Test return means for grind_lower regime"""
        params = SimulationParams(regime="grind_lower")
        simulator = RetirementSimulator(params)
        
        # Years 0-9: lower returns
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(5)
        assert eq_mean == 0.005
        assert bond_mean == 0.01
        assert re_mean == 0.005
        
        # Year 10+: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(10)
        assert eq_mean == params.equity_mean
        assert bond_mean == params.bonds_mean
    
    def test_simulation_reproducible(self):
        """Test that simulation is reproducible with fixed seed"""
        params = SimulationParams(num_sims=100, random_seed=42, horizon_years=10)
        simulator = RetirementSimulator(params)
        
        results1 = simulator.run_simulation()
        results2 = simulator.run_simulation()
        
        # Results should be identical with same seed
        np.testing.assert_array_equal(results1.terminal_wealth, results2.terminal_wealth)
        assert results1.success_rate == results2.success_rate
    
    def test_simulation_output_shapes(self):
        """Test that simulation outputs have correct shapes"""
        params = SimulationParams(num_sims=50, horizon_years=20)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()
        
        assert len(results.terminal_wealth) == 50
        assert results.wealth_paths.shape == (50, 21)  # +1 for initial wealth
        assert len(results.guardrail_hits) == 50
        assert len(results.years_depleted) == 50
        assert 0 <= results.success_rate <= 1
    
    def test_simulation_with_depletion(self):
        """Test simulation that leads to portfolio depletion"""
        params = SimulationParams(
            start_capital=300_000,  # Very small portfolio
            num_sims=10,
            horizon_years=15,  # Longer horizon
            spending_floor_real=120_000,  # Very high floor
            social_security_enabled=False,  # Disable SS to force depletion
            random_seed=42
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Should have some failures with these aggressive parameters
        assert results.success_rate < 1.0
        assert np.any(results.years_depleted > 0)


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_calculate_percentiles(self):
        """Test percentile calculation"""
        # Create test data with known percentiles
        wealth_paths = np.array([
            [100, 110, 120],  # Sim 1
            [100, 105, 110],  # Sim 2
            [100, 115, 130],  # Sim 3
            [100, 125, 140],  # Sim 4
            [100, 135, 150]   # Sim 5
        ])
        
        percentiles = calculate_percentiles(wealth_paths)
        
        # Check shape
        assert percentiles['p10'].shape == (3,)
        assert percentiles['p50'].shape == (3,)
        assert percentiles['p90'].shape == (3,)
        
        # Initial values should all be 100
        assert percentiles['p10'][0] == 100
        assert percentiles['p50'][0] == 100
        assert percentiles['p90'][0] == 100
        
        # Final values: [110, 120, 130, 140, 150]
        # Check that percentiles are in reasonable ranges
        assert 110 <= percentiles['p10'][2] <= 120  # P10 should be between min and 2nd value
        assert percentiles['p50'][2] == 130  # P50 should be median (middle value)
        assert 140 <= percentiles['p90'][2] <= 150  # P90 should be between 4th and max value
    
    def test_calculate_summary_stats(self):
        """Test summary statistics calculation"""
        terminal_wealth = np.array([5_000_000, 8_000_000, 12_000_000, 15_000_000, 20_000_000])
        
        stats = calculate_summary_stats(terminal_wealth)
        
        assert stats['mean'] == 12_000_000
        assert stats['p50'] == 12_000_000
        # Check percentiles are in reasonable ranges
        assert 5_000_000 <= stats['p10'] <= 8_000_000
        assert 15_000_000 <= stats['p90'] <= 20_000_000
        
        # Probability calculations
        assert stats['prob_below_5m'] == 0.0  # None below 5M
        assert stats['prob_below_10m'] == 0.4  # 2 out of 5
        assert stats['prob_below_15m'] == 0.6  # 3 out of 5
    
    def test_return_means_late_recession(self):
        """Test return means for late_recession regime"""
        params = SimulationParams(regime="late_recession")
        simulator = RetirementSimulator(params)
        
        # Years 0-9: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(5)
        assert eq_mean == params.equity_mean
        
        # Year 10: recession start
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(10)
        assert eq_mean == -0.20
        assert re_mean == -0.05
        
        # Year 11: continued recession
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(11)
        assert eq_mean == -0.05
        
        # Year 12: recovery bounce
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(12)
        assert eq_mean == 0.15
        
        # Year 13+: back to baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(13)
        assert eq_mean == params.equity_mean
    
    def test_return_means_inflation_shock(self):
        """Test return means for inflation_shock regime"""
        params = SimulationParams(regime="inflation_shock")
        simulator = RetirementSimulator(params)
        
        # Years 0-2: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(2)
        assert eq_mean == params.equity_mean
        
        # Years 3-7: inflation period
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(5)
        assert eq_mean == 0.01  # Poor equity returns
        assert bond_mean == -0.02  # Bonds hurt by inflation
        assert re_mean == 0.08  # RE benefits from inflation
        assert cash_mean == 0.01
        
        # Year 8+: back to baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(8)
        assert eq_mean == params.equity_mean
    
    def test_return_means_long_bear(self):
        """Test return means for long_bear regime"""
        params = SimulationParams(regime="long_bear")
        simulator = RetirementSimulator(params)
        
        # Years 0-4: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(3)
        assert eq_mean == params.equity_mean
        
        # Years 5-15: bear market
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(10)
        assert eq_mean == 0.02
        assert bond_mean == 0.025
        assert re_mean == 0.015
        
        # Year 16+: back to baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(16)
        assert eq_mean == params.equity_mean
    
    def test_return_means_tech_bubble(self):
        """Test return means for tech_bubble regime"""
        params = SimulationParams(regime="tech_bubble")
        simulator = RetirementSimulator(params)
        
        # Years 0-3: bubble
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(2)
        assert eq_mean == params.equity_mean * 1.5
        
        # Years 4-6: crash
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(5)
        assert eq_mean == -0.10
        
        # Year 7+: back to baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(7)
        assert eq_mean == params.equity_mean
    
    def test_return_means_custom_regime(self):
        """Test return means for custom regime"""
        params = SimulationParams(
            regime="custom",
            custom_equity_shock_year=3,
            custom_equity_shock_return=-0.25,
            custom_shock_duration=2,
            custom_recovery_years=3,
            custom_recovery_equity_return=0.015
        )
        simulator = RetirementSimulator(params)
        
        # Years 0-2: baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(2)
        assert eq_mean == params.equity_mean
        
        # Years 3-4: shock period
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(3)
        assert eq_mean == -0.25
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(4)
        assert eq_mean == -0.25
        
        # Years 5-7: recovery period
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(6)
        assert eq_mean == 0.015
        
        # Year 8+: back to baseline
        eq_mean, bond_mean, re_mean, cash_mean = simulator._get_return_means(8)
        assert eq_mean == params.equity_mean
    
    def test_college_disabled(self):
        """Test college expenses can be disabled"""
        params = SimulationParams(college_enabled=False)
        simulator = RetirementSimulator(params)
        
        # Should return 0 for all college years
        assert simulator._get_college_topup(2032) == 0
        assert simulator._get_college_topup(2035) == 0
        assert simulator._get_college_topup(2041) == 0
    
    def test_college_custom_parameters(self):
        """Test custom college parameters"""
        params = SimulationParams(
            college_enabled=True,
            college_base_amount=75_000,
            college_start_year=2030,
            college_end_year=2033,
            college_growth_real=0.02
        )
        simulator = RetirementSimulator(params)
        
        # Before start
        assert simulator._get_college_topup(2029) == 0
        
        # During college period
        assert abs(simulator._get_college_topup(2030) - 75_000) < 1
        assert abs(simulator._get_college_topup(2031) - 76_500) < 1  # 75k * 1.02
        assert abs(simulator._get_college_topup(2032) - 78_030) < 1  # 75k * 1.02^2
        assert abs(simulator._get_college_topup(2033) - 79_591) < 1  # 75k * 1.02^3
        
        # After end
        assert simulator._get_college_topup(2034) == 0
    
    def test_re_flow_disabled(self):
        """Test real estate cash flow can be disabled"""
        params = SimulationParams(re_flow_enabled=False, start_year=2026)
        simulator = RetirementSimulator(params)
        
        # Should return 0 for all years
        assert simulator._get_re_income(2026) == 0
        assert simulator._get_re_income(2030) == 0
        assert simulator._get_re_income(2035) == 0
    
    def test_re_flow_custom_parameters(self):
        """Test custom real estate parameters"""
        params = SimulationParams(
            re_flow_enabled=True,
            re_flow_preset="custom",
            re_flow_start_year=2028,
            re_flow_year1_amount=25_000,
            re_flow_year2_amount=35_000,
            re_flow_steady_amount=50_000,
            re_flow_delay_years=2,
            start_year=2026
        )
        simulator = RetirementSimulator(params)
        
        # Before effective start (2028 + 2 = 2030)
        assert simulator._get_re_income(2029) == 0
        
        # Year 1 of RE income
        assert simulator._get_re_income(2030) == 25_000
        
        # Year 2 of RE income
        assert simulator._get_re_income(2031) == 35_000
        
        # Steady state
        assert simulator._get_re_income(2032) == 50_000
        assert simulator._get_re_income(2035) == 50_000

    def test_social_security_income_integration(self):
        """Test Social Security income integration with simulation"""
        params = SimulationParams(
            social_security_enabled=True,
            ss_annual_benefit=45_000,
            ss_start_age=67,
            ss_benefit_scenario="moderate",
            ss_reduction_start_year=2034,
            start_year=2026
        )
        simulator = RetirementSimulator(params)

        # Before eligible age (age 66 in 2027, start_age is 67)
        ss_income = simulator._get_social_security_income(2027)
        assert ss_income == 0

        # At eligible age (age 68 in 2029, start_age is 67)
        ss_income = simulator._get_social_security_income(2029)
        assert ss_income == 45_000

        # Later (age 70 in 2031)
        ss_income = simulator._get_social_security_income(2031)
        assert ss_income == 45_000

        # Before reduction year (2033)
        ss_income = simulator._get_social_security_income(2033)
        assert ss_income == 45_000

        # After reduction starts (2035) - moderate scenario
        ss_income = simulator._get_social_security_income(2035)
        expected = 45_000 * (1 - 0.06)  # 5% base + 1% for 1 year = 6%
        assert abs(ss_income - expected) < 1

    def test_social_security_income_disabled(self):
        """Test Social Security income when disabled"""
        params = SimulationParams(
            social_security_enabled=False,
            ss_annual_benefit=45_000,
            start_year=2026
        )
        simulator = RetirementSimulator(params)

        # Should return 0 even when age-eligible
        ss_income = simulator._get_social_security_income(2035)
        assert ss_income == 0

    def test_social_security_income_scenarios(self):
        """Test different Social Security funding scenarios"""
        base_params = {
            'social_security_enabled': True,
            'ss_annual_benefit': 40_000,
            'ss_start_age': 67,
            'ss_reduction_start_year': 2034,
            'start_year': 2026
        }

        # Conservative scenario
        params = SimulationParams(**base_params, ss_benefit_scenario="conservative")
        simulator = RetirementSimulator(params)
        ss_income = simulator._get_social_security_income(2035)
        expected = 40_000 * (1 - 0.19)  # 19% cut
        assert abs(ss_income - expected) < 1

        # Optimistic scenario
        params = SimulationParams(**base_params, ss_benefit_scenario="optimistic")
        simulator = RetirementSimulator(params)
        ss_income = simulator._get_social_security_income(2035)
        assert ss_income == 40_000  # No cuts

        # Custom scenario
        params = SimulationParams(**base_params, ss_benefit_scenario="custom", ss_custom_reduction=0.12)
        simulator = RetirementSimulator(params)
        ss_income = simulator._get_social_security_income(2035)
        expected = 40_000 * (1 - 0.12)  # 12% custom cut
        assert abs(ss_income - expected) < 1