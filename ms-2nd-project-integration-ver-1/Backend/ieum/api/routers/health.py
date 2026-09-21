from fastapi import APIRouter

from ieum.config import get_settings
from ieum.providers.llm import get_llm_provider
from ieum.providers.productivity import get_productivity_provider
from ieum.providers.vector_search import get_vector_search_provider
from ieum.providers.embedding import get_embedding_provider


router = APIRouter(tags=["health"])


@router.get("/")
def read_root():
    return {"status": "Backend is running", "mode": get_settings().app_mode}


@router.get("/health/live")
def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready():
    settings = get_settings()
    llm_provider = get_llm_provider()
    productivity_provider = get_productivity_provider()
    vector_search_provider = get_vector_search_provider()
    embedding_provider = get_embedding_provider()
    return {
        "status": "ready",
        "mode": settings.app_mode,
        "llm_provider": llm_provider.provider_name,
        "llm_model": llm_provider.model_name,
        "productivity_provider": productivity_provider.provider_name,
        "vector_search_provider": vector_search_provider.provider_name,
        "embedding_provider": embedding_provider.provider_name,
        "embedding_model": embedding_provider.model_id,
        "azure_providers_loaded": settings.app_mode == "azure",
    }
