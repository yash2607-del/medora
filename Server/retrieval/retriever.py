from typing import List, Optional, Any
import sys
import os

# Ensure the Server directory is in the path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from pydantic import Field
from vectordb.chroma_client import ChromaClient
from retrieval.normalizer import QueryNormalizer

class NormalizedRetriever(BaseRetriever):
    """
    Custom Retriever that normalizes queries, corrects typos,
    expands medical abbreviations and layperson synonyms, and merges candidates.
    """
    base_retriever: Any = Field(description="The underlying ChromaDB retriever")
    normalizer: QueryNormalizer = Field(default_factory=QueryNormalizer)

    def _get_relevant_documents(self, query: str) -> List[Document]:
        normalized_query = self.normalizer.normalize(query)
        if normalized_query.lower() != query.lower():
            print(f"[Query Normalization] '{query}' -> '{normalized_query}'")
            return self.base_retriever.invoke(normalized_query)
        return self.base_retriever.invoke(query)

class AdvancedRetriever:
    """
    Fast Retriever that utilizes ChromaDB vector store + Query Normalization & Variation Handling.
    """
    def __init__(self, chroma_client: Optional[ChromaClient] = None, llm: Optional[BaseChatModel] = None, k: int = 5):
        self.chroma_client = chroma_client or ChromaClient()
        self.base_retriever = self.chroma_client.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        self.retriever = NormalizedRetriever(base_retriever=self.base_retriever)
        
    def get_retriever(self):
        return self.retriever
        
    def invoke(self, query: str):
        return self.retriever.invoke(query)
