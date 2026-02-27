"""
Simple Authentication Module for Streamlit App
"""
import streamlit as st
import hashlib
import os
import datetime
import extra_streamlit_components as stx

# Simple user database (you can move this to environment variables or config file)
USERS = {
    "admin": "unicefinnovation",  # username: password
    "supplydivision": "wefns^dkfjsnewf",
    # Add more users as needed
}

# @st.cache_resource(experimental_allow_widgets=True) # Removed to fix CachedWidgetWarning
def get_manager():
    return stx.CookieManager()

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_credentials(username: str, password: str) -> bool:
    """
    Verify username and password
    
    Args:
        username: Username to verify
        password: Password to verify
    
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    # Check environment variables first (for production)
    env_username = os.getenv("APP_USERNAME")
    env_password = os.getenv("APP_PASSWORD")
    
    if env_username and env_password:
        return username == env_username and password == env_password
    
    # Fallback to hardcoded users (for development)
    if username in USERS:
        return USERS[username] == password
    
    return False

def initialize_session_state():
    """Initialize authentication session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None

def login_page(cookie_manager):
    """
    Render the login page
    
    Args:
        cookie_manager: The CookieManager instance
    
    Returns:
        bool: True if user is authenticated, False otherwise
    """
    st.markdown(
        """
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background-color: #f8f9fa;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 Login")
        st.markdown("---")
        
        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            col_a, col_b, col_c = st.columns([1, 2, 1])
            with col_b:
                submit = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                elif verify_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    
                    # Set cookie for persistence (7 days)
                    expires = datetime.datetime.now() + datetime.timedelta(days=7)
                    cookie_manager.set('auth_username', username, expires_at=expires)
                    
                    st.success(f"✅ Welcome, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")


def logout(cookie_manager):
    """
    Logout the current user
    
    Args:
        cookie_manager: The CookieManager instance
    """
    st.session_state.authenticated = False
    st.session_state.username = None
    
    # Delete cookie
    cookie_manager.delete('auth_username')
    
    st.rerun()

def require_authentication(cookie_manager):
    """
    Decorator-like function to require authentication
    
    Args:
        cookie_manager: The CookieManager instance
        
    Returns:
        bool: True if authenticated, False otherwise
    """
    initialize_session_state()
    
    # Check for cookie if not authenticated in session
    if not st.session_state.authenticated:
        cookie_username = cookie_manager.get('auth_username')
        
        if cookie_username and cookie_username in USERS:
            st.session_state.authenticated = True
            st.session_state.username = cookie_username
            return True
    
    if not st.session_state.authenticated:
        login_page(cookie_manager)
        return False
    
    return True

def render_logout_button(cookie_manager):
    """Render logout button in sidebar"""
    if st.session_state.authenticated:
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state.username}")
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout(cookie_manager)

