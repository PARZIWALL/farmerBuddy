<<<<<<< HEAD
import os
import json
import time
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from docx import Document
import google.generativeai as genai
import pytesseract
import fitz  # PyMuPDF
from PIL import Image

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated_forms'
TEMPLATE_FOLDER = 'application_templates'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'docx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER
app.config['TEMPLATE_FOLDER'] = TEMPLATE_FOLDER
app.secret_key = 'your_super_secret_key' # Change this in production

# --- Gemini API Configuration ---
# IMPORTANT: Set your GEMINI_API_KEY as an environment variable
# For example, in your terminal: export GEMINI_API_KEY="your_actual_api_key"
GEMINI_API_KEY = ""
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.0-pro')
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
else:
    print("GEMINI_API_KEY environment variable not found.")

# --- Scheme Configuration ---
SCHEMES = {
    'pm-kisan': {
        'name': 'Pradhan Mantri Kisan Samman Nidhi (PM-Kisan)',
        'template_file': 'pm-kisan_new_application_form_english.docx',
        'required_documents': [
            'Aadhaar Card',
            'Bank Passbook/Statement',
            'Land Records (Khasra/Khatauni)'
        ],
        'additional_documents': [
            'Aadhaar Card photocopy',
            'Bank Passbook photocopy',
            'Land ownership documents',
            '2 Passport size photographs',
        ]
    },
    'kcc': {
        'name': 'Kisan Credit Card (KCC)',
        'template_file': 'kcc_application_format.docx',
        'required_documents': [
            'Aadhaar Card',
            'PAN Card',
            'Bank Passbook',
            'Land Records',
        ],
        'additional_documents': [
            'Aadhaar Card photocopy',
            'PAN Card photocopy',
            'Land ownership proof',
            '2 Passport size photographs'
        ]
    },
    'ridf': {
        'name': 'Rural Infrastructure Development Fund (RIDF)',
        'template_file': 'RIDF G.APPLICATION FORM (1).docx',
        'required_documents': [
            'Project Proposal',
            'Land Documents',
            'Aadhaar Card of authorized person',
            'Bank Passbook'
        ],
        'additional_documents': [
            'Detailed project proposal',
            'Land ownership documents',
            'Identity and address proof of promoters',
            'Bank account statements'
        ]
    }
}

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if a file's extension is in the ALLOWED_EXTENSIONS set."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath):
    """Extracts text from various file types (pdf, image, docx)."""
    text = ""
    try:
        extension = filepath.rsplit('.', 1)[1].lower()
        if extension == 'pdf':
            with fitz.open(filepath) as doc:
                for page in doc:
                    text += page.get_text()
        elif extension in ('png', 'jpg', 'jpeg'):
            text = pytesseract.image_to_string(Image.open(filepath))
        elif extension == 'docx':
            doc = Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + "\t"
                    text += "\n"
    except Exception as e:
        print(f"Error extracting text from {filepath}: {e}")
    return text

def generate_field_name_from_label(label):
    """Generates a standardized snake_case field name from a given label."""
    # Lowercase, remove punctuation, strip whitespace
    name = label.lower().strip().replace(':', '').replace('*', '').replace('.', '')
    # Replace spaces and hyphens with underscores
    name = name.replace(' ', '_').replace('-', '_')
    # Remove any duplicate underscores
    name = "_".join(filter(None, name.split('_')))
    return name

def analyze_form_fields_with_rag(template_path):
    """Analyzes a DOCX form to identify fillable fields using heuristics and Gemini AI for refinement."""
    if not model:
        flash("AI Model is not configured. Please set the GEMINI_API_KEY.", "danger")
        return []

    try:
        doc = Document(template_path)
        raw_fields = []
        # Heuristically find potential fields in tables and paragraphs
        for table_idx, table in enumerate(doc.tables):
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    text = cell.text.strip()
                    if text and (':' in text or len(text.split()) < 5) and cell_idx + 1 < len(row.cells):
                        raw_fields.append({
                            "field_id": f"table_{table_idx}_row_{row_idx}_cell_{cell_idx+1}",
                            "label": text.replace(':', '').strip()
                        })

        for para_idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if ':' in text and len(text.split(':')[-1].strip()) < 10: # Label-like paragraphs
                raw_fields.append({
                    "field_id": f"para_{para_idx}",
                    "label": text.split(':')[0].strip()
                })

        if not raw_fields:
            return []

        # Use RAG to enhance and structure the found fields
        prompt = f"""
        You are an AI expert at analyzing Indian government application forms.
        Based on the following list of field labels extracted from a form, please process them.

        Extracted Labels:
        {json.dumps(raw_fields, indent=2)}

        Your tasks are to:
        1. Consolidate semantically duplicate fields (e.g., "Applicant Name" and "Full Name").
        2. Generate a standardized, snake_case `field_name` for each unique field (e.g., 'father_name', 'date_of_birth').
        3. Determine the most appropriate HTML input `field_type` (e.g., 'text', 'date', 'number', 'email', 'tel', 'select').
        4. Assign a `priority` score from 1 (least important) to 10 (most important).
        5. Keep the original `field_id` for mapping. If consolidating, choose the most appropriate `field_id`.

        Return ONLY a valid JSON array of objects, where each object represents a unique field.
        Example format:
        [
          {{
            "field_id": "table_0_row_1_cell_1",
            "field_name": "applicant_name",
            "label": "Applicant Name",
            "field_type": "text",
            "priority": 10
          }}
        ]

        JSON Output:
        """
        response = model.generate_content(prompt)
        # Clean the response to get a valid JSON string
        json_string = response.text.strip().replace('```json', '').replace('```', '')
        enhanced_fields = json.loads(json_string)
        return enhanced_fields

    except Exception as e:
        print(f"Error analyzing form fields with RAG: {e}")
        flash(f"AI could not analyze the form. Error: {e}", "warning")
        return []


def get_structured_data_with_rag(documents_text, required_fields):
    """Uses Gemini AI (RAG) to extract structured data from text based on a list of required fields."""
    if not model or not documents_text:
        return {}

    # The "Retrieval" part: providing the structured fields the model should look for.
    fields_json = json.dumps([{"field_name": f["field_name"], "label": f["label"]} for f in required_fields], indent=2)

    prompt = f"""
    You are an AI assistant specialized in extracting data from Indian KYC and land documents.
    Based on the **Required Fields** list below, extract the corresponding information from the **Document Text**.

    **Required Fields (JSON format):**
    {fields_json}

    **Document Text:**
    ---
    {documents_text}
    ---

    **Instructions:**
    1. Carefully map the information from the text to the `field_name` in the required fields list.
    2. Pay close attention to details like names, dates (format as YYYY-MM-DD), and multi-digit numbers (Aadhaar, Account numbers).
    3. If a piece of information for a required field is not found, use an empty string `""` as its value.
    4. Return ONLY a single, valid JSON object where keys are the `field_name`s from the list.

    JSON Output:
    """
    try:
        response = model.generate_content(prompt)
        json_string = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(json_string)
    except Exception as e:
        print(f"Error calling Gemini API or parsing JSON: {e}")
        return {}

def fill_form_template_precise(template_path, form_data, output_name):
    """Fills the DOCX template with data, placing it at the precise field locations."""
    try:
        doc = Document(template_path)
        filled_any = False

        for field_id, value in form_data.items():
            if not value:
                continue
            
            try:
                parts = field_id.split('_')
                if field_id.startswith('table_'):
                    table_idx, row_idx, cell_idx = int(parts[1]), int(parts[3]), int(parts[5])
                    if table_idx < len(doc.tables) and row_idx < len(doc.tables[table_idx].rows) and cell_idx < len(doc.tables[table_idx].rows[row_idx].cells):
                        target_cell = doc.tables[table_idx].rows[row_idx].cells[cell_idx]
                        target_cell.text = value
                        filled_any = True
                elif field_id.startswith('para_'):
                    para_idx = int(parts[1])
                    if para_idx < len(doc.paragraphs):
                        para = doc.paragraphs[para_idx]
                        # Append value, preserving the label
                        if ':' in para.text:
                            para.text = para.text.split(':')[0] + ': ' + value
                        else:
                            para.text = value
                        filled_any = True
            except (ValueError, IndexError) as e:
                print(f"Could not parse or find position for field_id {field_id}: {e}")
                continue

        if not filled_any:
            print("Warning: No fields were filled in the document.")
            return None

        timestamp = str(int(time.time()))
        output_filename = f"{output_name}-filled-{timestamp}.docx"
        output_path = os.path.join(app.config['GENERATED_FOLDER'], output_filename)
        doc.save(output_path)
        return output_filename

    except Exception as e:
        print(f"Error filling form template: {e}")
        return None

# --- App Routes ---
@app.route('/')
def index():
    return render_template('index.html', schemes=SCHEMES)

@app.route('/auto_fill', methods=['GET', 'POST'])
def auto_fill():
    if not model:
        flash("AI Model is not configured due to missing API key. Please contact the administrator.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        scheme_id = request.form.get('scheme')
        files = request.files.getlist('documents')

        if not scheme_id or scheme_id not in SCHEMES:
            flash('Please select a valid scheme.', 'danger')
            return redirect(request.url)

        if not files or all(f.filename == '' for f in files):
            flash('Please upload the required documents.', 'danger')
            return redirect(request.url)

        scheme_info = SCHEMES[scheme_id]
        template_path = os.path.join(app.config['TEMPLATE_FOLDER'], scheme_info['template_file'])
        
        if not os.path.exists(template_path):
            flash(f'Template file for {scheme_info["name"]} not found.', 'danger')
            return redirect(request.url)

        try:
            # 1. Analyze the form template to understand its fields
            required_fields = analyze_form_fields_with_rag(template_path)
            if not required_fields:
                flash('Could not analyze the form template to identify fields.', 'danger')
                return redirect(request.url)

            # 2. Extract text from all uploaded user documents
            combined_text = ""
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    combined_text += extract_text_from_file(filepath) + "\n\n"

            if not combined_text.strip():
                flash('Could not extract any text from your documents. Please check the file formats and quality.', 'danger')
                return redirect(request.url)

            # 3. Use RAG to get structured data from the text
            extracted_data = get_structured_data_with_rag(combined_text, required_fields)
            if not extracted_data:
                flash('AI failed to extract structured information from your documents.', 'danger')
                return redirect(request.url)

            # 4. Map the extracted data to the field IDs from the form analysis
            field_mapped_data = {}
            for field in required_fields:
                field_name = field.get('field_name')
                if field_name in extracted_data and extracted_data[field_name]:
                    field_mapped_data[field['field_id']] = str(extracted_data[field_name])
            
            # 5. Fill the form with precise positioning
            filled_form_filename = fill_form_template_precise(template_path, field_mapped_data, scheme_id)

            if filled_form_filename:
                flash(f'Form filled successfully! You may also need to submit: {", ".join(scheme_info["additional_documents"])}.', 'success')
                return redirect(url_for('download_page', filename=filled_form_filename))
            else:
                flash('An error occurred while filling the form. It is possible no data could be mapped.', 'danger')
                return redirect(request.url)
                
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('auto_fill.html', schemes=SCHEMES)

@app.route('/manual', methods=['GET', 'POST'])
def manual_fill():
    if not model:
        flash("AI Model is not configured due to missing API key. Please contact the administrator.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        step = request.form.get('step')

        if step == '1':
            form_file = request.files.get('form_template')
            support_docs = request.files.getlist('support_documents')

            if not form_file or not allowed_file(form_file.filename) or not form_file.filename.endswith('.docx'):
                flash('Please upload a valid DOCX form template.', 'danger')
                return redirect(request.url)

            try:
                form_filename = secure_filename(form_file.filename)
                form_path = os.path.join(app.config['UPLOAD_FOLDER'], form_filename)
                form_file.save(form_path)

                # Analyze form fields using RAG
                required_fields = analyze_form_fields_with_rag(form_path)
                if not required_fields:
                    flash('Could not analyze the form. Ensure it contains identifiable fields (like "Name:", "Address:", etc.).', 'danger')
                    return redirect(request.url)

                # Pre-fill data if supporting documents are provided
                extracted_data = {}
                if support_docs and any(f.filename for f in support_docs):
                    combined_text = ""
                    for doc in support_docs:
                        if doc and allowed_file(doc.filename):
                            doc_filename = secure_filename(doc.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
                            doc.save(filepath)
                            combined_text += extract_text_from_file(filepath) + "\n\n"
                    
                    if combined_text.strip():
                        extracted_data = get_structured_data_with_rag(combined_text, required_fields)

                # Merge extracted data into the fields list
                if extracted_data:
                    for field in required_fields:
                        if field['field_name'] in extracted_data and extracted_data[field['field_name']]:
                            field['pre_filled_value'] = extracted_data[field['field_name']]

                return render_template('manual_fill_step2.html', 
                                     fields=required_fields, 
                                     form_filename=form_filename,
                                     has_extracted_data=bool(extracted_data))
            except Exception as e:
                flash(f'Error processing your request: {e}', 'danger')
                return redirect(request.url)
        
        elif step == '2':
            form_filename = request.form.get('form_filename')
            form_path = os.path.join(app.config['UPLOAD_FOLDER'], form_filename)

            if not form_filename or not os.path.exists(form_path):
                flash('Form template not found. Please start over.', 'danger')
                return redirect(url_for('manual_fill'))
            
            form_data = {key: value for key, value in request.form.items() if key not in ['step', 'form_filename']}
            
            filled_form_filename = fill_form_template_precise(form_path, form_data, "manual-form")

            if filled_form_filename:
                flash('Form filled successfully! Please review the downloaded document.', 'success')
                return redirect(url_for('download_page', filename=filled_form_filename))
            else:
                flash('An error occurred while filling the form. No data was entered.', 'danger')
                return redirect(url_for('manual_fill'))

    return render_template('manual_fill.html')

@app.route('/get_scheme_info/<scheme_id>')
def get_scheme_info(scheme_id):
    """API endpoint to get scheme information for the frontend."""
    scheme = SCHEMES.get(scheme_id)
    if scheme:
        return jsonify(scheme)
    return jsonify({'error': 'Scheme not found'}), 404

@app.route('/download_page/<filename>')
def download_page(filename):
    """Shows a page with a download link for the generated form."""
    return render_template('download.html', filename=filename)

@app.route('/generated/<filename>')
def download_form(filename):
    """Serves the generated form for downloading."""
    return send_from_directory(app.config['GENERATED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Create necessary folders on startup
    for folder in [UPLOAD_FOLDER, GENERATED_FOLDER, TEMPLATE_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    app.run(debug=True)
=======
<<<<<<< HEAD
import io
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st
from docx import Document
import re
from datetime import datetime
# ---------------- CONFIG ----------------
SCHEMES_INFO = {
    "PM-Kisan": {
        "name": "Pradhan Mantri Kisan Samman Nidhi Yojana",
        "description": "Direct income support of ₹6,000 per year for land-holding farmer families.",
        "eligibility": "All land-holding farmer families, subject to certain exclusion criteria (e.g., income tax payers, high-pensioners).",
        "documents_required": [
            "Land ownership documents (e.g., Khasra/Khatauni)",
            "Aadhaar Card (Mandatory for eKYC)",
            "Bank Account Passbook (for direct benefit transfer)",
            "Proof of Citizenship",
            "Passport Size Photograph"
        ],
        "submission_notes": "Submit the filled form and all documents to a Common Service Center (CSC), your local Patwari, or a designated Nodal Officer. Online self-registration is also available on the official PM-KISAN portal.",
        "template_file": "templates/pm-kisan_application_form.docx",
        "official_link": "https://pmkisan.gov.in/"
    },
    "PM-KMY": {
        "name": "Pradhan Mantri Kisan Maan Dhan Yojana",
        "description": "A voluntary and contributory pension scheme for small and marginal farmers.",
        "eligibility": "Small and Marginal Farmers (SMF) aged between 18 and 40 with cultivable land up to 2 hectares.",
        "documents_required": [
            "Aadhaar Card",
            "Bank Passbook or Bank Account Details",
            "Land Records (Khasra/Khatauni)",
            "Passport Size Photograph"
        ],
        "submission_notes": "Enrollment is done at the nearest Common Service Center (CSC). You will need to provide the filled form and documents, and the CSC will complete the online registration for you. PM-KISAN beneficiaries can opt for auto-debit of their contributions from the benefits they receive.",
        "template_file": "templates/pm-kmy_application_form.docx",
        "official_link": "https://pmkmy.gov.in/"
    },
    "KCC": {
        "name": "Kisan Credit Card",
        "description": "Concessional credit facility for agricultural and allied activities, offering short-term loans up to ₹3 lakh.",
        "eligibility": "All farmers, including owner cultivators, tenant farmers, sharecroppers, and members of Self Help Groups (SHGs) or Joint Liability Groups (JLGs).",
        "documents_required": [
            "Duly filled and signed application form",
            "Aadhaar Card",
            "PAN Card",
            "Land ownership/cultivation documents (e.g., land records, lease agreement)",
            "Bank Account Passbook",
            "Passport size photographs (2-3 copies)",
            "Income Certificate",
            "Any other security documents required by the bank"
        ],
        "submission_notes": "Submit the completed application form and all required documents to the bank's branch where you wish to open the account. The bank will then verify the details and process your application.",
        "template_file": "templates/kcc_application_form.docx",
        "official_link": "https://pmkisan.gov.in/Documents/Kcc.pdf"
    },
    "PMFBY": {
        "name": "Pradhan Mantri Fasal Bima Yojana",
        "description": "A crop insurance scheme that provides financial support to farmers suffering crop loss/damage arising out of unforeseen events.",
        "eligibility": "All farmers, including sharecroppers and tenant farmers, growing notified crops in a notified area.",
        "documents_required": [
            "Aadhaar Card",
            "Bank Account Passbook",
            "Land Records (Khatauni/Patwari records)",
            "Sowing Certificate from Village Revenue Officer",
            "Passport Size Photograph"
        ],
        "submission_notes": "The form must be submitted to the nearest bank branch, cooperative society, or CSC. Farmers who have taken institutional loans will have their premiums deducted automatically.",
        "template_file": "templates/pmfby_application_form.docx",
        "official_link": "https://pmfby.gov.in/"
    },
    "Soil Health Card": {
        "name": "Soil Health Card Scheme",
        "description": "A scheme to provide a Soil Health Card to all farmers, containing information on nutrient status and recommendations for soil improvement.",
        "eligibility": "All farmers with agricultural land.",
        "documents_required": [
            "Aadhaar Card",
            "Land records (Khatauni)",
            "Mobile number",
            "Copy of Bank Passbook"
        ],
        "submission_notes": "The form should be submitted to the local Agriculture Department or Krishi Vigyan Kendra. A soil sample will be collected from your farm for testing, and the card will be issued based on the results.",
        "template_file": "templates/soil_health_card_form.docx",
        "official_link": "https://soilhealth.dac.gov.in/"
    },
    "PM-KISAN SAMMAN": {
        "name": "Pradhan Mantri Kisan Samman Nidhi - Samman Patra (Certificate)",
        "description": "A scheme providing certificates to all PM-KISAN beneficiaries, verifying their enrollment in the scheme.",
        "eligibility": "All enrolled beneficiaries of the PM-KISAN scheme.",
        "documents_required": [
            "Aadhaar Card",
            "PM-KISAN registration number",
            "Land records (Khatauni)"
        ],
        "submission_notes": "The certificate can be downloaded online from the PM-KISAN official website or obtained from a CSC. The form is for verifying and updating beneficiary details before the certificate is issued.",
        "template_file": "templates/pm_kisan_samman_patra_form.docx",
        "official_link": "https://pmkisan.gov.in/"
    }
}

# ---------------- CORE DYNAMIC FUNCTIONS ----------------

def guess_input_type(label_text: str) -> str:
    """Guesses the input type based on keywords in the label."""
    text = label_text.lower()
    if any(keyword in text for keyword in ["date", "दिनांक", "तारीख"]):
        return "date"
    if any(keyword in text for keyword in ["mobile", "phone", "मोबाइल", "फोन"]):
        return "phone"
    if any(keyword in text for keyword in ["aadhaar", "uid", "आधार", "pan"]):
        return "text"
    if any(keyword in text for keyword in ["photo", "फोटो", "photograph"]):
        return "photo"
    if any(keyword in text for keyword in ["area", "क्षेत्र", "acre", "hectare", "amount"]):
        return "number"
    if any(keyword in text for keyword in ["account", "खाता", "ifsc", "name of bank"]):
        return "text"
    return "text"

def analyze_docx_dynamically(docx_file_path: str) -> List[Dict[str, Any]]:
    """
    Dynamically analyzes the DOCX file to find potential fillable fields.
    Prioritizes tables and then looks for standalone labels.
    """
    st.info("🧠 Dynamically analyzing DOCX structure...")
    doc = Document(docx_file_path)
    detected_fields = []
    
    # 1. Analyze Tables
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                if cell.text.strip():
                    # Look for empty cells in the same row, to the right
                    if col_idx + 1 < len(row.cells) and not row.cells[col_idx + 1].text.strip():
                        label_text = cell.text.strip()
                        detected_fields.append({
                            "type": "table",
                            "question": label_text,
                            "input_type": guess_input_type(label_text),
                            "table_idx": table_idx,
                            "row_idx": row_idx,
                            "col_idx": col_idx + 1
                        })
    
    # 2. Analyze Paragraphs
    for para_idx, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        # Look for labels followed by a colon, dots, or underscores
        match = re.match(r"(.*?)(:|\.|\_)\s*$", text)
        if match and not text.endswith((".docx", ".pdf", "doc")) and len(match.group(1).strip()) > 3:
            label_text = match.group(1).strip()
            # Ensure this isn't a duplicate of a table field
            if not any(f["question"] == label_text for f in detected_fields):
                detected_fields.append({
                    "type": "paragraph",
                    "question": label_text,
                    "input_type": guess_input_type(label_text),
                    "para_idx": para_idx
                })

    if not detected_fields:
        st.warning("⚠️ No fillable fields detected automatically. The form may be non-standard.")
        return []
        
    st.success(f"✅ Found {len(detected_fields)} potential fillable fields!")
    return detected_fields

def fill_docx_template(docx_file_path: str, fields: List[Dict[str, Any]], photo_files: Dict = None) -> Optional[bytes]:
    """
    Fills a DOCX template with user answers.
    """
    try:
        doc = Document(docx_file_path)
        
        # 1. Fill fields in tables
        for field in [f for f in fields if f["type"] == "table"]:
            answer = field.get("answer", "")
            doc.tables[field["table_idx"]].rows[field["row_idx"]].cells[field["col_idx"]].text = str(answer)

        # 2. Fill fields in paragraphs
        for field in [f for f in fields if f["type"] == "paragraph"]:
            answer = field.get("answer", "")
            paragraph = doc.paragraphs[field["para_idx"]]
            paragraph.add_run(f" {str(answer)}")
            
        # Photos are not directly supported in docx filling like in PDFs.
        # This part of the functionality will be disabled for DOCX.
        if photo_files:
            st.warning("Photo uploads are not currently supported for DOCX templates.")

        # Save the filled document to a bytes buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        st.error(f"Error filling DOCX file: {e}")
        return None

# ---------------- STREAMLIT UI ----------------
def main():
    st.set_page_config(page_title="Krishi Sahayak - Smart Farmer Application System", layout="wide", initial_sidebar_state="expanded")
    
    st.markdown("""
        <style>
        .main-header { background: linear-gradient(90deg, #2E7D32, #4CAF50); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem; }
        .scheme-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;}
        .success-box { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 5px; margin: 1rem 0;}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="main-header">
            <h1>🌾 Krishi Sahayak - Smart Farmer Application System</h1>
            <p>A dynamic, AI-powered solution for Indian Government Farmer Schemes</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("📋 Select Scheme")
        scheme_options = list(SCHEMES_INFO.keys())
        selected_scheme = st.selectbox("Choose Government Scheme:", scheme_options)
        
        if selected_scheme:
            scheme_info = SCHEMES_INFO[selected_scheme]
            st.markdown(f"""
                <div class="scheme-card">
                    <h4>{scheme_info['name']}</h4>
                    <p><strong>Description:</strong> {scheme_info['description']}</p>
                    <p><strong>Eligibility:</strong> {scheme_info['eligibility']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📄 Required Documents:")
            for doc in scheme_info['documents_required']:
                st.markdown(f"✓ {doc}")
            st.markdown(f"[🔗 Official Website]({scheme_info['official_link']})")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📤 Upload Application Form")
        
        uploaded_file = st.file_uploader(
            "Upload DOCX Application Form", 
            type=["docx"],
            help="Upload the official application form in .docx format to be filled"
        )
        
        template_file = None
        if uploaded_file:
            template_path = Path("templates") / uploaded_file.name
            template_path.parent.mkdir(exist_ok=True)
            with open(template_path, "wb") as f:
                f.write(uploaded_file.read())
            template_file = str(template_path)
            st.success("✅ Custom form uploaded successfully!")
        
        if template_file:
            st.info("""
            💡 **Prompt for Correct Placement:**
            - For best results, use **tables** for structured data (e.g., Name | [fillable cell]).
            - For standalone fields, end the label with a **colon (:)** or a series of **dots (...)**.
            - This system will automatically detect these patterns and fill the adjacent space.
            """)
            if st.button("🧠 Analyze Form to Find Fields", type="primary"):
                with st.spinner("Scanning DOCX to find fillable fields..."):
                    fields = analyze_docx_dynamically(template_file)
                    st.session_state["fields"] = fields
                    st.session_state["template_file"] = template_file
                    st.session_state["scheme_type"] = selected_scheme
            
            if "fields" in st.session_state and st.session_state["fields"]:
                with st.expander("🔍 Detected Fields Preview"):
                    for i, field in enumerate(st.session_state["fields"][:5]):
                        st.write(f"{i+1}. **{field['question']}** (type: {field['input_type']}, source: {field['type']})")
    
    with col2:
        st.header("ℹ️ Quick Info")
        st.info("""
            **How it works:**
            1. Upload a DOCX form template.
            2. The AI scans the document for tables and special characters to find fillable fields.
            3. Fill in the details for each field in the form below.
            4. Download your completed application as a new DOCX file.
        """)
    
    if "fields" in st.session_state and st.session_state["fields"]:
        st.header("📝 Fill Application Details")
        
        answers = {}
        photo_files = {}
        
        with st.form("farmer_application_form"):
            for field in st.session_state["fields"]:
                unique_key = f"field_{field['type']}_{field.get('table_idx', '')}_{field.get('row_idx', '')}_{field.get('para_idx', '')}"
                
                # Check for input type and create the appropriate widget
                if field["input_type"] == "photo":
                    st.write(f"**Photo field detected, but DOCX photo filling is not supported.**")
                    answers[unique_key] = None
                elif field["input_type"] == "date":
                    answers[unique_key] = st.date_input(field["question"], key=unique_key)
                elif field["input_type"] == "number":
                    answers[unique_key] = st.number_input(field["question"], min_value=0.0, step=0.01, key=unique_key)
                else:
                    answers[unique_key] = st.text_input(field["question"], key=unique_key)
            
            submitted = st.form_submit_button("🚀 Generate Filled Application", type="primary")
        
        if submitted:
            with st.spinner("Generating your filled application..."):
                for field in st.session_state["fields"]:
                    unique_key = f"field_{field['type']}_{field.get('table_idx', '')}_{field.get('row_idx', '')}_{field.get('para_idx', '')}"
                    answer_value = answers.get(unique_key)
                    
                    if field["input_type"] == "date" and answer_value:
                        field["answer"] = answer_value.strftime("%d/%m/%Y")
                    elif field["input_type"] == "photo":
                        field["answer"] = ""
                    else:
                        field["answer"] = str(answer_value) if answer_value is not None else ""
                
                final_docx_bytes = fill_docx_template(st.session_state["template_file"], st.session_state["fields"], photo_files)
                
                if final_docx_bytes:
                    st.markdown("""<div class="success-box"><h4>🎉 Application Successfully Generated!</h4><p>Your application has been filled and is ready for download.</p></div>""", unsafe_allow_html=True)
                    
                    filename = f"{st.session_state['scheme_type']}_application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                    st.download_button(label="📥 Download Filled Application DOCX", data=final_docx_bytes, file_name=filename, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
                    
                    st.header("📋 Next Steps")
                    scheme_info = SCHEMES_INFO.get(st.session_state["scheme_type"], {})
                    st.success(f"""
                    **What to do next:**
                    1. 📄 Print the downloaded application form
                    2. ✍️ Sign the form where required
                    3. 📎 Attach all required documents (see sidebar)
                    4. 🏛️ Submit to nearest CSC/Bank/Government office
                    """)
                else:
                    st.error("❌ Failed to generate the final DOCX file. Please check your inputs.")

if __name__ == "__main__":
    Path("templates").mkdir(exist_ok=True)
    main()
=======
import io
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st
from docx import Document
import re
from datetime import datetime

# ---------------- CONFIG ----------------
SCHEMES_INFO = {
    "PM-Kisan": {
        "name": "Pradhan Mantri Kisan Samman Nidhi Yojana",
        "description": "Direct income support of ₹6,000 per year for land-holding farmer families.",
        "eligibility": "All land-holding farmer families, subject to certain exclusion criteria (e.g., income tax payers, high-pensioners).",
        "documents_required": [
            "Land ownership documents (e.g., Khasra/Khatauni)",
            "Aadhaar Card (Mandatory for eKYC)",
            "Bank Account Passbook (for direct benefit transfer)",
            "Proof of Citizenship",
            "Passport Size Photograph"
        ],
        "submission_notes": "Submit the filled form and all documents to a Common Service Center (CSC), your local Patwari, or a designated Nodal Officer. Online self-registration is also available on the official PM-KISAN portal.",
        "template_file": "templates/pm-kisan_application_form.docx",
        "official_link": "https://pmkisan.gov.in/"
    },
    "PM-KMY": {
        "name": "Pradhan Mantri Kisan Maan Dhan Yojana",
        "description": "A voluntary and contributory pension scheme for small and marginal farmers.",
        "eligibility": "Small and Marginal Farmers (SMF) aged between 18 and 40 with cultivable land up to 2 hectares.",
        "documents_required": [
            "Aadhaar Card",
            "Bank Passbook or Bank Account Details",
            "Land Records (Khasra/Khatauni)",
            "Passport Size Photograph"
        ],
        "submission_notes": "Enrollment is done at the nearest Common Service Center (CSC). You will need to provide the filled form and documents, and the CSC will complete the online registration for you. PM-KISAN beneficiaries can opt for auto-debit of their contributions from the benefits they receive.",
        "template_file": "templates/pm-kmy_application_form.docx",
        "official_link": "https://pmkmy.gov.in/"
    },
    "KCC": {
        "name": "Kisan Credit Card",
        "description": "Concessional credit facility for agricultural and allied activities, offering short-term loans up to ₹3 lakh.",
        "eligibility": "All farmers, including owner cultivators, tenant farmers, sharecroppers, and members of Self Help Groups (SHGs) or Joint Liability Groups (JLGs).",
        "documents_required": [
            "Duly filled and signed application form",
            "Aadhaar Card",
            "PAN Card",
            "Land ownership/cultivation documents (e.g., land records, lease agreement)",
            "Bank Account Passbook",
            "Passport size photographs (2-3 copies)",
            "Income Certificate",
            "Any other security documents required by the bank"
        ],
        "submission_notes": "Submit the completed application form and all required documents to the bank's branch where you wish to open the account. The bank will then verify the details and process your application.",
        "template_file": "templates/kcc_application_form.docx",
        "official_link": "https://pmkisan.gov.in/Documents/Kcc.pdf"
    },
    "PMFBY": {
        "name": "Pradhan Mantri Fasal Bima Yojana",
        "description": "A crop insurance scheme that provides financial support to farmers suffering crop loss/damage arising out of unforeseen events.",
        "eligibility": "All farmers, including sharecroppers and tenant farmers, growing notified crops in a notified area.",
        "documents_required": [
            "Aadhaar Card",
            "Bank Account Passbook",
            "Land Records (Khatauni/Patwari records)",
            "Sowing Certificate from Village Revenue Officer",
            "Passport Size Photograph"
        ],
        "submission_notes": "The form must be submitted to the nearest bank branch, cooperative society, or CSC. Farmers who have taken institutional loans will have their premiums deducted automatically.",
        "template_file": "templates/pmfby_application_form.docx",
        "official_link": "https://pmfby.gov.in/"
    },
    "Soil Health Card": {
        "name": "Soil Health Card Scheme",
        "description": "A scheme to provide a Soil Health Card to all farmers, containing information on nutrient status and recommendations for soil improvement.",
        "eligibility": "All farmers with agricultural land.",
        "documents_required": [
            "Aadhaar Card",
            "Land records (Khatauni)",
            "Mobile number",
            "Copy of Bank Passbook"
        ],
        "submission_notes": "The form should be submitted to the local Agriculture Department or Krishi Vigyan Kendra. A soil sample will be collected from your farm for testing, and the card will be issued based on the results.",
        "template_file": "templates/soil_health_card_form.docx",
        "official_link": "https://soilhealth.dac.gov.in/"
    },
    "PM-KISAN SAMMAN": {
        "name": "Pradhan Mantri Kisan Samman Nidhi - Samman Patra (Certificate)",
        "description": "A scheme providing certificates to all PM-KISAN beneficiaries, verifying their enrollment in the scheme.",
        "eligibility": "All enrolled beneficiaries of the PM-KISAN scheme.",
        "documents_required": [
            "Aadhaar Card",
            "PM-KISAN registration number",
            "Land records (Khatauni)"
        ],
        "submission_notes": "The certificate can be downloaded online from the PM-KISAN official website or obtained from a CSC. The form is for verifying and updating beneficiary details before the certificate is issued.",
        "template_file": "templates/pm_kisan_samman_patra_form.docx",
        "official_link": "https://pmkisan.gov.in/"
    }
}

# ---------------- CORE DYNAMIC FUNCTIONS ----------------

def guess_input_type(label_text: str) -> str:
    """Guesses the input type based on keywords in the label."""
    text = label_text.lower()
    if any(keyword in text for keyword in ["date", "दिनांक", "तारीख"]):
        return "date"
    if any(keyword in text for keyword in ["mobile", "phone", "मोबाइल", "फोन"]):
        return "phone"
    if any(keyword in text for keyword in ["aadhaar", "uid", "आधार", "pan"]):
        return "text"
    if any(keyword in text for keyword in ["photo", "फोटो", "photograph"]):
        return "photo"
    if any(keyword in text for keyword in ["area", "क्षेत्र", "acre", "hectare", "amount"]):
        return "number"
    if any(keyword in text for keyword in ["account", "खाता", "ifsc", "name of bank"]):
        return "text"
    return "text"

def analyze_docx_dynamically(docx_file_path: str) -> List[Dict[str, Any]]:
    """
    Dynamically analyzes the DOCX file to find potential fillable fields.
    Prioritizes tables and then looks for standalone labels.
    """
    st.info("🧠 Dynamically analyzing DOCX structure...")
    detected_fields = []
    
    try:
        doc = Document(docx_file_path)
    except Exception as e:
        st.error(f"Error reading DOCX file: {e}")
        return []

    # 1. Analyze Tables
    for table_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                if cell_text:
                    # Look for an empty cell in the same row, to the right, to serve as the fillable field
                    if col_idx + 1 < len(row.cells) and not row.cells[col_idx + 1].text.strip():
                        label_text = cell_text
                        
                        # Check for duplicates
                        if not any(f.get("question") == label_text and f.get("type") == "table" for f in detected_fields):
                            detected_fields.append({
                                "type": "table",
                                "question": label_text,
                                "input_type": guess_input_type(label_text),
                                "table_idx": table_idx,
                                "row_idx": row_idx,
                                "col_idx": col_idx + 1
                            })
    
    # 2. Analyze Paragraphs
    for para_idx, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        # Regex to find a label ending with a colon, dots, or underscores
        match = re.match(r"(.*?)(:|\.|\_)\s*$", text)
        if match and not text.endswith((".docx", ".pdf", "doc")) and len(match.group(1).strip()) > 3:
            label_text = match.group(1).strip()
            
            # Ensure this isn't a duplicate of a table field
            if not any(f.get("question") == label_text for f in detected_fields):
                detected_fields.append({
                    "type": "paragraph",
                    "question": label_text,
                    "input_type": guess_input_type(label_text),
                    "para_idx": para_idx
                })

    if not detected_fields:
        st.warning("⚠️ No fillable fields detected automatically. The form may be non-standard.")
        return []
        
    st.success(f"✅ Found {len(detected_fields)} potential fillable fields!")
    return detected_fields

def fill_docx_template(docx_file_path: str, fields: List[Dict[str, Any]], photo_files: Dict = None) -> Optional[bytes]:
    """
    Fills a DOCX template with user answers.
    """
    try:
        doc = Document(docx_file_path)
        
        # 1. Fill fields in tables
        for field in [f for f in fields if f["type"] == "table"]:
            answer = field.get("answer", "")
            if answer:
                doc.tables[field["table_idx"]].rows[field["row_idx"]].cells[field["col_idx"]].text = str(answer)

        # 2. Fill fields in paragraphs
        for field in [f for f in fields if f["type"] == "paragraph"]:
            answer = field.get("answer", "")
            if answer:
                paragraph = doc.paragraphs[field["para_idx"]]
                # Ensure a space is added to separate the label from the answer
                paragraph.add_run(f" {str(answer)}")
            
        if photo_files:
            st.warning("Photo uploads are not currently supported for DOCX templates and will be ignored.")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        st.error(f"Error filling DOCX file: {e}")
        return None

# ---------------- STREAMLIT UI ----------------
def main():
    st.set_page_config(page_title="Krishi Sahayak - Smart Farmer Application System", layout="wide", initial_sidebar_state="expanded")
    
    st.markdown("""
        <style>
        .main-header { background: linear-gradient(90deg, #2E7D32, #4CAF50); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 2rem; }
        .scheme-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 1rem; margin: 0.5rem 0;}
        .success-box { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 5px; margin: 1rem 0;}
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
        <div class="main-header">
            <h1>🌾 Krishi Sahayak - Smart Farmer Application System</h1>
            <p>A dynamic, AI-powered solution for Indian Government Farmer Schemes</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("📋 Select Scheme")
        scheme_options = list(SCHEMES_INFO.keys())
        selected_scheme = st.selectbox("Choose Government Scheme:", scheme_options)
        
        if selected_scheme:
            scheme_info = SCHEMES_INFO[selected_scheme]
            st.markdown(f"""
                <div class="scheme-card">
                    <h4>{scheme_info['name']}</h4>
                    <p><strong>Description:</strong> {scheme_info['description']}</p>
                    <p><strong>Eligibility:</strong> {scheme_info['eligibility']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📄 Required Documents:")
            for doc in scheme_info['documents_required']:
                st.markdown(f"✓ {doc}")
            st.markdown(f"[🔗 Official Website]({scheme_info['official_link']})")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📤 Upload Application Form")
        
        uploaded_file = st.file_uploader(
            "Upload DOCX Application Form", 
            type=["docx"],
            help="Upload the official application form in .docx format to be filled"
        )
        
        template_file = None
        if uploaded_file:
            template_path = Path("templates") / uploaded_file.name
            template_path.parent.mkdir(exist_ok=True)
            with open(template_path, "wb") as f:
                f.write(uploaded_file.read())
            template_file = str(template_path)
            st.success("✅ Custom form uploaded successfully!")
        
        if template_file:
            st.info("""
            💡 **Prompt for Correct Placement:**
            - For best results, use **tables** for structured data (e.g., Name | [fillable cell]).
            - For standalone fields, end the label with a **colon (:)** or a series of **dots (...)**.
            - This system will automatically detect these patterns and fill the adjacent space.
            """)
            if st.button("🧠 Analyze Form to Find Fields", type="primary"):
                with st.spinner("Scanning DOCX to find fillable fields..."):
                    fields = analyze_docx_dynamically(template_file)
                    st.session_state["fields"] = fields
                    st.session_state["template_file"] = template_file
                    st.session_state["scheme_type"] = selected_scheme
            
            if "fields" in st.session_state and st.session_state["fields"]:
                with st.expander("🔍 Detected Fields Preview"):
                    for i, field in enumerate(st.session_state["fields"][:5]):
                        st.write(f"{i+1}. **{field['question']}** (type: {field['input_type']}, source: {field['type']})")
    
    with col2:
        st.header("ℹ️ Quick Info")
        st.info("""
            **How it works:**
            1. Upload a DOCX form template.
            2. The AI scans the document for tables and special characters to find fillable fields.
            3. Fill in the details for each field in the form below.
            4. Download your completed application as a new DOCX file.
        """)
    
    if "fields" in st.session_state and st.session_state["fields"]:
        st.header("📝 Fill Application Details")
        
        answers = {}
        
        with st.form("farmer_application_form"):
            for field in st.session_state["fields"]:
                unique_key = f"field_{field['type']}_{field.get('table_idx', '')}_{field.get('row_idx', '')}_{field.get('col_idx', '')}_{field.get('para_idx', '')}"
                
                # Create the appropriate Streamlit widget based on the guessed input type
                if field["input_type"] == "photo":
                    st.write(f"**Photo field detected, but DOCX photo filling is not supported.**")
                    answers[unique_key] = None
                elif field["input_type"] == "date":
                    answers[unique_key] = st.date_input(field["question"], key=unique_key)
                elif field["input_type"] == "number":
                    answers[unique_key] = st.number_input(field["question"], min_value=0.0, step=0.01, key=unique_key)
                else:
                    answers[unique_key] = st.text_input(field["question"], key=unique_key)
            
            submitted = st.form_submit_button("🚀 Generate Filled Application", type="primary")
        
        if submitted:
            with st.spinner("Generating your filled application..."):
                for field in st.session_state["fields"]:
                    unique_key = f"field_{field['type']}_{field.get('table_idx', '')}_{field.get('row_idx', '')}_{field.get('col_idx', '')}_{field.get('para_idx', '')}"
                    answer_value = answers.get(unique_key)
                    
                    if field["input_type"] == "date" and answer_value:
                        field["answer"] = answer_value.strftime("%d/%m/%Y")
                    elif field["input_type"] == "photo":
                        field["answer"] = ""
                    else:
                        field["answer"] = str(answer_value) if answer_value is not None else ""
                
                # Note: photo_files is not used for DOCX, so we pass an empty dict
                final_docx_bytes = fill_docx_template(st.session_state["template_file"], st.session_state["fields"], {})
                
                if final_docx_bytes:
                    st.markdown("""<div class="success-box"><h4>🎉 Application Successfully Generated!</h4><p>Your application has been filled and is ready for download.</p></div>""", unsafe_allow_html=True)
                    
                    filename = f"{st.session_state['scheme_type']}_application_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                    st.download_button(label="📥 Download Filled Application DOCX", data=final_docx_bytes, file_name=filename, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
                    
                    st.header("📋 Next Steps")
                    scheme_info = SCHEMES_INFO.get(st.session_state["scheme_type"], {})
                    st.success(f"""
                    **What to do next:**
                    1. 📄 Print the downloaded application form
                    2. ✍️ Sign the form where required
                    3. 📎 Attach all required documents (see sidebar)
                    4. 🏛️ Submit to nearest CSC/Bank/Government office
                    """)
                else:
                    st.error("❌ Failed to generate the final DOCX file. Please check your inputs.")

if __name__ == "__main__":
    Path("templates").mkdir(exist_ok=True)
    main()
