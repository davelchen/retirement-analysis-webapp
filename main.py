"""
Retirement Analysis Suite - Main Application Entry Point

A comprehensive Streamlit multipage application for retirement planning featuring:
- Interactive Setup Wizard with guided parameter configuration
- Advanced Monte Carlo simulation with tax-aware withdrawals
- Seamless navigation between wizard and analysis
- Direct parameter sharing without file transfers
"""

import streamlit as st

def start_page():
    """Start page content"""
    # Initialize session state for shared parameters
    if 'wizard_completed' not in st.session_state:
        st.session_state.wizard_completed = False
    if 'wizard_params' not in st.session_state:
        st.session_state.wizard_params = {}

    # Main page content
    st.title("🏦 Retirement Analysis Suite")

    st.markdown("""
    ### Welcome to Your Comprehensive Retirement Planning Tool

    Navigate between the **Run Wizard** and **Simulation** using the sidebar, or choose your starting point below.
    """)

    # Two-column layout for navigation
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🧙‍♂️ Setup Wizard")
        st.markdown("""
        **Perfect for new users or parameter updates**

        ✨ **Features:**
        - Step-by-step guided setup
        - Interactive visualizations
        - Parameter explanations
        - Real-time feedback
        - Educational content

        📋 **Covers:**
        - Financial basics & asset allocation
        - Market assumptions & taxes
        - Social Security & guardrails
        - Cash flows & advanced options
        """)

        if st.button("🚀 Start Setup Wizard", type="primary"):
            st.switch_page("pages/wizard.py")

    with col2:
        st.markdown("### 📊 Monte Carlo Analysis")
        st.markdown("""
        **Advanced simulation and visualization**

        ⚡ **Features:**
        - Up to 50,000 Monte Carlo simulations
        - Tax-aware withdrawal calculations
        - Interactive charts & analysis
        - AI-powered insights (optional)
        - Export results & reports

        📈 **Includes:**
        - Terminal wealth distributions
        - Success probability analysis
        - Guardrail trigger statistics
        - Year-by-year projections
        """)

        if st.button("📈 Run Monte Carlo Analysis", type="secondary"):
            st.switch_page("pages/monte_carlo.py")

    # Status and tips
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.session_state.wizard_completed:
            st.success("✅ Wizard parameters ready for analysis")
        else:
            st.info("ℹ️ No wizard parameters yet")

    with col2:
        st.info("💡 **Tip**: Use sidebar navigation to switch between pages anytime")

    with col3:
        st.info("🔖 **Tip**: Bookmark specific pages for direct access")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 14px;'>
        <p>🏦 Retirement Analysis Suite | Built with Streamlit | Educational Use</p>
    </div>
    """, unsafe_allow_html=True)

# Configure pages with custom navigation labels
st.set_page_config(
    page_title="Retirement Analysis Suite",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define pages with custom titles
pages = [
    st.Page(start_page, title="Start", icon="🏠"),
    st.Page("pages/wizard.py", title="Run Wizard", icon="🧙‍♂️"),
    st.Page("pages/monte_carlo.py", title="Simulation", icon="📊"),
]

# Create navigation
pg = st.navigation(pages)
pg.run()