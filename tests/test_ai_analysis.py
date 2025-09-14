"""
Unit tests for AI retirement analysis module.
Tests both Gemini integration and mock analysis functionality.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import json
from ai_analysis import (
    RetirementAnalyzer, RetirementAnalysis, create_mock_analysis,
    GEMINI_AVAILABLE
)
from simulation import SimulationParams


class TestRetirementAnalysis(unittest.TestCase):
    """Test RetirementAnalysis dataclass"""

    def test_retirement_analysis_creation(self):
        """Test creating RetirementAnalysis object"""
        analysis = RetirementAnalysis(
            success_assessment="Plan looks good",
            key_risks=["Risk 1", "Risk 2"],
            recommendations=[
                {"category": "Spending", "suggestion": "Reduce by 5%", "reasoning": "Improves success rate"}
            ],
            summary="Overall positive outlook",
            confidence_level="High"
        )

        self.assertEqual(analysis.success_assessment, "Plan looks good")
        self.assertEqual(len(analysis.key_risks), 2)
        self.assertEqual(len(analysis.recommendations), 1)
        self.assertEqual(analysis.confidence_level, "High")


class TestRetirementAnalyzer(unittest.TestCase):
    """Test RetirementAnalyzer functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock simulation results
        self.mock_simulation_results = Mock()
        self.mock_simulation_results.terminal_wealth = np.array([1000000, 800000, 1200000, 0, 500000])
        self.mock_simulation_results.guardrail_hits_median = 2
        self.mock_simulation_results.success_rate = 0.85
        # Mock guardrail_hits as None to avoid numpy calculation issues in tests
        self.mock_simulation_results.guardrail_hits = None
        self.mock_simulation_results.wealth_paths = None
        self.mock_simulation_results.years_depleted = None
        self.mock_simulation_results.median_path_details = None
        self.mock_simulation_results.p10_path_details = None  # Add for new percentile analysis
        self.mock_simulation_results.p90_path_details = None  # Add for new percentile analysis

        # Mock simulation parameters
        self.mock_params = SimulationParams(
            start_capital=2_500_000,
            horizon_years=30,
            spending_floor_real=150_000,
            spending_ceiling_real=300_000,
            lower_wr=0.035,
            upper_wr=0.055,
            adjustment_pct=0.10,
            w_equity=0.65,
            w_bonds=0.25,
            w_real_estate=0.08,
            w_cash=0.02,
            social_security_enabled=True,
            ss_annual_benefit=40_000,
            ss_start_age=67,
            regime="baseline",
            standard_deduction=29200,
            equity_mean=0.05,
            equity_vol=0.18,
            bonds_mean=0.015,
            bonds_vol=0.07
        )

        # Mock summary stats
        self.mock_summary_stats = {
            'success_rate': 0.85,
            'median_terminal_wealth': 800_000
        }

    def test_analyzer_initialization_without_api_key(self):
        """Test analyzer initialization without API key"""
        analyzer = RetirementAnalyzer()
        self.assertFalse(analyzer.is_available)
        self.assertIsNone(analyzer.api_key)
        self.assertIsNone(analyzer.model)

    def test_analyzer_initialization_with_api_key(self):
        """Test analyzer initialization with API key"""
        with patch('ai_analysis.genai', create=True) as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model

            analyzer = RetirementAnalyzer("test-api-key")

            if GEMINI_AVAILABLE:
                self.assertTrue(analyzer.is_available)
                self.assertEqual(analyzer.api_key, "test-api-key")
                self.assertEqual(analyzer.model_name, "gemini-2.5-pro")  # Default model
                mock_genai.configure.assert_called_once_with(api_key="test-api-key")
                mock_genai.GenerativeModel.assert_called_once_with("gemini-2.5-pro")
            else:
                self.assertFalse(analyzer.is_available)

    def test_analyzer_initialization_with_custom_model(self):
        """Test analyzer initialization with custom model"""
        with patch('ai_analysis.genai', create=True) as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model

            analyzer = RetirementAnalyzer("test-api-key", "gemini-1.5-pro")

            if GEMINI_AVAILABLE:
                self.assertTrue(analyzer.is_available)
                self.assertEqual(analyzer.api_key, "test-api-key")
                self.assertEqual(analyzer.model_name, "gemini-1.5-pro")
                mock_genai.configure.assert_called_once_with(api_key="test-api-key")
                mock_genai.GenerativeModel.assert_called_once_with("gemini-1.5-pro")
            else:
                self.assertFalse(analyzer.is_available)

    def test_analyze_retirement_plan_without_gemini(self):
        """Test analysis when Gemini is not available"""
        analyzer = RetirementAnalyzer()
        result, error_type = analyzer.analyze_retirement_plan(
            self.mock_simulation_results,
            self.mock_params,
            self.mock_summary_stats
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error_type)

    def test_extract_analysis_data(self):
        """Test comprehensive data extraction for analysis"""
        analyzer = RetirementAnalyzer()
        data = analyzer._extract_analysis_data(
            self.mock_simulation_results,
            self.mock_params,
            self.mock_summary_stats
        )

        # Check success metrics
        self.assertEqual(data['success_metrics']['success_rate'], 0.85)
        self.assertGreaterEqual(data['success_metrics']['failure_rate'], 0)
        self.assertLessEqual(data['success_metrics']['failure_rate'], 1)

        # Check complete parameters structure
        params = data['complete_parameters']
        self.assertEqual(params['financial']['start_capital'], 2_500_000)
        self.assertEqual(params['financial']['horizon_years'], 30)
        self.assertEqual(params['financial']['spending_floor_real'], 150_000)

        # CRITICAL: Validate annual spending is calculated and non-zero
        self.assertIn('annual_spending', params['financial'])
        annual_spending = params['financial']['annual_spending']
        self.assertGreater(annual_spending, 0, "Annual spending should never be $0 - this causes incorrect AI analysis")
        self.assertIsInstance(annual_spending, (int, float), "Annual spending must be numeric")
        # Verify CAPE-based calculation is reasonable (CAPE=38.5, WR=0.0305, spending=~$76,218)
        expected_wr = 0.0175 + 0.5 * (1.0 / 38.5)  # Default CAPE=38.5
        expected_spending = expected_wr * 2_500_000
        self.assertAlmostEqual(annual_spending, expected_spending, delta=10000,
                              msg="Annual spending calculation appears incorrect")

        # Validate other critical financial parameters
        self.assertIn('initial_withdrawal_rate', params['financial'])
        self.assertGreater(params['financial']['initial_withdrawal_rate'], 0)

        self.assertEqual(params['allocation']['equity'], 0.65)
        self.assertTrue(params['social_security']['enabled'])
        self.assertEqual(params['social_security']['annual_benefit'], 40_000)

        # Check terminal wealth analysis
        terminal_stats = data['terminal_wealth_analysis']
        self.assertIn('p50', terminal_stats)  # Median
        self.assertIn('p10', terminal_stats)  # P10
        self.assertIn('p90', terminal_stats)  # P90

        # Check metadata
        self.assertEqual(data['analysis_metadata']['data_completeness'], 'comprehensive')
        self.assertIn('Analyzing', data['analysis_metadata']['model_context'])

    def test_extract_analysis_data_comprehensive_validation(self):
        """Test that ALL critical data fields are present and non-zero/valid for AI analysis"""
        analyzer = RetirementAnalyzer()
        data = analyzer._extract_analysis_data(
            self.mock_simulation_results,
            self.mock_params,
            self.mock_summary_stats
        )

        # Critical financial data validation
        financial = data['complete_parameters']['financial']
        required_financial_fields = [
            'start_capital', 'annual_spending', 'horizon_years',
            'spending_floor_real', 'spending_ceiling_real', 'initial_withdrawal_rate'
        ]
        for field in required_financial_fields:
            self.assertIn(field, financial, f"Missing critical financial field: {field}")
            if field in ['start_capital', 'annual_spending']:
                self.assertGreater(financial[field], 0, f"{field} should be positive, got {financial[field]}")

        # Asset allocation validation
        allocation = data['complete_parameters']['allocation']
        allocation_sum = allocation['equity'] + allocation['bonds'] + allocation['real_estate'] + allocation['cash']
        self.assertAlmostEqual(allocation_sum, 1.0, places=2, msg="Asset allocation should sum to 100%")

        # Social Security validation
        ss = data['complete_parameters']['social_security']
        if ss['enabled']:
            self.assertGreater(ss['annual_benefit'], 0, "SS benefit should be positive when enabled")
            self.assertIsNotNone(ss['start_age'], "SS start age should be specified when enabled")

        # Market parameters validation
        market = data['complete_parameters']['market']
        self.assertIn('cape_ratio', market)
        self.assertGreater(market['cape_ratio'], 0, "CAPE ratio should be positive")

        # Terminal wealth analysis validation
        terminal_stats = data['terminal_wealth_analysis']
        required_percentiles = ['p1', 'p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99']
        for percentile in required_percentiles:
            self.assertIn(percentile, terminal_stats, f"Missing percentile: {percentile}")
            self.assertIsInstance(terminal_stats[percentile], (int, float))

    def test_extract_analysis_data_edge_cases(self):
        """Test data extraction with edge case parameters"""
        from simulation import SimulationParams
        import numpy as np

        # Create edge case parameters (very high CAPE, low spending floor)
        edge_params = SimulationParams(
            start_capital=1_000_000,
            cape_now=50.0,  # Very high CAPE (expensive market)
            spending_floor_real=30_000,  # Very low spending floor
            social_security_enabled=False
        )

        # Mock results with some failures
        class EdgeCaseResults:
            def __init__(self):
                self.terminal_wealth = np.array([0, 500_000, 1_200_000, 0, 800_000])  # Some failures
                self.success_rate = 0.6

        analyzer = RetirementAnalyzer()
        data = analyzer._extract_analysis_data(EdgeCaseResults(), edge_params, {})

        # Validate annual spending calculation with high CAPE
        financial = data['complete_parameters']['financial']
        expected_wr = 0.0175 + 0.5 * (1.0 / 50.0)  # = 0.0175 + 0.01 = 0.0275
        expected_spending = expected_wr * 1_000_000  # = $27,500
        self.assertAlmostEqual(financial['annual_spending'], expected_spending, delta=100)

        # Validate failure rate is calculated correctly
        self.assertEqual(data['success_metrics']['failure_rate'], 0.4)  # 2 out of 5 failed

        # Validate disabled social security
        self.assertFalse(data['complete_parameters']['social_security']['enabled'])
        self.assertEqual(data['complete_parameters']['social_security']['annual_benefit'], 0)

    def test_create_analysis_prompt(self):
        """Test comprehensive prompt creation for AI analysis"""
        analyzer = RetirementAnalyzer()

        # Create sample comprehensive analysis data
        data = {
            'analysis_metadata': {
                'model_context': 'Analyzing 10000 Monte Carlo simulations',
                'data_completeness': 'comprehensive'
            },
            'success_metrics': {
                'success_rate': 0.85,
                'failure_rate': 0.15
            },
            'terminal_wealth_analysis': {
                'mean': 5_000_000,
                'p50': 4_000_000,
                'p10': 1_000_000,
                'p90': 8_000_000,
                'std': 2_000_000,
                'p1': 500_000,
                'p25': 2_500_000,
                'p75': 6_000_000,
                'p95': 10_000_000,
                'p99': 12_000_000
            },
            'complete_parameters': {
                'financial': {
                    'start_capital': 2_500_000,
                    'horizon_years': 30,
                    'spending_floor_real': 150_000,
                    'spending_ceiling_real': 300_000,
                    'initial_withdrawal_rate': 0.06,
                    'start_year': 2026
                },
                'allocation': {'equity': 0.65, 'bonds': 0.25, 'real_estate': 0.08, 'cash': 0.02},
                'guardrails': {'lower_wr': 0.035, 'upper_wr': 0.055, 'adjustment_pct': 0.1},
                'social_security': {'enabled': True, 'annual_benefit': 40_000, 'start_age': 67, 'spouse_benefit': 0, 'funding_scenario': 'conservative'},
                'market': {'regime': 'baseline', 'cape_ratio': 25.0, 'equity_mean': 0.07, 'equity_vol': 0.20, 'bond_mean': 0.03, 'bond_vol': 0.05},
                'taxes': {'state': 'CA'},
                'expenses': {'college_enabled': True, 'college_base_amount': 75000, 'real_estate_enabled': True, 'expense_streams': [], 'income_streams': []}
            },
            'guardrail_analysis': {},
            'path_statistics': {}
        }

        prompt = analyzer._create_analysis_prompt(data)

        # Check that key information is included in comprehensive prompt
        self.assertIn("85.0%", prompt)  # Success rate
        self.assertIn("$2,500,000", prompt)  # Start capital
        self.assertIn("30 years", prompt)  # Time horizon
        self.assertIn("Equity: 65.0%", prompt)  # Allocation
        self.assertIn("$40,000", prompt)  # Social Security
        self.assertIn("Nobel Prize-level", prompt)  # Expert positioning
        self.assertIn("JSON structure", prompt)  # Format instruction
        self.assertIn("comprehensive", prompt)  # Data completeness

    def test_parse_analysis_response_valid_json(self):
        """Test parsing valid JSON response"""
        analyzer = RetirementAnalyzer()

        json_response = json.dumps({
            "success_assessment": "Plan shows good probability of success",
            "key_risks": ["Market volatility", "Inflation risk"],
            "recommendations": [
                {
                    "category": "Allocation",
                    "suggestion": "Increase bonds by 5%",
                    "reasoning": "Reduces portfolio volatility"
                }
            ],
            "summary": "Strong plan with minor adjustments needed",
            "confidence_level": "High"
        })

        analysis = analyzer._parse_analysis_response(json_response)

        self.assertEqual(analysis.success_assessment, "Plan shows good probability of success")
        self.assertEqual(len(analysis.key_risks), 2)
        self.assertEqual(len(analysis.recommendations), 1)
        self.assertEqual(analysis.confidence_level, "High")

    def test_parse_analysis_response_invalid_json(self):
        """Test parsing invalid JSON response"""
        analyzer = RetirementAnalyzer()

        invalid_response = "This is not a JSON response but contains useful analysis information."
        analysis = analyzer._parse_analysis_response(invalid_response)

        # Should create fallback analysis
        self.assertIsInstance(analysis, RetirementAnalysis)
        self.assertIn("analysis completed", analysis.success_assessment.lower())
        self.assertEqual(analysis.confidence_level, "Low")

    def test_parse_analysis_response_partial_json(self):
        """Test parsing response with JSON embedded in text"""
        analyzer = RetirementAnalyzer()

        response_with_json = """
        Here's my analysis:

        {
            "success_assessment": "Plan needs improvement",
            "key_risks": ["High withdrawal rate"],
            "recommendations": [],
            "summary": "Reduce spending by 10%",
            "confidence_level": "Medium"
        }

        Additional commentary follows.
        """

        analysis = analyzer._parse_analysis_response(response_with_json)

        self.assertEqual(analysis.success_assessment, "Plan needs improvement")
        self.assertEqual(analysis.summary, "Reduce spending by 10%")
        self.assertEqual(analysis.confidence_level, "Medium")

    @patch('ai_analysis.genai', create=True)
    def test_analyze_retirement_plan_with_gemini(self, mock_genai):
        """Test full analysis with mocked Gemini"""
        # Mock Gemini model and response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = json.dumps({
            "success_assessment": "Plan looks excellent",
            "key_risks": ["Sequence of returns risk"],
            "recommendations": [
                {"category": "Guardrails", "suggestion": "Maintain current settings", "reasoning": "Working well"}
            ],
            "summary": "Continue with current strategy",
            "confidence_level": "High"
        })

        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        analyzer = RetirementAnalyzer("test-key")

        if GEMINI_AVAILABLE:
            result, error_type = analyzer.analyze_retirement_plan(
                self.mock_simulation_results,
                self.mock_params,
                self.mock_summary_stats
            )

            self.assertIsInstance(result, RetirementAnalysis)
            self.assertEqual(result.success_assessment, "Plan looks excellent")
            self.assertEqual(result.confidence_level, "High")
            self.assertIsNone(error_type)
            mock_model.generate_content.assert_called_once()

    def test_gemini_availability_check(self):
        """Test Gemini availability detection"""
        availability = RetirementAnalyzer.is_gemini_available()
        self.assertIsInstance(availability, bool)

    def test_installation_instructions(self):
        """Test getting installation instructions"""
        instructions = RetirementAnalyzer.get_installation_instructions()
        self.assertIn("pip install", instructions)
        self.assertIn("google-generativeai", instructions)

    def test_get_available_models(self):
        """Test getting available models"""
        models = RetirementAnalyzer.get_available_models()
        self.assertIsInstance(models, dict)
        self.assertIn("gemini-2.0-flash", models)
        self.assertIn("gemini-1.5-flash", models)
        self.assertIn("gemini-1.5-pro", models)

        # Test that descriptions are provided
        for model_key, description in models.items():
            self.assertIsInstance(model_key, str)
            self.assertIsInstance(description, str)
            self.assertTrue(len(description) > 0)

    def test_error_classification(self):
        """Test error classification functionality"""
        analyzer = RetirementAnalyzer()

        # Test rate limit error
        rate_limit_error = Exception("Rate limit exceeded for requests")
        error_type = analyzer._classify_error(rate_limit_error)
        self.assertEqual(error_type, "rate_limit")

        # Test invalid API key error
        auth_error = Exception("Invalid API key provided")
        error_type = analyzer._classify_error(auth_error)
        self.assertEqual(error_type, "invalid_key")

        # Test quota exceeded error
        quota_error = Exception("Quota exceeded for this project")
        error_type = analyzer._classify_error(quota_error)
        self.assertEqual(error_type, "quota_exceeded")

        # Test network error
        network_error = Exception("Network connection timeout")
        error_type = analyzer._classify_error(network_error)
        self.assertEqual(error_type, "network_error")

        # Test JSON parsing error
        json_error = Exception("JSON parsing failed")
        error_type = analyzer._classify_error(json_error)
        self.assertEqual(error_type, "parsing_error")

        # Test unknown error
        unknown_error = Exception("Some unexpected error")
        error_type = analyzer._classify_error(unknown_error)
        self.assertEqual(error_type, "unknown_error")

    @patch('ai_analysis.genai', create=True)
    def test_api_error_handling(self, mock_genai):
        """Test various API error scenarios"""
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model

        analyzer = RetirementAnalyzer("test-key")

        if GEMINI_AVAILABLE:
            # Test rate limit error
            mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
            result, error_type = analyzer.analyze_retirement_plan(
                self.mock_simulation_results,
                self.mock_params,
                self.mock_summary_stats
            )
            self.assertIsNone(result)
            self.assertEqual(error_type, "rate_limit")

            # Test invalid key error
            mock_model.generate_content.side_effect = Exception("Invalid API key")
            result, error_type = analyzer.analyze_retirement_plan(
                self.mock_simulation_results,
                self.mock_params,
                self.mock_summary_stats
            )
            self.assertIsNone(result)
            self.assertEqual(error_type, "invalid_key")

    def test_api_error_messages(self):
        """Test user-friendly error messages"""
        from ai_analysis import APIError

        # Test all error message types
        rate_limit_msg = APIError.get_user_message(APIError.RATE_LIMIT)
        self.assertIn("Rate limit", rate_limit_msg)
        self.assertIn("15 requests", rate_limit_msg)

        invalid_key_msg = APIError.get_user_message(APIError.INVALID_KEY)
        self.assertIn("Invalid API key", invalid_key_msg)
        self.assertIn("Google AI Studio", invalid_key_msg)

        quota_msg = APIError.get_user_message(APIError.QUOTA_EXCEEDED)
        self.assertIn("quota exceeded", quota_msg.lower())
        self.assertIn("1M tokens", quota_msg)

        network_msg = APIError.get_user_message(APIError.NETWORK_ERROR)
        self.assertIn("Network", network_msg)

        # Test unknown error fallback
        unknown_msg = APIError.get_user_message("nonexistent_error")
        self.assertIn("Unexpected error", unknown_msg)


class TestMockAnalysis(unittest.TestCase):
    """Test mock analysis functionality"""

    def test_create_mock_analysis_excellent_success(self):
        """Test mock analysis for excellent success rate"""
        analysis = create_mock_analysis(0.95)

        self.assertIn("excellent", analysis.success_assessment.lower())
        self.assertEqual(analysis.confidence_level, "High")
        self.assertTrue(len(analysis.recommendations) > 0)
        self.assertTrue(len(analysis.key_risks) > 0)

    def test_create_mock_analysis_good_success(self):
        """Test mock analysis for good success rate"""
        analysis = create_mock_analysis(0.85)

        self.assertIn("good", analysis.success_assessment.lower())
        self.assertEqual(analysis.confidence_level, "Medium")

        # Should have specific recommendations for improvement
        recommendation_categories = [rec["category"] for rec in analysis.recommendations]
        self.assertTrue(len(recommendation_categories) > 0)

    def test_create_mock_analysis_poor_success(self):
        """Test mock analysis for poor success rate"""
        analysis = create_mock_analysis(0.65)

        self.assertIn("improvement", analysis.success_assessment.lower())
        self.assertEqual(analysis.confidence_level, "High")  # High confidence in need for changes

        # Should have aggressive recommendations
        recommendations_text = " ".join([rec["suggestion"] for rec in analysis.recommendations])
        self.assertTrue(any(word in recommendations_text.lower()
                          for word in ["reduce", "conservative", "cut", "lower"]))

    def test_create_mock_analysis_boundary_conditions(self):
        """Test mock analysis at boundary conditions"""
        # Test exactly at thresholds
        analysis_90 = create_mock_analysis(0.90)
        analysis_80 = create_mock_analysis(0.80)

        # Should be different assessments
        self.assertNotEqual(analysis_90.success_assessment, analysis_80.success_assessment)

        # Test extreme values
        analysis_low = create_mock_analysis(0.01)
        analysis_perfect = create_mock_analysis(1.0)

        self.assertIsInstance(analysis_low, RetirementAnalysis)
        self.assertIsInstance(analysis_perfect, RetirementAnalysis)

    def test_create_mock_analysis_with_error_type(self):
        """Test mock analysis with error types"""
        from ai_analysis import APIError

        # Test with rate limit error
        analysis = create_mock_analysis(0.85, APIError.RATE_LIMIT)
        self.assertIsNotNone(analysis.error_message)
        self.assertIn("Rate limit", analysis.error_message)

        # Test with invalid key error
        analysis = create_mock_analysis(0.75, APIError.INVALID_KEY)
        self.assertIsNotNone(analysis.error_message)
        self.assertIn("Invalid API key", analysis.error_message)

        # Test without error type
        analysis = create_mock_analysis(0.85)
        self.assertIsNone(analysis.error_message)


class TestIntegration(unittest.TestCase):
    """Integration tests for the AI analysis module"""

    def test_full_workflow_without_api_key(self):
        """Test complete workflow when API is not available"""
        analyzer = RetirementAnalyzer()

        # Should handle gracefully
        self.assertFalse(analyzer.is_available)

        # Mock analysis should still work
        mock_analysis = create_mock_analysis(0.85)
        self.assertIsInstance(mock_analysis, RetirementAnalysis)
        self.assertIn("good", mock_analysis.success_assessment.lower())

    def test_error_handling_in_analysis(self):
        """Test error handling during analysis"""
        with patch('ai_analysis.genai', create=True) as mock_genai:
            # Mock an error during model initialization
            mock_genai.configure.side_effect = Exception("API Error")

            analyzer = RetirementAnalyzer("test-key")

            # Should handle error gracefully
            if GEMINI_AVAILABLE:
                self.assertFalse(analyzer.is_available)


if __name__ == '__main__':
    unittest.main()