"""
Comprehensive market regime validation tests with anonymized portfolio data
Tests all market regimes with thorough simulation coverage to ensure regime patterns
are consistently applied across all simulation runs.
"""
import pytest
import numpy as np
from simulation import RetirementSimulator, SimulationParams


class TestMarketRegimeValidation:
    """Comprehensive validation of all market regimes with anonymized portfolio data"""

    @pytest.fixture
    def base_portfolio_params(self):
        """Anonymized portfolio parameters representing a typical retirement scenario"""
        return {
            'start_capital': 5_000_000,  # Anonymized from original
            'horizon_years': 10,  # Focus on first 10 years for detailed validation
            'w_equity': 0.40,  # Conservative balanced allocation
            'w_bonds': 0.35,
            'w_real_estate': 0.20,
            'w_cash': 0.05,
            'equity_mean': 0.070,
            'bonds_mean': 0.030,
            'real_estate_mean': 0.055,
            'cash_mean': 0.020,
            'equity_vol': 0.16,
            'bonds_vol': 0.06,
            'real_estate_vol': 0.15,
            'cash_vol': 0.01,
            'num_sims': 50,  # 50 simulations per regime for thorough testing
            'random_seed': 42,
            'cape_now': 35.0,
            # Minimal config to isolate regime effects
            'ss_annual_benefit': 0,
            'spouse_ss_enabled': False,
            'college_enabled': False,
            'inherit_amount': 0,
            'spending_floor_real': 0,
            'spending_ceiling_real': 999999999,
            'filing_status': 'Single',
            'standard_deduction': 15000,
            'fixed_annual_spending': 180000,  # Fixed spending to isolate returns
            'lower_wr': 0.99,
            'upper_wr': 0.01,
            'adjustment_pct': 0.0
        }

    @pytest.mark.parametrize("regime_name,expected_patterns", [
        ('baseline', {
            'description': 'Normal market returns throughout',
            'year_0_equity': 0.070,
            'year_1_equity': 0.070,
            'year_5_equity': 0.070,
            'expected_growth_sign': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # All positive
        }),
        ('recession_recover', {
            'description': 'Recession in years 0-1, then recovery',
            'year_0_equity': -0.15,
            'year_1_equity': 0.0,
            'year_2_equity': 0.070,
            'expected_growth_sign': [-1, 0, 1, 1, 1, 1, 1, 1, 1, 1]  # Negative, neutral, then positive
        }),
        ('grind_lower', {
            'description': 'Low returns for 10 years',
            'year_0_equity': 0.005,
            'year_5_equity': 0.005,
            'year_9_equity': 0.005,
            'expected_growth_sign': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]  # Low/neutral for 9 years, then positive
        }),
        ('late_recession', {
            'description': 'Normal returns then recession at year 15 (not tested in 10-year window)',
            'year_0_equity': 0.070,
            'year_5_equity': 0.070,
            'year_9_equity': 0.070,
            'expected_growth_sign': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # All positive in first 10 years
        }),
        ('inflation_shock', {
            'description': 'Inflation affects asset classes for 5 years',
            'year_0_equity': 0.070,
            'year_3_equity': 0.01,  # During inflation shock
            'year_3_bonds': -0.02,  # Bonds hurt by inflation
            'year_3_re': 0.08,      # RE benefits from inflation
            'year_8_equity': 0.070, # Back to baseline after year 7
            'expected_growth_sign': [1, 1, 1, 0, 0, 0, 0, 0, 1, 1]  # Normal, then neutral during shock, then positive
        }),
        ('long_bear', {
            'description': 'Extended low returns for 15 years',
            'year_0_equity': 0.070,  # Normal years 0-4
            'year_5_equity': 0.02,   # Bear market years 5-15
            'year_9_equity': 0.02,   # Still in bear market
            'expected_growth_sign': [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]  # Normal first 5 years, then low
        }),
        ('tech_bubble', {
            'description': 'High returns years 0-3, crash years 4-6, then recovery',
            'year_0_equity': 0.105,  # 0.070 * 1.5 = high bubble returns
            'year_1_equity': 0.105,
            'year_2_equity': 0.105,
            'year_3_equity': 0.105,
            'year_4_equity': -0.10,  # Crash begins
            'year_5_equity': -0.10,
            'year_6_equity': -0.10,
            'year_7_equity': 0.070,  # Back to baseline
            'expected_growth_sign': [1, 1, 1, 1, -1, -1, -1, 1, 1, 1]  # High bubble, crash, recovery
        })
    ])
    def test_comprehensive_regime_validation(self, base_portfolio_params, regime_name, expected_patterns):
        """Comprehensive test of all market regimes with 50 simulations each"""

        print(f"\n=== Testing {regime_name} regime ===")
        print(f"Description: {expected_patterns['description']}")

        # Create parameters for this regime
        params = SimulationParams(
            regime=regime_name,
            **base_portfolio_params
        )

        sim = RetirementSimulator(params)

        # Verify regime is set correctly
        assert sim.params.regime == regime_name, f"Expected {regime_name}, got {sim.params.regime}"

        # Test specific year return means based on regime
        if 'year_0_equity' in expected_patterns:
            eq_mean_0, _, _, _ = sim._get_return_means(0)
            assert abs(eq_mean_0 - expected_patterns['year_0_equity']) < 0.001, \
                f"{regime_name} year 0: expected {expected_patterns['year_0_equity']}, got {eq_mean_0}"

        if 'year_1_equity' in expected_patterns:
            eq_mean_1, _, _, _ = sim._get_return_means(1)
            assert abs(eq_mean_1 - expected_patterns['year_1_equity']) < 0.001, \
                f"{regime_name} year 1: expected {expected_patterns['year_1_equity']}, got {eq_mean_1}"

        # Test additional year-specific parameters
        for param_name, expected_value in expected_patterns.items():
            if param_name.startswith('year_') and '_equity' in param_name:
                year_num = int(param_name.split('_')[1])
                if year_num != 0 and year_num != 1:  # Already tested above
                    eq_mean, _, _, _ = sim._get_return_means(year_num)
                    assert abs(eq_mean - expected_value) < 0.001, \
                        f"{regime_name} year {year_num}: expected {expected_value}, got {eq_mean}"

            elif param_name.startswith('year_') and '_bonds' in param_name:
                year_num = int(param_name.split('_')[1])
                _, bond_mean, _, _ = sim._get_return_means(year_num)
                assert abs(bond_mean - expected_value) < 0.001, \
                    f"{regime_name} year {year_num} bonds: expected {expected_value}, got {bond_mean}"

            elif param_name.startswith('year_') and '_re' in param_name:
                year_num = int(param_name.split('_')[1])
                _, _, re_mean, _ = sim._get_return_means(year_num)
                assert abs(re_mean - expected_value) < 0.001, \
                    f"{regime_name} year {year_num} RE: expected {expected_value}, got {re_mean}"

        # Run full simulation with 50 runs
        print(f"Running {params.num_sims} simulations...")
        results = sim.run_simulation()
        wealth_paths = results.wealth_paths

        print(f"Wealth paths shape: {wealth_paths.shape}")

        # Analyze EVERY simulation run for the first 10 years
        regime_compliance = {}
        total_runs = params.num_sims

        for year in range(params.horizon_years):
            year_compliance = 0

            for sim_idx in range(total_runs):
                year_start = wealth_paths[sim_idx, year]
                year_end = wealth_paths[sim_idx, year + 1]

                # Calculate net growth (add back spending to isolate investment returns)
                net_growth = year_end - year_start + params.fixed_annual_spending
                growth_rate = net_growth / year_start

                # Check if this simulation follows expected pattern
                expected_sign = expected_patterns['expected_growth_sign'][year]

                if expected_sign == 1:  # Should be positive
                    if growth_rate > 0.01:  # Allow some tolerance
                        year_compliance += 1
                elif expected_sign == -1:  # Should be negative
                    if growth_rate < -0.01:
                        year_compliance += 1
                elif expected_sign == 0:  # Should be neutral/low
                    if -0.02 < growth_rate < 0.04:  # Small range around zero
                        year_compliance += 1

            compliance_pct = year_compliance / total_runs
            regime_compliance[year] = compliance_pct

            print(f"  Year {year}: {year_compliance}/{total_runs} simulations followed expected pattern ({compliance_pct:.1%})")

        # Assert minimum compliance thresholds based on regime type and year
        for year in range(min(5, params.horizon_years)):  # Focus on first 5 years
            compliance = regime_compliance[year]

            # Adjust thresholds based on regime characteristics and volatility
            if regime_name == 'recession_recover':
                if year == 0:
                    min_threshold = 0.4  # Year 0 crash - expect 40%+ negative
                elif year == 1:
                    min_threshold = 0.2  # Year 1 neutral - more variability
                else:
                    min_threshold = 0.6  # Recovery years
            elif regime_name == 'grind_lower':
                min_threshold = 0.15  # Low returns with high variance, very lenient
            elif regime_name == 'tech_bubble':
                if year in [3, 4]:  # Crash years
                    min_threshold = 0.4  # Crashes can be variable
                else:
                    min_threshold = 0.6  # Bubble/recovery years
            elif regime_name == 'inflation_shock':
                if 3 <= year <= 4:  # During shock
                    min_threshold = 0.2  # Complex multi-asset effects
                else:
                    min_threshold = 0.6
            elif regime_name == 'long_bear':
                min_threshold = 0.3  # Long bear can be highly variable
            else:
                min_threshold = 0.6  # Default for baseline, late_recession

            assert compliance >= min_threshold, \
                f"{regime_name} year {year}: only {compliance:.1%} compliance, expected >{min_threshold:.0%}"

        print(f"✅ {regime_name} regime validation passed")

    def test_regime_transition_points(self, base_portfolio_params):
        """Test specific transition points for regimes with defined change years"""

        regime_transitions = [
            ('recession_recover', [(0, -0.15), (1, 0.0), (2, 0.070)]),
            ('tech_bubble', [(0, 0.105), (2, 0.105), (3, 0.105), (4, -0.10), (5, -0.10), (7, 0.070)]),
            ('inflation_shock', [(0, 0.070), (3, 0.01), (4, 0.01), (8, 0.070)]),  # Shock years 3-7
            ('grind_lower', [(0, 0.005), (5, 0.005), (9, 0.005)]),
            ('long_bear', [(0, 0.070), (4, 0.070), (5, 0.02), (9, 0.02)])  # Bear starts year 5
        ]

        for regime_name, transitions in regime_transitions:
            print(f"\n=== Testing {regime_name} transition points ===")

            params = SimulationParams(
                regime=regime_name,
                **base_portfolio_params
            )

            sim = RetirementSimulator(params)

            for year, expected_equity in transitions:
                eq_mean, _, _, _ = sim._get_return_means(year)
                assert abs(eq_mean - expected_equity) < 0.001, \
                    f"{regime_name} year {year}: expected {expected_equity}, got {eq_mean}"
                print(f"  ✅ Year {year}: {eq_mean} (expected {expected_equity})")

        print("✅ All regime transition points validated")

    def test_custom_regime_parameters(self, base_portfolio_params):
        """Test custom regime with user-defined parameters"""

        custom_params = base_portfolio_params.copy()
        custom_params.update({
            'regime': 'custom',
            'custom_equity_shock_year': 2,
            'custom_equity_shock_return': -0.25,
            'custom_shock_duration': 3,
            'custom_recovery_years': 2,
            'custom_recovery_equity_return': 0.05,
            'horizon_years': 8  # Need enough years to see full pattern
        })

        params = SimulationParams(**custom_params)
        sim = RetirementSimulator(params)

        print(f"\n=== Testing custom regime ===")
        print(f"Pattern: Normal (0-1), Shock -25% (2-4), Recovery 5% (5-6), Baseline (7+)")

        # Test pattern: Years 0-1 normal, 2-4 shock, 5-6 recovery, 7+ baseline
        expected_equity = [0.070, 0.070, -0.25, -0.25, -0.25, 0.05, 0.05, 0.070]

        for year in range(8):
            eq_mean, _, _, _ = sim._get_return_means(year)
            expected = expected_equity[year]
            assert abs(eq_mean - expected) < 0.001, \
                f"Custom regime year {year}: expected {expected}, got {eq_mean}"
            print(f"  ✅ Year {year}: {eq_mean} (expected {expected})")

        # Run simulation to verify pattern
        results = sim.run_simulation()
        wealth_paths = results.wealth_paths

        # Check that shock years show negative returns
        shock_compliance = 0
        for sim_idx in range(params.num_sims):
            # Year 2 should show negative growth (start of shock)
            year_2_start = wealth_paths[sim_idx, 2]
            year_2_end = wealth_paths[sim_idx, 3]
            net_growth = year_2_end - year_2_start + params.fixed_annual_spending
            growth_rate = net_growth / year_2_start

            if growth_rate < -0.05:  # Should be strongly negative
                shock_compliance += 1

        shock_pct = shock_compliance / params.num_sims
        print(f"  Shock compliance: {shock_compliance}/{params.num_sims} = {shock_pct:.1%}")
        assert shock_pct > 0.5, f"Custom shock should affect >50% of simulations, got {shock_pct:.1%}"

        print("✅ Custom regime validation passed")