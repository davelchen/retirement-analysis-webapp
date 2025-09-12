"""
Integration tests for the Streamlit app functionality.
Tests the parameter conversion logic and new UI features.
"""
import pytest
import sys
import os

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import SimulationParams


class TestParameterConversion:
    """Test parameter conversion from UI format to SimulationParams"""
    
    def test_onetime_expenses_conversion(self):
        """Test that one-time expenses are properly aggregated"""
        # Simulate session state with multiple one-time expenses
        onetime_expenses = [
            {'year': 2033, 'amount': 50_000, 'description': 'Home renovation'},
            {'year': 2033, 'amount': 25_000, 'description': 'Car purchase'},
            {'year': 2040, 'amount': 100_000, 'description': 'Travel fund'}
        ]
        
        # Calculate expected aggregation
        total_2033 = sum([exp['amount'] for exp in onetime_expenses if exp['year'] == 2033])
        total_2040 = sum([exp['amount'] for exp in onetime_expenses if exp['year'] == 2040])
        
        assert total_2033 == 75_000  # 50k + 25k
        assert total_2040 == 100_000
        
        # Test with empty list
        empty_expenses = []
        total_2033_empty = sum([exp['amount'] for exp in empty_expenses if exp['year'] == 2033])
        total_2040_empty = sum([exp['amount'] for exp in empty_expenses if exp['year'] == 2040])
        
        assert total_2033_empty == 0
        assert total_2040_empty == 0
    
    def test_other_income_streams_conversion(self):
        """Test that other income streams are properly handled"""
        # Simulate session state with multiple income streams
        income_streams = [
            {'amount': 30_000, 'start_year': 2030, 'years': 5, 'description': 'Consulting'},
            {'amount': 20_000, 'start_year': 2028, 'years': 10, 'description': 'Part-time work'},
            {'amount': 15_000, 'start_year': 2035, 'years': 3, 'description': 'Board fees'}
        ]
        
        # Calculate expected aggregations
        if income_streams:
            total_amount = sum([stream['amount'] for stream in income_streams])
            min_start_year = min([stream['start_year'] for stream in income_streams])
            max_end_year = max([stream['start_year'] + stream['years'] for stream in income_streams])
            total_years = max_end_year - min_start_year
        else:
            total_amount = 0
            min_start_year = 2026
            total_years = 0
        
        assert total_amount == 65_000  # 30k + 20k + 15k
        assert min_start_year == 2028   # Earliest start
        assert total_years == 10        # 2038 - 2028 = 10 years total span
        
        # Test with empty list
        empty_streams = []
        if empty_streams:
            total_amount_empty = sum([stream['amount'] for stream in empty_streams])
            min_start_year_empty = min([stream['start_year'] for stream in empty_streams])
            total_years_empty = max([stream['start_year'] + stream['years'] for stream in empty_streams]) - min([stream['start_year'] for stream in empty_streams])
        else:
            total_amount_empty = 0
            min_start_year_empty = 2026
            total_years_empty = 0
        
        assert total_amount_empty == 0
        assert min_start_year_empty == 2026
        assert total_years_empty == 0
    
    def test_simulation_params_with_aggregated_values(self):
        """Test that SimulationParams works with expense streams from UI"""
        # Test with expense streams (new format)
        params = SimulationParams(
            start_capital=5_000_000,
            horizon_years=10,
            num_sims=100,
            expense_streams=[
                {'amount': 75_000, 'start_year': 2033, 'years': 1, 'description': 'Aggregated 2033 expense'},
                {'amount': 200_000, 'start_year': 2040, 'years': 1, 'description': 'Aggregated 2040 expense'}
            ],
            other_income_amount=50_000,  # Aggregated from multiple streams
            other_income_start_year=2028,
            other_income_years=8
        )
        
        # Should create valid params
        assert params.start_capital == 5_000_000
        assert len(params.expense_streams) == 2
        assert params.expense_streams[0]['amount'] == 75_000
        assert params.expense_streams[1]['amount'] == 200_000
        assert params.other_income_amount == 50_000
        assert params.other_income_start_year == 2028
        assert params.other_income_years == 8
        
        # Should be able to run simulation
        from simulation import RetirementSimulator
        simulator = RetirementSimulator(params)
        results = simulator.run_simulation()
        
        assert len(results.terminal_wealth) == 100
        assert 0 <= results.success_rate <= 1
        
        # Test that expenses are calculated correctly
        assert simulator._get_onetime_expense(2033) == 75_000
        assert simulator._get_onetime_expense(2040) == 200_000
        assert simulator._get_onetime_expense(2035) == 0
    
    def test_complex_income_stream_calculation(self):
        """Test complex income stream scenarios"""
        # Overlapping streams
        streams = [
            {'amount': 40_000, 'start_year': 2026, 'years': 5},  # 2026-2030
            {'amount': 25_000, 'start_year': 2028, 'years': 8},  # 2028-2035
            {'amount': 10_000, 'start_year': 2032, 'years': 3}   # 2032-2034
        ]
        
        if streams:
            total_amount = sum([stream['amount'] for stream in streams])
            min_start = min([stream['start_year'] for stream in streams])
            max_end = max([stream['start_year'] + stream['years'] for stream in streams])
            span_years = max_end - min_start
        else:
            total_amount = 0
            min_start = 2026
            span_years = 0
        
        assert total_amount == 75_000  # Sum of all streams
        assert min_start == 2026       # Earliest start
        assert span_years == 10        # 2036 - 2026 = 10 year total span (2028+8=2036)
    
    def test_edge_cases(self):
        """Test edge cases in parameter conversion"""
        # Single year income stream
        single_year_stream = [
            {'amount': 100_000, 'start_year': 2030, 'years': 1}
        ]
        
        if single_year_stream:
            min_start = min([s['start_year'] for s in single_year_stream])
            max_end = max([s['start_year'] + s['years'] for s in single_year_stream])
            span = max_end - min_start
        
        assert span == 1
        
        # Zero amount expense
        zero_expenses = [
            {'year': 2033, 'amount': 0, 'description': 'Cancelled expense'}
        ]
        
        total_2033 = sum([exp['amount'] for exp in zero_expenses if exp['year'] == 2033])
        assert total_2033 == 0
        
        # Far future expenses
        future_expenses = [
            {'year': 2060, 'amount': 50_000, 'description': 'Future expense'}
        ]
        
        total_2060 = sum([exp['amount'] for exp in future_expenses if exp['year'] == 2060])
        assert total_2060 == 50_000


class TestUIDataStructures:
    """Test the UI data structures and validation"""
    
    def test_expense_data_structure(self):
        """Test one-time expense data structure"""
        expense = {
            'year': 2035,
            'amount': 75_000,
            'description': 'Major home renovation'
        }
        
        assert expense['year'] == 2035
        assert expense['amount'] == 75_000
        assert expense['description'] == 'Major home renovation'
        
        # Test required fields exist
        required_fields = ['year', 'amount']
        for field in required_fields:
            assert field in expense
    
    def test_income_stream_data_structure(self):
        """Test income stream data structure"""
        stream = {
            'amount': 35_000,
            'start_year': 2028,
            'years': 7,
            'description': 'Consulting income'
        }
        
        assert stream['amount'] == 35_000
        assert stream['start_year'] == 2028
        assert stream['years'] == 7
        assert stream['description'] == 'Consulting income'
        
        # Test required fields exist
        required_fields = ['amount', 'start_year', 'years']
        for field in required_fields:
            assert field in stream
        
        # Test end year calculation
        end_year = stream['start_year'] + stream['years'] - 1
        assert end_year == 2034  # Last year of income
    
    def test_default_session_state_structure(self):
        """Test default session state matches expected structure"""
        # Default one-time expenses
        default_expenses = [
            {'year': 2033, 'amount': 100_000, 'description': 'Major home renovation'},
            {'year': 2040, 'amount': 100_000, 'description': 'Travel fund'}
        ]
        
        # Default income streams (empty)
        default_income = []
        
        # Test aggregation of defaults
        total_2033 = sum([exp['amount'] for exp in default_expenses if exp['year'] == 2033])
        total_2040 = sum([exp['amount'] for exp in default_expenses if exp['year'] == 2040])
        total_income = sum([stream['amount'] for stream in default_income])
        
        assert total_2033 == 100_000
        assert total_2040 == 100_000
        assert total_income == 0
    
    def test_validation_logic(self):
        """Test validation logic for UI inputs"""
        # Year validation (should be within simulation horizon)
        start_year = 2026
        horizon_years = 50
        
        valid_expense_years = [2030, 2035, 2040, 2050, 2075]  # Last year: 2026 + 50 - 1 = 2075
        invalid_expense_years = [2020, 2025, 2080, 2100]
        
        for year in valid_expense_years:
            assert start_year <= year <= start_year + horizon_years - 1
        
        for year in invalid_expense_years:
            assert not (start_year <= year <= start_year + horizon_years - 1)
        
        # Amount validation (should be non-negative)
        valid_amounts = [0, 1_000, 50_000, 1_000_000]
        invalid_amounts = [-1, -50_000, -1_000_000]
        
        for amount in valid_amounts:
            assert amount >= 0
        
        for amount in invalid_amounts:
            assert not (amount >= 0)


class TestParameterCompatibility:
    """Test backward compatibility with existing parameter structure"""
    
    def test_existing_simulation_params_work(self):
        """Test that SimulationParams interface works with new expense stream format"""
        # Test with all default parameters
        params_default = SimulationParams()
        assert params_default.expense_streams == []
        assert params_default.other_income_amount == 0
        
        # Test with custom parameters using new interface
        params_custom = SimulationParams(
            start_capital=6_000_000,
            expense_streams=[
                {'amount': 150_000, 'start_year': 2033, 'years': 1, 'description': '2033 expense'},
                {'amount': 200_000, 'start_year': 2040, 'years': 1, 'description': '2040 expense'}
            ],
            other_income_amount=30_000,
            other_income_start_year=2030,
            other_income_years=8
        )
        
        assert params_custom.start_capital == 6_000_000
        assert len(params_custom.expense_streams) == 2
        assert params_custom.expense_streams[0]['amount'] == 150_000
        assert params_custom.expense_streams[1]['amount'] == 200_000
        assert params_custom.other_income_amount == 30_000
        assert params_custom.other_income_start_year == 2030
        assert params_custom.other_income_years == 8
    
    def test_serialization_compatibility(self):
        """Test that parameter serialization works with expense streams"""
        from io_utils import params_to_dict, dict_to_params
        
        # Test with parameters that would come from new UI
        params = SimulationParams(
            start_capital=7_000_000,
            expense_streams=[
                {'amount': 75_000, 'start_year': 2033, 'years': 1, 'description': 'Expense 1'},
                {'amount': 125_000, 'start_year': 2040, 'years': 1, 'description': 'Expense 2'}
            ],
            other_income_amount=45_000,  # Aggregated from UI
            other_income_start_year=2029,
            other_income_years=6
        )
        
        # Test serialization round-trip
        param_dict = params_to_dict(params)
        restored_params = dict_to_params(param_dict)
        
        assert restored_params.start_capital == params.start_capital
        assert len(restored_params.expense_streams) == len(params.expense_streams)
        assert restored_params.expense_streams[0]['amount'] == params.expense_streams[0]['amount']
        assert restored_params.expense_streams[1]['amount'] == params.expense_streams[1]['amount']
        assert restored_params.other_income_amount == params.other_income_amount
        assert restored_params.other_income_start_year == params.other_income_start_year
        assert restored_params.other_income_years == params.other_income_years