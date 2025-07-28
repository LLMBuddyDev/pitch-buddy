import json
import os
import hashlib
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional

class ContextManager:
    def __init__(self, storage_file="company_contexts.json"):
        # We'll use user-provided workspace keys for privacy
        self.base_storage_dir = "user_contexts"
        self.ensure_storage_dir()
    
    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.base_storage_dir):
            os.makedirs(self.base_storage_dir)
    
    def get_user_file_path(self, workspace_key: str) -> str:
        """Generate a unique file path based on workspace key"""
        # Hash the workspace key for security and valid filename
        key_hash = hashlib.sha256(workspace_key.encode()).hexdigest()[:16]
        return os.path.join(self.base_storage_dir, f"contexts_{key_hash}.json")
    
    def load_contexts(self, workspace_key: str) -> Dict:
        """Load contexts from user's workspace file"""
        if not workspace_key:
            return {}
        
        try:
            file_path = self.get_user_file_path(workspace_key)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_contexts(self, contexts: Dict, workspace_key: str):
        """Save contexts to user's workspace file"""
        if not workspace_key:
            return
        
        file_path = self.get_user_file_path(workspace_key)
        with open(file_path, 'w') as f:
            json.dump(contexts, f, indent=2)
    
    def get_context_names(self, workspace_key: str) -> List[str]:
        """Get list of all context names for this workspace"""
        contexts = self.load_contexts(workspace_key)
        return list(contexts.keys())
    
    def get_context(self, name: str, workspace_key: str) -> Optional[Dict]:
        """Get a specific context by name for this workspace"""
        contexts = self.load_contexts(workspace_key)
        return contexts.get(name)
    
    def save_context(self, name: str, context_data: Dict, workspace_key: str):
        """Save a context to this workspace"""
        if not workspace_key:
            return
        
        contexts = self.load_contexts(workspace_key)
        context_data["last_updated"] = datetime.now().isoformat()
        contexts[name] = context_data
        self.save_contexts(contexts, workspace_key)
    
    def delete_context(self, name: str, workspace_key: str):
        """Delete a context from this workspace"""
        if not workspace_key:
            return
        
        contexts = self.load_contexts(workspace_key)
        if name in contexts:
            del contexts[name]
            self.save_contexts(contexts, workspace_key)
    
    def export_context(self, name: str, workspace_key: str) -> Optional[str]:
        """Export a context as JSON string"""
        context = self.get_context(name, workspace_key)
        if context:
            return json.dumps(context, indent=2)
        return None
    
    def import_context(self, json_string: str, workspace_key: str, context_name: str = None) -> bool:
        """Import a context from JSON string to this workspace"""
        if not workspace_key:
            return False
        
        try:
            context_data = json.loads(json_string)
            # Use company_name as the context identifier
            if not context_name:
                context_name = context_data.get("company_name", "Imported Context")
            self.save_context(context_name, context_data, workspace_key)
            return True
        except json.JSONDecodeError:
            return False

def get_workspace_key():
    """Handle workspace key input and validation"""
    if 'workspace_key' not in st.session_state:
        st.session_state.workspace_key = ""
    
    if not st.session_state.workspace_key:
        st.subheader("🔑 Enter Your Workspace Key")
        st.info("Choose a unique workspace key to securely store your company contexts. This key is like a password - only you will have access to your data.")
        
        workspace_input = st.text_input(
            "Workspace Key:", 
            type="password",
            placeholder="Enter a unique key (e.g., MyCompany2024)",
            help="This key encrypts your data and keeps it private. Choose something memorable but unique to you."
        )
        
        if st.button("Access Workspace") and workspace_input.strip():
            st.session_state.workspace_key = workspace_input.strip()
            st.success("✅ Workspace accessed! Your contexts will be saved securely.")
            st.rerun()
        elif st.button("Access Workspace"):
            st.error("Please enter a workspace key.")
        
        st.stop()
    
    return st.session_state.workspace_key

def create_default_context() -> Dict:
    """Create an empty context template"""
    return {
        "company_name": "",
        "company_info": "",
        "created": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat()
    }

def render_context_selector(context_manager: ContextManager):
    """Render the context selection UI"""
    workspace_key = st.session_state.workspace_key
    context_names = context_manager.get_context_names(workspace_key)
    
    st.subheader("🏢 Company Context Management")
    
    if not context_names:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("No company contexts found. Create your first context below!")
            selected_context = None
        with col2:
            if st.button("+ New Context"):
                st.session_state.creating_new_context = True
                st.session_state.editing_context = True
    else:
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            selected_context = st.selectbox(
                "Select Company Context:",
                options=context_names,
                key="context_selector"
            )
        with col2:
            if st.button("+ New Context"):
                st.session_state.creating_new_context = True
                st.session_state.editing_context = True
        with col3:
            if selected_context and st.button("🗑️ Delete", key="quick_delete"):
                # Add confirmation using session state
                if not st.session_state.get("confirm_delete", False):
                    st.session_state.confirm_delete = True
                    st.warning(f"⚠️ Are you sure you want to delete '{selected_context}'? This cannot be undone!")
                    
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Yes, Delete", key="confirm_yes"):
                            context_manager.delete_context(selected_context, workspace_key)
                            st.success(f"✅ Deleted '{selected_context}'!")
                            st.session_state.confirm_delete = False
                            st.rerun()
                    with col_no:
                        if st.button("❌ Cancel", key="confirm_no"):
                            st.session_state.confirm_delete = False
                            st.rerun()
                else:
                    st.session_state.confirm_delete = False
    
    return selected_context

def render_context_editor(context_manager: ContextManager, context_name: str = None):
    """Render the context editing UI"""
    workspace_key = st.session_state.workspace_key
    
    # Initialize context data
    if context_name:
        context_data = context_manager.get_context(context_name, workspace_key)
        if not context_data:
            context_data = create_default_context()
            context_data["company_name"] = context_name
    else:
        context_data = create_default_context()
    
    # Check if we're creating a new context
    creating_new = st.session_state.get("creating_new_context", False)
    
    with st.expander("⚙️ Context Settings", expanded=creating_new or not context_name):
        
        # Context name
        if creating_new:
            st.info("💡 Your company name will be used as the context name")
        else:
            st.write(f"**Context:** {context_name}")
        
        # Company details
        company_name = st.text_input(
            "Company Name:",
            value=context_data.get("company_name", ""),
            placeholder="e.g., Acme Corporation, TechStart Inc"
        )
        
        # Document upload section
        st.write("**📄 Auto-enhance from documents:**")
        uploaded_docs = st.file_uploader(
            "Upload company materials",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Upload pitch decks, company overviews, or other relevant materials to auto-enhance your company context",
            label_visibility="collapsed"
        )
        st.caption("💡 Upload any company pitch decks/theses/other relevant items here.")
        
        # Process uploaded documents
        if uploaded_docs:
            with st.spinner("Processing documents..."):
                extracted_content = ""
                for doc in uploaded_docs:
                    if doc.type == "application/pdf":
                        # Extract PDF content
                        import PyPDF2
                        reader = PyPDF2.PdfReader(doc)
                        content = ""
                        for page in reader.pages:
                            content += page.extract_text() or ""
                        extracted_content += f"\n\nFrom {doc.name}:\n{content}"
                    elif doc.type == "text/plain":
                        content = str(doc.read(), "utf-8")
                        extracted_content += f"\n\nFrom {doc.name}:\n{content}"
                
                if extracted_content:
                    # Use AI to summarize and extract key company info
                    enhanced_info = enhance_company_context(extracted_content, context_data.get("company_info", ""))
                    if enhanced_info:
                        st.success(f"✅ Enhanced context from {len(uploaded_docs)} document(s)")
                        # Update the context data for display
                        context_data["company_info"] = enhanced_info
        
        # Company Information (consolidated)
        company_info = st.text_area(
            "Company Information:",
            value=context_data.get("company_info", ""),
            placeholder="Tell us about your company...",
            height=200,
            help="Add your company's strong points here. Don't hold back - anything you think your customers might like to know, from strengths to location to background to positioning."
        )
        
        st.caption("💡 **Tip:** Add your company's strong points here. Don't hold back - anything you think your customers might like to know, from strengths to location to background to positioning.")
        
        # Action buttons
        st.write("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Context"):
                if not company_name:
                    st.error("Please provide a company name.")
                    return None
                
                # Company name IS the context name
                final_context_name = company_name
                
                # Build context data
                updated_context = {
                    "company_name": company_name,
                    "company_info": company_info
                }
                
                context_manager.save_context(final_context_name, updated_context, workspace_key)
                st.success(f"✅ Context '{final_context_name}' saved!")
                
                # Reset state
                st.session_state.creating_new_context = False
                st.rerun()
        
        with col2:
            if not creating_new and context_name:
                if st.button("📥 Export"):
                    exported = context_manager.export_context(context_name, workspace_key)
                    if exported:
                        st.download_button(
                            "⬇️ Download JSON",
                            data=exported,
                            file_name=f"{context_name.replace(' ', '_')}_context.json",
                            mime="application/json"
                        )
        
        with col3:
            if not creating_new and context_name:
                if st.button("🗑️ Delete"):
                    if not st.session_state.get("confirm_editor_delete", False):
                        st.session_state.confirm_editor_delete = True
                        st.warning(f"⚠️ Are you sure you want to delete '{context_name}'? This cannot be undone!")
                        
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes, Delete", key="editor_confirm_yes"):
                                context_manager.delete_context(context_name, workspace_key)
                                st.success(f"Context '{context_name}' deleted!")
                                st.session_state.confirm_editor_delete = False
                                st.rerun()
                        with col_no:
                            if st.button("❌ Cancel", key="editor_confirm_no"):
                                st.session_state.confirm_editor_delete = False
                                st.rerun()
                    else:
                        st.session_state.confirm_editor_delete = False
        
        if creating_new:
            if st.button("❌ Cancel"):
                st.session_state.creating_new_context = False
                st.rerun()
    
    # Return the current context for use in the app
    if context_name:
        return context_manager.get_context(context_name, workspace_key)
    return None

def enhance_company_context(extracted_content: str, existing_info: str = "") -> str:
    """Use AI to enhance company context from uploaded documents"""
    try:
        from openai import OpenAI
        from company_config import OPENAI_API_KEY
        
        if not OPENAI_API_KEY:
            return existing_info
        
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
You are a helpful assistant that extracts and organizes company information from documents.

Existing company information:
{existing_info}

New document content:
{extracted_content}

Please create an enhanced company information summary that combines the existing information with new insights from the documents. Focus on:
- Company strengths and value propositions
- Technology and products
- Market positioning
- Background and achievements
- Location and key facts
- Anything that would be valuable for sales outreach

Make it comprehensive but concise. If there's existing information, enhance it rather than replace it entirely.
"""
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception:
        return existing_info 