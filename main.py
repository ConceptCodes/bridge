from src.logger import get_logger


logger = get_logger(__name__)


def main() -> None:
    logger.info("Application starting")


if __name__ == "__main__":
    main()
