import os
import requests
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Cloud registry for Google Drive files mapped per country
DESTINATION_REGISTRY = {
    "singapore": {
        "data_dir": "./data/singapore",
        "chroma_dir": "./chroma_store/singapore",
        "gdrive_files": [
            {
                "filename": "visit_singapore_itineraries.md",
                "file_id": "REPLACE_WITH_ITINERARIES_FILE_ID",
                "source_url": "https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/"
            },
            {
                "filename": "visit_singapore_practical.md",
                "file_id": "REPLACE_WITH_PRACTICAL_FILE_ID",
                "source_url": "https://www.visitsingapore.com/travel-tips/essential-travel-information/"
            },
            {
                "filename": "wikivoyage_singapore.md",
                "file_id": "REPLACE_WITH_WIKIVOYAGE_FILE_ID",
                "source_url": "https://en.wikivoyage.org/wiki/Singapore"
            }
        ]
    },
    "japan": {
        "data_dir": "./data/japan",
        "chroma_dir": "./chroma_store/japan",
        "gdrive_files": []
    }
}

class RAGEngine:
    def __init__(self, country: str = "singapore"):
        self.country = country.lower().strip()
        self.config = DESTINATION_REGISTRY.get(self.country, DESTINATION_REGISTRY["singapore"])
        self.data_dir = self.config["data_dir"]
        self.persist_dir = self.config["chroma_dir"]
        
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self._ensure_files_downloaded()
        self.vector_store = self._init_or_load_store()

    def _download_file(self, file_id: str, dest_path: str):
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(res.text)

    def _ensure_files_downloaded(self):
        os.makedirs(self.data_dir, exist_ok=True)
        for item in self.config.get("gdrive_files", []):
            if "REPLACE_WITH" in item["file_id"]:
                continue  # Skip download if running off locally placed markdown files
            dest = os.path.join(self.data_dir, item["filename"])
            if not os.path.exists(dest) or os.path.getsize(dest) == 0:
                self._download_file(item["file_id"], dest)

    def _init_or_load_store(self):
        if os.path.exists(self.persist_dir) and os.listdir(self.persist_dir):
            return Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)

        loader = DirectoryLoader(self.data_dir, glob="**/*.md", loader_cls=TextLoader)
        docs = loader.load()

        if not docs:
            # Fallback if directory is initialized empty
            return None

        splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
        chunks = splitter.split_documents(docs)

        for chunk in chunks:
            chunk.metadata["country"] = self.country
            chunk.metadata["source"] = os.path.basename(chunk.metadata.get("source", "knowledge_base"))

        return Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.persist_dir
        )

    def retrieve(self, query: str, top_k: int = 3):
        if not self.vector_store:
            return []
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=top_k)
        retrieved_contexts = []
        for doc, score in results:
            retrieved_contexts.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "knowledge_base"),
                "country": self.country,
                "relevance_score": round(score, 3)
            })
        return retrieved_contexts