"""FastAPI server startup script."""

import logging
import uvicorn
from .main import app
from ..core.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def start_server():
    """Start the FastAPI server."""
    logger.info("Starting Document Forensics API server")
    
    uvicorn.run(
        "src.document_forensics.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    start_server()