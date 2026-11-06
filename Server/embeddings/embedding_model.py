import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

class EmbeddingModel:
    """
    Lightweight, high-performance ONNX embedding model using FastEmbed.
    Consumes ~80MB RAM (zero PyTorch overhead), perfectly sized for Render's 512MB RAM cap.
    """
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        print(f"Initializing FastEmbed ONNX model: {self.model_name} (~80MB RAM)")
        self.embeddings = FastEmbedEmbeddings(model_name=self.model_name)

    def get_embeddings(self) -> FastEmbedEmbeddings:
        """
        Returns the LangChain-compatible embeddings object, 
        ready to be passed to a VectorStore like Chroma.
        """
        return self.embeddings

if __name__ == "__main__":
    embedder = EmbeddingModel()
    test_text = "CBC blood test"
    print(f"\nTest embed_query(\"{test_text}\")")
    vector = embedder.embeddings.embed_query(test_text)
    print(f"Returns vector? {'Yes' if vector else 'No'}")
    print(f"Vector dimensions: {len(vector)}")
    print(f"First 5 dimensions: {vector[:5]}")
    print("Done.")
