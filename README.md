# farmerBuddy - Complete Setup & Usage Guide

A comprehensive farmer assistance platform with AI-powered form filling, document processing, and browser extension support.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Gemini API Key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))
- Chrome/Edge browser (for extension)

## 📋 Table of Contents
- [Main Application Setup](#main-application-setup)
- [Extension Setup](#extension-setup)
- [API Key Configuration](#api-key-configuration)
- [Usage Instructions](#usage-instructions)
- [Available Commands](#available-commands)
- [Troubleshooting](#troubleshooting)

## Main Application Setup

### 1. Clone & Install
```bash
git clone <repository-url>
cd farmerBuddy
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Initialization
```bash
python app.py
# This will create necessary folders and initialize the database
```

### 3. Run Development Server
```bash
python app.py
# Server starts at http://127.0.0.1:5000
```

## Extension Setup

### 1. Load Extension in Chrome
1. Open Chrome → Extensions → Developer Mode
2. Click "Load unpacked"
3. Select the `extension/` folder

### 2. Extension Permissions
The extension requires:
- Active tab access
- Storage access
- Script injection capabilities

## API Key Configuration

### Required API Keys
1. **Google Gemini API Key** (Required for AI features)
   - Get from: https://makersuite.google.com/app/apikey
   - Add to environment variable: `GEMINI_API_KEY=your_key_here`

2. **Aadhaar Salt** (Required for secure hashing)
   - Set environment variable: `AADHAAR_SALT=your_secure_salt`

### Environment Setup
```bash
# Windows
set GEMINI_API_KEY=your_api_key_here
set AADHAAR_SALT=your_secure_salt

# Linux/Mac
export GEMINI_API_KEY=your_api_key_here
export AADHAAR_SALT=your_secure_salt
```

## Usage Instructions

### Main Application (app.py)

#### 1. Document Upload & Processing
- Navigate to http://127.0.0.1:5000
- Upload PDF documents (Aadhaar, PAN, Land records, etc.)
- Select scheme (PM-Kisan, KCC, RIDF)
- System extracts text and processes documents

#### 2. Form Generation
- Choose template or upload custom form
- System auto-fills forms using extracted data
- Download filled forms

#### 3. Manual Form Filling
- Use `/manual` route for step-by-step form filling
- Upload documents and get assistance

### Extension Usage

#### 1. Collect Form Fields
- Click extension icon on any webpage
- Select scheme and upload document
- Extension collects form fields from the page

#### 2. Autofill Forms
- Paste user ID
- Click "Autofill Page"
- Extension fills forms automatically

## Available Commands

### Backend API Endpoints
```bash
# Document Ingestion
POST /ingest
Content-Type: multipart/form-data
Body: {
  "scheme": "pm-kisan",
  "user_id": "uuid",
  "documents": [file1, file2]
}

# Auto-fill Forms
POST /auto_fill_user
Content-Type: application/json
Body: {
  "user_id": "uuid",
  "output_type": "pdf",
  "fields": [...]
}

# Get Scheme Info
GET /get_scheme_info/<scheme_id>
```

### Extension Commands
```javascript
// Collect fields from page
chrome.runtime.sendMessage({
  action: 'collect_fields'
})

// Apply autofill
chrome.runtime.sendMessage({
  action: 'apply_fields',
  mapped_fields: {...}
})
```

### CLI Commands
```bash
# Development
python app.py

# Testing
pytest tests/

# Database reset
python -c "from app import init_db; init_db()"
```

## Usage Examples

### 1. Upload and Process Documents
```bash
# Start server
python app.py

# Upload via web interface
# Navigate to http://127.0.0.1:5000
# Upload PDF documents
# Select scheme and process
```

### 2. Use Extension
1. Install extension from `extension/` folder
2. Click extension icon on any form page
3. Upload document and select scheme
4. Click "Autofill Page"

### 3. Manual Form Filling
```bash
# Navigate to /manual route
# Upload documents
# Fill forms step by step
```

## Troubleshooting

### Common Issues

#### 1. API Key Not Working
- Ensure `GEMINI_API_KEY` is set correctly
- Check API key validity at Google AI Studio
- Verify environment variables are loaded

#### 2. Extension Not Loading
- Ensure extension is loaded in developer mode
- Check manifest.json permissions
- Verify content script injection

#### 3. Database Issues
- Run `python app.py` to initialize database
- Check file permissions for uploads folder
- Verify SQLite database path

#### 4. File Upload Issues
- Ensure uploads folder exists and has write permissions
- Check file size limits (max 12MB)
- Verify file type restrictions

### Debug Mode
```bash
# Enable debug logging
export FLASK_DEBUG=1
python app.py
```

### Support
- Check logs in browser console for extension issues
- Use `/health` endpoint to verify backend status
- Review error messages in the application

## Security Notes
- Never commit API keys to version control
- Use environment variables for sensitive data
- Validate all user inputs
- Implement proper authentication for production use

## License
This project is provided as-is for educational and demonstration purposes.
