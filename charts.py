"""
Plotly chart builders for retirement simulation visualizations.
Creates interactive charts for wealth distributions, percentile bands, and comparisons.
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


def create_terminal_wealth_distribution(terminal_wealth: np.ndarray,
                                      title: str = "Terminal Wealth Distribution",
                                      currency_format: str = "real") -> go.Figure:
    """
    Create histogram showing distribution of terminal wealth outcomes.
    
    Args:
        terminal_wealth: Array of terminal wealth values from simulation
        title: Chart title
        currency_format: "real" or "nominal" for axis labels
        
    Returns:
        Plotly figure
    """
    # Convert to millions for readability
    wealth_millions = terminal_wealth / 1_000_000
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=wealth_millions,
        nbinsx=50,
        name="Terminal Wealth",
        hovertemplate="<b>Wealth Range:</b> $%{x:.1f}M - $%{x:.1f}M<br>" +
                     "<b>Number of Simulations:</b> %{y}<br>" +
                     "<extra></extra>",
        marker=dict(color='lightblue', line=dict(color='darkblue', width=1))
    ))
    
    # Add percentile lines
    p10 = np.percentile(wealth_millions, 10)
    p50 = np.percentile(wealth_millions, 50)
    p90 = np.percentile(wealth_millions, 90)
    
    fig.add_vline(x=p10, line_dash="dash", line_color="red", 
                 annotation_text=f"P10: ${p10:.1f}M")
    fig.add_vline(x=p50, line_dash="dash", line_color="green", 
                 annotation_text=f"P50: ${p50:.1f}M")
    fig.add_vline(x=p90, line_dash="dash", line_color="blue", 
                 annotation_text=f"P90: ${p90:.1f}M")
    
    # Format axes
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=f"{title} ({currency_label} Dollars)",
        xaxis_title=f"Terminal Wealth (${currency_label} Millions)",
        yaxis_title="Number of Simulations",
        showlegend=False,
        template="plotly_white",
        hovermode="x unified"
    )
    
    return fig


def create_wealth_percentile_bands(years: np.ndarray,
                                 percentiles: Dict[str, np.ndarray],
                                 title: str = "Wealth Path Percentile Bands",
                                 currency_format: str = "real") -> go.Figure:
    """
    Create filled area chart showing P10/P50/P90 wealth bands over time.
    
    Args:
        years: Array of years
        percentiles: Dictionary with 'p10', 'p50', 'p90' arrays
        title: Chart title
        currency_format: "real" or "nominal" for axis labels
        
    Returns:
        Plotly figure
    """
    # Convert to millions for readability
    p10_millions = percentiles['p10'] / 1_000_000
    p50_millions = percentiles['p50'] / 1_000_000
    p90_millions = percentiles['p90'] / 1_000_000
    
    fig = go.Figure()
    
    # Add filled areas
    fig.add_trace(go.Scatter(
        x=years, y=p90_millions,
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=years, y=p10_millions,
        fill='tonexty',
        mode='lines',
        line=dict(color='lightblue'),
        name='P10-P90 Range',
        fillcolor='rgba(173,216,230,0.3)',
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>P10-P90 Range:</b> $%{y:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    fig.add_trace(go.Scatter(
        x=years, y=p50_millions,
        mode='lines',
        line=dict(color='darkblue', width=3),
        name='P50 (Median)',
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>Median Wealth:</b> $%{y:.1f}M<br>" +
                     "<extra></extra>"
    ))
    
    # Format axes
    currency_label = "Real" if currency_format == "real" else "Nominal"
    fig.update_layout(
        title=f"{title} ({currency_label} Dollars)",
        xaxis_title="Year",
        yaxis_title=f"Wealth (${currency_label} Millions)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def create_comparison_chart(scenarios: Dict[str, np.ndarray],
                           chart_type: str = "terminal_wealth",
                           title: str = "Scenario Comparison") -> go.Figure:
    """
    Create comparison chart for multiple scenarios.
    
    Args:
        scenarios: Dictionary mapping scenario names to terminal wealth arrays
        chart_type: "terminal_wealth" or "success_rate"
        title: Chart title
        
    Returns:
        Plotly figure
    """
    if chart_type == "terminal_wealth":
        return _create_terminal_wealth_comparison(scenarios, title)
    elif chart_type == "success_rate":
        return _create_success_rate_comparison(scenarios, title)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


def _create_terminal_wealth_comparison(scenarios: Dict[str, np.ndarray],
                                     title: str) -> go.Figure:
    """Create overlaid histograms comparing terminal wealth distributions"""
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    
    for i, (scenario_name, terminal_wealth) in enumerate(scenarios.items()):
        wealth_millions = terminal_wealth / 1_000_000
        
        fig.add_trace(go.Histogram(
            x=wealth_millions,
            name=scenario_name,
            opacity=0.7,
            nbinsx=40,
            marker_color=colors[i % len(colors)],
            hovertemplate=f"<b>{scenario_name}</b><br>" +
                         "<b>Wealth Range:</b> $%{x:.1f}M<br>" +
                         "<b>Count:</b> %{y}<br>" +
                         "<extra></extra>"
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Terminal Wealth ($ Millions)",
        yaxis_title="Number of Simulations",
        template="plotly_white",
        barmode='overlay',
        hovermode="x unified"
    )
    
    return fig


def _create_success_rate_comparison(scenarios: Dict[str, np.ndarray],
                                   title: str) -> go.Figure:
    """Create bar chart comparing success rates across scenarios"""
    scenario_names = list(scenarios.keys())
    success_rates = []
    
    for terminal_wealth in scenarios.values():
        # Success = non-depletion (wealth > 0)
        success_rate = np.mean(terminal_wealth > 0) * 100
        success_rates.append(success_rate)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=scenario_names,
        y=success_rates,
        marker_color='lightblue',
        marker_line_color='darkblue',
        marker_line_width=1,
        hovertemplate="<b>%{x}</b><br>" +
                     "<b>Success Rate:</b> %{y:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Scenario",
        yaxis_title="Success Rate (%)",
        template="plotly_white",
        showlegend=False
    )
    
    # Add percentage labels on bars
    for i, rate in enumerate(success_rates):
        fig.add_annotation(
            x=i,
            y=rate + 1,
            text=f"{rate:.1f}%",
            showarrow=False,
            font=dict(size=12)
        )
    
    return fig


def create_spending_chart(years: np.ndarray,
                         spending_components: Dict[str, np.ndarray],
                         title: str = "Annual Spending Breakdown") -> go.Figure:
    """
    Create stacked area chart showing spending components over time.
    
    Args:
        years: Array of years
        spending_components: Dict with component names and values
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Define component order and colors
    component_order = ['Base Spending', 'College Top-Up', 'One-Time Expenses']
    colors = ['lightblue', 'lightgreen', 'lightcoral']
    
    for i, component in enumerate(component_order):
        if component in spending_components:
            values = spending_components[component] / 1000  # Convert to thousands
            
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                stackgroup='one',
                name=component,
                line=dict(width=0.5),
                fillcolor=colors[i % len(colors)],
                hovertemplate=f"<b>{component}</b><br>" +
                             "<b>Year:</b> %{x}<br>" +
                             "<b>Amount:</b> $%{y:.0f}K<br>" +
                             "<extra></extra>"
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Annual Spending ($000s)",
        template="plotly_white",
        hovermode="x unified"
    )
    
    return fig


def create_withdrawal_rate_chart(years: np.ndarray,
                                withdrawal_rates: np.ndarray,
                                guardrail_lower: float = 0.028,
                                guardrail_upper: float = 0.045,
                                title: str = "Withdrawal Rate Over Time") -> go.Figure:
    """
    Create line chart showing withdrawal rates with guardrail bands.
    
    Args:
        years: Array of years
        withdrawal_rates: Array of withdrawal rates (as decimals)
        guardrail_lower: Lower guardrail threshold
        guardrail_upper: Upper guardrail threshold
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Convert to percentages
    wr_pct = withdrawal_rates * 100
    lower_pct = guardrail_lower * 100
    upper_pct = guardrail_upper * 100
    
    # Add withdrawal rate line
    fig.add_trace(go.Scatter(
        x=years,
        y=wr_pct,
        mode='lines+markers',
        name='Withdrawal Rate',
        line=dict(color='darkblue', width=2),
        marker=dict(size=4),
        hovertemplate="<b>Year:</b> %{x}<br>" +
                     "<b>Withdrawal Rate:</b> %{y:.1f}%<br>" +
                     "<extra></extra>"
    ))
    
    # Add guardrail bands
    fig.add_hline(y=lower_pct, line_dash="dash", line_color="green",
                 annotation_text=f"Lower Guardrail: {lower_pct:.1f}%")
    fig.add_hline(y=upper_pct, line_dash="dash", line_color="red",
                 annotation_text=f"Upper Guardrail: {upper_pct:.1f}%")
    
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Withdrawal Rate (%)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=False
    )
    
    return fig


def create_tax_analysis_chart(gross_withdrawals: np.ndarray,
                             taxes_paid: np.ndarray,
                             years: np.ndarray,
                             title: str = "Tax Analysis") -> go.Figure:
    """
    Create chart showing gross withdrawals vs taxes paid.
    
    Args:
        gross_withdrawals: Array of gross withdrawal amounts
        taxes_paid: Array of taxes paid
        years: Array of years
        title: Chart title
        
    Returns:
        Plotly figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Annual Amounts', 'Effective Tax Rate'),
        vertical_spacing=0.08
    )
    
    # Convert to thousands for readability
    gross_k = gross_withdrawals / 1000
    taxes_k = taxes_paid / 1000
    
    # Top plot: Gross withdrawals and taxes
    fig.add_trace(
        go.Scatter(x=years, y=gross_k, name='Gross Withdrawal',
                  line=dict(color='darkblue', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Gross Withdrawal:</b> $%{y:.0f}K<br>" +
                               "<extra></extra>"),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(x=years, y=taxes_k, name='Taxes Paid',
                  line=dict(color='red', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Taxes:</b> $%{y:.0f}K<br>" +
                               "<extra></extra>"),
        row=1, col=1
    )
    
    # Bottom plot: Effective tax rate
    effective_rates = np.where(gross_withdrawals > 0, 
                              (taxes_paid / gross_withdrawals) * 100, 0)
    
    fig.add_trace(
        go.Scatter(x=years, y=effective_rates, name='Effective Tax Rate',
                  line=dict(color='green', width=2),
                  hovertemplate="<b>Year:</b> %{x}<br>" +
                               "<b>Effective Rate:</b> %{y:.1f}%<br>" +
                               "<extra></extra>"),
        row=2, col=1
    )
    
    fig.update_layout(
        title=title,
        template="plotly_white",
        hovermode="x unified",
        height=600
    )
    
    fig.update_xaxes(title_text="Year", row=2, col=1)
    fig.update_yaxes(title_text="Amount ($000s)", row=1, col=1)
    fig.update_yaxes(title_text="Tax Rate (%)", row=2, col=1)
    
    return fig