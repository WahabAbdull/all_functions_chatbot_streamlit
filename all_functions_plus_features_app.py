import streamlit as st
from openai import OpenAI
import time
from typing import List, Dict, Optional
from pypdf import PdfReader
from docx import Document
import io
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import json

# Set plotting defaults
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10

# Page configuration
st.set_page_config(
    page_title="AI Document Chat Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state FIRST
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'documents' not in st.session_state:
    st.session_state.documents = []  # List of dicts with 'name', 'content', 'type', 'dataframe'
if 'combined_content' not in st.session_state:
    st.session_state.combined_content = None
if 'dataframes' not in st.session_state:
    st.session_state.dataframes = {}  # Dict mapping filename to dataframe
if 'api_key' not in st.session_state:
    st.session_state.api_key = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_conversation_index' not in st.session_state:
    st.session_state.current_conversation_index = -1
if 'plots' not in st.session_state:
    st.session_state.plots = []  # Store generated plots
if 'plot_width' not in st.session_state:
    st.session_state.plot_width = 10
if 'plot_height' not in st.session_state:
    st.session_state.plot_height = 6
if 'plot_format' not in st.session_state:
    st.session_state.plot_format = 'png'
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True  # Default to dark mode (rainforest theme)

# Custom CSS - Glassmorphism Rainforest + Claymorphism UI/UX
# Check dark mode state
if st.session_state.dark_mode:
    # Dark Mode - Rainforest Theme
    st.markdown("""
<style>
    /* Rainforest-themed background with glassmorphism */
    .stApp {
        background: linear-gradient(135deg, 
            #1a4d2e 0%, 
            #2d6a43 25%, 
            #4f9b6f 50%, 
            #3d7a52 75%, 
            #1f5639 100%);
        background-attachment: fixed;
    }
    
    /* Main content area with glass effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        box-shadow: 0 8px 32px 0 rgba(31, 86, 57, 0.37);
    }
    
    /* Sidebar with glassmorphism */
    section[data-testid="stSidebar"] {
        background: rgba(79, 155, 111, 0.2) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    section[data-testid="stSidebar"] > div {
        background: rgba(79, 155, 111, 0.15);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.7);
    }
    
    /* Main header with rainforest gradient */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #7bc96f 0%, #4f9b6f 50%, #2d6a43 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        filter: drop-shadow(0 0 20px rgba(123, 201, 111, 0.3));
    }
    
    .sub-header {
        color: #ffffff !important;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        font-weight: 600 !important;
    }
    
    /* Claymorphism buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(145deg, #5dad7e, #4f9b6f);
        color: white;
        border-radius: 20px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        border: none;
        box-shadow: 
            8px 8px 16px rgba(26, 77, 46, 0.4),
            -8px -8px 16px rgba(123, 201, 111, 0.2),
            inset 2px 2px 4px rgba(255, 255, 255, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button:hover {
        background: linear-gradient(145deg, #4f9b6f, #5dad7e);
        transform: translateY(-3px);
        box-shadow: 
            10px 10px 20px rgba(26, 77, 46, 0.5),
            -10px -10px 20px rgba(123, 201, 111, 0.3),
            inset 2px 2px 6px rgba(255, 255, 255, 0.3);
    }
    
    .stButton>button:active {
        transform: translateY(-1px);
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.4),
            -4px -4px 8px rgba(123, 201, 111, 0.2),
            inset 3px 3px 6px rgba(0, 0, 0, 0.2);
    }
    
    /* Glass cards for chat messages */
    .chat-message {
        padding: 1.25rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        animation: fadeInUp 0.4s ease-out;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.3),
            -6px -6px 12px rgba(255, 255, 255, 0.1);
    }
    
    .user-message {
        background: rgba(123, 201, 111, 0.25);
        border: 1px solid rgba(123, 201, 111, 0.4);
        border-left: 5px solid #7bc96f;
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.3),
            -6px -6px 12px rgba(123, 201, 111, 0.2),
            inset 1px 1px 2px rgba(255, 255, 255, 0.2);
    }
    
    .assistant-message {
        background: rgba(79, 155, 111, 0.25);
        border: 1px solid rgba(79, 155, 111, 0.4);
        border-left: 5px solid #4f9b6f;
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.3),
            -6px -6px 12px rgba(79, 155, 111, 0.2),
            inset 1px 1px 2px rgba(255, 255, 255, 0.2);
    }
    
    /* Smooth animations */
    @keyframes fadeInUp {
        from { 
            opacity: 0; 
            transform: translateY(20px);
        }
        to { 
            opacity: 1; 
            transform: translateY(0);
        }
    }
    
    /* Stats box with claymorphism */
    .stats-box {
        background: rgba(79, 155, 111, 0.35) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 20px;
        border: 1px solid rgba(123, 201, 111, 0.5) !important;
        box-shadow: 
            8px 8px 16px rgba(26, 77, 46, 0.25),
            -8px -8px 16px rgba(123, 201, 111, 0.15),
            inset 2px 2px 4px rgba(255, 255, 255, 0.15);
        margin-bottom: 1rem;
    }
    
    .stats-box p, .stats-box span, .stats-box div {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    .stats-box strong {
        color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.6);
    }
    
    /* Input fields with glass effect */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 16px;
        color: #ffffff !important;
        padding: 0.75rem;
        box-shadow: 
            inset 4px 4px 8px rgba(26, 77, 46, 0.2),
            inset -4px -4px 8px rgba(255, 255, 255, 0.1);
        font-weight: 500 !important;
    }
    
    .stTextInput>div>div>input::placeholder,
    .stTextArea>div>div>textarea::placeholder {
        color: rgba(255, 255, 255, 0.7) !important;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border: 1px solid rgba(123, 201, 111, 0.8) !important;
        background: rgba(255, 255, 255, 0.3) !important;
        box-shadow: 
            0 0 15px rgba(123, 201, 111, 0.4),
            inset 4px 4px 8px rgba(26, 77, 46, 0.2),
            inset -4px -4px 8px rgba(255, 255, 255, 0.1);
    }
    
    /* File uploader with glass effect */
    .stFileUploader>div {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 2px dashed rgba(123, 201, 111, 0.8);
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.3),
            -6px -6px 12px rgba(255, 255, 255, 0.15);
    }
    
    .stFileUploader label {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    }
    
    .stFileUploader p, .stFileUploader span {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    }
    
    .stFileUploader small {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.7);
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.15) !important;
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.8);
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] small {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
    }
    
    /* Select boxes and dropdowns */
    .stSelectbox>div>div,
    .stMultiSelect>div>div {
        background: rgba(255, 255, 255, 0.25) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 16px;
        box-shadow: 
            inset 3px 3px 6px rgba(26, 77, 46, 0.2),
            inset -3px -3px 6px rgba(255, 255, 255, 0.1);
    }
    
    .stSelectbox label, .stMultiSelect label {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    .stSelectbox option, .stMultiSelect option {
        background: #2d6a43 !important;
        color: #ffffff !important;
    }
    
    /* Tabs with claymorphism */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(79, 155, 111, 0.2);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 0.5rem;
        gap: 0.5rem;
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.25),
            -6px -6px 12px rgba(123, 201, 111, 0.15);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(79, 155, 111, 0.25);
        border-radius: 16px;
        padding: 0.75rem 1.5rem;
        color: #ffffff !important;
        font-weight: 600;
        border: 1px solid rgba(123, 201, 111, 0.3);
        transition: all 0.3s;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4);
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(145deg, #5dad7e, #4f9b6f);
        color: #ffffff !important;
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.4),
            -4px -4px 8px rgba(123, 201, 111, 0.2),
            inset 2px 2px 4px rgba(255, 255, 255, 0.2);
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.4);
    }
    
    /* Expander with glass effect */
    .streamlit-expanderHeader {
        background: rgba(79, 155, 111, 0.35);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(123, 201, 111, 0.4);
        color: #ffffff !important;
        font-weight: 600;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.2),
            -4px -4px 8px rgba(123, 201, 111, 0.1);
    }
    
    .streamlit-expanderContent {
        background: rgba(45, 106, 67, 0.2);
        border-radius: 0 0 16px 16px;
        border: 1px solid rgba(123, 201, 111, 0.2);
        border-top: none;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background: rgba(79, 155, 111, 0.2);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid rgba(123, 201, 111, 0.3);
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.25),
            -6px -6px 12px rgba(123, 201, 111, 0.1);
    }
    
    .stDataFrame table {
        color: #ffffff !important;
    }
    
    .stDataFrame th {
        background: rgba(79, 155, 111, 0.4) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
    }
    
    .stDataFrame td {
        color: #ffffff !important;
        background: rgba(255, 255, 255, 0.1) !important;
        font-weight: 500 !important;
    }
    
    /* Error messages */
    .stError {
        background: rgba(244, 67, 54, 0.25) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(244, 67, 54, 0.4) !important;
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.2),
            -4px -4px 8px rgba(244, 67, 54, 0.1);
    }
    
    .stSuccess p, .stInfo p, .stWarning p, .stError p {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    /* Sidebar elements */
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(26, 77, 46, 0.2);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(145deg, #5dad7e, #4f9b6f);
        border-radius: 10px;
        box-shadow: 
            inset 2px 2px 4px rgba(255, 255, 255, 0.2),
            inset -2px -2px 4px rgba(26, 77, 46, 0.3);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(145deg, #4f9b6f, #5dad7e);
    }
    
    /* Text colors for better readability */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.8);
        font-weight: 800 !important;
    }
    
    p, span, div, label {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
        font-weight: 600 !important;
    }
    
    /* Strong text elements */
    strong, b {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.8);
    }
    
    /* Specific text elements */
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #ffffff !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    /* Chat message text */
    .chat-message p, .chat-message span, .chat-message div {
        color: #ffffff !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.4);
        font-weight: 500 !important;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        font-size: 2rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #d4f1e8 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.4);
    }
    
    /* Plot containers */
    .js-plotly-plot {
        background: rgba(79, 155, 111, 0.2);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid rgba(123, 201, 111, 0.3);
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.25),
            -6px -6px 12px rgba(123, 201, 111, 0.1);
    }
    
    /* Slider styling */
    .stSlider label, .stNumberInput label {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    /* Radio and checkbox labels */
    .stRadio label, .stCheckbox label {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
    }
    
    /* Code blocks */
    .stCodeBlock, pre, code {
        background: rgba(26, 77, 46, 0.4) !important;
        color: #7bc96f !important;
        border-radius: 12px;
        border: 1px solid rgba(123, 201, 111, 0.3);
        font-weight: 500 !important;
    }
    
    /* Browse file button styling - match save chat button */
    .stFileUploader button {
        background: linear-gradient(145deg, #5dad7e, #4f9b6f) !important;
        color: white !important;
        border-radius: 20px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        box-shadow: 
            8px 8px 16px rgba(26, 77, 46, 0.4),
            -8px -8px 16px rgba(123, 201, 111, 0.2),
            inset 2px 2px 4px rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stFileUploader button:hover {
        background: linear-gradient(145deg, #4f9b6f, #5dad7e) !important;
        transform: translateY(-3px) !important;
        box-shadow: 
            10px 10px 20px rgba(26, 77, 46, 0.5),
            -10px -10px 20px rgba(123, 201, 111, 0.3),
            inset 2px 2px 6px rgba(255, 255, 255, 0.3) !important;
    }
    
    /* File uploader spacing */
    .stFileUploader {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Success/Warning/Info boxes with rainforest colors */
    .stSuccess {
        background: rgba(93, 173, 126, 0.3) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(123, 201, 111, 0.5) !important;
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.2),
            -4px -4px 8px rgba(123, 201, 111, 0.1);
    }
    
    .stWarning {
        background: rgba(255, 193, 7, 0.2) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(255, 193, 7, 0.4) !important;
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.2),
            -4px -4px 8px rgba(255, 193, 7, 0.1);
    }
    
    .stInfo {
        background: rgba(79, 155, 111, 0.25) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(123, 201, 111, 0.4) !important;
        box-shadow: 
            4px 4px 8px rgba(26, 77, 46, 0.2),
            -4px -4px 8px rgba(123, 201, 111, 0.1);
    }
    
    /* Light/Dark mode toggle button */
    .mode-toggle {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999;
        background: linear-gradient(145deg, #5dad7e, #4f9b6f);
        border-radius: 50px;
        padding: 0.6rem 1.2rem;
        box-shadow: 
            6px 6px 12px rgba(26, 77, 46, 0.4),
            -6px -6px 12px rgba(123, 201, 111, 0.2),
            inset 2px 2px 4px rgba(255, 255, 255, 0.2);
        cursor: pointer;
        transition: all 0.3s;
        border: none;
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .mode-toggle:hover {
        transform: scale(1.05);
        box-shadow: 
            8px 8px 16px rgba(26, 77, 46, 0.5),
            -8px -8px 16px rgba(123, 201, 111, 0.3),
            inset 2px 2px 6px rgba(255, 255, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)
else:
    # Light Mode - Clean and Bright
    st.markdown("""
<style>
    /* Light background with subtle gradient */
    .stApp {
        background: linear-gradient(135deg, 
            #f0f9f4 0%, 
            #e8f5e9 25%, 
            #c8e6c9 50%, 
            #e8f5e9 75%, 
            #f1f8f4 100%);
        background-attachment: fixed;
    }
    
    /* Main content area with light glass effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(76, 175, 80, 0.2);
        padding: 2rem;
        box-shadow: 0 8px 32px 0 rgba(76, 175, 80, 0.15);
    }
    
    /* Sidebar with light glass effect */
    section[data-testid="stSidebar"] {
        background: rgba(200, 230, 201, 0.3) !important;
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-right: 1px solid rgba(76, 175, 80, 0.3);
    }
    
    section[data-testid="stSidebar"] > div {
        background: rgba(200, 230, 201, 0.2);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #1b5e20 !important;
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    /* Main header with light gradient */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2e7d32 0%, #388e3c 50%, #43a047 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 0 20px rgba(46, 125, 50, 0.2));
    }
    
    .sub-header {
        color: #2e7d32 !important;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
        font-weight: 600 !important;
    }
    
    /* Claymorphism buttons for light mode */
    .stButton>button {
        width: 100%;
        background: linear-gradient(145deg, #66bb6a, #4caf50);
        color: white;
        border-radius: 20px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        border: none;
        box-shadow: 
            6px 6px 12px rgba(46, 125, 50, 0.3),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 2px 2px 4px rgba(255, 255, 255, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stButton>button:hover {
        background: linear-gradient(145deg, #4caf50, #66bb6a);
        transform: translateY(-3px);
        box-shadow: 
            8px 8px 16px rgba(46, 125, 50, 0.4),
            -8px -8px 16px rgba(255, 255, 255, 0.9),
            inset 2px 2px 6px rgba(255, 255, 255, 0.4);
    }
    
    .stButton>button:active {
        transform: translateY(-1px);
        box-shadow: 
            3px 3px 6px rgba(46, 125, 50, 0.3),
            -3px -3px 6px rgba(255, 255, 255, 0.8),
            inset 3px 3px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Glass cards for chat messages */
    .chat-message {
        padding: 1.25rem;
        border-radius: 20px;
        margin-bottom: 1rem;
        animation: fadeInUp 0.4s ease-out;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.15),
            -4px -4px 8px rgba(255, 255, 255, 0.8);
    }
    
    .user-message {
        background: rgba(129, 199, 132, 0.3);
        border: 1px solid rgba(76, 175, 80, 0.4);
        border-left: 5px solid #4caf50;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.2),
            -4px -4px 8px rgba(255, 255, 255, 0.8),
            inset 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    .assistant-message {
        background: rgba(165, 214, 167, 0.3);
        border: 1px solid rgba(102, 187, 106, 0.4);
        border-left: 5px solid #66bb6a;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.2),
            -4px -4px 8px rgba(255, 255, 255, 0.8),
            inset 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    @keyframes fadeInUp {
        from { 
            opacity: 0; 
            transform: translateY(20px);
        }
        to { 
            opacity: 1; 
            transform: translateY(0);
        }
    }
    
    /* Stats box with light claymorphism */
    .stats-box {
        background: rgba(200, 230, 201, 0.4);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 20px;
        border: 1px solid rgba(76, 175, 80, 0.3);
        box-shadow: 
            6px 6px 12px rgba(46, 125, 50, 0.15),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 2px 2px 4px rgba(255, 255, 255, 0.4);
        margin-bottom: 1rem;
    }
    
    .stats-box p, .stats-box span, .stats-box div {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    /* Input fields */
    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(76, 175, 80, 0.4) !important;
        border-radius: 16px;
        color: #1b5e20 !important;
        padding: 0.75rem;
        box-shadow: 
            inset 3px 3px 6px rgba(46, 125, 50, 0.1),
            inset -3px -3px 6px rgba(255, 255, 255, 0.8);
        font-weight: 500 !important;
    }
    
    .stTextInput>div>div>input::placeholder,
    .stTextArea>div>div>textarea::placeholder {
        color: rgba(27, 94, 32, 0.6) !important;
    }
    
    .stTextInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border: 1px solid rgba(76, 175, 80, 0.8) !important;
        background: rgba(255, 255, 255, 0.85) !important;
        box-shadow: 
            0 0 15px rgba(76, 175, 80, 0.3),
            inset 3px 3px 6px rgba(46, 125, 50, 0.1),
            inset -3px -3px 6px rgba(255, 255, 255, 0.8);
    }
    
    /* File uploader */
    .stFileUploader>div {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 2px dashed rgba(76, 175, 80, 0.6);
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.15),
            -4px -4px 8px rgba(255, 255, 255, 0.8);
    }
    
    .stFileUploader label {
        color: #1b5e20 !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stFileUploader p, .stFileUploader span {
        color: #2e7d32 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stFileUploader small {
        color: #388e3c !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.3) !important;
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] p {
        color: #1b5e20 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stFileUploader [data-testid="stFileUploaderDropzone"] small {
        color: #2e7d32 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    /* Select boxes and dropdowns */
    .stSelectbox>div>div,
    .stMultiSelect>div>div {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(76, 175, 80, 0.4) !important;
        border-radius: 16px;
        box-shadow: 
            inset 2px 2px 4px rgba(46, 125, 50, 0.1),
            inset -2px -2px 4px rgba(255, 255, 255, 0.8);
    }
    
    .stSelectbox label, .stMultiSelect label {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(200, 230, 201, 0.3);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 0.5rem;
        gap: 0.5rem;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.15),
            -4px -4px 8px rgba(255, 255, 255, 0.8);
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.5);
        border-radius: 16px;
        padding: 0.75rem 1.5rem;
        color: #2e7d32 !important;
        font-weight: 600;
        border: 1px solid rgba(76, 175, 80, 0.3);
        transition: all 0.3s;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(145deg, #66bb6a, #4caf50);
        color: #ffffff !important;
        box-shadow: 
            3px 3px 6px rgba(46, 125, 50, 0.3),
            -3px -3px 6px rgba(255, 255, 255, 0.8),
            inset 2px 2px 4px rgba(255, 255, 255, 0.3);
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(200, 230, 201, 0.4);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        border: 1px solid rgba(76, 175, 80, 0.3);
        color: #1b5e20 !important;
        font-weight: 600;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
        box-shadow: 
            3px 3px 6px rgba(46, 125, 50, 0.15),
            -3px -3px 6px rgba(255, 255, 255, 0.8);
    }
    
    /* Dataframe */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.15),
            -4px -4px 8px rgba(255, 255, 255, 0.8);
    }
    
    .stDataFrame table {
        color: #1b5e20 !important;
    }
    
    .stDataFrame th {
        background: rgba(76, 175, 80, 0.3) !important;
        color: #1b5e20 !important;
        font-weight: 700 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    .stDataFrame td {
        color: #2e7d32 !important;
        background: rgba(255, 255, 255, 0.4) !important;
        font-weight: 500 !important;
    }
    
    /* Alert messages */
    .stSuccess, .stInfo, .stWarning, .stError {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        box-shadow: 
            3px 3px 6px rgba(46, 125, 50, 0.15),
            -3px -3px 6px rgba(255, 255, 255, 0.8);
    }
    
    .stSuccess p, .stInfo p, .stWarning p, .stError p {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(200, 230, 201, 0.3);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(145deg, #66bb6a, #4caf50);
        border-radius: 10px;
        box-shadow: 
            inset 2px 2px 4px rgba(255, 255, 255, 0.3),
            inset -2px -2px 4px rgba(46, 125, 50, 0.2);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(145deg, #4caf50, #66bb6a);
    }
    
    /* Text colors */
    h1, h2, h3, h4, h5, h6 {
        color: #1b5e20 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
        font-weight: 800 !important;
    }
    
    p, span, div, label {
        color: #2e7d32 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
        font-weight: 600 !important;
    }
    
    strong, b {
        color: #1b5e20 !important;
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stMarkdown, .stMarkdown p, .stMarkdown span {
        color: #2e7d32 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    .chat-message p, .chat-message span, .chat-message div {
        color: #1b5e20 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
        font-weight: 500 !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #1b5e20 !important;
        font-weight: 800 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
        font-size: 2rem !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #2e7d32 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
    }
    
    .js-plotly-plot {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.15),
            -4px -4px 8px rgba(255, 255, 255, 0.8);
    }
    
    .stSlider label, .stNumberInput label {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stRadio label, .stCheckbox label {
        color: #1b5e20 !important;
        font-weight: 600 !important;
        text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.7);
    }
    
    .stCodeBlock, pre, code {
        background: rgba(27, 94, 32, 0.1) !important;
        color: #2e7d32 !important;
        border-radius: 12px;
        border: 1px solid rgba(76, 175, 80, 0.3);
        font-weight: 500 !important;
    }
    
    /* Browse file button styling */
    .stFileUploader button {
        background: linear-gradient(145deg, #66bb6a, #4caf50) !important;
        color: white !important;
        border-radius: 20px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        box-shadow: 
            6px 6px 12px rgba(46, 125, 50, 0.3),
            -6px -6px 12px rgba(255, 255, 255, 0.8),
            inset 2px 2px 4px rgba(255, 255, 255, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stFileUploader button:hover {
        background: linear-gradient(145deg, #4caf50, #66bb6a) !important;
        transform: translateY(-3px) !important;
        box-shadow: 
            8px 8px 16px rgba(46, 125, 50, 0.4),
            -8px -8px 16px rgba(255, 255, 255, 0.9),
            inset 2px 2px 6px rgba(255, 255, 255, 0.4) !important;
    }
    
    /* Light/Dark mode toggle button */
    .mode-toggle {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 999;
        background: linear-gradient(145deg, #66bb6a, #4caf50);
        border-radius: 50px;
        padding: 0.6rem 1.2rem;
        box-shadow: 
            4px 4px 8px rgba(46, 125, 50, 0.3),
            -4px -4px 8px rgba(255, 255, 255, 0.8),
            inset 2px 2px 4px rgba(255, 255, 255, 0.3);
        cursor: pointer;
        transition: all 0.3s;
        border: none;
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    .mode-toggle:hover {
        transform: scale(1.05);
        box-shadow: 
            6px 6px 12px rgba(46, 125, 50, 0.4),
            -6px -6px 12px rgba(255, 255, 255, 0.9),
            inset 2px 2px 6px rgba(255, 255, 255, 0.4);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_document(uploaded_file) -> tuple[Optional[str], str, str, Optional[pd.DataFrame]]:
    """Cache document loading to avoid re-reading the same file
    Returns: (content, filename, file_type, dataframe)
    """
    try:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Create a clean variable name from filename
        var_name = uploaded_file.name.split('.')[0].replace(' ', '_').replace('-', '_')
        var_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in var_name)
        
        if file_extension == 'txt':
            # Handle TXT files
            content = uploaded_file.read().decode('utf-8')
            return content, uploaded_file.name, 'text', None
        
        elif file_extension == 'pdf':
            # Handle PDF files
            pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))
            content = ""
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
            return content, uploaded_file.name, 'text', None
        
        elif file_extension in ['doc', 'docx']:
            # Handle DOC/DOCX files
            doc = Document(io.BytesIO(uploaded_file.read()))
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return content, uploaded_file.name, 'text', None
        
        elif file_extension == 'csv':
            # Handle CSV files
            df = pd.read_csv(uploaded_file)
            content = get_dataframe_summary(df, uploaded_file.name, var_name)
            return content, uploaded_file.name, 'data', df
        
        elif file_extension == 'tsv':
            # Handle TSV files
            df = pd.read_csv(uploaded_file, sep='\t')
            content = get_dataframe_summary(df, uploaded_file.name, var_name)
            return content, uploaded_file.name, 'data', df
        
        elif file_extension in ['xlsx', 'xls']:
            # Handle Excel files
            df = pd.read_excel(uploaded_file)
            content = get_dataframe_summary(df, uploaded_file.name, var_name)
            return content, uploaded_file.name, 'data', df
        
        else:
            st.error(f"Unsupported file type: {file_extension}")
            return None, uploaded_file.name, 'unknown', None
    
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None, uploaded_file.name, 'error', None


def get_dataframe_summary(df: pd.DataFrame, filename: str, var_name: str) -> str:
    """Generate a comprehensive summary of a dataframe for AI context"""
    summary = f"Data File: {filename}\n"
    summary += f"DataFrame variable name: {var_name}\n"
    summary += f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n"
    
    summary += "Column Information:\n"
    for col in df.columns:
        dtype = df[col].dtype
        null_count = df[col].isnull().sum()
        summary += f"  - {col} ({dtype}): {null_count} missing values\n"
    
    summary += "\nFirst 5 rows:\n"
    summary += df.head().to_string()
    
    summary += "\n\nStatistical Summary:\n"
    summary += df.describe().to_string()
    
    return summary


@st.cache_data(show_spinner=False)
def get_document_stats(content: str) -> Dict[str, int]:
    """Cache document statistics calculation"""
    if not content:
        return {"characters": 0, "words": 0, "lines": 0}

    return {
        "characters": len(content),
        "words": len(content.split()),
        "lines": len(content.split('\n'))
    }


def combine_documents(documents: List[Dict]) -> str:
    """Combine multiple documents into a single string with clear separation"""
    if not documents:
        return None
    
    combined = ""
    for idx, doc in enumerate(documents, 1):
        combined += f"\n\n{'='*60}\n"
        combined += f"DOCUMENT {idx}: {doc['name']} (Type: {doc['type']})\n"
        combined += f"{'='*60}\n\n"
        combined += doc['content']
        combined += "\n"
    
    return combined


def generate_plot_from_code(code: str, dataframes: Dict[str, pd.DataFrame], width: int = 10, height: int = 6) -> Optional[plt.Figure]:
    """Execute plotting code safely and return the figure"""
    try:
        # Create a safe namespace with pandas, matplotlib, plotly, and dataframes
        namespace = {
            'pd': pd,
            'plt': plt,
            'px': px,
            'go': go,
            'sns': sns,
            **dataframes  # Add all dataframes to namespace
        }
        
        # If there's only one dataframe, also create a 'df' alias
        if len(dataframes) == 1:
            namespace['df'] = list(dataframes.values())[0]
        
        # Modify code to use custom figure size if plt.figure() is in the code
        if 'plt.figure(' in code and 'figsize' not in code:
            code = code.replace('plt.figure()', f'plt.figure(figsize=({width}, {height}))')
        elif 'plt.figure(' not in code and ('plt.' in code or 'sns.' in code):
            # If no plt.figure() but using matplotlib/seaborn, add it at the beginning
            code = f'plt.figure(figsize=({width}, {height}))\n' + code
        
        # Execute the code
        exec(code, namespace)
        
        # Return the current figure if using matplotlib
        if plt.get_fignums():
            return plt.gcf()
        
        return None
    
    except Exception as e:
        st.error(f"Error generating plot: {str(e)}")
        return None


def save_plot_to_bytes(fig, format: str = 'png', is_plotly: bool = False) -> io.BytesIO:
    """Save a plot to bytes buffer for download"""
    buf = io.BytesIO()
    
    if is_plotly:
        # For Plotly figures
        if format == 'html':
            fig.write_html(buf)
        elif format == 'png':
            fig.write_image(buf, format='png')
        elif format == 'svg':
            fig.write_image(buf, format='svg')
        elif format == 'pdf':
            fig.write_image(buf, format='pdf')
    else:
        # For Matplotlib figures
        fig.savefig(buf, format=format, dpi=300, bbox_inches='tight')
    
    buf.seek(0)
    return buf


def get_ai_response(messages: List[Dict], api_key: str, document_content: str, num_documents: int = 1, has_data_files: bool = False, dataframe_names: List[str] = None) -> str:
    """Get response from OpenAI API with document context"""
    try:
        client = OpenAI(api_key=api_key)

        # Create system message with document context
        doc_text = "documents" if num_documents > 1 else "document"
        
        data_instructions = ""
        if has_data_files:
            df_info = ""
            if dataframe_names:
                if len(dataframe_names) == 1:
                    df_info = f"\nThe dataframe is available as both '{dataframe_names[0]}' and 'df'.\n"
                else:
                    df_info = f"\nThe dataframes are available as: {', '.join(dataframe_names)}\n"
            
            data_instructions = f"""\n\nFor data files (CSV, XLSX, TSV), you can suggest visualizations and analyses.{df_info}
When suggesting a plot:
1. Describe what visualization would be helpful
2. Provide Python code using matplotlib, seaborn, or plotly
3. Wrap the code in ```python code blocks
4. Use the exact dataframe variable names shown in the document summaries
5. Make sure to include plt.figure() and appropriate labels
6. For single dataframe, you can use 'df' as the variable name

Example for matplotlib/seaborn:
```python
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(10, 6))
sns.barplot(data=df, x='column1', y='column2')
plt.title('Title Here')
plt.xlabel('X Label')
plt.ylabel('Y Label')
plt.tight_layout()
```

Example for plotly:
```python
import plotly.express as px

fig = px.bar(df, x='column1', y='column2', title='Title Here')
fig.show()
```"""
        
        system_message = {
            "role": "system",
            "content": f"""You are a helpful AI assistant. You have access to the following {doc_text}:

---DOCUMENTS START---
{document_content}
---DOCUMENTS END---

Please answer questions based on these {doc_text}. When referencing information, mention which document it comes from if multiple documents are provided. If the information is not in the {doc_text}, mention that and provide a helpful response anyway.{data_instructions}"""
        }

        # Combine system message with user messages
        full_messages = [system_message] + messages

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            temperature=0.7,
            max_tokens=1000
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"


def save_conversation():
    """Save current conversation to history"""
    if st.session_state.messages:
        doc_names = ", ".join([doc['name'] for doc in st.session_state.documents])
        conversation = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "document_name": doc_names if doc_names else "No documents",
            "messages": st.session_state.messages.copy()
        }
        st.session_state.conversation_history.append(conversation)
        st.session_state.current_conversation_index = len(st.session_state.conversation_history) - 1


def load_conversation(index: int):
    """Load a conversation from history"""
    if 0 <= index < len(st.session_state.conversation_history):
        conversation = st.session_state.conversation_history[index]
        st.session_state.messages = conversation["messages"].copy()
        st.session_state.current_conversation_index = index
        st.rerun()


def clear_current_chat():
    """Clear current chat messages"""
    st.session_state.messages = []
    st.rerun()


# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # API Key input
    api_key_input = st.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.api_key or "",
        help="Enter your OpenAI API key to start chatting",
        key="api_key_input_field"
    )
   
    # Status message
    if st.session_state.api_key:
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ Please enter your API key")

    # st.markdown("---") 

    # Enter button
    if st.button("⏎ Enter", key="api_key_enter_btn", use_container_width=True):
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.rerun()

    # Document upload
    st.markdown("### 📤 Upload Documents")
    

    uploaded_files = st.file_uploader(
        "Choose documents (TXT, PDF, DOC, DOCX, CSV, XLSX, TSV)",
        type=['txt', 'pdf', 'doc', 'docx', 'csv', 'xlsx', 'xls', 'tsv'],
        help="Upload documents and data files to analyze and chat with",
        accept_multiple_files=True
    )

    if uploaded_files:        
        # Add gap between file uploader widget and uploaded files card
        st.markdown("<div style='margin: 1.5rem 0 0 0;'></div>", unsafe_allow_html=True)
        # Load all documents
        documents = []
        dataframes = {}
        for uploaded_file in uploaded_files:
            content, name, file_type, df = load_document(uploaded_file)
            if content:
                doc_dict = {"name": name, "content": content, "type": file_type}
                if df is not None:
                    # Store dataframe with a clean variable name
                    var_name = name.split('.')[0].replace(' ', '_').replace('-', '_')
                    dataframes[var_name] = df
                    doc_dict['dataframe'] = var_name
                documents.append(doc_dict)
        
        if documents:
            st.session_state.documents = documents
            st.session_state.dataframes = dataframes
            st.session_state.combined_content = combine_documents(documents)
            
            # Display document stats
            st.markdown("#### 📊 Document Statistics")
            
            total_stats = {"characters": 0, "words": 0, "lines": 0}
            data_files = 0
            text_files = 0
            
            for doc in documents:
                icon = "📊" if doc['type'] == 'data' else "📄"
                if doc['type'] == 'data':
                    data_files += 1
                    # Show dataframe preview for data files
                    df_name = doc.get('dataframe', '')
                    if df_name in dataframes:
                        df = dataframes[df_name]
                        st.markdown(f"""
                        <div class="stats-box" style="margin-bottom: 0.5rem;">
                            <strong>{icon} {doc['name']}</strong> (Data File)<br>
                            Rows: {df.shape[0]:,} | Columns: {df.shape[1]:,}
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander(f"Preview {doc['name']}"):
                            st.dataframe(df.head(10), use_container_width=True)
                else:
                    text_files += 1
                    stats = get_document_stats(doc['content'])
                    st.markdown(f"""
                    <div class="stats-box" style="margin-bottom: 0.5rem;">
                        <strong>{icon} {doc['name']}</strong><br>
                        Characters: {stats['characters']:,} | 
                        Words: {stats['words']:,} | 
                        Lines: {stats['lines']:,}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    total_stats['characters'] += stats['characters']
                    total_stats['words'] += stats['words']
                    total_stats['lines'] += stats['lines']
            
            # Display total stats if multiple documents
            if len(documents) > 1:
                summary = f"{text_files} text file(s), {data_files} data file(s)" if data_files > 0 else f"{text_files} document(s)"
                st.markdown(f"""
                <div class="stats-box">
                    <strong>📚 Total: {summary}</strong>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Plot settings (only show if data files are loaded)
    if st.session_state.dataframes:
        st.markdown("### 📏 Plot Settings")
        
        st.session_state.plot_width = st.slider(
            "Plot Width",
            min_value=6,
            max_value=20,
            value=st.session_state.plot_width,
            step=1,
            help="Adjust the width of generated plots"
        )
        
        st.session_state.plot_height = st.slider(
            "Plot Height",
            min_value=4,
            max_value=15,
            value=st.session_state.plot_height,
            step=1,
            help="Adjust the height of generated plots"
        )
        
        st.session_state.plot_format = st.selectbox(
            "Download Format",
            options=['png', 'svg', 'pdf', 'html'],
            index=['png', 'svg', 'pdf', 'html'].index(st.session_state.plot_format),
            help="Choose format for downloading plots (HTML for Plotly charts)"
        )
        
        st.markdown(f"**Current Size:** {st.session_state.plot_width} × {st.session_state.plot_height} inches")

    # st.markdown("---")

    # Chat controls
    st.markdown("### 💬 Chat Controls")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat"):
            clear_current_chat()

    with col2:
        if st.button("💾 Save Chat"):
            save_conversation()
            st.success("Saved!")
            time.sleep(0.5)
            st.rerun()

    # Conversation history
    if st.session_state.conversation_history:
        st.markdown("---")
        st.markdown("### 📚 Conversation History")

        for idx, conv in enumerate(reversed(st.session_state.conversation_history)):
            actual_idx = len(st.session_state.conversation_history) - 1 - idx
            if st.button(
                f"📝 {conv['timestamp']}\n{conv['document_name'][:20]}...",
                key=f"conv_{actual_idx}",
                use_container_width=True
            ):
                load_conversation(actual_idx)

# Main content
# Add light/dark mode toggle at top right
col1, col2 = st.columns([6, 1])
with col2:
    mode_icon = "🌙" if st.session_state.dark_mode else "☀️"
    mode_text = "Dark" if not st.session_state.dark_mode else "Light"
    if st.button(f"{mode_icon} {mode_text}", key="mode_toggle", use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

st.markdown('<p class="main-header">📄 AI Multi-Document & Data Chat Assistant</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Upload documents and data files, chat with them, and generate visualizations using AI</p>', unsafe_allow_html=True)

# Check if ready to chat
if not st.session_state.api_key:
    st.info("👈 Please enter your OpenAI API key in the sidebar to get started")
elif not st.session_state.combined_content:
    st.info("👈 Please upload documents or data files (TXT, PDF, DOC, DOCX, CSV, XLSX, TSV) in the sidebar to begin chatting")
else:
    # Display chat messages
    for idx, message in enumerate(st.session_state.messages):
        role = message["role"]
        content = message["content"]

        if role == "user":
            st.markdown(
                f'<div class="chat-message user-message"><strong>🧑 You:</strong><br>{content}</div>',
                unsafe_allow_html=True
            )
        else:
            # Process AI message: extract and hide code blocks, show only text
            display_content = content
            
            # Remove Python code blocks from display (but we'll still execute them)
            if '```python' in content:
                lines = content.split('\n')
                filtered_lines = []
                in_code_block = False
                
                for line in lines:
                    if line.strip().startswith('```python'):
                        in_code_block = True
                    elif line.strip() == '```' and in_code_block:
                        in_code_block = False
                    elif not in_code_block:
                        filtered_lines.append(line)
                
                display_content = '\n'.join(filtered_lines).strip()
            
            st.markdown(
                f'<div class="chat-message assistant-message"><strong>🤖 AI:</strong><br>{display_content}</div>',
                unsafe_allow_html=True
            )
            
            # Check if this message has associated plots
            if '```python' in content and st.session_state.dataframes:
                # Extract and display plots
                lines = content.split('\n')
                in_code_block = False
                current_code = []
                plot_counter = 0
                
                for line in lines:
                    if line.strip().startswith('```python'):
                        in_code_block = True
                        current_code = []
                    elif line.strip() == '```' and in_code_block:
                        in_code_block = False
                        if current_code:
                            code = '\n'.join(current_code)
                            if any(plot_lib in code for plot_lib in ['plt.', 'sns.', 'px.', 'go.']):
                                # Try to generate and display the plot
                                plot_counter += 1
                                try:
                                    if 'px.' in code or 'go.' in code:
                                        # Plotly plot
                                        namespace = {
                                            'pd': pd,
                                            'px': px,
                                            'go': go,
                                            **st.session_state.dataframes
                                        }
                                        # Add 'df' alias if single dataframe
                                        if len(st.session_state.dataframes) == 1:
                                            namespace['df'] = list(st.session_state.dataframes.values())[0]
                                        
                                        # Update plotly figure sizes
                                        width_px = st.session_state.plot_width * 100
                                        height_px = st.session_state.plot_height * 100
                                        
                                        exec(code, namespace)
                                        # Get the figure from namespace if it was assigned to a variable
                                        plotly_fig = None
                                        for var_name in ['fig', 'figure']:
                                            if var_name in namespace:
                                                plotly_fig = namespace[var_name]
                                                plotly_fig.update_layout(width=width_px, height=height_px)
                                                st.plotly_chart(plotly_fig, use_container_width=True)
                                                
                                                # Add download button for Plotly
                                                col1, col2, col3 = st.columns([1, 1, 4])
                                                with col1:
                                                    # Plotly HTML export (always available)
                                                    html_bytes = io.BytesIO()
                                                    plotly_fig.write_html(html_bytes)
                                                    html_bytes.seek(0)
                                                    st.download_button(
                                                        label="📥 HTML",
                                                        data=html_bytes,
                                                        file_name=f"plot_{idx}_{plot_counter}.html",
                                                        mime="text/html",
                                                        key=f"download_plotly_html_{idx}_{plot_counter}",
                                                        help="Download as interactive HTML"
                                                    )
                                                with col2:
                                                    # Try image export (requires kaleido)
                                                    try:
                                                        if st.session_state.plot_format in ['png', 'svg', 'pdf']:
                                                            img_bytes = io.BytesIO()
                                                            plotly_fig.write_image(img_bytes, format=st.session_state.plot_format)
                                                            img_bytes.seek(0)
                                                            st.download_button(
                                                                label=f"📥 {st.session_state.plot_format.upper()}",
                                                                data=img_bytes,
                                                                file_name=f"plot_{idx}_{plot_counter}.{st.session_state.plot_format}",
                                                                mime=f"image/{st.session_state.plot_format}",
                                                                key=f"download_plotly_img_{idx}_{plot_counter}",
                                                                help=f"Download as {st.session_state.plot_format.upper()}"
                                                            )
                                                    except Exception as img_err:
                                                        st.caption("⚠️ Install: pip install kaleido")
                                                break
                                    else:
                                        # Matplotlib/Seaborn plot
                                        fig = generate_plot_from_code(
                                            code, 
                                            st.session_state.dataframes,
                                            st.session_state.plot_width,
                                            st.session_state.plot_height
                                        )
                                        if fig:
                                            st.pyplot(fig)
                                            
                                            # Add download button
                                            col1, col2, col3 = st.columns([1, 1, 4])
                                            with col1:
                                                plot_bytes = save_plot_to_bytes(fig, st.session_state.plot_format)
                                                st.download_button(
                                                    label=f"📥 {st.session_state.plot_format.upper()}",
                                                    data=plot_bytes,
                                                    file_name=f"plot_{idx}_{plot_counter}.{st.session_state.plot_format}",
                                                    mime=f"image/{st.session_state.plot_format}" if st.session_state.plot_format != 'pdf' else "application/pdf",
                                                    key=f"download_{idx}_{plot_counter}",
                                                    help=f"Download plot as {st.session_state.plot_format.upper()} ({st.session_state.plot_width}×{st.session_state.plot_height} in, 300 DPI)"
                                                )
                                            
                                            plt.close()
                                except Exception as e:
                                    st.error(f"Could not generate plot: {str(e)}")
                    elif in_code_block:
                        current_code.append(line)

    # Chat input
    doc_text = "documents" if len(st.session_state.documents) > 1 else "document"
    user_input = st.chat_input(f"Ask a question about your {doc_text}...")

    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        # Get AI response with spinner
        with st.spinner("🤔 AI is thinking..."):
            has_data = any(doc.get('type') == 'data' for doc in st.session_state.documents)
            df_names = [doc.get('dataframe') for doc in st.session_state.documents if doc.get('dataframe')]
            ai_response = get_ai_response(
                st.session_state.messages,
                st.session_state.api_key,
                st.session_state.combined_content,
                len(st.session_state.documents),
                has_data,
                df_names
            )

        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Check if response contains Python code for plotting
        if '```python' in ai_response and st.session_state.dataframes:
            # Extract code blocks
            code_blocks = []
            lines = ai_response.split('\n')
            in_code_block = False
            current_code = []
            
            for line in lines:
                if line.strip().startswith('```python'):
                    in_code_block = True
                    current_code = []
                elif line.strip() == '```' and in_code_block:
                    in_code_block = False
                    if current_code:
                        code_blocks.append('\n'.join(current_code))
                elif in_code_block:
                    current_code.append(line)
            
            # Try to execute each code block
            for code in code_blocks:
                if any(plot_lib in code for plot_lib in ['plt.', 'sns.', 'px.', 'go.']):
                    st.session_state.plots.append(code)

        # Rerun to display new messages
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #6c757d; padding: 1rem;'>
        Made with ❤️ using Streamlit & OpenAI |
        <a href='https://platform.openai.com/api-keys' target='_blank'>Get API Key</a>
    </div>
    """,
    unsafe_allow_html=True
)
