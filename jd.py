import os
import io
import re
import json
import requests
from pdf2image import convert_from_bytes
import pytesseract
import docx2txt
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# AWS and OpenAI credentials
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pydantic model for Job Description
class JobDescription(BaseModel):
    role: Optional[str] = None
    experience: Optional[str] = None
    location: Optional[str] = None
    job_description: Optional[str] = None
    key_responsibilities: Optional[List[str]] = []
    qualifications: Optional[List[str]] = []
    skills: Optional[List[str]] = []

# Authenticate to S3
def authenticate_to_s3():
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        print("✅ Authenticated to S3.")
        return s3_client
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"❌ Authentication failed: {e}")
        raise

# List files in an S3 bucket
def list_files_in_bucket(s3_client, bucket_name, prefix=""):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        return response.get('Contents', []) if 'Contents' in response else []
    except Exception as e:
        print(f"❌ Error listing files: {e}")
        return []

# Download a file from S3 as bytes
def download_file_as_bytes(s3_client, bucket_name, file_key):
    try:
        file_stream = io.BytesIO()
        s3_client.download_fileobj(bucket_name, file_key, file_stream)
        file_stream.seek(0)
        return file_stream
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return None

# Extract text from a PDF file
def extract_text_from_pdf(pdf_bytes):
    try:
        images = convert_from_bytes(pdf_bytes.read())
        extracted_text = " ".join([pytesseract.image_to_string(image) for image in images if image])
        return extracted_text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return ""

# Extract text from a Word document
def extract_text_from_word(doc_bytes):
    try:
        text = docx2txt.process(io.BytesIO(doc_bytes.read()))
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from Word: {e}")
        return ""

# Clean OpenAI JSON response
def clean_json_response(response_text):
    match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
    return match.group(1) if match else response_text.strip()

# Process extracted text with OpenAI
def process_text_with_openai(extracted_text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    schema = {
        "role": "string or null",
        "experience": "string or null",
        "location": "string or null",
        "job_description": "string or null",
        "key_responsibilities": ["string"],
        "qualifications": ["string"],
        "skills": ["string"]
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    f"Extract job details from the given text based on this JSON schema: {json.dumps(schema, indent=2)}.\n"
                    "Ensure the response avoids Unicode characters (e.g., use '-' instead of '—').\n"
                    "Additionally, infer relevant skills based on the qualifications provided."
                )
            },
            {"role": "user", "content": extracted_text}
        ],
        "max_tokens": 2000
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
        
        response_json = response.json()
        if "choices" not in response_json or not response_json["choices"]:
            print("❌ OpenAI API returned an empty response.")
            return None
        
        content = response_json["choices"][0]["message"]["content"].strip()
        cleaned_json = clean_json_response(content)
        
        return json.loads(cleaned_json)

    except json.JSONDecodeError:
        print("❌ Error: Unable to parse JSON response.")
        print("Raw Response:", content)
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None

# Validate and map JD data to the Pydantic model
def validate_and_map_jd_data(jd_data):
    try:
        return JobDescription(**jd_data).dict()
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return None

# Save JSON data to a local file
def save_json_to_local(json_data, output_file_path):
    try:
        # Ensure we overwrite any existing file
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        with open(output_file_path, "w", encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=4)
        print(f"✅ JSON data successfully saved to: {output_file_path}")
    except Exception as e:
        print(f"❌ Error saving JSON to local file: {e}")

# Process a single file
def process_file(s3_client, bucket_name, file):
    file_key = file['Key']
    print(f"🔍 Processing: {file_key}")
    file_stream = download_file_as_bytes(s3_client, bucket_name, file_key)
    if not file_stream:
        return None

    if file_key.endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file_stream)
    elif file_key.endswith('.docx') or file_key.endswith('.doc'):
        extracted_text = extract_text_from_word(file_stream)
    else:
        return None

    if not extracted_text:
        print(f"⏩ Skipping {file_key} due to empty extracted text.")
        return None

    jd_data = process_text_with_openai(extracted_text)
    validated_jd = validate_and_map_jd_data(jd_data) if jd_data else None

    return validated_jd

# Process JDs from S3 and save JSON to local drive
def process_jds_to_local(s3_client, bucket_name, prefix, output_file_path):
    files = list_files_in_bucket(s3_client, bucket_name, prefix)
    aggregated_data = {"job_descriptions": []}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {executor.submit(process_file, s3_client, bucket_name, file): file for file in files}
        
        for future in as_completed(future_to_file):
            validated_jd = future.result()
            if validated_jd:
                aggregated_data["job_descriptions"].append(validated_jd)

    # Save JSON to local file
    save_json_to_local(aggregated_data, output_file_path)

if __name__ == "__main__":
    bucket_name = "datacrux-dev"
    prefix = "conversationAttachment/"  
    output_file_path = "jd_data.json"  # Local file path to save the JSON

    try:
        # Authenticate to S3
        s3_client = authenticate_to_s3()
        
        # Process JDs and save JSON to local drive
        process_jds_to_local(s3_client, bucket_name, prefix, output_file_path)
    except Exception as e:
        print(f"❌ Error in main execution: {e}")