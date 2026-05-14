
import httpx
import os
from fastapi import APIRouter, Response
from pydantic import BaseModel
import asyncio
import google.generativeai as genai

router = APIRouter()

# --- Configuration ---
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:1236/v1/chat/completions")
OPENWEBUI_API_URL = os.getenv("OPENWEBUI_API_URL", "http://localhost:8080/api/chat/completions")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Configure Google AI
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Extract base URLs for health checks
OLLAMA_BASE_URL = OLLAMA_API_URL.rsplit('/', 2)[0] if '/v1/chat/completions' in OLLAMA_API_URL else OLLAMA_API_URL
OPENWEBUI_BASE_URL = OPENWEBUI_API_URL.rsplit('/', 2)[0] if '/api/chat' in OPENWEBUI_API_URL else OPENWEBUI_API_URL


class ServiceStatus(BaseModel):
    status: str
    url: str
    details: str | None = None

class HealthCheckResponse(BaseModel):
    google_ai_service: ServiceStatus
    openwebui_rag_service: ServiceStatus
    ollama_llm_service: ServiceStatus


async def check_service(url: str) -> tuple[str, str]:
    """Checks if a service is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.head(url)
            if response.is_success or response.is_redirect:
                return "ONLINE", f"Service is reachable (Status: {response.status_code})"
            else:
                return "OFFLINE", f"Service returned status {response.status_code}"
    except httpx.ConnectError as e:
        return "OFFLINE", f"Connection error: {e}"
    except httpx.TimeoutException:
        return "OFFLINE", "Request timed out after 5 seconds"
    except Exception as e:
        return "ERROR", f"An unexpected error occurred: {e}"

async def check_google_ai_status() -> tuple[str, str]:
    """Checks the status of the Google AI (Gemini) API."""
    if not GOOGLE_API_KEY:
        return "OFFLINE", "GOOGLE_API_KEY is not set"
    try:
        # A lightweight, non-billed call to list models
        models = await asyncio.to_thread(lambda: [m for m in genai.list_models()])
        if any("generateContent" in m.supported_generation_methods for m in models):
             return "ONLINE", "Successfully connected and found usable models"
        else:
            return "ERROR", "Connected, but no models with 'generateContent' method found"
    except Exception as e:
        return "ERROR", f"API connection failed: {str(e)}"


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """
    Performs a health check on dependent services (Google AI, OpenWebUI, Ollama).
    """
    (google_status, google_details), (openwebui_status, openwebui_details), (ollama_status, ollama_details) = await asyncio.gather(
        check_google_ai_status(),
        check_service(OPENWEBUI_BASE_URL),
        check_service(OLLAMA_BASE_URL)
    )

    return HealthCheckResponse(
        google_ai_service=ServiceStatus(status=google_status, url="https://generativeai.google.com", details=google_details),
        openwebui_rag_service=ServiceStatus(status=openwebui_status, url=OPENWEBUI_BASE_URL, details=openwebui_details),
        ollama_llm_service=ServiceStatus(status=ollama_status, url=OLLAMA_BASE_URL, details=ollama_details)
    )
