"""
Wizard Chart Utilities
Chart creation functions for the retirement planning wizard interface.
Extracted from wizard.py to improve code organization and maintainability.
"""

import plotly.graph_objects as go


def create_allocation_pie_chart(equity, bonds, real_estate, cash):
    """Create an interactive allocation pie chart"""
    labels = ['Stocks/Equity', 'Bonds', 'Real Estate', 'Cash']
    values = [equity * 100, bonds * 100, real_estate * 100, cash * 100]
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='outside'
    )])

    fig.update_layout(
        title="Your Portfolio Allocation",
        font=dict(size=14),
        height=400,
        showlegend=False
    )

    return fig


def create_risk_return_scatter():
    """Create risk vs return visualization"""
    assets = ['Cash', 'Bonds', 'Real Estate', 'Stocks']
    returns = [2.25, 3.18, 5.63, 7.42]
    risks = [0.96, 5.76, 16.12, 17.34]
    colors = ['#96CEB4', '#4ECDC4', '#45B7D1', '#FF6B6B']

    fig = go.Figure()

    for i, asset in enumerate(assets):
        fig.add_trace(go.Scatter(
            x=[risks[i]],
            y=[returns[i]],
            mode='markers+text',
            marker=dict(size=20, color=colors[i]),
            text=asset,
            textposition="top center",
            name=asset,
            showlegend=False
        ))

    fig.update_layout(
        title="Asset Classes: Risk vs Expected Return",
        xaxis_title="Volatility (Risk) %",
        yaxis_title="Expected Return %",
        height=400,
        template="plotly_white"
    )

    return fig