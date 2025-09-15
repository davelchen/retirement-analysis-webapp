#!/usr/bin/env python3
"""
Comprehensive tests for guardrail logic and parameter validation.

Tests the corrected guardrail defaults and logic:
- Lower guardrail (higher threshold): Cut spending when WR exceeds this
- Upper guardrail (lower threshold): Increase spending when WR falls below this
"""

import pytest
import numpy as np
from simulation import SimulationParams, RetirementSimulator
from deterministic import DeterministicProjector
from pages.monte_carlo import validate_simulation_parameters, get_parameter_changes


class TestGuardrailLogic:
    """Test guardrail behavior with correct thresholds"""

    def test_guardrail_defaults_are_correct(self):
        """Test that new defaults follow correct logic: lower_wr > upper_wr"""
        params = SimulationParams()

        # Should follow the pattern: upper_wr < lower_wr
        assert params.upper_wr < params.lower_wr, f"upper_wr ({params.upper_wr}) should be < lower_wr ({params.lower_wr})"

        # Reasonable default values
        assert 0.02 <= params.upper_wr <= 0.04, f"upper_wr ({params.upper_wr}) should be reasonable (2-4%)"
        assert 0.04 <= params.lower_wr <= 0.06, f"lower_wr ({params.lower_wr}) should be reasonable (4-6%)"

    def test_guardrail_spending_adjustments(self):
        """Test that guardrails trigger spending adjustments correctly"""
        params = SimulationParams(
            start_capital=1_000_000,
            start_year=2025,
            horizon_years=10,
            num_sims=3,  # Small for speed
            lower_wr=0.05,  # 5% - cut spending above this
            upper_wr=0.03,  # 3% - increase spending below this
            adjustment_pct=0.20,  # 20% adjustments for clear testing
            initial_base_spending=40_000  # 4% initial WR
        )

        simulator = RetirementSimulator(params)

        # Test individual guardrail method
        # Case 1: High WR (6%) should trigger spending cut
        portfolio_value = 1_000_000
        current_spend = 60_000  # 6% WR
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)

        expected_cut = current_spend * (1 - params.adjustment_pct)  # 60k * 0.8 = 48k
        assert new_spend == expected_cut, f"High WR should cut spending: {new_spend} vs {expected_cut}"
        assert direction == "down", f"Direction should be 'down', got '{direction}'"

        # Case 2: Low WR (2%) should trigger spending increase
        current_spend = 20_000  # 2% WR
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)

        expected_increase = current_spend * (1 + params.adjustment_pct)  # 20k * 1.2 = 24k
        assert new_spend == expected_increase, f"Low WR should increase spending: {new_spend} vs {expected_increase}"
        assert direction == "up", f"Direction should be 'up', got '{direction}'"

        # Case 3: Middle WR (4%) should stay unchanged
        current_spend = 40_000  # 4% WR
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)

        assert new_spend == current_spend, f"Middle WR should stay same: {new_spend} vs {current_spend}"
        assert direction == "none", f"Direction should be 'none', got '{direction}'"

    def test_guardrail_edge_cases(self):
        """Test guardrail behavior at exact threshold boundaries"""
        params = SimulationParams(
            lower_wr=0.05,  # Exactly 5%
            upper_wr=0.03,  # Exactly 3%
            adjustment_pct=0.10
        )

        simulator = RetirementSimulator(params)
        portfolio_value = 1_000_000

        # Exactly at lower threshold (5.0%)
        current_spend = 50_000
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert direction == "none", "Exactly at lower threshold should not trigger"

        # Just above lower threshold (5.1%)
        current_spend = 51_000
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert direction == "down", "Just above lower threshold should trigger cut"

        # Exactly at upper threshold (3.0%)
        current_spend = 30_000
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert direction == "none", "Exactly at upper threshold should not trigger"

        # Just below upper threshold (2.9%)
        current_spend = 29_000
        new_spend, direction = simulator._apply_spending_guardrails(current_spend, portfolio_value)
        assert direction == "up", "Just below upper threshold should trigger increase"

    def test_zero_portfolio_edge_case(self):
        """Test guardrail behavior when portfolio value is zero or negative"""
        params = SimulationParams(lower_wr=0.05, upper_wr=0.03, adjustment_pct=0.10)
        simulator = RetirementSimulator(params)

        # Zero portfolio
        new_spend, direction = simulator._apply_spending_guardrails(40_000, 0)
        assert new_spend == 40_000, "Zero portfolio should not change spending"
        assert direction == "none", "Zero portfolio should have no direction"

        # Negative portfolio (edge case)
        new_spend, direction = simulator._apply_spending_guardrails(40_000, -10_000)
        assert new_spend == 40_000, "Negative portfolio should not change spending"
        assert direction == "none", "Negative portfolio should have no direction"

    def test_deterministic_vs_monte_carlo_guardrail_consistency(self):
        """Test that deterministic and Monte Carlo use same guardrail logic"""
        params = SimulationParams(
            start_capital=1_000_000,
            start_year=2025,
            horizon_years=5,
            num_sims=3,
            lower_wr=0.06,  # 6% upper threshold
            upper_wr=0.02,  # 2% lower threshold
            adjustment_pct=0.15,
            initial_base_spending=50_000,  # 5% - between thresholds
            # Use fixed returns to make deterministic
            equity_mean=0.05, bonds_mean=0.03, real_estate_mean=0.04, cash_mean=0.02,
            equity_vol=0.0, bonds_vol=0.0, real_estate_vol=0.0  # No volatility
        )

        # Monte Carlo
        mc_simulator = RetirementSimulator(params)
        mc_results = mc_simulator.run_simulation()

        # Deterministic
        det_projector = DeterministicProjector(params)
        det_results = det_projector.run_projection()

        # Both should have spending data
        assert len(mc_results.median_path_details['adjusted_base_spending']) > 0, "MC should have spending data"
        assert len(det_results.year_by_year_details['adjusted_base_spending']) > 0, "Deterministic should have spending data"

        # Since we have no volatility, results should be very similar
        mc_final_spending = mc_results.median_path_details['adjusted_base_spending'][-1]
        det_final_spending = det_results.year_by_year_details['adjusted_base_spending'][-1]

        # Allow 5% difference due to median calculation
        relative_diff = abs(mc_final_spending - det_final_spending) / det_final_spending
        assert relative_diff < 0.05, f"MC and deterministic should be similar: {mc_final_spending} vs {det_final_spending}"

    def test_extreme_guardrail_scenarios(self):
        """Test guardrails with extreme market scenarios"""

        # Scenario 1: Market crash (high WR, should cut spending aggressively)
        params = SimulationParams(
            start_capital=2_000_000,
            start_year=2025,
            horizon_years=5,
            num_sims=3,
            lower_wr=0.05,  # 5%
            upper_wr=0.025, # 2.5%
            adjustment_pct=0.25,  # Aggressive 25% adjustments
            initial_base_spending=80_000,  # 4% starting WR
            spending_floor_real=0,  # No floor to allow guardrails to work
            spending_ceiling_real=1_000_000,  # High ceiling
            # Simulate market crash
            equity_mean=-0.20, bonds_mean=0.02,
            equity_vol=0.01, bonds_vol=0.01  # Low vol for predictable test
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Should have some spending cuts due to market crash
        spending_path = results.median_path_details['adjusted_base_spending']
        initial_spending = spending_path[0]
        final_spending = spending_path[-1]

        # In a crash scenario, final spending should be lower
        assert final_spending < initial_spending, f"Market crash should reduce spending: {initial_spending} to {final_spending}"

        # Scenario 2: Market boom (low WR, should increase spending)
        params_boom = SimulationParams(
            start_capital=1_000_000,
            start_year=2025,
            horizon_years=5,
            num_sims=3,
            lower_wr=0.06,  # 6%
            upper_wr=0.02,  # 2%
            adjustment_pct=0.20,
            initial_base_spending=30_000,  # 3% starting WR
            spending_floor_real=0,  # No floor to allow guardrails to work
            spending_ceiling_real=1_000_000,  # High ceiling
            # Simulate market boom
            equity_mean=0.15, bonds_mean=0.05,
            equity_vol=0.01, bonds_vol=0.01
        )

        simulator_boom = RetirementSimulator(params_boom)
        results_boom = simulator_boom.run_simulation()

        spending_path_boom = results_boom.median_path_details['adjusted_base_spending']
        initial_spending_boom = spending_path_boom[0]
        final_spending_boom = spending_path_boom[-1]

        # In boom scenario, final spending could be higher (though not guaranteed due to randomness)
        # At minimum, shouldn't crash to zero
        assert final_spending_boom > 0, "Boom scenario should maintain positive spending"
        assert final_spending_boom >= initial_spending_boom * 0.8, "Boom shouldn't cause major spending cuts"


class TestParameterValidation:
    """Test the new parameter validation functionality"""

    def test_validate_simulation_parameters_basic(self):
        """Test basic parameter validation logic"""

        # Valid parameters should have no warnings
        valid_params = SimulationParams(
            start_capital=2_000_000,
            retirement_age=65,
            horizon_years=30,
            lower_wr=0.05,  # Correct: higher threshold
            upper_wr=0.03,  # Correct: lower threshold
            ss_start_age=67,
            num_sims=10_000
        )

        warnings = validate_simulation_parameters(valid_params)
        assert len(warnings) == 0, f"Valid params should have no warnings: {warnings}"

    def test_validate_allocation_sum(self):
        """Test allocation sum validation"""

        # Invalid allocation sum
        bad_params = SimulationParams(
            w_equity=0.7,
            w_bonds=0.3,
            w_real_estate=0.1,  # This makes total = 1.1
            w_cash=0.0
        )

        warnings = validate_simulation_parameters(bad_params)
        allocation_warnings = [w for w in warnings if "sums to" in w]
        assert len(allocation_warnings) > 0, "Should detect bad allocation sum"

    def test_validate_capital_ranges(self):
        """Test start capital validation"""

        # Too low
        low_params = SimulationParams(start_capital=50_000)
        warnings = validate_simulation_parameters(low_params)
        low_warnings = [w for w in warnings if "seems low" in w]
        assert len(low_warnings) > 0, "Should warn about low capital"

        # Too high
        high_params = SimulationParams(start_capital=100_000_000)
        warnings = validate_simulation_parameters(high_params)
        high_warnings = [w for w in warnings if "very high" in w]
        assert len(high_warnings) > 0, "Should warn about very high capital"

    def test_validate_horizon_vs_age(self):
        """Test horizon vs retirement age validation"""

        # Too short (ends at age 75)
        short_params = SimulationParams(retirement_age=65, horizon_years=10)
        warnings = validate_simulation_parameters(short_params)
        short_warnings = [w for w in warnings if "ends at age" in w and "consider longer" in w]
        assert len(short_warnings) > 0, "Should warn about short horizon"

        # Too long (ends at age 135)
        long_params = SimulationParams(retirement_age=65, horizon_years=70)
        warnings = validate_simulation_parameters(long_params)
        long_warnings = [w for w in warnings if "very long horizon" in w]
        assert len(long_warnings) > 0, "Should warn about very long horizon"

    def test_validate_guardrail_relationship(self):
        """Test guardrail ordering validation"""

        # Backwards guardrails (this is the bug we fixed!)
        backwards_params = SimulationParams(
            lower_wr=0.03,  # Wrong: should be higher
            upper_wr=0.05   # Wrong: should be lower
        )

        warnings = validate_simulation_parameters(backwards_params)
        guardrail_warnings = [w for w in warnings if "Lower guardrail should be > upper guardrail" in w]
        assert len(guardrail_warnings) > 0, "Should detect backwards guardrails"

    def test_validate_social_security_ages(self):
        """Test Social Security age validation"""

        # Too early
        early_params = SimulationParams(
            social_security_enabled=True,
            ss_start_age=60  # Below minimum 62
        )
        warnings = validate_simulation_parameters(early_params)
        early_warnings = [w for w in warnings if "< 62" in w]
        assert len(early_warnings) > 0, "Should warn about early SS age"

        # Too late
        late_params = SimulationParams(
            social_security_enabled=True,
            ss_start_age=72  # Above optimal 70
        )
        warnings = validate_simulation_parameters(late_params)
        late_warnings = [w for w in warnings if "> 70" in w]
        assert len(late_warnings) > 0, "Should warn about late SS age"

        # Disabled SS should not trigger warnings
        disabled_params = SimulationParams(
            social_security_enabled=False,
            ss_start_age=55  # Would be invalid if enabled
        )
        warnings = validate_simulation_parameters(disabled_params)
        ss_warnings = [w for w in warnings if "Social Security" in w]
        assert len(ss_warnings) == 0, "Disabled SS should not trigger warnings"

    def test_validate_simulation_count(self):
        """Test simulation count validation"""

        # Too few
        few_params = SimulationParams(num_sims=500)
        warnings = validate_simulation_parameters(few_params)
        few_warnings = [w for w in warnings if "Low simulation count" in w]
        assert len(few_warnings) > 0, "Should warn about low sim count"

        # Too many
        many_params = SimulationParams(num_sims=100_000)
        warnings = validate_simulation_parameters(many_params)
        many_warnings = [w for w in warnings if "High simulation count" in w]
        assert len(many_warnings) > 0, "Should warn about high sim count"

    def test_multiple_validation_warnings(self):
        """Test that multiple issues are all detected"""

        # Parameters with multiple problems
        bad_params = SimulationParams(
            start_capital=10_000,      # Too low
            retirement_age=70,         # With short horizon -> age 75
            horizon_years=5,           # Too short
            lower_wr=0.02,            # Backwards
            upper_wr=0.06,            # Backwards
            social_security_enabled=True,
            ss_start_age=61,          # Too early
            num_sims=100              # Too few
        )

        warnings = validate_simulation_parameters(bad_params)

        # Should catch all issues
        assert len(warnings) >= 5, f"Should detect multiple issues, got {len(warnings)}: {warnings}"

        # Check specific issues are detected
        warning_text = " ".join(warnings)
        assert "seems low" in warning_text, "Should detect low capital"
        assert "ends at age" in warning_text, "Should detect short horizon"
        assert "Lower guardrail should be >" in warning_text, "Should detect backwards guardrails"
        assert "< 62" in warning_text, "Should detect early SS"
        assert "Low simulation count" in warning_text, "Should detect low sim count"


class TestParameterChanges:
    """Test parameter change detection functionality"""

    def test_get_parameter_changes_basic(self):
        """Test basic parameter change detection"""

        old_params = SimulationParams(
            start_capital=1_000_000,
            retirement_age=65,
            w_equity=0.6,
            ss_annual_benefit=35_000
        )

        new_params = SimulationParams(
            start_capital=2_000_000,  # Changed
            retirement_age=65,        # Same
            w_equity=0.7,            # Changed
            ss_annual_benefit=35_000  # Same
        )

        changes = get_parameter_changes(old_params, new_params)

        # Should detect the 2 changes
        assert len(changes) == 2, f"Should detect 2 changes, got {len(changes)}: {changes}"

        # Check specific changes
        change_text = " ".join(changes)
        assert "$1,000,000 → $2,000,000" in change_text, "Should detect capital change"
        assert "60.0% → 70.0%" in change_text, "Should detect equity allocation change"

    def test_get_parameter_changes_no_changes(self):
        """Test no changes detected when parameters are identical"""

        params = SimulationParams(
            start_capital=1_500_000,
            retirement_age=62,
            horizon_years=35
        )

        # Same parameters
        changes = get_parameter_changes(params, params)
        assert len(changes) == 0, f"Identical params should have no changes: {changes}"

    def test_get_parameter_changes_formatting(self):
        """Test that change formatting is correct"""

        old_params = SimulationParams(
            start_capital=1_234_567,
            w_equity=0.6789,
            ss_start_age=62,
            lower_wr=0.045,
            upper_wr=0.028
        )

        new_params = SimulationParams(
            start_capital=2_345_678,
            w_equity=0.5432,
            ss_start_age=67,
            lower_wr=0.050,
            upper_wr=0.030
        )

        changes = get_parameter_changes(old_params, new_params)

        # Check formatting
        change_text = " ".join(changes)

        # Currency formatting (commas)
        assert "$1,234,567 → $2,345,678" in change_text, "Should format currency with commas"

        # Percentage formatting (1 decimal)
        assert "67.9% → 54.3%" in change_text, "Should format percentages with 1 decimal"

        # Age formatting (simple integers)
        assert "62 → 67" in change_text, "Should format ages as integers"

        # Guardrail formatting (percentage)
        assert "4.5% → 5.0%" in change_text, "Should format guardrails as percentages"


class TestGuardrailIntegration:
    """Test guardrail integration with full simulation"""

    def test_guardrail_triggers_in_simulation(self):
        """Test that guardrails actually trigger during simulation runs"""

        # Create scenario that should trigger guardrails
        params = SimulationParams(
            start_capital=1_000_000,
            start_year=2025,
            horizon_years=10,
            num_sims=50,  # Enough for statistical significance

            # Wide guardrail band to catch triggers
            lower_wr=0.08,  # 8% - high threshold
            upper_wr=0.02,  # 2% - low threshold
            adjustment_pct=0.30,  # Large adjustments for visibility

            # Volatile market to trigger guardrails
            equity_mean=0.06,
            equity_vol=0.25,  # High volatility
            w_equity=0.8,     # High equity allocation
            w_bonds=0.2,      # Ensure allocation sums to 1.0
            w_real_estate=0.0,
            w_cash=0.0,

            initial_base_spending=50_000,  # 5% initial WR
            spending_floor_real=0,  # No floor to allow guardrails to work
            spending_ceiling_real=1_000_000  # High ceiling
        )

        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()

        # Check that simulation completed
        assert results is not None, "Simulation should complete"
        assert len(results.median_path_details['adjusted_base_spending']) > 0, "Should have spending data"

        # With high volatility and wide guardrails, should have some guardrail activity
        guardrail_total_hits = np.sum(results.guardrail_hits)
        spending_path = results.median_path_details['adjusted_base_spending']

        # Should have some guardrail activity OR spending variance
        has_guardrail_activity = guardrail_total_hits > 0
        spending_variance = np.var(spending_path)
        has_spending_variance = spending_variance > 0

        assert has_guardrail_activity or has_spending_variance, \
            f"Should have guardrail activity or spending variance. Hits: {guardrail_total_hits}, Variance: {spending_variance}, Spending: {spending_path}"

        # Check that spending stays within reasonable bounds
        min_spending = min(spending_path)
        max_spending = max(spending_path)

        assert min_spending > 0, "Spending should stay positive"
        assert max_spending < params.start_capital, "Spending shouldn't exceed portfolio"

    def test_extreme_guardrail_scenarios_robustness(self):
        """Test guardrails handle extreme scenarios without crashing"""

        # Extreme scenario 1: Very tight guardrails
        tight_params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=5,
            num_sims=3,
            lower_wr=0.041,   # Very tight band
            upper_wr=0.039,   # Only 0.2% difference
            adjustment_pct=0.05,  # Small adjustments
            initial_base_spending=40_000
        )

        simulator = RetirementSimulator(tight_params)
        results = simulator.run_simulation()

        # Should complete without errors
        assert results is not None, "Tight guardrails should not crash simulation"

        # Extreme scenario 2: Very wide guardrails (should rarely trigger)
        wide_params = SimulationParams(
            start_capital=1_000_000,
            horizon_years=5,
            num_sims=3,
            lower_wr=0.15,   # 15% - very high
            upper_wr=0.01,   # 1% - very low
            adjustment_pct=0.50,  # 50% adjustments
            initial_base_spending=40_000
        )

        simulator_wide = RetirementSimulator(wide_params)
        results_wide = simulator_wide.run_simulation()

        # Should complete without errors
        assert results_wide is not None, "Wide guardrails should not crash simulation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])