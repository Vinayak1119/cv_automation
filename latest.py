import os
import io
import json
import time
from datetime import datetime
from pdf2image import convert_from_bytes
import pytesseract
import requests
from pydantic import ValidationError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found in .env file")

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

class Experience(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    duration: Optional[str] = None
    responsibilities: Optional[List[str]] = []

class Education(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    duration: Optional[str] = None

class Project(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    technologies_used: Optional[List[str]] = []

class Certification(BaseModel):
    title: Optional[str] = None
    issuing_organization: Optional[str] = None
    date_issued: Optional[str] = None

class Achievement(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class Candidate(BaseModel):
    personal_info: Optional[PersonalInfo] = None
    career_objective: Optional[str] = None
    skills: Optional[List[str]] = []
    experience: Optional[List[Experience]] = []
    education: Optional[List[Education]] = []
    projects: Optional[List[Project]] = []
    certifications: Optional[List[Certification]] = []
    achievements: Optional[List[Achievement]] = []
    total_experience: Optional[float] = None
    relevant_experience: Optional[dict] = None

class AggregatedData(BaseModel):
    candidates: List[Candidate] = []

def log_message(message, start_time=None):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if start_time:
        time_taken = time.time() - start_time
        print(f"[{current_time}] {message} (Time taken: {time_taken:.2f} seconds)")
    else:
        print(f"[{current_time}] {message}")

def authenticate_to_drive(credentials_path):
    """Authenticate to Google Drive using service account credentials."""
    try:
        credentials = Credentials.from_service_account_file(credentials_path, scopes=["https://www.googleapis.com/auth/drive"])
        drive_service = build('drive', 'v3', credentials=credentials)
        log_message("Successfully authenticated to Google Drive.")
        return drive_service
    except Exception as e:
        log_message(f"Authentication failed: {e}")
        raise

def list_files_in_folder(drive_service, folder_id):
    """List all files in a Google Drive folder."""
    print(f"📂 Fetching files from Google Drive Folder: {folder_id}")

    try:
        query = f"'{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = response.get('files', [])
        print(f"🔍 Found {len(files)} files in the folder.")
        for file in files:
            print(f"📄 {file['name']} (ID: {file['id']})")  
        return files
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return []

def download_file_as_bytes(drive_service, file_id):
    """Download a file from Google Drive as bytes."""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            log_message(f"Processing: {int(status.progress() * 100)}%")
        file_stream.seek(0)  
        return file_stream
    except Exception as e:
        log_message(f"Error downloading file: {e}")
        return None

def pdf_bytes_to_images(pdf_bytes):
    start_time = time.time()
    log_message("Converting PDF bytes to images.", start_time)
    try:
        images = convert_from_bytes(pdf_bytes.read())
        log_message("Conversion completed.", start_time)
        return images
    except Exception as e:
        log_message(f"Error converting PDF bytes to images: {e}", start_time)
        return []

def extract_text_from_image(image):
    start_time = time.time()
    log_message("Extracting text from image.", start_time)
    try:
        text = pytesseract.image_to_string(image)
        log_message("Text extraction completed.", start_time)
        return text
    except Exception as e:
        error_message = f"Error extracting text: {str(e)}"
        log_message(error_message, start_time)
        return error_message

def process_text_with_openai(api_key, extracted_text):
    start_time = time.time()
    log_message("Processing text with OpenAI API.", start_time)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    schema = {
        "personal_info": {
            "name": "string or null",
            "email": "string or null",
            "phone": "string or null",
            "address": "string or null",
            "linkedin": "string or null",
            "github": "string or null"
        },
        "career_objective": "string or null",
        "skills": ["string"],
        "experience": [
            {
                "job_title": "string or null",
                "company": "string or null",
                "location": "string or null",
                "duration": "string or null",
                "responsibilities": ["string"]
            }
        ],
        "education": [
            {
                "degree": "string or null",
                "institution": "string or null",
                "duration": "string or null"
            }
        ],
        "projects": [
            {
                "title": "string or null",
                "description": "string or null",
                "technologies_used": ["string"]
            }
        ],
        "certifications": [
            {
                "title": "string or null",
                "issuing_organization": "string or null",
                "date_issued": "string or null"
            }
        ],
        "achievements": [
            {
                "title": "string or null",
                "description": "string or null"
            }
        ],
        "total_experience": "float or null",
        "relevant_experience": "dict or null"
    }

    prompt_content = (
        "You are a structured JSON generator. Convert the provided resume text into a JSON object "
        f"matching the following schema: {json.dumps(schema, indent=2)}. "
        "### Instructions:\n"
        "1. **Strict Schema Adherence**: Ensure all fields are correctly structured. Use `null` for missing values.\n"
        "2. **Education Extraction**: Only include the highest pursued degree with both full and short form (e.g., 'Master of Science (M.Sc)').\n"
        "3. **Experience Handling**:\n"
        "   - Capture all details, ensuring exact company location (if provided).\n"
        "   - Convert all experience durations into a structured format.\n"
        "   - Handle formats like 'Jan 2020 - Present', 'April 2019 - Nov 2021', '5 months'.\n"
        "   - Convert months to years where applicable (e.g., '2 years 3 months' → 2.25 years).\n"
        "   - If the end date is 'present', 'till, 'current', 'now', 'ongoing', 'on-going', 'till now' calculate experience up to today's date (17/03/2025).\n"
        "4. **Total Experience Calculation**:\n"
        "   - Ensure no double counting of overlapping job durations.\n"
        "   - Accurately compute total experience as a numeric value.\n"
        "5. **Relevant Experience Calculation**:\n"
        "   - Compute and map total duration per job title into `relevant_experience`.\n"
        "   - Example:\n"
        "     ```json\n"
        "     \"total_experience\": 4.8,\n"
        "     \"relevant_experience\": {\n"
        "         \"Sr. Technical Lead\": 0.1,\n"
        "         \"Senior Python Developer\": 1.1,\n"
        "         \"Software Developer\": 3.6\n"
        "     }\n"
        "     ```\n"
        "6. **Ensure Data Integrity**:\n"
        "   - Extract all resume details without omitting any relevant information.\n"
        "   - Maintain correct company addresses, ensuring JSON validity.\n"
        "   - Avoid unnecessary formatting errors or hallucinations.\n"
    )

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": prompt_content},
            {"role": "user", "content": f"Here is the extracted text from the resume:\n\n{extracted_text}"}
        ],
        "max_tokens": 2000
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code != 200:
            log_message(f"Error: {response.status_code} - {response.text}")
            return None

        content = response.json()["choices"][0]["message"]["content"]
        cleaned_content = content.strip("```json").strip("```").strip()
        processed_data = json.loads(cleaned_content)

        try:
            candidate = Candidate(**processed_data)
            return candidate.dict()
        except ValidationError as e:
            log_message(f"Validation error: {str(e)}")
            return None

    except Exception as e:
        log_message(f"Error during OpenAI API call: {str(e)}")
        return None

def process_pdfs_to_nested_json(drive_service, folder_id, output_file):
    start_time = time.time()
    log_message("Processing PDFs in Google Drive folder.", start_time)
    files = list_files_in_folder(drive_service, folder_id)

    if not files:
        log_message("No PDF files found in the folder.", start_time)
        return

    aggregated_data = {"candidates": []}

    for file in files:
        if file['mimeType'] == 'application/pdf':
            log_message(f"Processing PDF: {file['name']}", start_time)
            file_stream = download_file_as_bytes(drive_service, file['id'])
            if file_stream:
                images = pdf_bytes_to_images(file_stream)
                if images:
                    extracted_text = " ".join([extract_text_from_image(image) for image in images])
                    candidate_data = process_text_with_openai(OPENAI_API_KEY, extracted_text)
                    if candidate_data:
                        aggregated_data["candidates"].append(candidate_data)

    try:
        with open(output_file, 'w') as json_file:
            json.dump(aggregated_data, json_file, indent=4)
        log_message(f"Aggregated data saved to {output_file}.", start_time)
    except Exception as e:
        log_message(f"Error saving aggregated data: {str(e)}", start_time)

if __name__ == "__main__":
    credentials_path = "/Users/vinayaksharma/Documents/CV-Testing/securitykey.json"
    drive_folder_id = "1aI5t1ub-PlBoO3d6u2OEIJXFX5n49jRK"
    output_file_path = "//Users/vinayaksharma/Documents/cv_automation/aggregated_data.json"

    try:
        drive_service = authenticate_to_drive(credentials_path)
        process_pdfs_to_nested_json(drive_service, drive_folder_id, output_file_path)
    except Exception as e:
        log_message(f"Error in main execution: {str(e)}")
