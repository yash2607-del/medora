from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from rag.chain import RAGChain
import traceback
from groq import (
    AuthenticationError,
    RateLimitError,
    APIError,
    APITimeoutError,
    APIConnectionError,
    NotFoundError,
)

router = APIRouter()

# Lazy-loaded AI components to ensure fast boot, instant port binding, and <512MB RAM usage
rag_chain = None

def get_rag_chain():
    global rag_chain
    if rag_chain is None:
        print("Loading AI Components for API...")
        try:
            rag_chain = RAGChain()
            print("AI Components Loaded!")
        except Exception as e:
            print(f"CRITICAL: Failed to initialize AI components: {e}")
            rag_chain = None
    return rag_chain

# Request/Response Models
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default_session"

class ChatResponse(BaseModel):
    answer: str
    source: str # Indicates if it used RAG ('diagnostics') or bypassed it ('chitchat')

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    chain = get_rag_chain()
    if chain is None:
        raise HTTPException(
            status_code=503,
            detail="AI Assistant is not properly initialized. Please verify backend GROQ_API_KEY configuration."
        )
    try:
        # Fast simple router
        lower_q = request.query.strip().lower()
        
        # Simple routing logic
        if lower_q in ["hi", "hello", "hey", "good morning"]:
            route = "chitchat"
        elif any(word in lower_q for word in ["nearby centre", "nearby center", "centre near me", "center near me", "test centre", "test center", "location", "center contact", "centre contact"]):
            # Check if user mentioned a state
            states = ["andhra pradesh", "goa", "gujarat", "karnataka", "maharashtra"]
            if any(s in lower_q for s in states):
                route = "diagnostics"
            else:
                route = "centre_prompt"
        else:
            route = "diagnostics"
        
        if route == "diagnostics":
            # 2. Use full RAG pipeline (Retrieval + Generation + History)
            response = chain.invoke(request.query, session_id=request.session_id)
            answer = response["answer"]
        elif route == "centre_prompt":
            answer = "Please mention your state (Andhra Pradesh, Goa, Gujarat, Karnataka, or Maharashtra) or city to view nearby Lord Diagnostics centres."
        else:
            # 3. Handle casual conversation without expensive retrieval
            answer = "Hello! Welcome to Lord Diagnostics. How can I assist you with our tests, pricing, or centres today?"
            
        return ChatResponse(answer=answer, source=route)
        
    except AuthenticationError as e:
        print(f"[Groq Auth Error] Invalid or unauthorized API key: {e}")
        raise HTTPException(
            status_code=401,
            detail="AI service authentication failed. Please verify the backend API key configuration."
        )
    except RateLimitError as e:
        print(f"[Groq Rate Limit] Rate limit exceeded: {e}")
        raise HTTPException(
            status_code=429,
            detail="AI service rate limit exceeded. Please try again shortly."
        )
    except (APITimeoutError, APIConnectionError) as e:
        print(f"[Groq Network Error] Connection or timeout error: {e}")
        raise HTTPException(
            status_code=504,
            detail="AI service network or timeout error. Please check connectivity and try again."
        )
    except NotFoundError as e:
        print(f"[Groq Model Not Found] Model not found: {e}")
        raise HTTPException(
            status_code=404,
            detail="The configured AI model was not found or is unavailable. Please check GROQ_MODEL in configuration."
        )
    except APIError as e:
        print(f"[Groq API Error] Groq API returned an error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Upstream AI provider error. Please try again later."
        )
    except ValueError as e:
        print(f"[Configuration Error] {e}")
        raise HTTPException(
            status_code=500,
            detail="AI service configuration error. Please check backend settings."
        )
    except Exception as e:
        print(f"Error during chat processing: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error while processing your request.")

@router.get("/health")
async def health_check():
    ai_status = "ready" if rag_chain is not None else "degraded (AI uninitialized)"
    return {"status": "ok", "ai_status": ai_status, "message": "Lord Diagnostics API is running."}

