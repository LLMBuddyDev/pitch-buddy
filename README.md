# PitchBuddy

An AI-powered sales outreach assistant that helps generate personalized pitch messages based on LinkedIn profiles and company contexts.

## Features

- 📄 **PDF Processing**: Extract information from LinkedIn profile PDFs
- 🤖 **AI Analysis**: Parse contact details and company information using GPT-4
- 🔍 **Company Research**: Automatically research companies for recent innovations
- 🏢 **Context Management**: Create and manage multiple company contexts
- 📝 **Multiple Output Formats**: Generate different types of outreach messages
- ☁️ **Cloud Ready**: Easy deployment to Streamlit Cloud, Heroku, or other platforms

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key
- Google Custom Search API key and Search Engine ID

### Local Development

1. **Clone and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys:**
   
   **Option A: Using Streamlit Secrets (Recommended for development)**
   ```bash
   mkdir -p .streamlit
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml with your actual API keys
   ```

   **Option B: Using Environment Variables**
   ```bash
   export OPENAI_API_KEY="your_openai_api_key"
   export GOOGLE_API_KEY="your_google_api_key"
   export GOOGLE_CSE_ID="your_google_cse_id"
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

### Cloud Deployment

#### Streamlit Community Cloud (FREE - Recommended)

1. **Push your code to GitHub** (make sure `.streamlit/secrets.toml` is in `.gitignore`)
2. **Connect your GitHub repo** to [Streamlit Cloud](https://share.streamlit.io/)
3. **Add secrets** in the Streamlit Cloud dashboard:
   ```toml
   [openai]
   api_key = "your_openai_api_key"
   
   [google]
   api_key = "your_google_api_key"
   cse_id = "your_google_cse_id"
   ```
4. **Deploy!** Your app will be live at `https://yourapp.streamlit.app`

#### Heroku

1. **Create a Heroku app:**
   ```bash
   heroku create your-pitchbuddy-app
   ```

2. **Set environment variables:**
   ```bash
   heroku config:set OPENAI_API_KEY="your_openai_api_key"
   heroku config:set GOOGLE_API_KEY="your_google_api_key"
   heroku config:set GOOGLE_CSE_ID="your_google_cse_id"
   ```

3. **Deploy:**
   ```bash
   git push heroku main
   ```

## Getting API Keys

### OpenAI API Key
1. Go to [OpenAI API](https://platform.openai.com/api-keys)
2. Create a new API key
3. Make sure you have credits in your OpenAI account

### Google Custom Search API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the "Custom Search API"
3. Create an API key
4. Set up a [Custom Search Engine](https://cse.google.com/cse/)
5. Get your Search Engine ID

## Usage

1. **Create Company Context**: Set up your company's information, technology, value propositions, and positioning
2. **Upload LinkedIn PDF**: Upload a prospect's LinkedIn profile as PDF
3. **Add Notes**: Optionally add additional context about the person or company
4. **Select Output Format**: Choose from outreach message, internal summary, voicemail script, or meeting prep
5. **Generate Pitch**: AI will create a personalized message based on all inputs

## Security

- API keys are handled securely through environment variables or Streamlit secrets
- No sensitive data is hardcoded in the application
- Company contexts are stored locally as JSON files
- All data processing happens on secure cloud infrastructure

## File Structure

```
pitch-buddy/
├── app.py                    # Main Streamlit application
├── company_config.py         # Secure API key handling
├── context_manager.py        # Company context management
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md                # This file
└── .streamlit/
    └── secrets.toml.template # Template for local secrets
```

## Contributing

This is a private internal tool. For feature requests or bug reports, contact the development team. 