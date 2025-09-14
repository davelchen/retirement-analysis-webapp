# 🧙‍♂️ Retirement Planning Wizard

A beautiful, interactive wizard that guides users through setting up comprehensive retirement planning parameters. Now integrated as a page in the unified Retirement Analysis Suite with seamless parameter handoff to Monte Carlo analysis.

## 🌟 Features

### Interactive Step-by-Step Setup
- **Welcome & Overview** - Introduction with sample visualizations
- **Financial Basics** - Starting capital, spending needs, retirement timeline
- **Asset Allocation** - Portfolio mix with interactive pie charts and risk/return analysis
- **Market Expectations** - Return assumptions with historical context and real return calculations
- **AI Analysis Setup** - Optional Gemini API integration with model selection
- **Review & Generate** - Parameter summary and JSON file download

### 🎨 Beautiful Visualizations
- **Portfolio Allocation Pie Charts** - Interactive, color-coded asset class breakdown
- **Risk vs Return Scatter Plot** - Asset classes positioned by expected return and volatility
- **Glide Path Visualization** - How your allocation changes over time
- **Historical Comparison Charts** - Your assumptions vs historical averages
- **Real Return Calculations** - After-inflation return expectations

### 📊 Educational Content
- **Parameter Guidance** - Helpful descriptions, examples, and reasonable ranges
- **Historical Context** - 50+ years of market data for informed decisions
- **Risk Assessment** - Automatic portfolio risk level calculation
- **Best Practices** - Conservative, moderate, and aggressive strategy examples

### 🤖 AI Integration
- **Gemini API Setup** - Free tier configuration with model selection
- **API Key Testing** - Verify your configuration works
- **Model Selection** - Choose between Gemini 2.5 Pro, Flash, and other models
- **Usage Guidance** - Free tier limits and cost information

## 🚀 Quick Start

### Access the Wizard
```bash
# Run the unified application
./run.sh

# Or run directly:
streamlit run main.py
```

The wizard is available at: `http://localhost:8501/Wizard`

### Use Your Configuration
1. Complete the wizard steps
2. Click "Continue to Analysis" or use sidebar navigation
3. Run your Monte Carlo simulation with automatically loaded parameters!

### Legacy JSON Support
The wizard still generates downloadable JSON files for backup or sharing:
1. Complete wizard steps
2. Download JSON from the final step
3. Upload in Monte Carlo Analysis page if needed

## 📋 Wizard Steps Guide

### 1. 🏠 Welcome
- **Purpose**: Introduction and overview
- **Features**: Sample wealth trajectory visualization
- **Time**: 1-2 minutes reading

### 2. 💰 Financial Basics
- **Configure**: Starting capital, annual spending, retirement age, planning horizon
- **Visualizations**: Key metrics, withdrawal rate assessment
- **Guidance**: Conservative vs aggressive withdrawal rates
- **Time**: 3-5 minutes

### 3. 📊 Asset Allocation
- **Configure**: Stocks, bonds, real estate, cash percentages
- **Interactive**: Real-time pie chart updates
- **Features**: Glide path setup, risk/return calculation
- **Visualizations**: Portfolio risk assessment, diversification score
- **Time**: 5-8 minutes

### 4. 📈 Market Expectations
- **Configure**: Expected returns and volatility for each asset class
- **Context**: Historical averages (1970-2023) vs your assumptions
- **Features**: Real return calculations (after inflation)
- **Guidance**: Conservative, moderate, aggressive scenarios
- **Time**: 4-6 minutes

### 5. 🤖 AI Analysis (Optional)
- **Setup**: Gemini API key and model selection
- **Features**: API key testing, free tier guidance
- **Models**: Gemini 2.5 Pro (most capable), 2.5 Flash (efficient), others
- **Time**: 2-5 minutes (depending on API setup)

### 6. 📋 Review & Generate
- **Review**: Complete parameter summary
- **Visualize**: Final portfolio allocation chart
- **Generate**: Download JSON configuration file
- **Next Steps**: Instructions for main app usage
- **Time**: 2-3 minutes

## 🎯 Parameter Coverage

### Currently Implemented ✅
- **Financial basics**: Capital, spending, timeline
- **Asset allocation**: 4 asset classes + glide path
- **Market assumptions**: Returns, volatility, inflation
- **AI configuration**: API key, model selection
- **JSON generation**: Full compatibility with main app

### Coming Soon 🚧
- **Tax Planning**: State selection, tax brackets
- **Social Security**: Benefit calculation, funding scenarios
- **Spending Guardrails**: Dynamic adjustment rules
- **Income & Expenses**: Timeline-based cash flows
- **Advanced Options**: Market regimes, CAPE ratios

## 🔄 JSON Compatibility

The wizard generates JSON files with this structure:
```json
{
  "basic_params": { "start_capital": 2500000, ... },
  "allocation": { "equity_pct": 0.65, ... },
  "market_assumptions": { "equity_return": 0.0742, ... },
  "ai_config": { "enable_ai_analysis": true, ... },
  "metadata": { "created_by": "Retirement Planning Wizard", ... }
}
```

**100% compatible** with the main app's parameter loading system.

## 🎨 Design Philosophy

### Progressive Disclosure
- Start simple, add complexity gradually
- Optional advanced features
- Skip-friendly for quick setup

### Educational First
- Every parameter explained with context
- Historical data for informed decisions
- Best practice guidance throughout

### Visual Learning
- Interactive charts update in real-time
- Multiple visualization types
- Color-coded risk levels

### Mobile Friendly
- Responsive design works on tablets
- Touch-friendly controls
- Clean, uncluttered interface

## 🔧 Technical Notes

### Dependencies
- Same as main app: `streamlit`, `plotly`, `numpy`, `pandas`
- Optional: `google-generativeai` for AI testing

### Architecture
- **Stateless design**: All progress stored in `st.session_state`
- **Modular steps**: Each step is a separate function
- **JSON generation**: Uses same utilities as main app
- **Error handling**: Graceful fallbacks for missing dependencies

### Performance
- **Fast loading**: Minimal computation until user input
- **Efficient charts**: Plotly graphs with reasonable complexity
- **Session management**: Clean state transitions between steps

## 🎯 User Experience Goals

1. **Approachable**: Not intimidating for retirement planning beginners
2. **Educational**: Users learn concepts while configuring parameters
3. **Efficient**: Complete setup in 15-20 minutes
4. **Flexible**: Skip advanced sections, return later
5. **Trustworthy**: Grounded in historical data and best practices

## 🚀 Deployment Options

### Option 1: Separate Port
```bash
# Terminal 1 - Main app
streamlit run app.py --server.port 8501

# Terminal 2 - Wizard
streamlit run wizard_app.py --server.port 8502
```

### Option 2: Multipage App (Future)
Could be integrated as a page in the main Streamlit app using the multipage feature.

## 📈 Future Enhancements

### Additional Visualizations
- **Monte Carlo Preview**: Show sample simulation results
- **Success Rate Estimation**: Quick success probability
- **Sensitivity Analysis**: How parameter changes affect outcomes

### Enhanced Interactivity
- **Scenario Comparison**: Side-by-side parameter sets
- **Optimization Suggestions**: AI-recommended improvements
- **Goal-Based Planning**: Work backwards from desired outcomes

### Advanced Features
- **Template Library**: Pre-built scenarios (conservative, aggressive, etc.)
- **Collaborative Planning**: Share configs with advisors/spouses
- **Version Control**: Track parameter changes over time

The wizard makes sophisticated retirement planning accessible to everyone while maintaining the depth and accuracy needed for serious financial planning.