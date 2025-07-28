import streamlit as st
from openai import OpenAI
import PyPDF2
import requests
import json
import html
from company_config import OPENAI_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID
from context_manager import ContextManager, render_context_selector, render_context_editor

# --- Config ---
st.set_page_config(page_title="PitchBuddy", layout="wide")

# Initialize OpenAI client
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None

# Initialize context manager
if 'context_manager' not in st.session_state:
    st.session_state.context_manager = ContextManager()

#attempting to put Be Vietnam Pro (a la Ted's lore) in all UI. We will see how this goes lol 
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"]  {
    font-family: 'Be Vietnam Pro', sans-serif !important;
}
textarea, input, button, select, div, span {
    font-family: 'Be Vietnam Pro', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# --- Utilities ---
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def parse_linkedin_profile_with_llm(text):
    prompt = f"""
You are a helpful assistant. Extract the following details from this LinkedIn profile text:

- Full Name
- Job Title
- Company Name

Return *only* valid JSON in this exact format:
{{
  "name": "...",
  "title": "...",
  "company": "..."
}}

If any info is missing, put "Not found" in that field.

Profile text:
\"\"\"
{text}
\"\"\"
"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        json_text = response.choices[0].message.content.strip()
        data = json.loads(json_text)
        return data.get("name", ""), data.get("title", ""), data.get("company", "")
    except Exception:
        return "", "", ""

def search_company_summary(company_name):
    if not company_name or company_name.lower() == "not found":
        return ""
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": f"{company_name} recent innovations or projects in AI, moving to cloud, or cybersecurity",
        "num": 3,
    }
    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        results = response.json().get("items", [])
        summary = ""
        for item in results:
            summary += f"- **{item['title']}**: {item['snippet']} ({item['link']})\n"
        return summary if summary else "No relevant recent information found online."
    except Exception as e:
        return f"Error retrieving data: {e}"

def summarize_company_info(company_name, profile_text):
    web_data = search_company_summary(company_name)
    combined_source = f"""
Company: {company_name}

Web data:
{web_data}

LinkedIn profile text:
{profile_text}
"""
    prompt = f"""Summarize this information about {company_name} in 80–120 words, focusing on recent innovation projects or AI/cloud/cybersecurity efforts:

{combined_source}
"""
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content

def generate_pitch(profile_summary, company_summary, product_info, task_instruction):
    if not product_info:
        return "❌ No company context selected. Please create and select a company context first."
    
    prompt = f"""
You are a business development AI assistant.
Your task: {task_instruction}

---
PROSPECT PROFILE:
{profile_summary}

PROSPECT'S COMPANY RESEARCH:
{company_summary}

YOUR COMPANY INFO:
Company: {product_info.get('company_name', 'Unknown')}
Company Information: {product_info.get('company_info', 'No information provided')}
---

Generate the requested content following the task instructions above. Pay special attention to any specific instructions provided (tone, length, style, key points, etc.).
"""
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

# --- Streamlit UI ---
st.title("PitchBuddy")

# Check for API keys
if not OPENAI_API_KEY or not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    st.warning("⚠️ API keys not configured. Please check your environment variables or secrets.toml file.")
    st.stop()

# Context Management Section
selected_context_name = render_context_selector(st.session_state.context_manager)
current_context = render_context_editor(st.session_state.context_manager, selected_context_name)

# Only show the main app if we have a context selected
if selected_context_name and current_context:
    st.write("---")
    st.subheader("🎯 Generate Pitch")
    
    uploaded_pdf = st.file_uploader("Upload LinkedIn Profile PDF", type=["pdf"])

    extracted_profile_text = ""
    detected_name = ""
    detected_title = ""
    detected_company = ""
    company_summary_internal = ""

    if uploaded_pdf:
        with st.spinner("Extracting text from PDF..."):
            extracted_profile_text = extract_text_from_pdf(uploaded_pdf)

        with st.spinner("Parsing profile info with AI..."):
            detected_name, detected_title, detected_company = parse_linkedin_profile_with_llm(extracted_profile_text)

        if detected_name and detected_name.lower() != "not found":
            st.success(f"Detected name: {detected_name}")
        else:
            st.info("Detected name: Not found")

        if detected_title and detected_title.lower() != "not found":
            st.success(f"Detected title: {detected_title}")
        else:
            st.info("Detected title: Not found")

        if detected_company and detected_company.lower() != "not found":
            st.success(f"Detected company: {detected_company}")
            company_summary_internal = summarize_company_info(detected_company, extracted_profile_text)
        else:
            st.info("Detected company: Not found")

        if company_summary_internal:
            with st.expander("📌 Company Research Summary"):
                st.markdown(company_summary_internal)

    profile_notes = st.text_area("Optional: Add additional notes about the person", value="", placeholder="Anything beyond the LinkedIn: personal details, specific interests, recent achievements, mutual connections, etc.")
    
    message_instructions = st.text_area(
        "Specific message instructions:", 
        value="", 
        placeholder="e.g., 'Keep under 100 words', 'Use casual tone', 'Mention our partnership with Microsoft', 'Focus on cost savings', etc.",
        help="Specify tone, length, style, key points to emphasize, or any other guidance for the message"
    )

    output_type = st.radio(
        "Select output format",
        (
            "Full outreach message",
            "Internal-fit summary",
            "Cold-call voicemail",
            "Long-form meeting prep"
        ),
        index=0
    )

    if st.button("Generate Pitch"):
        with st.spinner("Generating pitch..."):
            # Combine profile information with personal notes
            combined_profile = extracted_profile_text
            if profile_notes.strip():
                combined_profile += f"\n\nAdditional personal insights:\n{profile_notes.strip()}"
            
            # Combine company research with any existing notes
            combined_company_info = company_summary_internal
            
            # Build enhanced task instruction with user specifications
            base_task_instruction = {
                "Internal-fit summary": (
                    "In 150 words or fewer, state how this organization is a strong fit for the product — "
                    "describe the best use case or alignment with their innovation, goals, or challenges. "
                    "Do not write a message to them directly; this is for internal BD insight."
                ),
                "Cold-call voicemail": (
                    "Write a one-sentence cold-call voicemail script that's direct, conversational, and "
                    "leaves a hook for the prospect to call back, max 35 words."
                ),
                "Long-form meeting prep": (
                    "Write a bullet-pointed internal briefing of 150 words or fewer (2–6 bullets). "
                    "Explain how our product might be introduced and discussed in a longer meeting with the prospect, and some topics to expand upon during a meeting. "
                    "Emphasize alignment with their personal background and company priorities. Use a neutral internal tone."
                ),
            }.get(
                output_type,
                (
                    "Write a full outreach message (under 150 words) in a friendly, professional tone. Be specific with addressing the prospect. "
                    "Be sure to lean on their resume more than external data but consider both."
                )
            )
            
            # Add message instructions if provided
            if message_instructions.strip():
                enhanced_task_instruction = f"{base_task_instruction}\n\nSpecific instructions: {message_instructions.strip()}"
            else:
                enhanced_task_instruction = base_task_instruction

            pitch = generate_pitch(combined_profile, combined_company_info, current_context, enhanced_task_instruction)
            st.subheader("🎯 Generated Message")
            st.code(pitch, language="markdown")

            # Copy to clipboard button
            escaped_pitch = html.escape(pitch)

            copy_label = {
                "Full outreach message": ("📋 Copy outreach message to clipboard", "Outreach message copied!"),
                "Internal-fit summary": ("📋 Copy summary to clipboard", "Summary copied!"),
                "Cold-call voicemail": ("📋 Copy voicemail to clipboard", "Voicemail copied!"),
                "Long-form meeting prep": ("📋 Copy meeting prep to clipboard", "Meeting prep copied!")
            }.get(output_type, ("📋 Copy pitch to clipboard", "Pitch copied!"))

            copy_js = f"""
            <div>
              <textarea id="pitch-text" style="position:absolute; left:-1000px; top:-1000px;">{escaped_pitch}</textarea>
              <button id="copy-btn" style="font-size: 18px; padding: 10px 20px; cursor: pointer;">
                {copy_label[0]}
              </button>
              <script>
                const btn = document.getElementById('copy-btn');
                btn.onclick = function() {{
                  navigator.clipboard.writeText(document.getElementById('pitch-text').value).then(function() {{
                    btn.innerText = '{copy_label[1]}';
                  }});
                }}
              </script>
            </div>
            """
            st.components.v1.html(copy_js, height=60)

elif not st.session_state.get("creating_new_context", False):
    st.info("👆 Create your first company context above to start generating pitches!")
