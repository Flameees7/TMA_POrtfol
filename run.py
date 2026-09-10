"""
Application entry point for running TMA Store Backend with Uvicorn.
"""

import sys
import uvicorn
from backend.app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print(f"================================================================")
    print(f"🚀 Starting TMA Shop Server on http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"📚 Swagger API Docs: http://localhost:{settings.SERVER_PORT}/docs")
    print(f"🛍 TMA Mini App UI: http://localhost:{settings.SERVER_PORT}/")
    print(f"================================================================")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
