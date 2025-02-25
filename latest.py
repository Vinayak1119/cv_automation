# import os
# import io
# import json
# import time
# import re
# from datetime import datetime
# from pdf2image import convert_from_bytes
# import pytesseract
# import requests
# from dateutil import parser
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaIoBaseDownload
# from google.oauth2.service_account import Credentials
# from pydantic import BaseModel, Field
# from typing import List, Optional
# from dotenv import load_dotenv

# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# if not OPENAI_API_KEY:
#     raise ValueError("OpenAI API key not found in .env file")

# class PersonalInfo(BaseModel):
#     name: Optional[str] = None
#     email: Optional[str] = None
#     phone: Optional[str] = None
#     address: Optional[str] = None

# class Experience(BaseModel):
#     job_title: Optional[str] = None
#     company: Optional[str] = None
#     address: Optional[str] = None
#     duration: Optional[str] = None
#     responsibilities: Optional[List[str]] = []

# class Education(BaseModel):
#     degree: Optional[str] = None
#     institution: Optional[str] = None
#     duration: Optional[str] = None

# class Project(BaseModel):
#     title: Optional[str] = None
#     description: Optional[str] = None
#     technologies_used: Optional[List[str]] = []

# class Certification(BaseModel):
#     title: Optional[str] = None
#     issuing_organization: Optional[str] = None
#     date_issued: Optional[str] = None

# class Achievement(BaseModel):
#     title: Optional[str] = None
#     description: Optional[str] = None

# class Candidate(BaseModel):
#     personal_info: Optional[PersonalInfo] = None
#     career_objective: Optional[str] = None
#     skills: Optional[List[str]] = []
#     experience: Optional[List[Experience]] = []
#     education: Optional[List[Education]] = []
#     projects: Optional[List[Project]] = []
#     certifications: Optional[List[Certification]] = []
#     achievements: Optional[List[Achievement]] = []
#     total_experience: Optional[float] = None
    

# class AggregatedData(BaseModel):
#     candidates: List[Candidate] = []

# def log_message(message, start_time=None):
#     current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     if start_time:
#         time_taken = time.time() - start_time
#         print(f"[{current_time}] {message} (Time taken: {time_taken:.2f} seconds)")
#     else:
#         print(f"[{current_time}] {message}")

# def authenticate_to_drive(credentials_path):
#     """Authenticate to Google Drive using service account credentials."""
#     try:
#         credentials = Credentials.from_service_account_file(credentials_path, scopes=["https://www.googleapis.com/auth/drive"])
#         drive_service = build('drive', 'v3', credentials=credentials)
#         log_message("Successfully authenticated to Google Drive.")
#         return drive_service
#     except Exception as e:
#         log_message(f"Authentication failed: {e}")
#         raise

# def list_files_in_folder(drive_service, folder_id):
#     """List all files in a Google Drive folder."""
#     print(f"📂 Fetching files from Google Drive Folder: {folder_id}")

#     try:
#         query = f"'{folder_id}' in parents and trashed=false"
#         response = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
#         files = response.get('files', [])
#         print(f"🔍 Found {len(files)} files in the folder.")
#         for file in files:
#             print(f"📄 {file['name']} (ID: {file['id']})")  # ✅ Debugging
#         return files
#     except Exception as e:
#         print(f"❌ Error listing files: {e}")
#         return []
        

# def download_file_as_bytes(drive_service, file_id):
#     """Download a file from Google Drive as bytes."""
#     try:
#         request = drive_service.files().get_media(fileId=file_id)
#         file_stream = io.BytesIO()
#         downloader = MediaIoBaseDownload(file_stream, request)
#         done = False
#         while not done:
#             status, done = downloader.next_chunk()
#             log_message(f"Processing: {int(status.progress() * 100)}%")
#         file_stream.seek(0)  # Reset stream position
#         return file_stream
#     except Exception as e:
#         log_message(f"Error downloading file: {e}")
#         return None

# # Convert PDF bytes to Images
# def pdf_bytes_to_images(pdf_bytes):
#     start_time = time.time()
#     log_message("Converting PDF bytes to images.", start_time)
#     try:
#         images = convert_from_bytes(pdf_bytes.read())
#         log_message("Conversion completed.", start_time)
#         return images
#     except Exception as e:
#         log_message(f"Error converting PDF bytes to images: {e}", start_time)
#         return []

# # Extract text from image using OCR
# def extract_text_from_image(image):
#     start_time = time.time()
#     log_message("Extracting text from image.", start_time)
#     try:
#         text = pytesseract.image_to_string(image)
#         log_message("Text extraction completed.", start_time)
#         return text
#     except Exception as e:
#         error_message = f"Error extracting text: {str(e)}"
#         log_message(error_message, start_time)
#         return error_message

# # Calculate total experience from experience list
# def calculate_total_experience(experience_list):
#     total_experience = 0
#     present_keywords = {"present", "current", "till date"}

#     for exp in experience_list:
#         duration = exp.duration.strip() if exp.duration else ""
#         if not duration:
#             log_message(f"Empty or missing duration field: {exp}")
#             continue

#         # Normalize duration string
#         duration = (
#             duration.replace("\u2014", "-")  # Replace em dash
#             .replace("\u2013", "-")          # Replace en dash
#             .replace("to", "-")
#             .replace("Till date", "Present")
#             .replace("till date", "Present")
#             .replace("Current", "Present")
#             .strip()
#         )

#         # Ensure proper spacing around hyphens
#         duration = re.sub(r"(\S)-(\S)", r"\1 - \2", duration)

#         # Handle durations like "2.5 years", "1.5 years"
#         match = re.match(r"(\d+(\.\d+)?)\s*years?", duration, re.IGNORECASE)
#         if match:
#             total_experience += float(match.group(1))
#             continue

#         # Handle "X years Y months" format
#         match = re.match(r"(\d+)\s*years?\s*(\d+)?\s*months?", duration, re.IGNORECASE)
#         if match:
#             years = int(match.group(1))
#             months = int(match.group(2)) if match.group(2) else 0
#             total_experience += years + months / 12
#             continue

#         # Handle "X months" format
#         match = re.match(r"(\d+)\s*months?", duration, re.IGNORECASE)
#         if match:
#             total_experience += int(match.group(1)) / 12
#             continue

#         try:
#             # Attempt to split durations like "July 2021 - Present" or malformed cases
#             parts = re.split(r"\s*-\s*", duration)
#             if len(parts) != 2:
#                 log_message(f"Malformed duration string: '{duration}'")
#                 continue

#             start_date_str, end_date_str = parts
#             try:
#                 start_date = parser.parse(start_date_str.strip(), dayfirst=True)
#             except Exception:
#                 log_message(f"Error parsing start date '{start_date_str.strip()}'")
#                 continue

#             if end_date_str.strip().lower() in present_keywords:
#                 end_date = datetime.now()
#             else:
#                 try:
#                     end_date = parser.parse(end_date_str.strip(), dayfirst=True)
#                 except Exception:
#                     log_message(f"Error parsing end date '{end_date_str.strip()}'")
#                     continue

#             # Calculate years of experience
#             years_of_experience = (end_date.year - start_date.year) + (end_date.month - start_date.month) / 12
#             total_experience += years_of_experience
#         except Exception as e:
#             log_message(f"Error parsing duration '{duration}': {str(e)}")

#     return round(total_experience, 2) 



# # Process text with OpenAI API using Pydantic schema
# def process_text_with_openai(api_key, extracted_text):
#     start_time = time.time()
#     log_message("Processing text with OpenAI API.", start_time)

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}"
#     }

#     schema = {
#         "personal_info": {
#             "name": "string or null",
#             "email": "string or null",
#             "phone": "string or null",
#             "address": "string or null"
#         },
#         "career_objective": "string or null",
#         "skills": ["string"],
#         "experience": [
#             {
#                 "job_title": "string or null",
#                 "company": "string or null",
#                 "location": "string or null",
#                 "duration": "string or null",
#                 "responsibilities": ["string"]
#             }
#         ],
#         "education": [
#             {
#                 "degree": "string or null",
#                 "institution": "string or null",
#                 "duration": "string or null"
#             }
#         ],
#         "projects": [
#             {
#                 "title": "string or null",
#                 "description": "string or null",
#                 "technologies_used": ["string"]
#             }
#         ],
#         "certifications": [
#             {
#                 "title": "string or null",
#                 "issuing_organization": "string or null",
#                 "date_issued": "string or null"
#             }
#         ],
#         "achievements": [
#             {
#                 "title": "string or null",
#                 "description": "string or null"
#             }
#         ],
#         "total_experience": "float or null"
#     }

#     payload = {
#         "model": "gpt-4o-mini",
#         "messages": [
#             {
#                 "role": "system",
#                 "content": (
#                     "You are a structured JSON generator. Convert the provided resume text into a JSON object "
#                     f"matching the following schema: {json.dumps(schema, indent=2)}. "
#                     "Ensure the JSON strictly adheres to this format. Handle missing fields with null values. "
#                     "Fetch only the highest level of education that the candidate has pursued. "
#                     "Ensure the response avoids Unicode characters (e.g., use '-' instead of '—')."
#                     "Ensure the accurate location or address of each company is captured exactly as mentioned in the experience section."
#                     "Fetch all details provided in the experience section without omitting any information."
#                     "For education details, include both the full name and short form (e.g., Bachelor of Technology (B.Tech) or Master of Science (M.Sc) or any other degree)."
#                     "Also, calculate the total experience based on the durations provided in the experience section and include this as a numeric value in the 'total_experience' field. "
#                     "If the current working location does not have an address, keep the address field null. Do not include the company name in the address."
#                     "If the duration is in months, convert it to years. If the duration is a mix of months and years (e.g., '2 years 3 months'), calculate the total experience accurately."
#                 )
#             },
#             {
#                 "role": "user",
#                 "content": f"Here is the extracted text from the resume:\n\n{extracted_text}"
#             }
#         ],
#         "max_tokens": 2000
#     }

#     try:
#         response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
#         if response.status_code != 200:
#             log_message(f"Error: {response.status_code} - {response.text}")
#             return None

#         content = response.json()["choices"][0]["message"]["content"]
#         cleaned_content = content.strip("```json").strip("```").strip()
#         processed_data = json.loads(cleaned_content)

#         # Validate the response with Pydantic models
#         try:
#             candidate = Candidate(**processed_data)
#             total_experience = calculate_total_experience(candidate.experience)
#             candidate.total_experience = total_experience
#             return candidate.dict()  # Return as a dictionary for easy storage
#         except Exception as e:
#             log_message(f"Validation error: {str(e)}")
#             return None

#     except Exception as e:
#         log_message(f"Error during OpenAI API call: {str(e)}")
#         return None

# # Process PDFs and save as nested JSON
# def process_pdfs_to_nested_json(drive_service, folder_id, output_file):
#     start_time = time.time()
#     log_message("Processing PDFs in Google Drive folder.", start_time)
#     files = list_files_in_folder(drive_service, folder_id)

#     if not files:
#         log_message("No PDF files found in the folder.", start_time)
#         return

#     aggregated_data = {"candidates": []}

#     for file in files:
#         if file['mimeType'] == 'application/pdf':
#             log_message(f"Processing PDF: {file['name']}", start_time)
#             file_stream = download_file_as_bytes(drive_service, file['id'])
#             if file_stream:
#                 images = pdf_bytes_to_images(file_stream)
#                 if images:
#                     extracted_text = " ".join([extract_text_from_image(image) for image in images])
#                     candidate_data = process_text_with_openai(OPENAI_API_KEY, extracted_text)
#                     if candidate_data:
#                         aggregated_data["candidates"].append(candidate_data)

#     try:
#         with open(output_file, 'w') as json_file:
#             json.dump(aggregated_data, json_file, indent=4)
#         log_message(f"Aggregated data saved to {output_file}.", start_time)
#     except Exception as e:
#         log_message(f"Error saving aggregated data: {str(e)}", start_time)

# if __name__ == "__main__":
#     credentials_path = "/Users/vinayaksharma/Documents/CV-Testing/securitykey.json"
#     drive_folder_id = "1zXQqZuc3UupGF1uPA9sIQxesUUN92C4x"
#     output_file_path = "/Users/vinayaksharma/Documents/CV-Testing/aggregated_data.json"

#     try:
#         drive_service = authenticate_to_drive(credentials_path)
#         process_pdfs_to_nested_json(drive_service, drive_folder_id, output_file_path)
#     except Exception as e:
#         log_message(f"Error in main execution: {str(e)}")       






import os
import io
import json
import time
import re
from datetime import datetime
from pdf2image import convert_from_bytes
import pytesseract
import requests
from dateutil import parser
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
            print(f"📄 {file['name']} (ID: {file['id']})")  # ✅ Debugging
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
        file_stream.seek(0)  # Reset stream position
        return file_stream
    except Exception as e:
        log_message(f"Error downloading file: {e}")
        return None

# Convert PDF bytes to Images
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

# Extract text from image using OCR
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

present_keywords = {"present", "current", "till date"}

# Calculate total experience from experience list
def calculate_total_experience(experience_list):
    total_experience = 0
    present_keywords = {"present", "current", "till date"}

    for exp in experience_list:
        duration = exp.duration.strip() if exp.duration else ""
        if not duration:
            log_message(f"Empty or missing duration field: {exp}")
            continue

        # Normalize duration string
        duration = (
            duration.replace("\u2014", "-")  # Replace em dash
            .replace("\u2013", "-")          # Replace en dash
            .replace("to", "-")
            .replace("Till date", "Present")
            .replace("till date", "Present")
            .replace("Current", "Present")
            .strip()
        )

        # Ensure proper spacing around hyphens
        duration = re.sub(r"(\S)-(\S)", r"\1 - \2", duration)

        # Handle durations like "2.5 years", "1.5 years"
        match = re.match(r"(\d+(\.\d+)?)\s*years?", duration, re.IGNORECASE)
        if match:
            total_experience += float(match.group(1))
            continue

        # Handle "X years Y months" format
        match = re.match(r"(\d+)\s*years?\s*(\d+)?\s*months?", duration, re.IGNORECASE)
        if match:
            years = int(match.group(1))
            months = int(match.group(2)) if match.group(2) else 0
            total_experience += years + months / 12
            continue

        # Handle "X months" format
        match = re.match(r"(\d+)\s*months?", duration, re.IGNORECASE)
        if match:
            total_experience += int(match.group(1)) / 12
            continue

        try:
            # Attempt to split durations like "July 2021 - Present" or malformed cases
            parts = re.split(r"\s*-\s*", duration)
            if len(parts) != 2:
                log_message(f"Malformed duration string: '{duration}'")
                continue

            start_date_str, end_date_str = parts
            try:
                start_date = parser.parse(start_date_str.strip(), dayfirst=True)
            except Exception:
                log_message(f"Error parsing start date '{start_date_str.strip()}'")
                continue

            if end_date_str.strip().lower() in present_keywords:
                end_date = datetime.now()
            else:
                try:
                    end_date = parser.parse(end_date_str.strip(), dayfirst=True)
                except Exception:
                    log_message(f"Error parsing end date '{end_date_str.strip()}'")
                    continue

            # Calculate years of experience
            years_of_experience = (end_date.year - start_date.year) + (end_date.month - start_date.month) / 12
            total_experience += years_of_experience
        except Exception as e:
            log_message(f"Error parsing duration '{duration}': {str(e)}")

    return round(total_experience, 2) 

# Calculate relevant years of experience
def calculate_relevant_experience(experience_list):
    relevant_experience = {}

    for exp in experience_list:
        duration = exp.duration.strip() if exp.duration else ""
        if not duration:
            log_message(f"Empty or missing duration field: {exp}")
            continue

        # Normalize duration string
        duration = (
            duration.replace("\u2014", "-")  # Replace em dash
            .replace("\u2013", "-")          # Replace en dash
            .replace("to", "-")
            .replace("Till date", "Present")
            .replace("till date", "Present")
            .replace("Current", "Present")
            .strip()
        )

        # Ensure proper spacing around hyphens
        duration = re.sub(r"(\S)-(\S)", r"\1 - \2", duration)

        # Handle durations like "2.5 years", "1.5 years"
        match = re.match(r"(\d+(\.\d+)?)\s*years?", duration, re.IGNORECASE)
        if match:
            years = float(match.group(1))
            relevant_experience[exp.job_title] = relevant_experience.get(exp.job_title, 0) + years
            continue

        # Handle "X years Y months" format
        match = re.match(r"(\d+)\s*years?\s*(\d+)?\s*months?", duration, re.IGNORECASE)
        if match:
            years = int(match.group(1))
            months = int(match.group(2)) if match.group(2) else 0
            total_years = years + months / 12
            relevant_experience[exp.job_title] = relevant_experience.get(exp.job_title, 0) + total_years
            continue

        # Handle "X months" format
        match = re.match(r"(\d+)\s*months?", duration, re.IGNORECASE)
        if match:
            years = int(match.group(1)) / 12
            relevant_experience[exp.job_title] = relevant_experience.get(exp.job_title, 0) + years
            continue

        try:
            # Attempt to split durations like "July 2021 - Present" or malformed cases
            parts = re.split(r"\s*-\s*", duration)
            if len(parts) != 2:
                log_message(f"Malformed duration string: '{duration}'")
                continue

            start_date_str, end_date_str = parts
            try:
                start_date = parser.parse(start_date_str.strip(), dayfirst=True)
            except Exception:
                log_message(f"Error parsing start date '{start_date_str.strip()}'")
                continue

            if end_date_str.strip().lower() in present_keywords:
                end_date = datetime.now()
            else:
                try:
                    end_date = parser.parse(end_date_str.strip(), dayfirst=True)
                except Exception:
                    log_message(f"Error parsing end date '{end_date_str.strip()}'")
                    continue

            # Calculate years of experience
            years_of_experience = (end_date.year - start_date.year) + (end_date.month - start_date.month) / 12
            relevant_experience[exp.job_title] = relevant_experience.get(exp.job_title, 0) + years_of_experience
        except Exception as e:
            log_message(f"Error parsing duration '{duration}': {str(e)}")

    return relevant_experience

# Process text with OpenAI API using Pydantic schema
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
            "address": "string or null"
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
        "total_experience": "float or null"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a structured JSON generator. Convert the provided resume text into a JSON object "
                    f"matching the following schema: {json.dumps(schema, indent=2)}. "
                    "Ensure the JSON strictly adheres to this format. Handle missing fields with null values. "
                    "Fetch only the highest level of education that the candidate has pursued. "
                    "Ensure the response avoids Unicode characters (e.g., use '-' instead of '—')."
                    "Ensure the accurate location or address of each company is captured exactly as mentioned in the experience section."
                    "Fetch all details provided in the experience section without omitting any information."
                    "For education details, include both the full name and short form (e.g., Bachelor of Technology (B.Tech) or Master of Science (M.Sc) or any other degree)."
                    "Also, calculate the total experience based on the durations provided in the experience section and include this as a numeric value in the 'total_experience' field. "
                    "If the current working location does not have an address, keep the address field null. Do not include the company name in the address."
                    "If the duration is in months, convert it to years. If the duration is a mix of months and years (e.g., '2 years 3 months'), calculate the total experience accurately."
                )
            },
            {
                "role": "user",
                "content": f"Here is the extracted text from the resume:\n\n{extracted_text}"
            }
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

        # Validate the response with Pydantic models
        try:
            candidate = Candidate(**processed_data)
            total_experience = calculate_total_experience(candidate.experience)
            candidate.total_experience = total_experience
            candidate.relevant_experience = calculate_relevant_experience(candidate.experience)
            return candidate.dict()  # Return as a dictionary for easy storage
        except Exception as e:
            log_message(f"Validation error: {str(e)}")
            return None

    except Exception as e:
        log_message(f"Error during OpenAI API call: {str(e)}")
        return None

# Process PDFs and save as nested JSON
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
    drive_folder_id = "1zXQqZuc3UupGF1uPA9sIQxesUUN92C4x"
    output_file_path = "/Users/vinayaksharma/Documents/CV-Testing/aggregated_data.json"

    try:
        drive_service = authenticate_to_drive(credentials_path)
        process_pdfs_to_nested_json(drive_service, drive_folder_id, output_file_path)
    except Exception as e:
        log_message(f"Error in main execution: {str(e)}")