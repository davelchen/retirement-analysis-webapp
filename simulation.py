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
    horizon_years: int = 50
    num_sims: int = 10_000
    random_seed: Optional[int] = None
    
    # Capital and allocation
    start_capital: float = 7_550_000
    w_equity: float = 0.6
    w_bonds: float = 0.2
    w_real_estate: float = 0.15
    w_cash: float = 0.05
    
    # Return model (annual, real)
    equity_mean: float = 0.05
    equity_vol: float = 0.18
    bonds_mean: float = 0.015
    bonds_vol: float = 0.07
    real_estate_mean: float = 0.01
    real_estate_vol: float = 0.10
    cash_mean: float = 0.0
    cash_vol: float = 0.0001
    
    # CAPE-based initial spending
    cape_now: float = 38.5
    
    # Guardrails (Guyton-Klinger style)
    lower_wr: float = 0.028
    upper_wr: float = 0.045
    adjustment_pct: float = 0.10
    
    # Spending bounds
    spending_floor_real: float = 160_000
    spending_ceiling_real: float = 275_000
    floor_end_year: int = 2041
    
    # College expenses
    college_growth_real: float = 0.013
    
    # Expense streams (replaces hardcoded onetime_2033/onetime_2040)
    expense_streams: List[Dict[str, Any]] = None
    
    # Real estate cash flow preset
    re_flow_preset: str = "ramp"  # "ramp" or "delayed"
    
    # Inheritance
    inherit_amount: float = 1_500_000
    inherit_year: int = 2040
    
    # Other income (net of tax)
    other_income_amount: float = 0.0
    other_income_start_year: int = 2026
    other_income_years: int = 0
    
    # Tax parameters
    filing_status: str = "MFJ"  # "MFJ" or "Single"
    standard_deduction: float = 29_200
    tax_brackets: List[Tuple[float, float]] = None
    
    # Regime
    regime: str = "baseline"  # "baseline", "recession_recover", "grind_lower"

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
        else:
            return 0
    
    def _get_college_topup(self, year: int) -> float:
        """Get college top-up for given year (real dollars)"""
        if 2032 <= year <= 2041:
            years_since_2032 = year - 2032
            return 100_000 * (1 + self.params.college_growth_real) ** years_since_2032
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
        if self.params.other_income_years == 0:
            return 0
        
        year_offset = year - self.params.other_income_start_year
        if 0 <= year_offset < self.params.other_income_years:
            return self.params.other_income_amount
        return 0
    
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
    
    def _get_return_means(self, year_offset: int) -> Tuple[float, float, float, float]:
        """Get return means based on regime"""
        if self.params.regime == "recession_recover":
            if year_offset == 0:
                return -0.15, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
            elif year_offset == 1:
                return 0.00, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
            else:
                return self.params.equity_mean, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
        elif self.params.regime == "grind_lower":
            if year_offset < 10:
                return 0.005, 0.01, 0.005, self.params.cash_mean
            else:
                return self.params.equity_mean, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
        else:  # baseline
            return self.params.equity_mean, self.params.bonds_mean, self.params.real_estate_mean, self.params.cash_mean
    
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
        
        # Track median path details for the year-by-year table
        median_sim_idx = self.params.num_sims // 2
        median_details = {
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
            'taxable_income': [],
            'taxes': [],
            'net_need': [],
            'gross_withdrawal': [],
            'growth': [],
            'inheritance': [],
            'end_assets': [],
            'withdrawal_rate': []
        }
        
        # Initial base spending from CAPE rule
        initial_base_spend = self._get_base_withdrawal_rate() * self.params.start_capital
        
        for sim in range(self.params.num_sims):
            portfolio_value = self.params.start_capital
            current_base_spend = initial_base_spend
            sim_guardrail_hits = 0
            
            # Store initial wealth
            wealth_paths[sim, 0] = portfolio_value
            
            for year_idx in range(self.params.horizon_years):
                current_year = self.params.start_year + year_idx
                
                # Apply guardrails to base spending
                adjusted_base_spend, guardrail_action = self._apply_spending_guardrails(
                    current_base_spend, portfolio_value)
                if guardrail_action != "none":
                    sim_guardrail_hits += 1
                    current_base_spend = adjusted_base_spend
                
                # Apply floor and ceiling
                final_base_spend, floor_applied, ceiling_applied = self._apply_spending_bounds(
                    adjusted_base_spend, current_year)
                
                # Add other spending components
                college_topup = self._get_college_topup(current_year)
                one_times = self._get_onetime_expense(current_year)
                total_spending_need = final_base_spend + college_topup + one_times
                
                # Subtract non-portfolio income
                re_income = self._get_re_income(current_year)
                other_income = self._get_other_income(current_year)
                net_need = total_spending_need - re_income - other_income
                
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
                
                weights = np.array([self.params.w_equity, self.params.w_bonds, 
                                  self.params.w_real_estate, self.params.w_cash])
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
                
                # Store median path details
                if sim == median_sim_idx:
                    withdrawal_rate = gross_withdrawal / wealth_paths[sim, year_idx] if wealth_paths[sim, year_idx] > 0 else 0
                    
                    median_details['years'].append(current_year)
                    median_details['start_assets'].append(wealth_paths[sim, year_idx])
                    median_details['base_spending'].append(adjusted_base_spend)
                    median_details['floor_applied'].append(floor_applied)
                    median_details['ceiling_applied'].append(ceiling_applied)
                    median_details['guardrail_action'].append(guardrail_action)
                    median_details['adjusted_base_spending'].append(final_base_spend)
                    median_details['college_topup'].append(college_topup)
                    median_details['one_times'].append(one_times)
                    median_details['re_income'].append(re_income)
                    median_details['other_income'].append(other_income)
                    median_details['taxable_income'].append(max(0, gross_withdrawal - self.params.standard_deduction))
                    median_details['taxes'].append(taxes)
                    median_details['net_need'].append(net_need)
                    median_details['gross_withdrawal'].append(gross_withdrawal)
                    median_details['growth'].append(portfolio_return * wealth_paths[sim, year_idx])
                    median_details['inheritance'].append(inheritance)
                    median_details['end_assets'].append(portfolio_value)
                    median_details['withdrawal_rate'].append(withdrawal_rate)
            
            # Store final results
            terminal_wealth[sim] = portfolio_value
            guardrail_hits[sim] = sim_guardrail_hits
        
        # Calculate success rate (non-depletion)
        success_rate = np.mean(years_depleted == -1)
        
        return SimulationResults(
            terminal_wealth=terminal_wealth,
            wealth_paths=wealth_paths,
            guardrail_hits=guardrail_hits,
            years_depleted=years_depleted,
            success_rate=success_rate,
            median_path_details=median_details
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