"""
Comprehensive tests for market regime implementation
Tests all regime scenarios to ensure they produce expected return patterns
"""
import pytest
import numpy as np
from simulation import RetirementSimulator, SimulationParams


class TestMarketRegimes:
    """Test all market regime scenarios"""

    def test_baseline_regime(self):
        """Test baseline regime returns normal market returns"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=5,
            num_sims=100,
            regime='baseline',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Test all years should return baseline values
        for year in range(5):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"
            assert re_mean == 0.056, f"Year {year}: Expected RE 0.056, got {re_mean}"
            assert cash_mean == 0.023, f"Year {year}: Expected cash 0.023, got {cash_mean}"

    def test_recession_recover_regime(self):
        """Test recession_recover regime has correct pattern"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=5,
            num_sims=100,
            regime='recession_recover',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Year 0: -15% equity, others normal
        eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(0)
        assert eq_mean == -0.15, f"Year 0: Expected equity -0.15, got {eq_mean}"
        assert bond_mean == 0.032, f"Year 0: Expected bonds 0.032, got {bond_mean}"
        assert re_mean == 0.056, f"Year 0: Expected RE 0.056, got {re_mean}"
        assert cash_mean == 0.023, f"Year 0: Expected cash 0.023, got {cash_mean}"

        # Year 1: 0% equity, others normal
        eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(1)
        assert eq_mean == 0.00, f"Year 1: Expected equity 0.00, got {eq_mean}"
        assert bond_mean == 0.032, f"Year 1: Expected bonds 0.032, got {bond_mean}"
        assert re_mean == 0.056, f"Year 1: Expected RE 0.056, got {re_mean}"
        assert cash_mean == 0.023, f"Year 1: Expected cash 0.023, got {cash_mean}"

        # Year 2+: Back to baseline
        for year in range(2, 5):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"
            assert re_mean == 0.056, f"Year {year}: Expected RE 0.056, got {re_mean}"
            assert cash_mean == 0.023, f"Year {year}: Expected cash 0.023, got {cash_mean}"

    def test_grind_lower_regime(self):
        """Test grind_lower regime has low returns for 10 years"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=12,
            num_sims=100,
            regime='grind_lower',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Years 0-9: Low returns
        for year in range(10):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.005, f"Year {year}: Expected equity 0.005, got {eq_mean}"
            assert bond_mean == 0.01, f"Year {year}: Expected bonds 0.01, got {bond_mean}"
            assert re_mean == 0.005, f"Year {year}: Expected RE 0.005, got {re_mean}"
            assert cash_mean == 0.023, f"Year {year}: Expected cash 0.023, got {cash_mean}"

        # Years 10+: Back to baseline
        for year in range(10, 12):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"

    def test_late_recession_regime(self):
        """Test late_recession regime has shock at years 10-12"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=20,
            num_sims=100,
            regime='late_recession',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Years 0-9: Normal baseline
        for year in range(10):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

        # Year 10: -20% equity shock
        eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(10)
        assert eq_mean == -0.20, f"Year 10: Expected equity -0.20, got {eq_mean}"
        assert re_mean == -0.05, f"Year 10: Expected RE -0.05, got {re_mean}"

        # Year 11: -5% equity continuation
        eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(11)
        assert eq_mean == -0.05, f"Year 11: Expected equity -0.05, got {eq_mean}"
        assert re_mean == 0.00, f"Year 11: Expected RE 0.00, got {re_mean}"

        # Year 12: 15% equity recovery bounce
        eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(12)
        assert eq_mean == 0.15, f"Year 12: Expected equity 0.15, got {eq_mean}"
        assert re_mean == 0.05, f"Year 12: Expected RE 0.05, got {re_mean}"

        # Years 13+: Back to baseline
        for year in range(13, 20):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

    def test_inflation_shock_regime(self):
        """Test inflation_shock regime"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=10,
            num_sims=100,
            regime='inflation_shock',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Years 0-2: Normal baseline
        for year in range(3):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"
            assert re_mean == 0.056, f"Year {year}: Expected RE 0.056, got {re_mean}"

        # Years 3-7: Inflation shock - poor equity/bonds, good RE
        for year in range(3, 8):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.01, f"Year {year}: Expected equity 0.01, got {eq_mean}"
            assert bond_mean == -0.02, f"Year {year}: Expected bonds -0.02, got {bond_mean}"
            assert re_mean == 0.08, f"Year {year}: Expected RE 0.08, got {re_mean}"
            assert cash_mean == 0.01, f"Year {year}: Expected cash 0.01, got {cash_mean}"

        # Years 8+: Back to baseline
        for year in range(8, 10):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"
            assert re_mean == 0.056, f"Year {year}: Expected RE 0.056, got {re_mean}"

    def test_long_bear_regime(self):
        """Test long_bear regime has extended low returns"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=20,
            num_sims=100,
            regime='long_bear',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Years 0-4: Normal baseline
        for year in range(5):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"
            assert bond_mean == 0.032, f"Year {year}: Expected bonds 0.032, got {bond_mean}"
            assert re_mean == 0.056, f"Year {year}: Expected RE 0.056, got {re_mean}"

        # Years 5-15: Extended bear market
        for year in range(5, 16):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.02, f"Year {year}: Expected equity 0.02, got {eq_mean}"
            assert bond_mean == 0.025, f"Year {year}: Expected bonds 0.025, got {bond_mean}"
            assert re_mean == 0.015, f"Year {year}: Expected RE 0.015, got {re_mean}"

        # Years 16+: Back to baseline
        for year in range(16, 20):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

    def test_tech_bubble_regime(self):
        """Test tech_bubble regime has high then low returns"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=10,
            num_sims=100,
            regime='tech_bubble',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023
        )

        sim = RetirementSimulator(params)

        # Years 0-3: High equity returns (1.5x multiplier)
        for year in range(4):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            expected_equity = 0.074 * 1.5  # 0.111
            assert abs(eq_mean - expected_equity) < 0.001, f"Year {year}: Expected equity {expected_equity}, got {eq_mean}"

        # Years 4-6: Crash
        for year in range(4, 7):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == -0.10, f"Year {year}: Expected equity -0.10, got {eq_mean}"

        # Years 7+: Back to baseline
        for year in range(7, 10):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

    def test_custom_regime(self):
        """Test custom regime respects user parameters"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=10,
            num_sims=100,
            regime='custom',
            random_seed=42,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023,
            # Custom parameters
            custom_equity_shock_year=2,
            custom_equity_shock_return=-0.25,
            custom_shock_duration=3,
            custom_recovery_years=2,
            custom_recovery_equity_return=0.05
        )

        sim = RetirementSimulator(params)

        # Years 0-1: Baseline
        for year in range(2):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

        # Years 2-4: Shock (3 year duration)
        for year in range(2, 5):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == -0.25, f"Year {year}: Expected equity -0.25, got {eq_mean}"

        # Years 5-6: Recovery (2 year recovery)
        for year in range(5, 7):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.05, f"Year {year}: Expected equity 0.05, got {eq_mean}"

        # Years 7+: Back to baseline
        for year in range(7, 10):
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            assert eq_mean == 0.074, f"Year {year}: Expected equity 0.074, got {eq_mean}"

    def test_simulation_respects_regime_pattern(self):
        """Test that full simulation shows expected growth patterns for recession_recover"""
        params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=5,
            num_sims=1000,  # More sims to reduce random noise
            regime='recession_recover',
            random_seed=42,
            w_equity=1.0,  # 100% equity to clearly see the effect
            w_bonds=0.0,
            w_real_estate=0.0,
            w_cash=0.0,
            equity_mean=0.074,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023,
            equity_vol=0.10,  # Lower volatility to reduce noise
            fixed_annual_spending=0  # Truly zero spending to isolate return effects
        )

        sim = RetirementSimulator(params)
        results = sim.run_simulation()

        # Calculate median growth rates for each year
        wealth_paths = results.wealth_paths
        median_growth_rates = []

        for year in range(params.horizon_years):
            start_wealth = wealth_paths[:, year]
            end_wealth = wealth_paths[:, year + 1]
            growth_rates = (end_wealth - start_wealth) / start_wealth
            median_growth = np.median(growth_rates)
            median_growth_rates.append(median_growth)
            print(f"Year {year}: Median growth rate = {median_growth:.3f} ({median_growth:.1%})")

        # Year 0 should be strongly negative (around -15%)
        assert median_growth_rates[0] < -0.10, f"Year 0 should be negative, got {median_growth_rates[0]:.3f}"

        # Year 1 should be around 0% (might be slightly negative due to noise)
        assert -0.05 < median_growth_rates[1] < 0.05, f"Year 1 should be near 0%, got {median_growth_rates[1]:.3f}"

        # Years 2+ should be positive (around 7.4%)
        for year in range(2, 5):
            assert median_growth_rates[year] > 0.05, f"Year {year} should be positive, got {median_growth_rates[year]:.3f}"

    def test_regime_with_realistic_portfolio(self):
        """Test recession_recover with realistic portfolio allocation (like user's)"""
        params = SimulationParams(
            start_capital=7_500_000,
            horizon_years=5,
            num_sims=1000,
            regime='recession_recover',
            random_seed=42,
            # User's actual allocation from config
            w_equity=0.35,
            w_bonds=0.40,
            w_real_estate=0.20,
            w_cash=0.05,
            equity_mean=0.072,
            bonds_mean=0.032,
            real_estate_mean=0.056,
            cash_mean=0.023,
            equity_vol=0.173,
            bonds_vol=0.058,
            real_estate_vol=0.161,
            cash_vol=0.010,
            fixed_annual_spending=0  # Zero spending to isolate returns
        )

        sim = RetirementSimulator(params)
        results = sim.run_simulation()

        # Test the median path details (like what shows in year-by-year table)
        median_details = results.median_path_details

        print("\nRealistic Portfolio - Growth Analysis:")
        for year in range(min(5, len(median_details['growth']))):
            start_assets = median_details['start_assets'][year]
            growth = median_details['growth'][year]
            growth_rate = growth / start_assets if start_assets > 0 else 0

            # Calculate expected portfolio return for this year
            eq_mean, bond_mean, re_mean, cash_mean = sim._get_return_means(year)
            expected_portfolio_return = (
                0.35 * eq_mean + 0.40 * bond_mean +
                0.20 * re_mean + 0.05 * cash_mean
            )

            print(f"Year {year}: Growth rate = {growth_rate:.1%}, Expected = {expected_portfolio_return:.1%}")

        # Year 0: Should be negative due to equity crash
        year0_growth_rate = median_details['growth'][0] / median_details['start_assets'][0]
        assert year0_growth_rate < 0, f"Year 0 should be negative, got {year0_growth_rate:.3f}"

        # Year 1: Should be small positive (0% equity + positive other assets)
        year1_growth_rate = median_details['growth'][1] / median_details['start_assets'][1]
        assert year1_growth_rate > 0, f"Year 1 should be positive with this allocation, got {year1_growth_rate:.3f}"