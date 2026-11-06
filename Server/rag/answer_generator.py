import os
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from langchain_groq import ChatGroq
from rag.prompts import qa_prompt, contextualize_q_prompt


class AnswerGenerator:
    """
    Manages the Groq LLM integration and system prompt templates.
    Replaces local Ollama inference with remote high-speed Groq API inference.
    """

    def __init__(self, model_name: str = None, temperature: float = 0.2):
        # 1. Validate API Key
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "GROQ_API_KEY is not set or empty. "
                "Please configure GROQ_API_KEY in your Server/.env file."
            )

        # 2. Configure model: priority to argument, then GROQ_MODEL env var, then default
        self.model_name = model_name or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.temperature = temperature

        print(f"Initializing Answer Generator with ChatGroq model: {self.model_name}")

        # 3. Initialize Groq Chat Model via LangChain
        self.llm = ChatGroq(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=400,
            max_retries=2,
            timeout=15.0,
        )

    def get_llm(self):
        return self.llm

    def get_qa_prompt(self):
        return qa_prompt

    def get_contextualize_q_prompt(self):
        return contextualize_q_prompt
 
