# import time
# import json
# import os
# from pathlib import Path
# import openai
# from pinecone import Pinecone, ServerlessSpec
# from dotenv import load_dotenv

# load_dotenv()

# openai.api_key = os.getenv("OPENAI_API_KEY")
# pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# class PineconeLoader:
#     """
#     A class designed to load JSON files from two sources (jd_json and aggregated_json),
#     process them, and index their content into a Pinecone vector database.

#     Attributes:
#         jd_json_path (str): Path to the Job Description JSON file.
#         aggregated_json_path (str): Path to the Aggregated JSON file.
#         index_name (str): Name of the Pinecone index for storing vector embeddings.
#         embedding_model (str): Model identifier for generating text embeddings using OpenAI.
#     """

#     def __init__(self, jd_json_path, aggregated_json_path, index_name="cv-automation", embedding_model='text-embedding-3-small'):
#         """
#         Initializes the loader with specified parameters and creates a Pinecone index if it does not exist.

#         Args:
#             jd_json_path (str): Path to the Job Description JSON file.
#             aggregated_json_path (str): Path to the Aggregated JSON file.
#             index_name (str): Name of the Pinecone index for storing vector embeddings. Defaults to "default-index".
#             embedding_model (str): Model identifier for generating text embeddings using OpenAI. Defaults to 'text-embedding-3-small'.
#         """
#         self.jd_json_path = jd_json_path
#         self.aggregated_json_path = aggregated_json_path
#         self.index_name = index_name
#         self.embedding_model = embedding_model
#         self.index_id = 0

#         index_names = [index['cv-index'] for index in pc.list_indexes()]
#         if self.index_name not in index_names:
#             pc.create_index(
#                 name=self.index_name,
#                 dimension=1536,
#                 metric="euclidean",
#                 spec=ServerlessSpec(cloud="aws", region="us-east-1")
#             )
#             print(f"Successfully created the new index with name {self.index_name}")

#     def load_and_index(self):
#         """
#         Main method to load JSON files, process them, and index their contents.
#         """
#         jd_data = self.load_json(self.jd_json_path)
#         if jd_data:
#             self.process_json(jd_data, "jd_json")

#         aggregated_data = self.load_json(self.aggregated_json_path)
#         if aggregated_data:
#             self.process_json(aggregated_data, "aggregated_json")

#     def load_json(self, file_path):
#         """
#         Loads a JSON file from the specified path.

#         Args:
#             file_path (str): Path to the JSON file.

#         Returns:
#             dict: The loaded JSON data.
#         """
#         try:
#             with open(file_path, 'r') as file:
#                 return json.load(file)
#         except Exception as e:
#             print(f"Error loading JSON file {file_path}: {e}")
#             return None

#     def process_json(self, json_data, source_type):
#         """
#         Processes JSON data and indexes it into Pinecone.

#         Args:
#             json_data (dict): The JSON data to be processed.
#             source_type (str): The type of JSON data (e.g., "jd_json" or "aggregated_json").
#         """
#         try:
#             # Convert JSON to text format for embedding
#             text_content = self.json_to_text(json_data)
#             if text_content:
#                 self.custom_upsert({'id': source_type, 'content': text_content}, source_type=source_type)
#         except Exception as e:
#             print(f"Error processing JSON data from {source_type}: {e}")

#     def json_to_text(self, json_data):
#         """
#         Converts JSON data into a text format suitable for embedding.

#         Args:
#             json_data (dict): The JSON data to be converted.

#         Returns:
#             str: The text representation of the JSON data.
#         """
#         text_content = []
#         for key, value in json_data.items():
#             text_content.append(f"{key}: {value}")
#         return ' '.join(text_content)

#     def generate_embedding(self, text):
#         """
#         Generates and returns a vector embedding for the given text using the specified embedding model.

#         Args:
#             text (str): The text to be embedded.

#         Returns:
#             list: A list containing the numerical vector embedding of the input text.
#         """
#         response = openai.embeddings.create(input=text, model=self.embedding_model)
#         return response.data[0].embedding

#     def custom_upsert(self, document, source_type):
#         """
#         Upserts the document into Pinecone with generated embeddings and metadata.

#         Args:
#             document (dict): The document containing the text content.
#             source_type (str): The type of JSON data (e.g., "jd_json" or "aggregated_json").
#         """
#         try:
#             # Manually split the document content into chunks
#             text_chunks = self.split_text_into_chunks(document['content'], chunk_size=4000)
#             index = pc.Index(self.index_name)
#             upsert_count = 0

#             # Generate and upsert embeddings for each chunk
#             for chunk in text_chunks:
#                 embedding = self.generate_embedding(chunk)
#                 upsert_count += 1
#                 vector_id = f'{self.index_id + 1}'
#                 self.index_id += 1
#                 metadata = {'Chunk_ID': upsert_count, 'source_type': source_type, 'content': chunk}
#                 index.upsert(vectors=[(vector_id, embedding, metadata)])
#                 print(f"Upserted chunk {upsert_count} of document {vector_id} into Pinecone.")

#             print(f"Total {upsert_count} parts upserted for document {source_type}.")
#         except Exception as e:
#             print(f"Error upserting document {document['id']}: {e}")

#     def split_text_into_chunks(self, text, chunk_size=2000):
#         """
#         Splits the text into chunks of specified size.

#         Args:
#             text (str): The text to be split.
#             chunk_size (int): The size of each chunk.

#         Returns:
#             list: A list of text chunks.
#         """
#         return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# # Define the local entry point for the application
# def run_loader():
#     """
#     Defines entry point for the application.
#     This function acts as the entry point for running the `loader_func`.
#     """
#     loader = PineconeLoader(
#         jd_json_path="/Users/vinayaksharma/Documents/cv_automation/jd_data.json",
#         aggregated_json_path="/Users/vinayaksharma/Documents/cv_automation/aggregated_data.json",
#         index_name="cv-index"
#     )
#     loader.load_and_index()

# if __name__ == "__main__":
#     run_loader()

########################################################################################################################################




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