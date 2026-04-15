from src.app import app
from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    import uvicorn

    settings = get_settings()
    logger.info("Application starting")
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        timeout_keep_alive=settings.uvicorn_timeout_keep_alive_seconds,
        limit_concurrency=settings.uvicorn_limit_concurrency,
    )


if __name__ == "__main__":
    main()
