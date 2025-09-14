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


class TestPercentilePathDetails:
    """Test P10/P50/P90 path details functionality"""

    def test_simulation_results_has_percentile_paths(self):
        """Test that SimulationResults includes P10/P50/P90 path details"""
        params = SimulationParams(num_sims=100, random_seed=42, horizon_years=10)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check that all path details exist
        assert hasattr(results, 'median_path_details')
        assert hasattr(results, 'p10_path_details')
        assert hasattr(results, 'p90_path_details')

        # Check that all path details are dictionaries with expected keys
        expected_keys = [
            'years', 'start_assets', 'end_assets', 'base_spending',
            'adjusted_base_spending', 'college_topup', 'one_times',
            're_income', 'other_income', 'taxable_income', 'taxes',
            'net_need', 'gross_withdrawal', 'growth', 'inheritance',
            'withdrawal_rate', 'floor_applied', 'ceiling_applied',
            'guardrail_action', 'equity_allocation', 'bonds_allocation',
            'real_estate_allocation', 'cash_allocation'
        ]

        for path_details in [results.median_path_details, results.p10_path_details, results.p90_path_details]:
            assert isinstance(path_details, dict)
            for key in expected_keys:
                assert key in path_details, f"Missing key: {key}"
                assert isinstance(path_details[key], list), f"Key {key} should be list"
                assert len(path_details[key]) == params.horizon_years, f"Key {key} should have {params.horizon_years} values"

    def test_percentile_paths_have_different_terminal_values(self):
        """Test that P10/P50/P90 paths have significantly different terminal wealth"""
        params = SimulationParams(num_sims=1000, random_seed=42, horizon_years=20)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Get terminal wealth values from path details
        p10_terminal = results.p10_path_details['end_assets'][-1]
        p50_terminal = results.median_path_details['end_assets'][-1]
        p90_terminal = results.p90_path_details['end_assets'][-1]

        # Verify ordering: P10 < P50 < P90
        assert p10_terminal < p50_terminal, f"P10 ({p10_terminal:,.0f}) should be less than P50 ({p50_terminal:,.0f})"
        assert p50_terminal < p90_terminal, f"P50 ({p50_terminal:,.0f}) should be less than P90 ({p90_terminal:,.0f})"

        # Check that differences are substantial (not just rounding errors)
        assert (p50_terminal / p10_terminal) > 1.5, "P50 should be significantly higher than P10"
        assert (p90_terminal / p50_terminal) > 1.5, "P90 should be significantly higher than P50"

    def test_percentile_paths_match_wealth_percentiles(self):
        """Test that path terminal values match overall terminal wealth percentiles"""
        params = SimulationParams(num_sims=1000, random_seed=42, horizon_years=15)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Calculate percentiles from terminal wealth distribution
        wealth_p10 = np.percentile(results.terminal_wealth, 10)
        wealth_p50 = np.percentile(results.terminal_wealth, 50)
        wealth_p90 = np.percentile(results.terminal_wealth, 90)

        # Get terminal values from path details
        path_p10 = results.p10_path_details['end_assets'][-1]
        path_p50 = results.median_path_details['end_assets'][-1]
        path_p90 = results.p90_path_details['end_assets'][-1]

        # Should be close (within 5% tolerance since we're selecting specific simulations)
        tolerance = 0.05
        assert abs(path_p10 - wealth_p10) / wealth_p10 < tolerance, f"P10 path ({path_p10:,.0f}) doesn't match wealth P10 ({wealth_p10:,.0f})"
        assert abs(path_p50 - wealth_p50) / wealth_p50 < tolerance, f"P50 path ({path_p50:,.0f}) doesn't match wealth P50 ({wealth_p50:,.0f})"
        assert abs(path_p90 - wealth_p90) / wealth_p90 < tolerance, f"P90 path ({path_p90:,.0f}) doesn't match wealth P90 ({wealth_p90:,.0f})"

    def test_percentile_paths_internal_consistency(self):
        """Test that percentile path values are internally consistent"""
        params = SimulationParams(num_sims=500, random_seed=42, horizon_years=10)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        for label, path_details in [("P10", results.p10_path_details),
                                   ("P50", results.median_path_details),
                                   ("P90", results.p90_path_details)]:
            # Check that all arrays have the same length
            first_key = list(path_details.keys())[0]
            expected_len = len(path_details[first_key])

            for key, values in path_details.items():
                assert len(values) == expected_len, f"{label} {key} has wrong length: {len(values)} vs {expected_len}"

            # Check that start_assets and end_assets have reasonable relationship
            start_assets = path_details['start_assets']
            end_assets = path_details['end_assets']
            gross_withdrawals = path_details['gross_withdrawal']
            growth = path_details['growth']
            inheritance = path_details['inheritance']

            # For each year, check wealth flow: start + growth + inheritance - withdrawal = end
            for i in range(len(start_assets)):
                expected_end = start_assets[i] + growth[i] + inheritance[i] - gross_withdrawals[i]
                actual_end = end_assets[i]
                # Allow some tolerance for floating point precision
                tolerance = max(1000, abs(expected_end) * 0.01)  # 1% or $1000, whichever is larger
                assert abs(actual_end - expected_end) < tolerance, f"{label} Year {i}: wealth flow inconsistent"

    def test_percentile_path_realistic_values(self):
        """Test that percentile path values are realistic and non-negative where appropriate"""
        params = SimulationParams(num_sims=200, random_seed=42, horizon_years=5)
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        for label, path_details in [("P10", results.p10_path_details),
                                   ("P50", results.median_path_details),
                                   ("P90", results.p90_path_details)]:
            # Assets should be non-negative
            for i, assets in enumerate(path_details['start_assets']):
                assert assets >= 0, f"{label} start_assets[{i}] is negative: {assets}"
            for i, assets in enumerate(path_details['end_assets']):
                assert assets >= 0, f"{label} end_assets[{i}] is negative: {assets}"

            # Spending should be positive
            for i, spending in enumerate(path_details['adjusted_base_spending']):
                assert spending > 0, f"{label} adjusted_base_spending[{i}] should be positive: {spending}"

            # Taxes should be non-negative
            for i, taxes in enumerate(path_details['taxes']):
                assert taxes >= 0, f"{label} taxes[{i}] should be non-negative: {taxes}"

            # Withdrawal rates should be reasonable (0-100%)
            for i, wr in enumerate(path_details['withdrawal_rate']):
                assert 0 <= wr <= 1.0, f"{label} withdrawal_rate[{i}] should be 0-100%: {wr*100:.1f}%"

            # Allocations should sum to 1.0
            for i in range(len(path_details['years'])):
                allocation_sum = (path_details['equity_allocation'][i] +
                                path_details['bonds_allocation'][i] +
                                path_details['real_estate_allocation'][i] +
                                path_details['cash_allocation'][i])
                assert abs(allocation_sum - 1.0) < 0.01, f"{label} allocations don't sum to 1.0 in year {i}: {allocation_sum}"


class TestGetPercentilePathDetails:
    """Test get_percentile_path_details function from monte_carlo.py"""

    def setup_method(self):
        """Set up test data"""
        params = SimulationParams(num_sims=100, random_seed=42, horizon_years=5)
        simulator = RetirementSimulator(params)
        self.results = simulator.run_simulation()

    def test_get_percentile_path_details_p10(self):
        """Test getting P10 path details"""
        from pages.monte_carlo import get_percentile_path_details
        path_details = get_percentile_path_details(self.results, 10)

        # Should return P10 path details
        assert path_details is self.results.p10_path_details
        assert 'end_assets' in path_details
        assert len(path_details['end_assets']) == 5

    def test_get_percentile_path_details_p50(self):
        """Test getting P50 (median) path details"""
        from pages.monte_carlo import get_percentile_path_details
        path_details = get_percentile_path_details(self.results, 50)

        # Should return median path details
        assert path_details is self.results.median_path_details

    def test_get_percentile_path_details_p90(self):
        """Test getting P90 path details"""
        from pages.monte_carlo import get_percentile_path_details
        path_details = get_percentile_path_details(self.results, 90)

        # Should return P90 path details
        assert path_details is self.results.p90_path_details

    def test_get_percentile_path_details_unsupported(self):
        """Test getting unsupported percentile defaults to median"""
        from pages.monte_carlo import get_percentile_path_details
        path_details = get_percentile_path_details(self.results, 25)

        # Should default to median
        assert path_details is self.results.median_path_details

    def test_percentile_paths_different_terminal_wealth(self):
        """Test that the three percentile paths have different terminal wealth values"""
        from pages.monte_carlo import get_percentile_path_details

        p10_path = get_percentile_path_details(self.results, 10)
        p50_path = get_percentile_path_details(self.results, 50)
        p90_path = get_percentile_path_details(self.results, 90)

        p10_terminal = p10_path['end_assets'][-1]
        p50_terminal = p50_path['end_assets'][-1]
        p90_terminal = p90_path['end_assets'][-1]

        # Values should be ordered and distinct
        assert p10_terminal < p50_terminal < p90_terminal
        assert p10_terminal != p50_terminal != p90_terminal


class TestSpendingMethods:
    """Test the new spending method functionality"""

    def test_cape_based_spending_default(self):
        """Test default CAPE-based spending calculation"""
        # Use larger portfolio to get spending above floor
        params = SimulationParams(start_capital=5_000_000, cape_now=20.0, spending_floor_real=50_000)
        simulator = RetirementSimulator(params)

        # CAPE-based rate: 1.75% + 0.5 * (1/20) = 1.75% + 2.5% = 4.25%
        expected_spending = 0.0425 * 5_000_000  # $212,500

        # Check that CAPE calculation works
        results = simulator.run_simulation()

        # Check that median spending is approximately what we expect
        median_spending = results.median_path_details['adjusted_base_spending'][0]
        assert abs(median_spending - expected_spending) < 5000  # Allow 5k tolerance

    def test_manual_spending_override(self):
        """Test manual spending overrides CAPE calculation"""
        manual_spending = 180_000  # Above spending floor
        params = SimulationParams(
            start_capital=5_000_000,
            cape_now=20.0,  # This would normally give ~212.5k
            initial_base_spending=manual_spending,
            spending_floor_real=50_000  # Lower floor for testing
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check that the manual spending is used instead of CAPE
        median_spending = results.median_path_details['adjusted_base_spending'][0]
        assert abs(median_spending - manual_spending) < 1000  # Allow small tolerance

    def test_cape_vs_manual_different_results(self):
        """Test that CAPE-based and manual spending give different results"""
        # CAPE scenario - use high CAPE to get lower spending
        cape_params = SimulationParams(
            start_capital=6_000_000,
            cape_now=40.0,  # High CAPE = lower spending
            spending_floor_real=50_000
        )
        cape_sim = RetirementSimulator(cape_params)
        cape_results = cape_sim.run_simulation()
        cape_spending = cape_results.median_path_details['adjusted_base_spending'][0]

        # Manual scenario with different amount
        manual_spending = 200_000  # Fixed amount, clearly different
        manual_params = SimulationParams(
            start_capital=6_000_000,
            cape_now=40.0,  # Same CAPE, but will be ignored
            initial_base_spending=manual_spending,
            spending_floor_real=50_000
        )
        manual_sim = RetirementSimulator(manual_params)
        manual_results = manual_sim.run_simulation()
        manual_actual = manual_results.median_path_details['adjusted_base_spending'][0]

        # Should be different results
        assert abs(cape_spending - manual_actual) > 5000
        # CAPE with CAPE=40: 1.75% + 0.5*(1/40) = 1.75% + 1.25% = 3% = $180k
        # Manual should be $200k, so difference should be ~$20k

    def test_fixed_annual_spending_no_guardrails(self):
        """Test that fixed annual spending stays constant and ignores guardrails"""
        fixed_amount = 250_000
        params = SimulationParams(
            start_capital=3_000_000,
            fixed_annual_spending=fixed_amount,
            spending_floor_real=100_000,  # Lower than fixed amount
            spending_ceiling_real=300_000,  # Higher than fixed amount
            lower_wr=0.02,  # Very low - would normally trigger guardrail
            upper_wr=0.15,  # Very high - would normally trigger guardrail
            num_sims=100  # Small for speed
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check that spending stays fixed across all years
        median_spending = results.median_path_details['adjusted_base_spending']

        # All years should have the same spending amount (fixed)
        for year_spending in median_spending:
            assert abs(year_spending - fixed_amount) < 1000, f"Expected {fixed_amount}, got {year_spending}"

        # Check that guardrails were not applied (should be 0 hits)
        assert results.guardrail_hits.sum() == 0, "Fixed spending should not trigger any guardrail adjustments"

    def test_spending_method_priority_fixed_wins(self):
        """Test that fixed_annual_spending takes priority over other methods"""
        fixed_amount = 300_000
        params = SimulationParams(
            start_capital=4_000_000,
            cape_now=25.0,  # Would give different amount
            initial_base_spending=200_000,  # Would give different amount
            fixed_annual_spending=fixed_amount,  # This should win
            spending_floor_real=50_000,
            num_sims=50
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Should use fixed amount, not CAPE or manual
        first_year_spending = results.median_path_details['adjusted_base_spending'][0]
        assert abs(first_year_spending - fixed_amount) < 1000


class TestIncomeStreams:
    """Test multiple income streams functionality"""

    def test_multiple_income_streams_timing(self):
        """Test that multiple income streams respect start year and duration"""
        params = SimulationParams(
            start_capital=2_000_000,
            start_year=2026,
            horizon_years=12,  # 2026-2037
            num_sims=50,  # Fast test
            income_streams=[
                {'amount': 35000, 'start_year': 2026, 'years': 5},  # 2026-2030
                {'amount': 20000, 'start_year': 2028, 'years': 8}   # 2028-2035
            ],
            spending_floor_real=50_000,  # Lower floor for testing
            random_seed=42  # Reproducible
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check income for specific years
        median_details = results.median_path_details
        years = median_details['years']
        other_income = median_details['other_income']

        # Create year->income mapping
        income_by_year = dict(zip(years, other_income))

        # Test specific years
        assert income_by_year[2026] == 35000, f"2026 should be $35K, got ${income_by_year[2026]}"
        assert income_by_year[2027] == 35000, f"2027 should be $35K, got ${income_by_year[2027]}"
        assert income_by_year[2028] == 55000, f"2028 should be $55K, got ${income_by_year[2028]}"
        assert income_by_year[2029] == 55000, f"2029 should be $55K, got ${income_by_year[2029]}"
        assert income_by_year[2030] == 55000, f"2030 should be $55K, got ${income_by_year[2030]}"
        assert income_by_year[2031] == 20000, f"2031 should be $20K, got ${income_by_year[2031]}"
        assert income_by_year[2035] == 20000, f"2035 should be $20K, got ${income_by_year[2035]}"
        assert income_by_year[2036] == 0, f"2036 should be $0, got ${income_by_year[2036]}"

    def test_single_income_stream(self):
        """Test backward compatibility with single income stream"""
        params = SimulationParams(
            start_capital=1_500_000,
            start_year=2026,
            horizon_years=8,
            num_sims=25,
            income_streams=[
                {'amount': 45000, 'start_year': 2027, 'years': 3}  # 2027-2029
            ],
            spending_floor_real=50_000,
            random_seed=123
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check income timing
        median_details = results.median_path_details
        income_by_year = dict(zip(median_details['years'], median_details['other_income']))

        assert income_by_year[2026] == 0
        assert income_by_year[2027] == 45000
        assert income_by_year[2028] == 45000
        assert income_by_year[2029] == 45000
        assert income_by_year[2030] == 0

    def test_overlapping_income_streams(self):
        """Test complex overlapping income streams"""
        params = SimulationParams(
            start_capital=3_000_000,
            start_year=2026,
            horizon_years=8,
            num_sims=25,
            income_streams=[
                {'amount': 40000, 'start_year': 2026, 'years': 4},  # 2026-2029
                {'amount': 25000, 'start_year': 2027, 'years': 3},  # 2027-2029
                {'amount': 30000, 'start_year': 2029, 'years': 5}   # 2029-2033
            ],
            spending_floor_real=50_000,
            random_seed=456
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check overlapping periods
        median_details = results.median_path_details
        income_by_year = dict(zip(median_details['years'], median_details['other_income']))

        assert income_by_year[2026] == 40000  # Stream 1 only
        assert income_by_year[2027] == 65000  # Stream 1 + 2
        assert income_by_year[2028] == 65000  # Stream 1 + 2
        assert income_by_year[2029] == 95000  # Stream 1 + 2 + 3
        assert income_by_year[2030] == 30000  # Stream 3 only
        assert income_by_year[2033] == 30000  # Stream 3 only

    def test_legacy_single_stream_compatibility(self):
        """Test that legacy single stream parameters still work"""
        params = SimulationParams(
            start_capital=1_000_000,
            start_year=2026,
            horizon_years=6,
            num_sims=25,
            # Legacy single stream (no income_streams parameter)
            other_income_amount=30000,
            other_income_start_year=2028,
            other_income_years=3,  # 2028-2030
            spending_floor_real=50_000,
            random_seed=789
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check legacy behavior
        median_details = results.median_path_details
        income_by_year = dict(zip(median_details['years'], median_details['other_income']))

        assert income_by_year[2027] == 0
        assert income_by_year[2028] == 30000
        assert income_by_year[2029] == 30000
        assert income_by_year[2030] == 30000
        assert income_by_year[2031] == 0


class TestExpenseStreams:
    """Test multiple expense streams functionality"""

    def test_multiple_expense_streams_timing(self):
        """Test that multiple expense streams respect start year and duration"""
        params = SimulationParams(
            start_capital=3_000_000,
            start_year=2026,
            horizon_years=12,  # 2026-2037
            num_sims=50,  # Fast test
            expense_streams=[
                {'amount': 80000, 'start_year': 2028, 'years': 4, 'description': 'College 1'},  # 2028-2031
                {'amount': 50000, 'start_year': 2030, 'years': 3, 'description': 'Home renovation'},  # 2030-2032
                {'amount': 200000, 'start_year': 2035, 'years': 1, 'description': 'One-time expense'}  # 2035 only
            ],
            spending_floor_real=100_000,
            fixed_annual_spending=250_000,  # Use fixed to make testing predictable
            random_seed=42  # Reproducible
        )
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check expense timing in simulation results
        median_details = results.median_path_details
        years = median_details['years']
        one_times = median_details['one_times']

        # Create year->expense mapping
        expenses_by_year = dict(zip(years, one_times))

        # Test specific years
        assert expenses_by_year[2026] == 0, f"2026 should be $0, got ${expenses_by_year[2026]}"
        assert expenses_by_year[2027] == 0, f"2027 should be $0, got ${expenses_by_year[2027]}"
        assert expenses_by_year[2028] == 80000, f"2028 should be $80K, got ${expenses_by_year[2028]}"
        assert expenses_by_year[2029] == 80000, f"2029 should be $80K, got ${expenses_by_year[2029]}"
        assert expenses_by_year[2030] == 130000, f"2030 should be $130K (80+50), got ${expenses_by_year[2030]}"
        assert expenses_by_year[2031] == 130000, f"2031 should be $130K (80+50), got ${expenses_by_year[2031]}"
        assert expenses_by_year[2032] == 50000, f"2032 should be $50K, got ${expenses_by_year[2032]}"
        assert expenses_by_year[2033] == 0, f"2033 should be $0, got ${expenses_by_year[2033]}"
        assert expenses_by_year[2034] == 0, f"2034 should be $0, got ${expenses_by_year[2034]}"
        assert expenses_by_year[2035] == 200000, f"2035 should be $200K, got ${expenses_by_year[2035]}"
        assert expenses_by_year[2036] == 0, f"2036 should be $0, got ${expenses_by_year[2036]}"

    def test_expense_stream_impact_on_withdrawals(self):
        """Test that expense streams increase portfolio withdrawals correctly"""
        # Base case - no expenses
        base_params = SimulationParams(
            start_capital=2_000_000,
            start_year=2026,
            horizon_years=5,
            num_sims=25,
            fixed_annual_spending=150_000,  # Fixed spending for predictable results
            spending_floor_real=50_000,
            random_seed=123
        )
        base_sim = RetirementSimulator(base_params)
        base_results = base_sim.run_simulation()
        base_withdrawal_2028 = base_results.median_path_details['gross_withdrawal'][2]  # 2028

        # With expense case
        expense_params = SimulationParams(
            start_capital=2_000_000,
            start_year=2026,
            horizon_years=5,
            num_sims=25,
            fixed_annual_spending=150_000,
            expense_streams=[
                {'amount': 100_000, 'start_year': 2028, 'years': 1}  # 2028 only
            ],
            spending_floor_real=50_000,
            random_seed=123  # Same seed for comparison
        )
        expense_sim = RetirementSimulator(expense_params)
        expense_results = expense_sim.run_simulation()
        expense_withdrawal_2028 = expense_results.median_path_details['gross_withdrawal'][2]  # 2028

        # The withdrawal in 2028 should be higher due to the expense + taxes on the additional withdrawal
        withdrawal_difference = expense_withdrawal_2028 - base_withdrawal_2028
        # Should be between $100K (just the expense) and ~$130K (expense + taxes)
        assert 100_000 <= withdrawal_difference <= 130_000, f"Expected $100K-$130K difference, got ${withdrawal_difference:,.0f}"

        # Verify the expense amount is correct in the results
        expense_one_times = expense_results.median_path_details['one_times']
        assert expense_one_times[2] == 100_000, f"Expected $100K expense in 2028, got ${expense_one_times[2]:,.0f}"

        # 2027 and 2029 should be similar between the two scenarios
        base_withdrawal_2027 = base_results.median_path_details['gross_withdrawal'][1]
        expense_withdrawal_2027 = expense_results.median_path_details['gross_withdrawal'][1]
        assert abs(base_withdrawal_2027 - expense_withdrawal_2027) < 5_000

    def test_overlapping_expense_streams(self):
        """Test complex overlapping expense streams"""
        params = SimulationParams(
            start_capital=4_000_000,
            start_year=2026,
            horizon_years=10,
            num_sims=25,
            expense_streams=[
                {'amount': 60000, 'start_year': 2026, 'years': 3, 'description': 'Expense A'},  # 2026-2028
                {'amount': 40000, 'start_year': 2027, 'years': 4, 'description': 'Expense B'},  # 2027-2030
                {'amount': 80000, 'start_year': 2029, 'years': 2, 'description': 'Expense C'},  # 2029-2030
                {'amount': 120000, 'start_year': 2032, 'years': 1, 'description': 'Expense D'}  # 2032 only
            ],
            spending_floor_real=50_000,
            random_seed=456
        )
        simulator = RetirementSimulator(params)

        # Test the expense calculation method directly
        assert simulator._get_onetime_expense(2025) == 0
        assert simulator._get_onetime_expense(2026) == 60000  # A only
        assert simulator._get_onetime_expense(2027) == 100000  # A + B
        assert simulator._get_onetime_expense(2028) == 100000  # A + B
        assert simulator._get_onetime_expense(2029) == 120000  # B + C
        assert simulator._get_onetime_expense(2030) == 120000  # B + C
        assert simulator._get_onetime_expense(2031) == 0
        assert simulator._get_onetime_expense(2032) == 120000  # D only
        assert simulator._get_onetime_expense(2033) == 0

    def test_edge_cases_expense_streams(self):
        """Test edge cases for expense streams"""
        # Test empty expense streams
        params_empty = SimulationParams(expense_streams=[])
        simulator_empty = RetirementSimulator(params_empty)
        assert simulator_empty._get_onetime_expense(2030) == 0

        # Test None expense streams
        params_none = SimulationParams(expense_streams=None)
        simulator_none = RetirementSimulator(params_none)
        assert simulator_none._get_onetime_expense(2030) == 0

        # Test zero amount expense
        params_zero = SimulationParams(
            expense_streams=[{'amount': 0, 'start_year': 2030, 'years': 1}]
        )
        simulator_zero = RetirementSimulator(params_zero)
        assert simulator_zero._get_onetime_expense(2030) == 0

        # Test missing keys (should default gracefully)
        params_missing = SimulationParams(
            expense_streams=[{'start_year': 2030, 'years': 1}]  # Missing 'amount'
        )
        simulator_missing = RetirementSimulator(params_missing)
        assert simulator_missing._get_onetime_expense(2030) == 0

    def test_single_year_expenses_legacy_format(self):
        """Test backward compatibility with legacy single-year expense format"""
        # Some expense streams might use 'year' instead of 'start_year' + 'years'
        params = SimulationParams(
            expense_streams=[
                {'amount': 50000, 'year': 2030, 'description': 'Legacy format'},  # Should work as 1-year expense
                {'amount': 75000, 'start_year': 2032, 'years': 1, 'description': 'New format'}
            ]
        )
        simulator = RetirementSimulator(params)

        # Both should work as single-year expenses
        assert simulator._get_onetime_expense(2030) == 50000
        assert simulator._get_onetime_expense(2031) == 0
        assert simulator._get_onetime_expense(2032) == 75000
        assert simulator._get_onetime_expense(2033) == 0

    def test_expense_streams_full_simulation(self):
        """Test expense streams in a full simulation to ensure integration works"""
        params = SimulationParams(
            start_capital=5_000_000,
            start_year=2026,
            horizon_years=8,
            num_sims=10,  # Small for speed
            expense_streams=[
                {'amount': 100000, 'start_year': 2028, 'years': 2, 'description': 'Major expense'}  # 2028-2029
            ],
            spending_floor_real=100_000,
            fixed_annual_spending=200_000,
            random_seed=789
        )

        # Should not raise any exceptions
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Verify results structure includes expense data
        assert 'one_times' in results.median_path_details
        assert len(results.median_path_details['one_times']) == params.horizon_years

        # Verify expense amounts in results
        median_details = results.median_path_details
        expenses_by_year = dict(zip(median_details['years'], median_details['one_times']))

        assert expenses_by_year[2027] == 0
        assert expenses_by_year[2028] == 100000
        assert expenses_by_year[2029] == 100000
        assert expenses_by_year[2030] == 0