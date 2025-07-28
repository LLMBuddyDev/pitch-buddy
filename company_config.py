# company_config.py
import os
import streamlit as st

# Secure API key handling - tries environment variables first, then Streamlit secrets
def get_api_key(key_name, secrets_path=None):
    """Get API key from environment variables or Streamlit secrets"""
    # Try environment variable first
    env_key = os.getenv(key_name)
    if env_key:
        return env_key
    
    # Try Streamlit secrets as fallback
    try:
        if key_name == "OPENAI_API_KEY":
            return st.secrets["openai"]["api_key"]
        elif key_name == "GOOGLE_API_KEY":
            return st.secrets["google"]["api_key"]
        elif key_name == "GOOGLE_CSE_ID":
            return st.secrets["google"]["cse_id"]
    except (KeyError, AttributeError):
        pass
    
    return None

# API Keys (secure)
OPENAI_API_KEY = get_api_key("OPENAI_API_KEY")
GOOGLE_API_KEY = get_api_key("GOOGLE_API_KEY") 
GOOGLE_CSE_ID = get_api_key("GOOGLE_CSE_ID")

# Validate that required keys are present
required_keys = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "GOOGLE_API_KEY": GOOGLE_API_KEY,
    "GOOGLE_CSE_ID": GOOGLE_CSE_ID
}

missing_keys = [key for key, value in required_keys.items() if not value]
if missing_keys:
    st.error(f"⚠️ Missing API keys: {', '.join(missing_keys)}")
    st.info("Please set these as environment variables or add them to .streamlit/secrets.toml")

# No default product info - users will create their own contexts
PRODUCT_INFO = None
