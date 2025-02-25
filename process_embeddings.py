import os
import json
import openai
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI and Pinecone
openai.api_key = os.getenv("OPENAI_API_KEY")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

class PineconeLoader:
    def __init__(self, aggregated_json_path, index_name="cv-automation", embedding_model='text-embedding-3-small'):
        self.aggregated_json_path = aggregated_json_path
        self.index_name = index_name
        self.embedding_model = embedding_model

        # Check if the index exists, and create it if it doesn't
        index_names = [index['name'] for index in pc.list_indexes()]
        if self.index_name not in index_names:
            pc.create_index(
                name=self.index_name,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric="euclidean",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            print(f"Successfully created the new index with name {self.index_name}")

    def load_and_index(self):
        """Load JSON data and index it into Pinecone."""
        aggregated_data = self.load_json(self.aggregated_json_path)
        if aggregated_data:
            self.process_candidates(aggregated_data)

    def load_json(self, file_path):
        """Load JSON data from a file."""
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading JSON file {file_path}: {e}")
            return None

    def process_candidates(self, json_data):
        """Process all candidates in the JSON data."""
        try:
            candidates = json_data.get("candidates", [])
            for candidate in candidates:
                self.process_candidate(candidate)
        except Exception as e:
            print(f"Error processing candidates: {e}")

    def process_candidate(self, candidate):
        """Process a single candidate."""
        try:
            candidate_id = candidate.get("personal_info", {}).get("name", "null")
            combined_text = self.combine_all_sections(candidate)
            self.upsert_candidate(candidate_id, combined_text)
        except Exception as e:
            print(f"Error processing candidate {candidate_id}: {e}")

    def combine_all_sections(self, candidate):
        """Combine all sections of a candidate's data into a single text."""
        sections = {
            "personal_info": candidate.get("personal_info", {}),
            "skills": candidate.get("skills", []),
            "experience": candidate.get("experience", []),
            "education": candidate.get("education", []),
            "projects": candidate.get("projects", []),
            "certifications": candidate.get("certifications", []),
            "achievements": candidate.get("achievements", []),
            "total_experience": candidate.get("total_experience", {}),
            "relevant_experience": candidate.get("relevant_experience", {})
        }
        combined_text = ""
        for section_name, section_content in sections.items():
            combined_text += f"{section_name}: {self.json_to_text(section_content)}\n"
        return combined_text

    def json_to_text(self, json_data):
        """Convert JSON data to a plain text string."""
        if isinstance(json_data, dict):
            return ' '.join([f"{key}: {value}" for key, value in json_data.items()])
        elif isinstance(json_data, list):
            return ' '.join([self.json_to_text(item) for item in json_data])
        else:
            return str(json_data)

    def generate_embedding(self, text):
        """Generate embeddings for the given text using OpenAI."""
        response = openai.embeddings.create(input=text, model=self.embedding_model)
        return response.data[0].embedding

    def upsert_candidate(self, candidate_id, combined_text):
        """Upsert a candidate's combined data into Pinecone."""
        try:
            index = pc.Index(self.index_name)
            embedding = self.generate_embedding(combined_text)
            metadata = {
                'candidate_id': candidate_id,
                'content': combined_text
            }
            # Upsert the candidate's data as a single vector
            index.upsert(vectors=[(candidate_id, embedding, metadata)])
            print(f"Upserted candidate {candidate_id} into Pinecone.")
        except Exception as e:
            print(f"Error upserting candidate {candidate_id}: {e}")

# Entry point
def run_loader():
    loader = PineconeLoader(
        aggregated_json_path="/Users/vinayaksharma/Documents/cv_automation/aggregated_data.json",
        index_name="cv-index"
    )
    loader.load_and_index()

if __name__ == "__main__":
    run_loader()
