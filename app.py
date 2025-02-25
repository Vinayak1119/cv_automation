import streamlit as st
import os
import json
from process_embeddings import PineconeLoader  
# Streamlit app title
st.title("Pinecone Candidate Data Loader")

# File uploader for JSON file
uploaded_file = st.file_uploader("Upload a JSON file containing candidate data", type=["json"])

if uploaded_file is not None:
    # Save the uploaded file temporarily
    file_path = os.path.join("/tmp", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Initialize PineconeLoader with the uploaded file
    loader = PineconeLoader(
        aggregated_json_path=file_path,
        index_name="cv-index"
    )

    # Button to trigger the loading and indexing process
    if st.button("Load and Index Data"):
        with st.spinner("Loading and indexing data..."):
            loader.load_and_index()
        st.success("Data successfully loaded and indexed into Pinecone!")

    # Optionally, display the content of the uploaded file
    if st.checkbox("Show uploaded JSON content"):
        with open(file_path, "r") as f:
            json_data = json.load(f)
            st.json(json_data)