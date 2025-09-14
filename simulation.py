"""
Monte Carlo retirement simulation engine with guardrails and tax-aware withdrawals.
Pure functions for simulation logic, decoupled from UI.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, NamedTuple, Any
from dataclasses import dataclass


@dataclass
class SimulationParams:
    """Parameters for Monte Carlo simulation"""
    start_year: int = 2026
    retirement_age: int = 65
    horizon_years: int = 50
    num_sims: int = 10_000
    random_seed: Optional[int] = None
    
    # Capital and allocation
    start_capital: float = 7_550_000
    w_equity: float = 0.6
    w_bonds: float = 0.2
    w_real_estate: float = 0.15
    w_cash: float = 0.05

    # Glide path (age-based allocation adjustment)
    glide_path_enabled: bool = False
    equity_reduction_per_year: float = 0.005  # 0.5% per year default
    
    # Return model (annual, real)
    equity_mean: float = 0.05
    equity_vol: float = 0.18
    bonds_mean: float = 0.015
    bonds_vol: float = 0.07
    real_estate_mean: float = 0.01
    real_estate_vol: float = 0.10
    cash_mean: float = 0.0
    cash_vol: float = 0.0001
    
    # Initial spending configuration
    cape_now: float = 38.5  # CAPE ratio for calculation
    initial_base_spending: Optional[float] = None  # Override CAPE-based calculation for year 1 only
    fixed_annual_spending: Optional[float] = None  # Fixed spending every year (overrides guardrails)
    
    # Guardrails (Guyton-Klinger style)
    lower_wr: float = 0.028
    upper_wr: float = 0.045
    adjustment_pct: float = 0.10
    
    # Spending bounds
    spending_floor_real: float = 160_000
    spending_ceiling_real: float = 275_000
    floor_end_year: int = 2041
    
    # College expenses
    college_enabled: bool = True
    college_base_amount: float = 100_000
    college_start_year: int = 2032
    college_end_year: int = 2041
    college_growth_real: float = 0.013
    
    # Expense streams (replaces hardcoded onetime_2033/onetime_2040)
    expense_streams: List[Dict[str, Any]] = None
    
    # Real estate cash flow configuration
    re_flow_enabled: bool = True
    re_flow_preset: str = "ramp"  # "ramp", "delayed", or "custom"
    
    # Custom real estate parameters (used when preset = "custom")
    re_flow_start_year: int = 2026  # When RE income begins
    re_flow_year1_amount: float = 50_000  # First year amount
    re_flow_year2_amount: float = 60_000  # Second year amount  
    re_flow_steady_amount: float = 75_000  # Ongoing amount after ramp-up
    re_flow_delay_years: int = 0  # Years to delay before starting
    
    # Inheritance
    inherit_amount: float = 1_500_000
    inherit_year: int = 2040
    
    # Other income (net of tax)
    other_income_amount: float = 0.0
    other_income_start_year: int = 2026
    other_income_years: int = 0

    # Multiple income streams (replaces single income stream when provided)
    income_streams: List[Dict[str, Any]] = None
    
    # Tax parameters
    filing_status: str = "MFJ"  # "MFJ" or "Single"
    standard_deduction: float = 29_200
    tax_brackets: List[Tuple[float, float]] = None

    # Social Security parameters
    social_security_enabled: bool = True
    ss_annual_benefit: float = 40_000  # Annual benefit at full retirement age
    ss_start_age: int = 67  # Age to start benefits (62-70)
    ss_benefit_scenario: str = "moderate"  # conservative, moderate, optimistic, custom
    ss_custom_reduction: float = 0.10  # Custom reduction percentage (for custom scenario)
    ss_reduction_start_year: int = 2034  # Year when benefit cuts begin

    # Spousal Social Security parameters
    spouse_ss_enabled: bool = False
    spouse_ss_annual_benefit: float = 30_000  # Spouse's annual benefit
    spouse_ss_start_age: int = 67  # Spouse's start age
    
    # Market regime - enhanced controls
    regime: str = "baseline"  
    # Regime options: "baseline", "recession_recover", "grind_lower", "late_recession", 
    # "inflation_shock", "long_bear", "tech_bubble", "custom"
    
    # Custom regime parameters (used when regime = "custom")
    custom_equity_shock_year: int = 0  # Year of equity shock (0-based)
    custom_equity_shock_return: float = -0.20  # Return in shock year
    custom_shock_duration: int = 1  # Number of years for shock
    custom_recovery_years: int = 2  # Years of below-normal returns after shock
    custom_recovery_equity_return: float = 0.02  # Equity return during recovery

    def __post_init__(self):
        if self.tax_brackets is None:
            if self.filing_status == "MFJ":
                self.tax_brackets = [(0, 0.10), (94_300, 0.22), (201_000, 0.24)]
            else:  # Single
                self.tax_brackets = [(0, 0.10), (47_150, 0.22), (100_500, 0.24)]
        
        if self.expense_streams is None:
            self.expense_streams = []


@dataclass
class SimulationResults:
    """Results from Monte Carlo simulation"""
    terminal_wealth: np.ndarray
    wealth_paths: np.ndarray
    guardrail_hits: np.ndarray
    years_depleted: np.ndarray
    success_rate: float
    median_path_details: Dict
    p10_path_details: Dict
    p90_path_details: Dict


class RetirementSimulator:
    """Monte Carlo retirement simulation with tax-aware withdrawals"""
    
    def __init__(self, params: SimulationParams):
        self.params = params
        self._validate_params()
    
    def _validate_params(self):
        """Validate simulation parameters"""
        weights = [self.params.w_equity, self.params.w_bonds, 
                  self.params.w_real_estate, self.params.w_cash]
        if abs(sum(weights) - 1.0) > 1e-6:
            raise ValueError(f"Allocation weights must sum to 1.0, got {sum(weights):.6f}")
    
    def _get_base_withdrawal_rate(self) -> float:
        """Calculate CAPE-based initial withdrawal rate"""
        return 0.0175 + 0.5 * (1.0 / self.params.cape_now)
    
    def _get_re_income(self, year: int) -> float:
        """Get real estate income for given year (real dollars)"""
        if not self.params.re_flow_enabled:
            return 0
            
        year_offset = year - self.params.start_year
        
        if self.params.re_flow_preset == "ramp":
            if year_offset == 0:
                return 50_000
            elif year_offset == 1:
                return 60_000
            elif year_offset >= 2:
                return 75_000
            else:
                return 0
        elif self.params.re_flow_preset == "delayed":
            if year_offset <= 4:  # Through 2030
                return 0
            elif year_offset == 5:  # 2031
                return 50_000
            elif year_offset == 6:  # 2032
                return 60_000
            elif year_offset >= 7:  # 2033+
                return 75_000
            else:
                return 0
        elif self.params.re_flow_preset == "custom":
            # Use custom parameters
            effective_start_year = self.params.re_flow_start_year + self.params.re_flow_delay_years
            years_since_start = year - effective_start_year
            
            if years_since_start < 0:
                return 0
            elif years_since_start == 0:
                return self.params.re_flow_year1_amount
            elif years_since_start == 1:
                return self.params.re_flow_year2_amount
            elif years_since_start >= 2:
                return self.params.re_flow_steady_amount
            else:
                return 0
        else:
            return 0
    
    def _get_college_topup(self, year: int) -> float:
        """Get college top-up for given year (real dollars)"""
        if not self.params.college_enabled:
            return 0
        
        if self.params.college_start_year <= year <= self.params.college_end_year:
            years_since_start = year - self.params.college_start_year
            return self.params.college_base_amount * (1 + self.params.college_growth_real) ** years_since_start
        return 0
    
    def _get_onetime_expense(self, year: int) -> float:
        """Get expense stream total for given year (real dollars)"""
        total = 0
        for stream in self.params.expense_streams:
            start_year = stream.get('start_year', stream.get('year', 0))
            years = stream.get('years', 1)
            if start_year <= year < start_year + years:
                total += stream.get('amount', 0)
        return total
    
    def _get_other_income(self, year: int) -> float:
        """Get other income for given year (real dollars, net of tax)"""
        # Use multiple income streams if provided, otherwise fall back to single stream
        if self.params.income_streams is not None and len(self.params.income_streams) > 0:
            total_income = 0.0
            for stream in self.params.income_streams:
                stream_start = stream['start_year']
                stream_years = stream['years']
                stream_amount = stream['amount']

                # Check if this year falls within this stream's duration
                year_offset = year - stream_start
                if 0 <= year_offset < stream_years:
                    total_income += stream_amount

            return total_income
        else:
            # Legacy single stream logic
            if self.params.other_income_years == 0:
                return 0

            year_offset = year - self.params.other_income_start_year
            if 0 <= year_offset < self.params.other_income_years:
                return self.params.other_income_amount
            return 0

    def _get_social_security_income(self, year: int) -> float:
        """Get Social Security income for given year (real dollars, net of tax)"""
        total_ss_income = 0

        # Primary Social Security
        if self.params.social_security_enabled:
            from tax_utils import calculate_social_security_benefit
            total_ss_income += calculate_social_security_benefit(
                year=year,
                start_year=self.params.start_year,
                retirement_age=self.params.retirement_age,
                annual_benefit=self.params.ss_annual_benefit,
                scenario=self.params.ss_benefit_scenario,
                custom_reduction=self.params.ss_custom_reduction,
                reduction_start_year=self.params.ss_reduction_start_year,
                start_age=self.params.ss_start_age
            )

        # Spousal Social Security
        if self.params.spouse_ss_enabled:
            from tax_utils import calculate_social_security_benefit
            total_ss_income += calculate_social_security_benefit(
                year=year,
                start_year=self.params.start_year,
                retirement_age=self.params.retirement_age,
                annual_benefit=self.params.spouse_ss_annual_benefit,
                scenario=self.params.ss_benefit_scenario,  # Use same scenario
                custom_reduction=self.params.ss_custom_reduction,  # Use same reduction
                reduction_start_year=self.params.ss_reduction_start_year,
                start_age=self.params.spouse_ss_start_age
            )

        return total_ss_income
    
    def _apply_spending_guardrails(self, current_base_spend: float, 
                                 portfolio_value: float) -> Tuple[float, str]:
        """Apply Guyton-Klinger guardrails to spending"""
        current_wr = current_base_spend / portfolio_value if portfolio_value > 0 else 0
        
        if current_wr > self.params.upper_wr:
            new_spend = current_base_spend * (1 - self.params.adjustment_pct)
            return new_spend, "down"
        elif current_wr < self.params.lower_wr:
            new_spend = current_base_spend * (1 + self.params.adjustment_pct)
            return new_spend, "up"
        else:
            return current_base_spend, "none"
    
    def _apply_spending_bounds(self, spending: float, year: int) -> Tuple[float, bool, bool]:
        """Apply floor and ceiling to spending"""
        floor_applied = False
        ceiling_applied = False
        
        # Apply floor only until floor_end_year
        if year <= self.params.floor_end_year:
            if spending < self.params.spending_floor_real:
                spending = self.params.spending_floor_real
                floor_applied = True
        
        # Apply ceiling always
        if spending > self.params.spending_ceiling_real:
            spending = self.params.spending_ceiling_real
            ceiling_applied = True
        
        return spending, floor_applied, ceiling_applied
    
    def _get_allocation_weights(self, year_offset: int) -> Tuple[float, float, float, float]:
        """Get asset allocation weights for given year, applying glide path if enabled"""
        if not self.params.glide_path_enabled:
            # Static allocation - use original weights
            return (self.params.w_equity, self.params.w_bonds,
                   self.params.w_real_estate, self.params.w_cash)

        # Calculate glide path adjustment
        equity_reduction = self.params.equity_reduction_per_year * year_offset
        adjusted_equity = max(0.1, self.params.w_equity - equity_reduction)  # Minimum 10% equity

        # Distribute reduced equity proportionally to other assets
        reduction_amount = self.params.w_equity - adjusted_equity

        # Original non-equity weights
        orig_non_equity = self.params.w_bonds + self.params.w_real_estate + self.params.w_cash

        if orig_non_equity > 0:
            # Distribute proportionally
            bonds_share = self.params.w_bonds / orig_non_equity
            re_share = self.params.w_real_estate / orig_non_equity
            cash_share = self.params.w_cash / orig_non_equity

            adjusted_bonds = self.params.w_bonds + (reduction_amount * bonds_share)
            adjusted_re = self.params.w_real_estate + (reduction_amount * re_share)
            adjusted_cash = self.params.w_cash + (reduction_amount * cash_share)
        else:
            # Fallback: add all to bonds
            adjusted_bonds = self.params.w_bonds + reduction_amount
            adjusted_re = self.params.w_real_estate
            adjusted_cash = self.params.w_cash

        return (adjusted_equity, adjusted_bonds, adjusted_re, adjusted_cash)

    def _get_return_means(self, year_offset: int) -> Tuple[float, float, float, float]:
        """Get return means based on regime"""
        base_returns = (self.params.equity_mean, self.params.bonds_mean, 
                       self.params.real_estate_mean, self.params.cash_mean)
        
        if self.params.regime == "recession_recover":
            # Early recession: -15% (Yr0), 0% (Yr1), then baseline
            if year_offset == 0:
                return -0.15, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
            elif year_offset == 1:
                return 0.00, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
            else:
                return base_returns
                
        elif self.params.regime == "grind_lower":
            # Low returns first 10 years: 0.5% equity, 1% bonds, 0.5% RE
            if year_offset < 10:
                return 0.005, 0.01, 0.005, self.params.cash_mean
            else:
                return base_returns
                
        elif self.params.regime == "late_recession":
            # Recession in years 10-12
            if 10 <= year_offset <= 12:
                if year_offset == 10:
                    return -0.20, self.params.bonds_mean, -0.05, self.params.cash_mean
                elif year_offset == 11:
                    return -0.05, self.params.bonds_mean, 0.00, self.params.cash_mean
                else:  # year 12
                    return 0.15, self.params.bonds_mean, 0.05, self.params.cash_mean  # Recovery bounce
            else:
                return base_returns
                
        elif self.params.regime == "inflation_shock":
            # High inflation years 3-7: Poor equity/bonds, good RE
            if 3 <= year_offset <= 7:
                return 0.01, -0.02, 0.08, 0.01  # Bonds hurt by inflation, RE benefits
            else:
                return base_returns
                
        elif self.params.regime == "long_bear":
            # Extended bear market years 5-15
            if 5 <= year_offset <= 15:
                return 0.02, 0.025, 0.015, self.params.cash_mean
            else:
                return base_returns
                
        elif self.params.regime == "tech_bubble":
            # Tech bubble: High early returns, then crash
            if year_offset <= 3:
                return self.params.equity_mean * 1.5, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
            elif 4 <= year_offset <= 6:
                return -0.10, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean  # Crash
            else:
                return base_returns
                
        elif self.params.regime == "custom":
            # User-defined shock pattern
            shock_start = self.params.custom_equity_shock_year
            shock_end = shock_start + self.params.custom_shock_duration - 1
            recovery_end = shock_end + self.params.custom_recovery_years
            
            if shock_start <= year_offset <= shock_end:
                return (self.params.custom_equity_shock_return, self.params.bonds_mean, 
                       self.params.real_estate_mean, self.params.cash_mean)
            elif shock_end < year_offset <= recovery_end:
                return (self.params.custom_recovery_equity_return, self.params.bonds_mean,
                       self.params.real_estate_mean, self.params.cash_mean)
            else:
                return base_returns
                
        else:  # baseline
            return base_returns
    
    def run_simulation(self) -> SimulationResults:
        """Run Monte Carlo simulation"""
        from tax import calculate_tax, solve_gross_withdrawal
        
        if self.params.random_seed is not None:
            np.random.seed(self.params.random_seed)
        
        # Initialize arrays
        terminal_wealth = np.zeros(self.params.num_sims)
        wealth_paths = np.zeros((self.params.num_sims, self.params.horizon_years + 1))
        guardrail_hits = np.zeros(self.params.num_sims)
        years_depleted = np.full(self.params.num_sims, -1)  # -1 means no depletion
        
        # Initialize path tracking for all simulations
        all_path_details = []
        for sim in range(self.params.num_sims):
            path_details = {
                'years': [],
                'start_assets': [],
                'base_spending': [],
                'floor_applied': [],
                'ceiling_applied': [],
                'guardrail_action': [],
                'adjusted_base_spending': [],
                'college_topup': [],
                'one_times': [],
                're_income': [],
                'other_income': [],
                'ss_income': [],
                'taxable_income': [],
                'taxes': [],
                'net_need': [],
                'gross_withdrawal': [],
                'growth': [],
                'inheritance': [],
                'end_assets': [],
                'withdrawal_rate': [],
                'equity_allocation': [],
                'bonds_allocation': [],
                'real_estate_allocation': [],
                'cash_allocation': []
            }
            all_path_details.append(path_details)
        
        # Initial base spending - priority: fixed > manual > CAPE
        if self.params.fixed_annual_spending is not None:
            initial_base_spend = self.params.fixed_annual_spending
        elif self.params.initial_base_spending is not None:
            initial_base_spend = self.params.initial_base_spending
        else:
            initial_base_spend = self._get_base_withdrawal_rate() * self.params.start_capital
        
        for sim in range(self.params.num_sims):
            portfolio_value = self.params.start_capital
            current_base_spend = initial_base_spend
            sim_guardrail_hits = 0
            
            # Store initial wealth
            wealth_paths[sim, 0] = portfolio_value
            
            for year_idx in range(self.params.horizon_years):
                current_year = self.params.start_year + year_idx
                
                # Apply guardrails to base spending (unless fixed spending mode)
                if self.params.fixed_annual_spending is not None:
                    # Fixed spending mode - no guardrails, same amount every year
                    adjusted_base_spend = self.params.fixed_annual_spending
                    guardrail_action = "none"
                else:
                    # Dynamic spending mode - apply guardrails
                    adjusted_base_spend, guardrail_action = self._apply_spending_guardrails(
                        current_base_spend, portfolio_value)
                    if guardrail_action != "none":
                        sim_guardrail_hits += 1
                        current_base_spend = adjusted_base_spend
                
                # Apply floor and ceiling (unless fixed spending mode)
                if self.params.fixed_annual_spending is not None:
                    # Fixed spending mode - no bounds applied
                    final_base_spend = adjusted_base_spend
                    floor_applied = False
                    ceiling_applied = False
                else:
                    # Dynamic spending mode - apply bounds
                    final_base_spend, floor_applied, ceiling_applied = self._apply_spending_bounds(
                        adjusted_base_spend, current_year)
                
                # Add other spending components
                college_topup = self._get_college_topup(current_year)
                one_times = self._get_onetime_expense(current_year)
                total_spending_need = final_base_spend + college_topup + one_times
                
                # Subtract non-portfolio income
                re_income = self._get_re_income(current_year)
                other_income = self._get_other_income(current_year)
                ss_income = self._get_social_security_income(current_year)
                net_need = total_spending_need - re_income - other_income - ss_income
                
                # Calculate gross withdrawal with taxes
                gross_withdrawal, taxes = solve_gross_withdrawal(
                    net_need, 
                    other_taxable_income=0,  # Simplified: other_income is net-of-tax
                    standard_deduction=self.params.standard_deduction,
                    tax_brackets=self.params.tax_brackets
                )
                
                # Generate returns
                year_offset = year_idx
                eq_mean, bond_mean, re_mean, cash_mean = self._get_return_means(year_offset)

                returns = np.array([
                    np.random.normal(eq_mean, self.params.equity_vol),
                    np.random.normal(bond_mean, self.params.bonds_vol),
                    np.random.normal(re_mean, self.params.real_estate_vol),
                    np.random.normal(cash_mean, self.params.cash_vol)
                ])

                # Get dynamic allocation weights (includes glide path logic)
                w_eq, w_bonds, w_re, w_cash = self._get_allocation_weights(year_offset)
                weights = np.array([w_eq, w_bonds, w_re, w_cash])
                portfolio_return = np.sum(weights * returns)
                
                # Apply returns
                portfolio_value *= (1 + portfolio_return)
                
                # Add inheritance
                inheritance = 0
                if current_year == self.params.inherit_year:
                    inheritance = self.params.inherit_amount
                    portfolio_value += inheritance
                
                # Withdraw
                portfolio_value = max(0, portfolio_value - gross_withdrawal)
                
                # Check for depletion
                if portfolio_value <= 0 and years_depleted[sim] == -1:
                    years_depleted[sim] = year_idx + 1
                
                # Store wealth path
                wealth_paths[sim, year_idx + 1] = portfolio_value
                
                # Store path details for all simulations
                withdrawal_rate = gross_withdrawal / wealth_paths[sim, year_idx] if wealth_paths[sim, year_idx] > 0 else 0

                current_details = all_path_details[sim]
                current_details['years'].append(current_year)
                current_details['start_assets'].append(wealth_paths[sim, year_idx])
                current_details['base_spending'].append(adjusted_base_spend)
                current_details['floor_applied'].append(floor_applied)
                current_details['ceiling_applied'].append(ceiling_applied)
                current_details['guardrail_action'].append(guardrail_action)
                current_details['adjusted_base_spending'].append(final_base_spend)
                current_details['college_topup'].append(college_topup)
                current_details['one_times'].append(one_times)
                current_details['re_income'].append(re_income)
                current_details['other_income'].append(other_income)
                current_details['ss_income'].append(ss_income)
                current_details['equity_allocation'].append(w_eq)
                current_details['bonds_allocation'].append(w_bonds)
                current_details['real_estate_allocation'].append(w_re)
                current_details['cash_allocation'].append(w_cash)
                current_details['taxable_income'].append(max(0, gross_withdrawal - self.params.standard_deduction))
                current_details['taxes'].append(taxes)
                current_details['net_need'].append(net_need)
                current_details['gross_withdrawal'].append(gross_withdrawal)
                current_details['growth'].append(portfolio_return * wealth_paths[sim, year_idx])
                current_details['inheritance'].append(inheritance)
                current_details['end_assets'].append(portfolio_value)
                current_details['withdrawal_rate'].append(withdrawal_rate)
            
            # Store final results
            terminal_wealth[sim] = portfolio_value
            guardrail_hits[sim] = sim_guardrail_hits
        
        # Calculate success rate (non-depletion)
        success_rate = np.mean(years_depleted == -1)

        # Find which simulations correspond to P10, P50, and P90 terminal wealth
        terminal_wealth_sorted_indices = np.argsort(terminal_wealth)

        # Get simulation indices for percentiles
        p10_idx = terminal_wealth_sorted_indices[int(0.10 * self.params.num_sims)]
        p50_idx = terminal_wealth_sorted_indices[int(0.50 * self.params.num_sims)]
        p90_idx = terminal_wealth_sorted_indices[int(0.90 * self.params.num_sims)]

        # Extract the detailed paths for these percentile simulations
        median_path_details = all_path_details[p50_idx]
        p10_path_details = all_path_details[p10_idx]
        p90_path_details = all_path_details[p90_idx]

        return SimulationResults(
            terminal_wealth=terminal_wealth,
            wealth_paths=wealth_paths,
            guardrail_hits=guardrail_hits,
            years_depleted=years_depleted,
            success_rate=success_rate,
            median_path_details=median_path_details,
            p10_path_details=p10_path_details,
            p90_path_details=p90_path_details
        )


def calculate_percentiles(wealth_paths: np.ndarray) -> Dict[str, np.ndarray]:
    """Calculate wealth percentile bands over time"""
    p10 = np.percentile(wealth_paths, 10, axis=0)
    p50 = np.percentile(wealth_paths, 50, axis=0)
    p90 = np.percentile(wealth_paths, 90, axis=0)
    
    return {
        'p10': p10,
        'p50': p50,
        'p90': p90
    }


def calculate_summary_stats(terminal_wealth: np.ndarray) -> Dict[str, float]:
    """Calculate summary statistics for terminal wealth"""
    return {
        'mean': np.mean(terminal_wealth),
        'p10': np.percentile(terminal_wealth, 10),
        'p50': np.percentile(terminal_wealth, 50),
        'p90': np.percentile(terminal_wealth, 90),
        'prob_below_5m': np.mean(terminal_wealth < 5_000_000),
        'prob_below_10m': np.mean(terminal_wealth < 10_000_000),
        'prob_below_15m': np.mean(terminal_wealth < 15_000_000)
    }