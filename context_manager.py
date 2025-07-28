import json
import os
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional

class ContextManager:
    def __init__(self, storage_file="company_contexts.json"):
        self.storage_file = storage_file
        self.ensure_storage_exists()
    
    def ensure_storage_exists(self):
        """Create storage file if it doesn't exist"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump({}, f)
    
    def load_contexts(self) -> Dict:
        """Load all contexts from storage"""
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_contexts(self, contexts: Dict):
        """Save all contexts to storage"""
        with open(self.storage_file, 'w') as f:
            json.dump(contexts, f, indent=2)
    
    def get_context_names(self) -> List[str]:
        """Get list of all context names"""
        contexts = self.load_contexts()
        return list(contexts.keys())
    
    def get_context(self, name: str) -> Optional[Dict]:
        """Get a specific context by name"""
        contexts = self.load_contexts()
        return contexts.get(name)
    
    def save_context(self, name: str, context_data: Dict):
        """Save a context"""
        contexts = self.load_contexts()
        context_data["last_updated"] = datetime.now().isoformat()
        contexts[name] = context_data
        self.save_contexts(contexts)
    
    def delete_context(self, name: str):
        """Delete a context"""
        contexts = self.load_contexts()
        if name in contexts:
            del contexts[name]
            self.save_contexts(contexts)
    
    def export_context(self, name: str) -> Optional[str]:
        """Export a context as JSON string"""
        context = self.get_context(name)
        if context:
            return json.dumps(context, indent=2)
        return None
    
    def import_context(self, json_string: str, context_name: str = None) -> bool:
        """Import a context from JSON string"""
        try:
            context_data = json.loads(json_string)
            # Use company_name as the context identifier
            if not context_name:
                context_name = context_data.get("company_name", "Imported Context")
            self.save_context(context_name, context_data)
            return True
        except json.JSONDecodeError:
            return False

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
    context_names = context_manager.get_context_names()
    
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
            if selected_context and st.button("Delete This Context", key="quick_delete"):
                context_manager.delete_context(selected_context)
                st.success(f"✅ Deleted '{selected_context}'!")
                st.rerun()
    
    return selected_context

def render_context_editor(context_manager: ContextManager, context_name: str = None):
    """Render the context editing UI"""
    
    # Initialize context data
    if context_name:
        context_data = context_manager.get_context(context_name)
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
                if creating_new:
                    # Auto-generate context name from company name if missing
                    if not company_name:
                        st.error("Please provide a company name to create a new context.")
                        return None
                    final_context_name = company_name
                elif context_name:
                    final_context_name = context_name
                else:
                    st.error("Please provide a context name")
                    return None
                
                # Build context data
                updated_context = {
                    "company_name": company_name,
                    "company_info": company_info
                }
                
                context_manager.save_context(final_context_name, updated_context)
                st.success(f"✅ Context '{final_context_name}' saved!")
                
                # Reset state
                st.session_state.creating_new_context = False
                st.rerun()
        
        with col2:
            if not creating_new and context_name:
                if st.button("📥 Export"):
                    exported = context_manager.export_context(context_name)
                    if exported:
                        st.download_button(
                            "⬇️ Download JSON",
                            data=exported,
                            file_name=f"{context_name.replace(' ', '_')}_context.json",
                            mime="application/json"
                        )
        
        with col3:
            if not creating_new and context_name:
                if st.button("Delete This Context"):
                    context_manager.delete_context(context_name)
                    st.success(f"Context '{context_name}' deleted!")
                    st.rerun()
        
        if creating_new:
            if st.button("❌ Cancel"):
                st.session_state.creating_new_context = False
                st.rerun()
    
    # Return the current context for use in the app
    if context_name:
        return context_manager.get_context(context_name)
    return None

def enhance_company_context(extracted_content: str, existing_info: str = "") -> str:
    """Use AI to enhance company context from uploaded documents"""
    try:
        import openai
        from company_config import OPENAI_API_KEY
        
        if not OPENAI_API_KEY:
            return existing_info
        
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
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message['content']
    except Exception:
        return existing_info 