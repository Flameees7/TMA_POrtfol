"""
Application entry point for running TMA Store Backend with Uvicorn.
"""

import os
import sys
import uvicorn
from backend.app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    port = int(os.getenv("PORT", settings.SERVER_PORT))
    host = os.getenv("HOST", settings.SERVER_HOST)

    print(f"================================================================")
    print(f"🚀 Starting TMA Shop Server on http://{host}:{port}")
    print(f"📚 Swagger API Docs: http://localhost:{port}/docs")
    print(f"🛍 TMA Mini App UI: http://localhost:{port}/")
    print(f"================================================================")

    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )
