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

# --- Usage Protection ---
DAILY_LIMIT = 250  # Maximum requests per day per session

def check_usage_limit():
    """Check and enforce daily usage limits"""
    import datetime
    
    today = datetime.date.today().isoformat()
    
    # Initialize usage tracking
    if 'usage_date' not in st.session_state or st.session_state.usage_date != today:
        st.session_state.usage_date = today
        st.session_state.daily_count = 0
    
    # Check if limit exceeded
    if st.session_state.daily_count >= DAILY_LIMIT:
        st.error(f"⚠️ Daily usage limit reached ({DAILY_LIMIT} requests). Please try again tomorrow.")
        st.info("This limit helps prevent unexpected API charges.")
        st.stop()
    
    return True

def increment_usage():
    """Increment the usage counter"""
    if 'daily_count' not in st.session_state:
        st.session_state.daily_count = 0
    st.session_state.daily_count += 1
    
    remaining = DAILY_LIMIT - st.session_state.daily_count
    if remaining <= 10:
        st.warning(f"⚠️ {remaining} requests remaining today")

# Apply usage protection
check_usage_limit()

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

def generate_pitch(profile_summary, company_summary, product_info, task_instruction, user_name=""):
    if not product_info:
        return "❌ No company context selected. Please create and select a company context first."
    
    # Add user name to prompt if provided and it's an email
    name_instruction = ""
    if user_name.strip() and "email" in task_instruction.lower():
        name_instruction = f"\nSign the email with: Best regards,\n{user_name.strip()}"
    
    prompt = f"""
You are a business development AI assistant.
Your task: {task_instruction}{name_instruction}

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

IMPORTANT: If this is an email, format your response as:
SUBJECT: [subject line here]

[email body here]

This makes it easy to copy the subject and body separately.
"""
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content

def render_single_copy_button(pitch, output_type):
    """Helper function to render a single copy button"""
    escaped_pitch = html.escape(pitch)

    copy_label = {
        "Email outreach": ("📋 Copy email to clipboard", "Email copied!"),
        "LinkedIn DM": ("📋 Copy LinkedIn DM to clipboard", "LinkedIn DM copied!"),
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

# --- Streamlit UI ---
st.title("PitchBuddy")

# Check for API keys
if not OPENAI_API_KEY or not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
    st.warning("⚠️ API keys not configured. Please check your environment variables or secrets.toml file.")
    st.stop()

# Usage display in sidebar
with st.sidebar:
    st.header("📊 Usage")
    daily_count = st.session_state.get('daily_count', 0)
    remaining = DAILY_LIMIT - daily_count
    st.metric("Requests Today", daily_count, f"{remaining} remaining")
    
    if remaining <= 10:
        st.warning("⚠️ Low requests remaining")
    
    st.markdown("---")
    st.markdown("**📝 Daily Limit:** 250 requests")
    st.caption("Limits reset daily to prevent API overcharges")

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
    
    # User name for email sign-offs
    user_name = st.text_input(
        "Your name (for email sign-offs):", 
        value="", 
        placeholder="e.g., John Smith",
        help="We don't save this - it just automatically fills the email sign-offs"
    )
    st.caption("💡 **Note:** We don't save this - it just automatically fills the email sign-offs")
    
    message_instructions = st.text_area(
        "Specific message instructions:", 
        value="", 
        placeholder="e.g., 'Keep under 100 words', 'Use casual tone', 'Mention our partnership with Microsoft', 'Focus on cost savings', etc.",
        help="Specify tone, length, style, key points to emphasize, or any other guidance for the message"
    )

    output_type = st.radio(
        "Select output format",
        (
            "Email outreach",
            "LinkedIn DM", 
            "Internal-fit summary",
            "Cold-call voicemail",
            "Long-form meeting prep"
        ),
        index=0
    )

    if st.button("Generate Pitch"):
        # Check usage limit before making API call
        check_usage_limit()
        
        with st.spinner("Generating pitch..."):
            # Increment usage counter
            increment_usage()
            
            # Combine profile information with personal notes
            combined_profile = extracted_profile_text
            if profile_notes.strip():
                combined_profile += f"\n\nAdditional personal insights:\n{profile_notes.strip()}"
            
            # Combine company research with any existing notes
            combined_company_info = company_summary_internal
            
            # Build enhanced task instruction with user specifications
            task_instructions = {
                "Email outreach": (
                    "Write a professional email outreach message (under 150 words) in a friendly, professional tone. "
                    "Include a clear subject line. Be specific with addressing the prospect. "
                    "Be sure to lean on their resume more than external data but consider both."
                ),
                "LinkedIn DM": (
                    "Write a LinkedIn direct message (under 100 words) in a conversational, professional tone. "
                    "Keep it concise and personalized. Focus on building connection and sparking interest. "
                    "Be sure to reference their background and make it feel genuine, not salesy."
                ),
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
            }
            
            base_task_instruction = task_instructions.get(output_type, task_instructions["Email outreach"])
            
            # Add message instructions if provided
            if message_instructions.strip():
                enhanced_task_instruction = f"{base_task_instruction}\n\nSpecific instructions: {message_instructions.strip()}"
            else:
                enhanced_task_instruction = base_task_instruction

            pitch = generate_pitch(combined_profile, combined_company_info, current_context, enhanced_task_instruction, user_name)
            st.subheader("🎯 Generated Message")
            st.code(pitch, language="markdown")

            # Handle email formatting with separate subject and body
            if output_type == "Email outreach" and "SUBJECT:" in pitch:
                # Parse subject and body
                lines = pitch.split('\n')
                subject_line = ""
                body_lines = []
                found_subject = False
                
                for line in lines:
                    if line.startswith("SUBJECT:"):
                        subject_line = line.replace("SUBJECT:", "").strip()
                        found_subject = True
                    elif found_subject and line.strip():
                        body_lines.append(line)
                
                email_body = '\n'.join(body_lines).strip()
                
                if subject_line and email_body:
                    st.write("---")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**📧 Subject Line:**")
                        st.code(subject_line, language="text")
                        
                        # Subject copy button
                        escaped_subject = html.escape(subject_line)
                        subject_copy_js = f"""
                        <div>
                          <textarea id="subject-text" style="position:absolute; left:-1000px; top:-1000px;">{escaped_subject}</textarea>
                          <button id="subject-copy-btn" style="font-size: 16px; padding: 8px 16px; cursor: pointer;">
                            📋 Copy Subject
                          </button>
                          <script>
                            const subjectBtn = document.getElementById('subject-copy-btn');
                            subjectBtn.onclick = function() {{
                              navigator.clipboard.writeText(document.getElementById('subject-text').value).then(function() {{
                                subjectBtn.innerText = '✅ Subject Copied!';
                                setTimeout(() => {{ subjectBtn.innerText = '📋 Copy Subject'; }}, 2000);
                              }});
                            }}
                          </script>
                        </div>
                        """
                        st.components.v1.html(subject_copy_js, height=50)
                    
                    with col2:
                        st.write("**✉️ Email Body:**")
                        st.code(email_body, language="text")
                        
                        # Body copy button
                        escaped_body = html.escape(email_body)
                        body_copy_js = f"""
                        <div>
                          <textarea id="body-text" style="position:absolute; left:-1000px; top:-1000px;">{escaped_body}</textarea>
                          <button id="body-copy-btn" style="font-size: 16px; padding: 8px 16px; cursor: pointer;">
                            📋 Copy Email Body
                          </button>
                          <script>
                            const bodyBtn = document.getElementById('body-copy-btn');
                            bodyBtn.onclick = function() {{
                              navigator.clipboard.writeText(document.getElementById('body-text').value).then(function() {{
                                bodyBtn.innerText = '✅ Email Copied!';
                                setTimeout(() => {{ bodyBtn.innerText = '📋 Copy Email Body'; }}, 2000);
                              }});
                            }}
                          </script>
                        </div>
                        """
                        st.components.v1.html(body_copy_js, height=50)
                else:
                    # Fallback to regular copy button if parsing fails
                    render_single_copy_button(pitch, output_type)
            else:
                # Regular copy button for non-email outputs
                render_single_copy_button(pitch, output_type)

elif not st.session_state.get("creating_new_context", False):
    st.info("👆 Create your first company context above to start generating pitches!")
