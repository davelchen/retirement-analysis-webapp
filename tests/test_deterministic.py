"""
Unit tests for deterministic retirement projection.
"""
import pytest
import numpy as np
from simulation import SimulationParams
from deterministic import DeterministicProjector, convert_to_nominal, create_nominal_table


class TestDeterministicProjector:
    """Test deterministic projection functionality"""
    
    def test_projection_output_shape(self):
        """Test that projection outputs have correct shapes"""
        params = SimulationParams(horizon_years=10, start_capital=1_000_000)
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        assert len(results.wealth_path) == 11  # horizon + 1 for initial
        assert len(results.spending_path) == 10
        assert len(results.withdrawal_path) == 10  
        assert len(results.tax_path) == 10
        assert isinstance(results.guardrail_hits, int)
        assert results.guardrail_hits >= 0
    
    def test_initial_wealth(self):
        """Test that projection starts with correct initial wealth"""
        start_capital = 2_000_000
        params = SimulationParams(horizon_years=5, start_capital=start_capital)
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        assert results.wealth_path[0] == start_capital
    
    def test_expected_return_calculation(self):
        """Test expected return calculation for different regimes"""
        params = SimulationParams(
            w_equity=0.6, w_bonds=0.2, w_real_estate=0.15, w_cash=0.05,
            equity_mean=0.05, bonds_mean=0.015, real_estate_mean=0.01, cash_mean=0.0
        )
        projector = DeterministicProjector(params)
        
        # Baseline regime
        params.regime = "baseline"
        projector = DeterministicProjector(params)
        expected_return = projector._get_expected_return(5)
        expected = 0.6 * 0.05 + 0.2 * 0.015 + 0.15 * 0.01 + 0.05 * 0.0
        assert abs(expected_return - expected) < 1e-10
        
        # Recession-recover regime - year 0
        params.regime = "recession_recover"
        projector = DeterministicProjector(params)
        expected_return = projector._get_expected_return(0)
        expected = 0.6 * (-0.15) + 0.2 * 0.015 + 0.15 * 0.01 + 0.05 * 0.0
        assert abs(expected_return - expected) < 1e-10
        
        # Recession-recover regime - year 1
        expected_return = projector._get_expected_return(1)
        expected = 0.6 * 0.0 + 0.2 * 0.015 + 0.15 * 0.01 + 0.05 * 0.0
        assert abs(expected_return - expected) < 1e-10
        
        # Grind-lower regime - year 5
        params.regime = "grind_lower"
        projector = DeterministicProjector(params)
        expected_return = projector._get_expected_return(5)
        expected = 0.6 * 0.005 + 0.2 * 0.01 + 0.15 * 0.005 + 0.05 * 0.0
        assert abs(expected_return - expected) < 1e-10
    
    def test_spending_components(self):
        """Test that spending components are calculated correctly"""
        params = SimulationParams(
            start_year=2026,
            horizon_years=20,
            start_capital=5_000_000,
            onetime_2033=50_000,
            onetime_2040=75_000,
            re_flow_preset="ramp"
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Check that one-time expenses appear in correct years
        year_2033_idx = details['years'].index(2033)
        year_2040_idx = details['years'].index(2040)
        
        assert details['one_times'][year_2033_idx] == 50_000
        assert details['one_times'][year_2040_idx] == 75_000
        
        # Check RE income for ramp preset
        year_2026_idx = details['years'].index(2026)
        year_2027_idx = details['years'].index(2027) 
        year_2028_idx = details['years'].index(2028)
        
        assert details['re_income'][year_2026_idx] == 50_000
        assert details['re_income'][year_2027_idx] == 60_000
        assert details['re_income'][year_2028_idx] == 75_000
    
    def test_college_topup_growth(self):
        """Test college top-up growth calculation"""
        params = SimulationParams(
            start_year=2026,
            horizon_years=20,
            college_growth_real=0.02  # 2% growth
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Find college years (2032-2041)
        college_years = [year for year in details['years'] if 2032 <= year <= 2041]
        college_topups = [details['college_topup'][details['years'].index(year)] 
                         for year in college_years]
        
        # First year should be 100,000
        assert abs(college_topups[0] - 100_000) < 1
        
        # Each subsequent year should grow by 2%
        for i in range(1, len(college_topups)):
            expected = college_topups[i-1] * 1.02
            assert abs(college_topups[i] - expected) < 1
    
    def test_other_income_duration(self):
        """Test other income duration logic"""
        params = SimulationParams(
            start_year=2026,
            horizon_years=15,
            other_income_amount=30_000,
            other_income_start_year=2030,
            other_income_years=5
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Check income appears in correct years
        for i, year in enumerate(details['years']):
            expected_income = 30_000 if 2030 <= year <= 2034 else 0
            assert details['other_income'][i] == expected_income
    
    def test_inheritance_timing(self):
        """Test inheritance appears in correct year"""
        params = SimulationParams(
            start_year=2026,
            horizon_years=20,
            inherit_amount=500_000,
            inherit_year=2035,
            start_capital=2_000_000
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Find inheritance year
        year_2035_idx = details['years'].index(2035)
        assert details['inheritance'][year_2035_idx] == 500_000
        
        # Check other years have zero inheritance
        for i, year in enumerate(details['years']):
            if year != 2035:
                assert details['inheritance'][i] == 0
    
    def test_guardrail_triggers(self):
        """Test that guardrails trigger appropriately"""
        # Set up scenario likely to trigger guardrails
        params = SimulationParams(
            start_capital=1_000_000,  # Smaller portfolio
            horizon_years=10,
            spending_floor_real=80_000,  # High floor
            lower_wr=0.04,
            upper_wr=0.08,
            adjustment_pct=0.15,  # 15% adjustments
            regime="recession_recover"  # Negative first year
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        # Should have some guardrail hits due to recession and high spending floor
        assert results.guardrail_hits > 0
        
        details = results.year_by_year_details
        guardrail_actions = details['guardrail_action']
        
        # Should have some non-"none" actions
        non_none_actions = [action for action in guardrail_actions if action != "none"]
        assert len(non_none_actions) > 0
    
    def test_spending_bounds_enforcement(self):
        """Test that spending bounds are enforced"""
        params = SimulationParams(
            start_capital=10_000_000,  # Large portfolio  
            horizon_years=10,
            spending_floor_real=200_000,
            spending_ceiling_real=400_000,
            floor_end_year=2035
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Check that spending never goes below floor (before floor_end_year)
        for i, year in enumerate(details['years']):
            base_spending = details['adjusted_base_spending'][i]
            if year <= params.floor_end_year:
                assert base_spending >= params.spending_floor_real - 1  # Allow small numerical errors
            assert base_spending <= params.spending_ceiling_real + 1
    
    def test_tax_calculations_positive(self):
        """Test that tax calculations produce reasonable results"""
        params = SimulationParams(
            start_capital=8_000_000,
            horizon_years=5,
            standard_deduction=30_000
        )
        projector = DeterministicProjector(params)
        results = projector.run_projection()
        
        details = results.year_by_year_details
        
        # Should have positive gross withdrawals and some taxes
        assert all(gw >= 0 for gw in details['gross_withdrawal'])
        assert any(tax > 0 for tax in details['taxes'])
        
        # Taxes should be less than gross withdrawal
        for i in range(len(details['taxes'])):
            assert details['taxes'][i] <= details['gross_withdrawal'][i]


class TestNominalConversion:
    """Test nominal dollar conversion utilities"""
    
    def test_convert_to_nominal_basic(self):
        """Test basic nominal conversion"""
        real_values = np.array([100_000, 100_000, 100_000])  # Constant real
        start_year = 2026
        inflation_rate = 0.03  # 3% inflation
        
        nominal_values = convert_to_nominal(real_values, start_year, inflation_rate)
        
        # Year 0: 100,000 * (1.03)^0 = 100,000
        # Year 1: 100,000 * (1.03)^1 = 103,000
        # Year 2: 100,000 * (1.03)^2 = 106,090
        
        assert abs(nominal_values[0] - 100_000) < 1
        assert abs(nominal_values[1] - 103_000) < 1
        assert abs(nominal_values[2] - 106_090) < 1
    
    def test_convert_to_nominal_zero_inflation(self):
        """Test nominal conversion with zero inflation"""
        real_values = np.array([50_000, 75_000, 100_000])
        nominal_values = convert_to_nominal(real_values, 2026, 0.0)
        
        # With zero inflation, nominal should equal real
        np.testing.assert_array_equal(nominal_values, real_values)
    
    def test_create_nominal_table(self):
        """Test creation of nominal details table"""
        # Create sample details in real dollars
        details = {
            'years': [2026, 2027, 2028],
            'start_assets': [1_000_000, 1_050_000, 1_100_000],
            'gross_withdrawal': [40_000, 42_000, 44_000],
            'taxes': [8_000, 8_500, 9_000],
            'guardrail_action': ['none', 'up', 'none'],  # Non-currency field
            'withdrawal_rate': [0.04, 0.04, 0.04]  # Non-currency field
        }
        
        start_year = 2026
        inflation_rate = 0.025  # 2.5%
        
        nominal_details = create_nominal_table(details, start_year, inflation_rate)
        
        # Check that currency fields were inflated
        assert 'start_assets' in nominal_details
        assert 'gross_withdrawal' in nominal_details
        assert 'taxes' in nominal_details
        
        # Check that non-currency fields were passed through
        assert nominal_details['guardrail_action'] == details['guardrail_action']
        assert nominal_details['withdrawal_rate'] == details['withdrawal_rate']
        
        # Check inflation calculation for first few values
        # Year 0 (2026): no inflation
        assert abs(nominal_details['start_assets'][0] - 1_000_000) < 1
        
        # Year 1 (2027): 2.5% inflation
        expected_2027 = 1_050_000 * 1.025
        assert abs(nominal_details['start_assets'][1] - expected_2027) < 1
        
        # Year 2 (2028): (2.5%)^2 inflation
        expected_2028 = 1_100_000 * (1.025 ** 2)
        assert abs(nominal_details['start_assets'][2] - expected_2028) < 1
    
    def test_create_nominal_table_missing_fields(self):
        """Test nominal table creation with missing fields"""
        details = {
            'years': [2026, 2027],
            'start_assets': [1_000_000, 1_050_000],
            # Missing some typical fields
        }
        
        nominal_details = create_nominal_table(details, 2026, 0.02)
        
        # Should handle missing fields gracefully
        assert 'start_assets' in nominal_details
        assert 'years' in nominal_details
        assert len(nominal_details['start_assets']) == 2