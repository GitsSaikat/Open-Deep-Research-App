import streamlit as st
import asyncio
from research import deep_research
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="Open DeepResearch",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load images
logo = Image.open('logo.png')
banner = Image.open('banner.png')

# Display banner at top
# st.image(banner, use_container_width=True)

# Custom CSS
st.markdown("""
    <style>
    .stImage > img {
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .api-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border: 1px solid #e0e0e0;
    }
    .api-header {
        color: #1E88E5;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'api_keys_configured' not in st.session_state:
    st.session_state.api_keys_configured = False

# Sidebar configuration
with st.sidebar:
    st.image(logo, width=200, use_container_width=True)
    st.markdown("### ⚙️ API Configuration")
    
    with st.expander("Configure API Keys", expanded=not st.session_state.api_keys_configured):
        api_form = st.form("api_keys_form")
        with api_form:
            openrouter_key = api_form.text_input(
                "OpenRouter API Key",
                type="password",
                value=st.session_state.get('openrouter_key', ''),
                help="Required for language model access"
            )
            
            serpapi_key = api_form.text_input(
                "SerpAPI Key",
                type="password",
                value=st.session_state.get('serpapi_key', ''),
                help="Required for web search functionality"
            )
            
            jina_key = api_form.text_input(
                "Jina API Key",
                type="password",
                value=st.session_state.get('jina_key', ''),
                help="Required for content extraction"
            )
            
            if api_form.form_submit_button("Save API Keys"):
                if not all([openrouter_key, serpapi_key, jina_key]):
                    st.error("❌ All API keys are required!")
                else:
                    st.session_state.openrouter_key = openrouter_key
                    st.session_state.serpapi_key = serpapi_key
                    st.session_state.jina_key = jina_key
                    st.session_state.api_keys_configured = True
                    st.success("✅ API keys saved successfully!")
                    st.rerun()

    if st.session_state.api_keys_configured:
        st.success("✅ API Keys configured")
    
    st.markdown("### 🔑 Get API Keys")
    st.markdown("""
        - [OpenRouter API Key](https://openrouter.ai/keys)
        - [SerpAPI Key](https://serpapi.com/manage-api-key)
        - [Jina API Key](https://jina.ai/api-key)
    """)

def run_research(user_query, iteration_limit, search_limit):
    deep_research.OPENROUTER_API_KEY = st.session_state.openrouter_key
    deep_research.SERPAPI_API_KEY = st.session_state.serpapi_key
    deep_research.JINA_API_KEY = st.session_state.jina_key
    return asyncio.run(deep_research.research_flow(user_query, iteration_limit, search_limit))

# Main content
st.title("🔍 Open DeepResearch")
st.markdown("""
    <div style='background-color: #5dade2; padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h4 style='color: #1565C0; margin-bottom: 0.5rem;'>Welcome to the Open DeepResearch!</h4>
        <p style='color: #424242;'>
            This application helps you conduct comprehensive research on any topic by:
            <br>
            • Generating relevant search queries<br>
            • Analyzing multiple sources<br>
            • Synthesizing information into a detailed report
        </p>
    </div>
""", unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.form("research_form", clear_on_submit=False):
            st.markdown("### Research Parameters")
            
            user_query = st.text_area(
                "Research Query",
                placeholder="Enter your research topic or question here...",
                help="Be as specific as possible for better results",
                height=100,
                disabled=not st.session_state.api_keys_configured
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                iter_limit_input = st.number_input(
                    "Maximum Iterations",
                    min_value=1,
                    max_value=20,
                    value=10,
                    help="Higher values mean more thorough research but longer processing time",
                    disabled=not st.session_state.api_keys_configured
                )
            
            with col_b:
                search_limit_input = st.number_input(
                    "Results Per Search",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="Number of results per search. Lower values reduce token usage",
                    disabled=not st.session_state.api_keys_configured
                )
            
            submitted = st.form_submit_button(
                "🚀 Start Research",
                disabled=not st.session_state.api_keys_configured
            )
    
    with col2:
        st.markdown("### Tips for Better Results")
        st.info("""
        • Be specific in your query
        • Use clear, focused questions
        • Consider including relevant keywords
        • Specify time periods if applicable
        • Lower search results reduce token usage
        """)

        if not st.session_state.api_keys_configured:
            st.warning("⚠️ Please configure your API keys in the sidebar to enable research.")

if submitted and st.session_state.api_keys_configured:
    if not user_query.strip():
        st.error("⚠️ Please enter a research query before proceeding.")
    else:
        try:
            with st.spinner("🔄 Conducting research... This may take a few minutes..."):
                final_report = run_research(user_query, int(iter_limit_input), int(search_limit_input))
            
            st.markdown("""
                <div class='report-container'>
                    <h3 style='color: #1E88E5; margin-bottom: 1rem;'>📊 Research Report</h3>
                </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["📝 Formatted Report", "📄 Raw Text"])
            
            with tab1:
                st.markdown(final_report)
            
            with tab2:
                st.text_area(
                    label="",
                    value=final_report,
                    height=500,
                    help="You can copy the raw text from here"
                )
            
            st.download_button(
                label="📥 Download Report",
                data=final_report,
                file_name="research_report.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            st.error(f"❌ An error occurred during research: {str(e)}")
            st.markdown("""
                <div style='background-color: #ffebee; padding: 1rem; border-radius: 10px;'>
                    <p style='color: #c62828;'>Please try again with a different query or contact support if the issue persists.</p>
                </div>
            """, unsafe_allow_html=True)

st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>Built by GitsSaikat ❤️</p>
    </div>
""", unsafe_allow_html=True)
