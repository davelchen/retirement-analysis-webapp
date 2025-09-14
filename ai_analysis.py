"""
AI-powered retirement analysis using Google Gemini.
Provides analysis and recommendations based on Monte Carlo simulation results.
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np

# Optional import - gracefully handle if not available
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


@dataclass
class RetirementAnalysis:
    """Structure for AI analysis results"""
    success_assessment: str
    key_risks: List[str]
    recommendations: List[Dict[str, str]]  # [{"category": "...", "suggestion": "...", "reasoning": "..."}]
    summary: str
    confidence_level: str
    error_message: Optional[str] = None  # For error cases


class APIError:
    """Common API error types and messages"""
    RATE_LIMIT = "rate_limit"
    INVALID_KEY = "invalid_key"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    PARSING_ERROR = "parsing_error"
    UNKNOWN_ERROR = "unknown_error"

    @staticmethod
    def get_user_message(error_type: str) -> str:
        """Get user-friendly error messages"""
        messages = {
            APIError.RATE_LIMIT: "🚦 **Rate limit exceeded.** Please wait a moment and try again. The free tier allows 15 requests per minute.",
            APIError.INVALID_KEY: "🔑 **Invalid API key.** Please check your API key at [Google AI Studio](https://aistudio.google.com/app/apikey).",
            APIError.QUOTA_EXCEEDED: "📊 **Daily quota exceeded.** The free tier provides 1M tokens per day. Try again tomorrow or upgrade your plan.",
            APIError.NETWORK_ERROR: "🌐 **Network error.** Please check your internet connection and try again.",
            APIError.PARSING_ERROR: "⚠️ **Analysis parsing issue.** Using fallback analysis.",
            APIError.UNKNOWN_ERROR: "❓ **Unexpected error occurred.** Using offline analysis instead."
        }
        return messages.get(error_type, messages[APIError.UNKNOWN_ERROR])


class RetirementAnalyzer:
    """AI-powered retirement analysis using Google Gemini"""

    # Available models for the free tier (as of 2025)
    AVAILABLE_MODELS = {
        'gemini-2.5-pro': 'Gemini 2.5 Pro (Most Powerful, Free Tier - 100 requests/day)',
        'gemini-2.5-flash': 'Gemini 2.5 Flash (Fast & Efficient, Free)',
        'gemini-2.0-flash': 'Gemini 2.0 Flash (Latest Flash)',
        'gemini-1.5-pro': 'Gemini 1.5 Pro (Stable Pro)',
        'gemini-1.5-flash': 'Gemini 1.5 Flash (Stable Flash)',
        'gemini-1.5-flash-8b': 'Gemini 1.5 Flash-8B (Fastest, Most Cost-Effective)',
        'gemini-2.0-flash-lite': 'Gemini 2.0 Flash-Lite (Lightweight)',
    }

    def __init__(self, api_key: Optional[str] = None, model_name: str = 'gemini-2.5-pro'):
        """
        Initialize the analyzer.

        Args:
            api_key: Google API key for Gemini. If None, analysis will be disabled.
            model_name: Name of the Gemini model to use. Defaults to gemini-2.0-flash.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.model = None
        self.is_available = GEMINI_AVAILABLE and api_key is not None

        if self.is_available:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
            except Exception as e:
                self.is_available = False
                print(f"Warning: Failed to initialize Gemini model '{model_name}': {e}")

    def analyze_retirement_plan(self,
                              simulation_results: Any,
                              params: Any,
                              summary_stats: Dict) -> Tuple[Optional[RetirementAnalysis], Optional[str]]:
        """
        Analyze retirement simulation results and provide recommendations.

        Args:
            simulation_results: Results from Monte Carlo simulation
            params: SimulationParams object with plan parameters
            summary_stats: Dictionary with success rates and other metrics

        Returns:
            Tuple of (RetirementAnalysis object, error_type string) or (None, error_type)
        """
        if not self.is_available:
            return None, APIError.UNKNOWN_ERROR

        try:
            # Extract key metrics for analysis
            analysis_data = self._extract_analysis_data(simulation_results, params, summary_stats)

            # Create prompt for Gemini
            prompt = self._create_analysis_prompt(analysis_data)

            # Get AI analysis with timeout and error handling
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                return None, APIError.UNKNOWN_ERROR

            # Extract usage metadata if available
            usage_info = self._extract_usage_metadata(response)
            if usage_info:
                self._track_usage(usage_info)

            # Parse response into structured format
            analysis = self._parse_analysis_response(response.text)
            return analysis, None

        except Exception as e:
            error_type = self._classify_error(e)
            print(f"Error in retirement analysis ({error_type}): {e}")
            return None, error_type

    def _classify_error(self, error: Exception) -> str:
        """Classify API errors into user-friendly categories"""
        error_str = str(error).lower()

        # Check for specific Gemini API errors
        if "rate limit" in error_str or "429" in error_str:
            return APIError.RATE_LIMIT
        elif "invalid api key" in error_str or "401" in error_str or "403" in error_str:
            return APIError.INVALID_KEY
        elif "quota exceeded" in error_str or "quota" in error_str:
            return APIError.QUOTA_EXCEEDED
        elif "network" in error_str or "connection" in error_str or "timeout" in error_str:
            return APIError.NETWORK_ERROR
        elif "json" in error_str or "parsing" in error_str:
            return APIError.PARSING_ERROR
        else:
            return APIError.UNKNOWN_ERROR

    def _extract_analysis_data(self, simulation_results, params, summary_stats) -> Dict[str, Any]:
        """Extract comprehensive data for AI analysis using full context window"""

        # Basic simulation results
        terminal_wealth = simulation_results.terminal_wealth
        success_rate = getattr(simulation_results, 'success_rate', 0)
        wealth_paths = getattr(simulation_results, 'wealth_paths', None)
        guardrail_hits = getattr(simulation_results, 'guardrail_hits', None)
        years_depleted = getattr(simulation_results, 'years_depleted', None)

        # Calculate comprehensive statistics
        failed_paths = terminal_wealth[terminal_wealth <= 0]
        failure_rate = len(failed_paths) / len(terminal_wealth) if len(terminal_wealth) > 0 else 0

        # Terminal wealth percentiles
        tw_percentiles = {
            'p1': float(np.percentile(terminal_wealth, 1)),
            'p5': float(np.percentile(terminal_wealth, 5)),
            'p10': float(np.percentile(terminal_wealth, 10)),
            'p25': float(np.percentile(terminal_wealth, 25)),
            'p50': float(np.percentile(terminal_wealth, 50)),
            'p75': float(np.percentile(terminal_wealth, 75)),
            'p90': float(np.percentile(terminal_wealth, 90)),
            'p95': float(np.percentile(terminal_wealth, 95)),
            'p99': float(np.percentile(terminal_wealth, 99)),
            'mean': float(np.mean(terminal_wealth)),
            'std': float(np.std(terminal_wealth))
        }

        # Calculate CAPE-based initial annual spending
        cape_withdrawal_rate = 0.0175 + 0.5 * (1.0 / params.cape_now) if hasattr(params, 'cape_now') and params.cape_now > 0 else 0.04
        initial_annual_spending = cape_withdrawal_rate * params.start_capital

        # Complete parameter set
        complete_params = {
            'financial': {
                'start_capital': params.start_capital,
                'horizon_years': params.horizon_years,
                'annual_spending': initial_annual_spending,
                'spending_floor_real': params.spending_floor_real,
                'spending_ceiling_real': params.spending_ceiling_real,
                'initial_withdrawal_rate': cape_withdrawal_rate,
                'start_year': params.start_year
            },
            'allocation': {
                'equity': params.w_equity,
                'bonds': params.w_bonds,
                'real_estate': params.w_real_estate,
                'cash': params.w_cash
            },
            'guardrails': {
                'lower_wr': params.lower_wr,
                'upper_wr': params.upper_wr,
                'adjustment_pct': params.adjustment_pct
            },
            'social_security': {
                'enabled': params.social_security_enabled,
                'annual_benefit': params.ss_annual_benefit if params.social_security_enabled else 0,
                'start_age': params.ss_start_age if params.social_security_enabled else None,
                'spouse_benefit': params.spouse_ss_annual_benefit if hasattr(params, 'spouse_ss_annual_benefit') else 0,
                'spouse_start_age': getattr(params, 'spouse_ss_start_age', None),
                'funding_scenario': getattr(params, 'ss_benefit_scenario', 'conservative')
            },
            'taxes': {
                'state': getattr(params, 'state_tax', 'CA'),
                'standard_deduction': params.standard_deduction
            },
            'market': {
                'regime': params.regime,
                'cape_ratio': getattr(params, 'cape_now', 25.0),
                'equity_mean': params.equity_mean,
                'equity_vol': params.equity_vol,
                'bond_mean': params.bonds_mean,
                'bond_vol': params.bonds_vol
            },
            'expenses': {
                'college_enabled': getattr(params, 'college_enabled', True),
                'college_base_amount': getattr(params, 'college_base_amount', 75000),
                'real_estate_enabled': getattr(params, 'real_estate_enabled', True),
                'expense_streams': getattr(params, 'expense_streams', []),
                'income_streams': getattr(params, 'income_streams', [])
            }
        }

        # Guardrail analysis
        guardrail_analysis = {}
        if guardrail_hits is not None:
            guardrail_analysis = {
                'median_hits': float(np.median(guardrail_hits)),
                'mean_hits': float(np.mean(guardrail_hits)),
                'max_hits': int(np.max(guardrail_hits)),
                'hit_distribution': {
                    '0_hits': float(np.mean(guardrail_hits == 0)),
                    '1-3_hits': float(np.mean((guardrail_hits >= 1) & (guardrail_hits <= 3))),
                    '4-7_hits': float(np.mean((guardrail_hits >= 4) & (guardrail_hits <= 7))),
                    '8+_hits': float(np.mean(guardrail_hits >= 8))
                }
            }

        # Year-by-year percentile path analysis (P10, P50, P90)
        percentile_paths_analysis = {}

        # Helper function to extract path data
        def extract_path_data(path_details, percentile_name):
            try:
                if not path_details:
                    return {'error': f'No {percentile_name} path data available'}

                # Sample first 5 and last 5 years for token efficiency
                years = path_details.get('years', [])
                if len(years) > 10:
                    sample_indices = list(range(5)) + list(range(-5, 0))
                    sample_years = [years[i] for i in sample_indices if i < len(years)]
                else:
                    sample_indices = list(range(len(years)))
                    sample_years = years

                # Safely extract trend data
                withdrawal_rates = path_details.get('withdrawal_rate', [])
                portfolio_values = path_details.get('end_assets', [])
                total_expenses = path_details.get('net_need', [])

                return {
                    'sample_years': sample_years,
                    'withdrawal_rate_trend': [withdrawal_rates[i] for i in sample_indices if i < len(withdrawal_rates)],
                    'portfolio_value_trend': [portfolio_values[i] for i in sample_indices if i < len(portfolio_values)],
                    'total_expenses_trend': [total_expenses[i] for i in sample_indices if i < len(total_expenses)]
                }
            except (KeyError, IndexError, AttributeError) as e:
                print(f"Warning: Error extracting {percentile_name} path analysis: {e}")
                return {'error': f'Could not extract {percentile_name} path data'}

        # Extract all three percentile paths
        if hasattr(simulation_results, 'p10_path_details'):
            percentile_paths_analysis['p10'] = extract_path_data(
                simulation_results.p10_path_details, 'P10'
            )

        if hasattr(simulation_results, 'median_path_details'):
            percentile_paths_analysis['p50'] = extract_path_data(
                simulation_results.median_path_details, 'P50/Median'
            )

        if hasattr(simulation_results, 'p90_path_details'):
            percentile_paths_analysis['p90'] = extract_path_data(
                simulation_results.p90_path_details, 'P90'
            )

        # Wealth path statistics
        path_statistics = {}
        if wealth_paths is not None and hasattr(wealth_paths, 'shape') and len(wealth_paths.shape) == 2:
            try:
                num_paths, num_years = wealth_paths.shape
                # Sample key years: start, 5, 10, 15, 20, 25, end
                key_year_indices = [0, 5, 10, 15, 20, 25, -1]
                key_year_indices = [i for i in key_year_indices if (i < num_years and i >= 0) or i == -1]

                path_statistics = {
                    'num_simulations': num_paths,
                    'years_analyzed': num_years,
                    'key_year_wealth_percentiles': {}
                }

                for year_idx in key_year_indices:
                    try:
                        year_label = f'year_{year_idx + 1}' if year_idx >= 0 else 'final_year'
                        year_wealth = wealth_paths[:, year_idx]
                        path_statistics['key_year_wealth_percentiles'][year_label] = {
                            'p10': float(np.percentile(year_wealth, 10)),
                            'p50': float(np.percentile(year_wealth, 50)),
                            'p90': float(np.percentile(year_wealth, 90))
                        }
                    except (IndexError, ValueError) as e:
                        print(f"Warning: Error processing year {year_idx}: {e}")
                        continue
            except (AttributeError, ValueError) as e:
                print(f"Warning: Error extracting wealth path statistics: {e}")
                path_statistics = {'error': 'Could not extract wealth path data'}

        return {
            'analysis_metadata': {
                'timestamp': '2025',
                'model_context': f'Analyzing {len(terminal_wealth)} Monte Carlo simulations',
                'data_completeness': 'comprehensive'
            },
            'success_metrics': {
                'success_rate': float(success_rate),
                'failure_rate': float(failure_rate),
                'years_until_depletion': {
                    'never_depleted': float(np.mean(years_depleted == 0)) if years_depleted is not None else None,
                    'median_depletion_year': float(np.median(years_depleted[years_depleted > 0])) if years_depleted is not None and np.any(years_depleted > 0) else None
                } if years_depleted is not None else {}
            },
            'terminal_wealth_analysis': tw_percentiles,
            'complete_parameters': complete_params,
            'guardrail_analysis': guardrail_analysis,
            'percentile_path_analysis': percentile_paths_analysis,
            'path_statistics': path_statistics,
            'summary_statistics': summary_stats
        }

    def _create_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Create sophisticated prompt for world-class expert analysis"""

        # Extract key data for readability
        success_rate = data['success_metrics']['success_rate']
        params = data['complete_parameters']
        terminal_stats = data['terminal_wealth_analysis']
        guardrails = data['guardrail_analysis']

        # Pre-format percentage values to avoid f-string issues
        success_rate_pct = f"{success_rate:.1%}"
        failure_rate_pct = f"{data['success_metrics']['failure_rate']:.1%}"

        # Build percentile path analysis section
        percentile_paths_section = ""
        if data.get('percentile_path_analysis'):
            path_details = []
            for percentile, path_data in data['percentile_path_analysis'].items():
                if path_data.get('error'):
                    path_details.append(f"- {percentile.upper()}: {path_data['error']}")
                else:
                    scenario_name = "Pessimistic" if percentile == "p10" else "Median" if percentile == "p50" else "Optimistic"
                    years_str = ", ".join(map(str, path_data.get('sample_years', []))) if path_data.get('sample_years') else "N/A"
                    portfolio_str = " → ".join([f"${val:,.0f}" for val in path_data.get('portfolio_value_trend', [])[:5]]) if path_data.get('portfolio_value_trend') else "N/A"
                    wr_str = " → ".join([f"{val:.2%}" for val in path_data.get('withdrawal_rate_trend', [])[:5]]) if path_data.get('withdrawal_rate_trend') else "N/A"
                    expense_str = " → ".join([f"${val:,.0f}" for val in path_data.get('total_expenses_trend', [])[:5]]) if path_data.get('total_expenses_trend') else "N/A"

                    path_details.append(f"""
{percentile.upper()} Scenario ({scenario_name}):
- Sample Years: {years_str}
- Portfolio Trajectory: {portfolio_str}
- Withdrawal Rate Trend: {wr_str}
- Expense Progression: {expense_str}""")

            if path_details:
                percentile_paths_section = "\n".join(path_details)

        return f"""
You are the world's premier retirement planning expert, combining decades of experience as:
- A Nobel Prize-level financial economist with deep expertise in portfolio theory, behavioral finance, and market dynamics
- A seasoned political economist who understands policy trends, regulatory changes, and their long-term implications
- A master strategist who has guided ultra-high-net-worth families through multiple market cycles
- A behavioral psychologist who understands human decision-making under uncertainty

COMPREHENSIVE RETIREMENT ANALYSIS REQUEST:
Analyze this sophisticated Monte Carlo simulation with the depth and rigor of the world's best financial advisory firms.

=== SIMULATION OVERVIEW ===
{data['analysis_metadata']['model_context']}
Data Quality: {data['analysis_metadata']['data_completeness']}

=== SUCCESS METRICS ===
Success Rate: {success_rate_pct}
Failure Rate: {failure_rate_pct}
Never Depleted: {f"{data['success_metrics'].get('years_until_depletion', {}).get('never_depleted', 0):.1%}" if data['success_metrics'].get('years_until_depletion', {}).get('never_depleted') is not None else 'N/A'}

=== COMPLETE FINANCIAL PROFILE ===
Portfolio Details:
- Starting Capital: ${params['financial']['start_capital']:,.0f}
- Time Horizon: {params['financial']['horizon_years']} years ({params['financial']['start_year']}-{params['financial']['start_year'] + params['financial']['horizon_years']})
- Spending Range: ${params['financial']['spending_floor_real']:,.0f} - ${params['financial']['spending_ceiling_real']:,.0f} (real dollars)
- Initial Withdrawal Rate: {params['financial']['initial_withdrawal_rate']:.2%}

Asset Allocation Strategy:
- Equity: {params['allocation']['equity']:.1%} (Expected Return: {params['market']['equity_mean']:.1%}, Volatility: {params['market']['equity_vol']:.1%})
- Bonds: {params['allocation']['bonds']:.1%} (Expected Return: {params['market']['bond_mean']:.1%}, Volatility: {params['market']['bond_vol']:.1%})
- Real Estate: {params['allocation']['real_estate']:.1%}
- Cash: {params['allocation']['cash']:.1%}

=== TERMINAL WEALTH DISTRIBUTION ===
Mean: ${terminal_stats['mean']:,.0f}
Percentile Analysis:
- P1: ${terminal_stats['p1']:,.0f} | P10: ${terminal_stats['p10']:,.0f} | P25: ${terminal_stats['p25']:,.0f}
- Median (P50): ${terminal_stats['p50']:,.0f}
- P75: ${terminal_stats['p75']:,.0f} | P90: ${terminal_stats['p90']:,.0f} | P99: ${terminal_stats['p99']:,.0f}
- Standard Deviation: ${terminal_stats['std']:,.0f}

=== DYNAMIC GUARDRAIL SYSTEM ===
Lower Guardrail: {params['guardrails']['lower_wr']:.1%} (adjustment: {params['guardrails']['adjustment_pct']:.0%})
Upper Guardrail: {params['guardrails']['upper_wr']:.1%} (adjustment: {params['guardrails']['adjustment_pct']:.0%})
{"Guardrail Performance:" if guardrails else "Guardrail data not available"}
{f"- Median Hits: {guardrails.get('median_hits', 'N/A')}" if guardrails else ""}
{f"- Distribution: {guardrails.get('hit_distribution', {}).get('0_hits', 0):.0%} no hits, {guardrails.get('hit_distribution', {}).get('1-3_hits', 0):.0%} low hits, {guardrails.get('hit_distribution', {}).get('8+_hits', 0):.0%} frequent adjustments" if guardrails else ""}

=== SOCIAL SECURITY INTEGRATION ===
Primary Benefit: ${params['social_security']['annual_benefit']:,.0f} {"(starting age " + str(params['social_security']['start_age']) + ")" if params['social_security']['enabled'] else ""}
Spousal Benefit: ${params['social_security']['spouse_benefit']:,.0f}
Funding Scenario: {params['social_security']['funding_scenario'].title()}
Tax Jurisdiction: {params['taxes']['state']}

=== MARKET ENVIRONMENT ===
Regime: {params['market']['regime'].title()}
Current CAPE Ratio: {params['market']['cape_ratio']:.1f}
Economic Context: Consider current 2025 market conditions, Fed policy, geopolitical tensions, and demographic trends

=== EXPENSE ANALYSIS ===
College Planning: {'Enabled' if params['expenses']['college_enabled'] else 'Disabled'} ${params['expenses']['college_base_amount']:,.0f}
Real Estate Income: {'Enabled' if params['expenses']['real_estate_enabled'] else 'Disabled'}
Additional Streams: {len(params['expenses']['expense_streams'])} expense streams, {len(params['expenses']['income_streams'])} income streams

=== WEALTH PATH ANALYSIS ===
{f"Simulation Paths: {data['path_statistics']['num_simulations']:,} over {data['path_statistics']['years_analyzed']} years" if data['path_statistics'] else ""}
{"Key Milestones:" if data['path_statistics'] else ""}
{chr(10).join([f"- {milestone.replace('_', ' ').title()}: P10=${stats['p10']:,.0f}, Median=${stats['p50']:,.0f}, P90=${stats['p90']:,.0f}" for milestone, stats in data['path_statistics'].get('key_year_wealth_percentiles', {}).items()])}

=== YEAR-BY-YEAR PERCENTILE ANALYSIS ===
{"Detailed path projections for P10 (pessimistic), P50 (median), and P90 (optimistic) scenarios:" if data.get('percentile_path_analysis') else ""}
{percentile_paths_section}

=== ANALYTICAL FRAMEWORK ===
Apply your expertise to assess:

1. **Success Rate Adequacy**: Is {success_rate_pct} success sufficient given their risk profile and time horizon?
2. **Tail Risk Management**: Analyze the P1-P10 outcomes for catastrophic scenario planning
3. **Sequence of Returns Risk**: Evaluate early-years vulnerability given their withdrawal strategy
4. **Guardrail Effectiveness**: Are the dynamic adjustments optimally calibrated for this scenario?
5. **Asset Allocation Efficiency**: Does the allocation match their time horizon and risk tolerance?
6. **Policy Risk Assessment**: Consider Social Security, tax policy, and healthcare cost inflation
7. **Behavioral Considerations**: Will this plan be psychologically sustainable during market stress?

=== RESPONSE FORMAT ===
Provide your world-class analysis in this exact JSON structure:

{{
  "success_assessment": "Sophisticated one-sentence summary integrating statistical rigor with practical wisdom",
  "key_risks": ["Most critical risk with specific impact", "Second most important systemic risk", "Third key vulnerability"],
  "recommendations": [
    {{
      "category": "Strategic Asset Allocation",
      "suggestion": "Specific, implementable portfolio adjustment with exact percentages",
      "reasoning": "Quantified rationale based on expected utility theory and behavioral finance"
    }},
    {{
      "category": "Dynamic Spending Strategy",
      "suggestion": "Precise guardrail or spending modifications with triggers",
      "reasoning": "Mathematical justification considering sequence risk and sustainability"
    }},
    {{
      "category": "Tax & Social Security Optimization",
      "suggestion": "Actionable timing or structuring recommendations",
      "reasoning": "Policy analysis and present value calculations"
    }},
    {{
      "category": "Risk Management",
      "suggestion": "Hedging, insurance, or contingency strategies",
      "reasoning": "Tail risk analysis and cost-benefit assessment"
    }}
  ],
  "summary": "2-3 sentences providing your expert verdict with specific confidence intervals and implementation priorities",
  "confidence_level": "High/Medium/Low with specific reasoning based on simulation robustness and market uncertainty"
}}

Channel the analytical depth of Jack Bogle, the strategic insight of David Swensen, and the risk awareness of Nassim Taleb. Be specific, quantitative, and actionable.
"""

    def _parse_analysis_response(self, response_text: str) -> RetirementAnalysis:
        """Parse Gemini response into structured analysis"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()

            # Find JSON content between { and }
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                analysis_data = json.loads(json_text)

                return RetirementAnalysis(
                    success_assessment=analysis_data.get('success_assessment', 'Analysis completed'),
                    key_risks=analysis_data.get('key_risks', []),
                    recommendations=analysis_data.get('recommendations', []),
                    summary=analysis_data.get('summary', 'No summary provided'),
                    confidence_level=analysis_data.get('confidence_level', 'Medium'),
                    error_message=None
                )
            else:
                # Fallback: create basic analysis from text
                return RetirementAnalysis(
                    success_assessment="AI analysis completed",
                    key_risks=["Analysis parsing incomplete"],
                    recommendations=[{"category": "General", "suggestion": "Review AI response manually", "reasoning": "JSON parsing failed"}],
                    summary=response_text[:200] + "..." if len(response_text) > 200 else response_text,
                    confidence_level="Low",
                    error_message=None
                )

        except json.JSONDecodeError:
            # Fallback for non-JSON responses
            return RetirementAnalysis(
                success_assessment="Analysis completed with parsing issues",
                key_risks=["Response format needs improvement"],
                recommendations=[{"category": "Technical", "suggestion": "Check API response format", "reasoning": "JSON parsing failed"}],
                summary=response_text[:200] + "..." if len(response_text) > 200 else response_text,
                confidence_level="Low",
                error_message=None
            )

    def chat_about_analysis(self,
                           question: str,
                           analysis_data: Optional[Dict[str, Any]] = None,
                           previous_context: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Interactive chat about the retirement analysis.

        Args:
            question: User's question about the analysis
            analysis_data: The extracted analysis data (from _extract_analysis_data)
            previous_context: Previous conversation context for continuity

        Returns:
            Tuple of (response text, error_type) or (None, error_type)
        """
        if not self.is_available:
            return None, APIError.UNKNOWN_ERROR

        try:
            # Build context-aware prompt for chat
            context_prompt = self._create_chat_prompt(question, analysis_data, previous_context)

            # Generate response
            response = self.model.generate_content(context_prompt)

            if response and hasattr(response, 'text'):
                # Extract usage metadata if available
                usage_info = self._extract_usage_metadata(response)
                if usage_info:
                    self._track_usage(usage_info)

                return response.text.strip(), None
            else:
                return None, APIError.PARSING_ERROR

        except Exception as e:
            error_msg = str(e).lower()
            if 'rate limit' in error_msg or 'quota' in error_msg:
                return None, APIError.RATE_LIMIT
            elif 'api key' in error_msg or 'invalid' in error_msg:
                return None, APIError.INVALID_KEY
            elif 'quota exceeded' in error_msg:
                return None, APIError.QUOTA_EXCEEDED
            elif 'network' in error_msg or 'connection' in error_msg:
                return None, APIError.NETWORK_ERROR
            else:
                return None, APIError.UNKNOWN_ERROR

    def _create_chat_prompt(self,
                           question: str,
                           analysis_data: Optional[Dict[str, Any]] = None,
                           previous_context: Optional[str] = None) -> str:
        """Create a prompt for chat interaction about retirement analysis"""

        base_context = """
You are the world's premier retirement planning expert, ready to answer detailed follow-up questions about retirement analysis with the expertise of:
- A Nobel Prize-level financial economist with deep expertise in portfolio theory and market dynamics
- A seasoned political economist who understands policy trends and regulatory changes
- A master strategist who has guided ultra-high-net-worth families through market cycles
- A behavioral psychologist who understands decision-making under uncertainty

Provide clear, actionable, and sophisticated responses. Use specific numbers from the analysis when relevant.
"""

        # Add analysis context if available
        context_section = ""
        if analysis_data:
            success_rate = analysis_data.get('success_metrics', {}).get('success_rate', 0)
            params = analysis_data.get('complete_parameters', {})
            financial = params.get('financial', {})

            context_section = f"""
=== CURRENT RETIREMENT ANALYSIS CONTEXT ===
Success Rate: {success_rate:.1%}
Starting Capital: ${financial.get('start_capital', 0):,}
Annual Spending: ${financial.get('annual_spending', 0):,}
Retirement Age: {params.get('simulation', {}).get('retirement_age', 'Unknown')}

Key Data Available:
- Monte Carlo simulation results with {analysis_data.get('analysis_metadata', {}).get('model_context', 'unknown number of')} simulations
- Complete parameter set including allocation, guardrails, taxes, and Social Security
- Terminal wealth analysis with percentile breakdowns
- Year-by-year projection samples and path statistics
"""

        # Add previous context if available
        conversation_context = ""
        if previous_context:
            conversation_context = f"""
=== PREVIOUS CONVERSATION CONTEXT ===
{previous_context}
"""

        return f"""{base_context}

{context_section}

{conversation_context}

=== USER QUESTION ===
{question}

Please provide a detailed, expert-level response that directly addresses the question using the available analysis data."""

    @staticmethod
    def is_gemini_available() -> bool:
        """Check if Gemini is available for use"""
        return GEMINI_AVAILABLE

    @staticmethod
    def get_installation_instructions() -> str:
        """Get instructions for installing Gemini dependency"""
        return "To enable AI analysis, install: pip install google-generativeai"

    @staticmethod
    def get_available_models() -> Dict[str, str]:
        """Get dictionary of available models for UI selection"""
        return RetirementAnalyzer.AVAILABLE_MODELS.copy()

    def _extract_usage_metadata(self, response) -> Optional[Dict[str, Any]]:
        """Extract usage metadata from Gemini response"""
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                return {
                    'prompt_tokens': getattr(usage, 'prompt_token_count', 0),
                    'completion_tokens': getattr(usage, 'candidates_token_count', 0),
                    'total_tokens': getattr(usage, 'total_token_count', 0),
                    'model': self.model_name,
                    'timestamp': np.datetime64('now')
                }
        except Exception as e:
            print(f"Warning: Could not extract usage metadata: {e}")
        return None

    def _track_usage(self, usage_info: Dict[str, Any]):
        """Track usage information in session state"""
        try:
            # Import here to avoid circular imports
            import streamlit as st

            # Initialize usage tracking if not exists
            if 'ai_usage_history' not in st.session_state:
                st.session_state.ai_usage_history = []

            # Add current usage
            st.session_state.ai_usage_history.append(usage_info)

            # Keep only last 50 entries to avoid memory bloat
            if len(st.session_state.ai_usage_history) > 50:
                st.session_state.ai_usage_history = st.session_state.ai_usage_history[-50:]

            # Calculate daily totals (approximate)
            from datetime import datetime, date
            today = date.today()

            today_usage = []
            for usage in st.session_state.ai_usage_history:
                if 'timestamp' in usage:
                    try:
                        # Convert numpy datetime64 to date for comparison
                        usage_timestamp = usage['timestamp']
                        if hasattr(usage_timestamp, 'astype'):
                            # It's a numpy datetime64
                            usage_date = usage_timestamp.astype('datetime64[D]').astype(date)
                        else:
                            # It might be a string or other format
                            usage_date = datetime.fromisoformat(str(usage_timestamp)).date()

                        if usage_date == today:
                            today_usage.append(usage)
                    except Exception:
                        continue  # Skip entries with invalid timestamps

            total_tokens_today = sum(usage.get('total_tokens', 0) for usage in today_usage)
            st.session_state.ai_tokens_used_today = total_tokens_today

        except Exception as e:
            print(f"Warning: Could not track usage: {e}")

    @staticmethod
    def get_usage_summary() -> Dict[str, Any]:
        """Get summary of AI usage for display"""
        try:
            import streamlit as st

            if 'ai_usage_history' not in st.session_state:
                return {'total_requests': 0, 'tokens_today': 0, 'models_used': []}

            history = st.session_state.ai_usage_history
            total_requests = len(history)
            tokens_today = st.session_state.get('ai_tokens_used_today', 0)
            models_used = list(set(usage.get('model', 'unknown') for usage in history))

            return {
                'total_requests': total_requests,
                'tokens_today': tokens_today,
                'models_used': models_used,
                'last_request_tokens': history[-1].get('total_tokens', 0) if history else 0
            }
        except Exception:
            return {'total_requests': 0, 'tokens_today': 0, 'models_used': []}


def create_mock_analysis(success_rate: float, error_type: str = None) -> RetirementAnalysis:
    """Create a mock analysis for testing when Gemini is not available"""

    if success_rate >= 0.9:
        assessment = "Plan shows excellent probability of success"
        risks = ["Market volatility in early retirement", "Inflation exceeding expectations"]
        recommendations = [
            {"category": "Allocation", "suggestion": "Consider slight increase in equity allocation for growth", "reasoning": "High success rate allows for more aggressive positioning"},
            {"category": "Spending", "suggestion": "Current spending levels appear sustainable", "reasoning": "Strong success metrics support current plan"}
        ]
        summary = "Your retirement plan demonstrates strong fundamentals with high success probability. Consider minor optimizations for enhanced growth."
        confidence = "High"
    elif success_rate >= 0.8:
        assessment = "Plan has good probability of success with room for improvement"
        risks = ["Extended market downturns", "Higher than expected healthcare costs", "Early sequence of returns risk"]
        recommendations = [
            {"category": "Guardrails", "suggestion": "Tighten lower guardrail from current level", "reasoning": "Earlier spending cuts can prevent plan failure"},
            {"category": "Allocation", "suggestion": "Increase bond allocation by 5-10%", "reasoning": "Reduced volatility improves success rates"},
            {"category": "Spending", "suggestion": "Reduce discretionary spending by 5-10%", "reasoning": "Lower withdrawal rate significantly improves outcomes"}
        ]
        summary = "Your plan has solid fundamentals but would benefit from more conservative adjustments to improve reliability."
        confidence = "Medium"
    else:
        assessment = "Plan needs significant improvements to achieve reliable success"
        risks = ["High withdrawal rates", "Insufficient portfolio size", "Extended market volatility", "Inflation risk"]
        recommendations = [
            {"category": "Spending", "suggestion": "Reduce annual spending by 15-20%", "reasoning": "Lower withdrawal rates are critical for plan viability"},
            {"category": "Guardrails", "suggestion": "Implement tighter guardrails with 20% spending cuts", "reasoning": "Aggressive adjustments needed to preserve capital"},
            {"category": "Allocation", "suggestion": "Shift to more conservative 50/40/10 equity/bonds/alternatives", "reasoning": "Reduced volatility essential for capital preservation"}
        ]
        summary = "Current plan has concerning success rates. Significant adjustments to spending and allocation are needed for viable retirement."
        confidence = "High"

    return RetirementAnalysis(
        success_assessment=assessment,
        key_risks=risks,
        recommendations=recommendations,
        summary=summary,
        confidence_level=confidence,
        error_message=APIError.get_user_message(error_type) if error_type else None
    )