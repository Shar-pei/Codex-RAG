from __future__ import annotations

import os
from contextlib import asynccontextmanager

from ascii_colors import ASCIIColors

from lightrag.kg.shared_storage import finalize_share_data
from lightrag.utils import logger


def create_app_lifespan(rag):
    @asynccontextmanager
    async def lifespan(app):
        """Lifespan context manager for startup and shutdown events."""
        app.state.background_tasks = set()

        try:
            await rag.initialize_storages()
            await rag.check_and_migrate_data()

            ASCIIColors.green("\nServer is ready to accept connections! 馃殌\n")

            yield

        finally:
            await rag.finalize_storages()

            if "LIGHTRAG_GUNICORN_MODE" not in os.environ:
                logger.debug("Unvicorn Mode: finalizing shared storage...")
                finalize_share_data()
            else:
                logger.debug(
                    "Gunicorn Mode: postpone shared storage finalization to master process"
                )

    return lifespan
