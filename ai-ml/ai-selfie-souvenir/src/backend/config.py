from os import environ
from pathlib import Path

from dotenv import load_dotenv

# Base directory setup
_base_dir = Path(__file__).resolve().parent
_src_dir = _base_dir.parent

# Check for .env.local file
if (_dotenv_path := _src_dir / ".env.local").exists():
    load_dotenv(_dotenv_path)

    _config_file_setting = environ.get("CONFIG_FILE")
    if not _config_file_setting:
        raise ValueError(
            "CONFIG_FILE environment variable is required when .env.local exists"
        )

    _config_file_path = (_src_dir / _config_file_setting).resolve()
    if not _config_file_path.exists():
        raise FileNotFoundError(
            f"Config file specified by CONFIG_FILE not found: {_config_file_path}"
        )

    load_dotenv(_config_file_path)

    ENVIRONMENT = environ.get("ENVIRONMENT", "local")
else:
    ENVIRONMENT = environ.get("ENVIRONMENT", "production")

EVENT_TITLE = environ["EVENT_TITLE"]
APP_NAME = environ["APP_NAME"]
APP_SUBTITLE = environ["APP_SUBTITLE"]
FOOTER_CREDIT = environ["FOOTER_CREDIT"]

BASE_IMAGE_URI = environ["BASE_IMAGE_URI"]
BASE_IMAGE_LABEL = environ["BASE_IMAGE_LABEL"]
BASE_IMAGE_ATTRIBUTION = environ["BASE_IMAGE_ATTRIBUTION"]
BASE_IMAGE_ATTRIBUTION_URL = environ["BASE_IMAGE_ATTRIBUTION_URL"]

NANO_BANANA_MODEL_ID = environ["NANO_BANANA_MODEL_ID"]
PROMPT_TEMPLATE = environ["PROMPT_TEMPLATE"]

PRIMARY_COLOR = environ["PRIMARY_COLOR"]
ACCENT_COLOR = environ["ACCENT_COLOR"]

PRIVACY_NOTICE = environ["PRIVACY_NOTICE"]

RATE_LIMIT_MAX = int(environ["RATE_LIMIT_MAX"])
RATE_LIMIT_WINDOW = int(environ["RATE_LIMIT_WINDOW"])

CLOUD_RUN_REGION = environ.get("CLOUD_RUN_REGION", "")
_show_region_raw = environ.get("SHOW_CLOUD_RUN_REGION", "true").strip().lower()
SHOW_CLOUD_RUN_REGION = _show_region_raw in ("true", "1", "yes", "y", "t")


def get_public_config() -> dict[str, str | int]:
    """Returns comprehensive non-sensitive public configuration for client-side configuration."""
    return {
        "event_title": EVENT_TITLE,
        "app_name": APP_NAME,
        "app_subtitle": APP_SUBTITLE,
        "footer_credit": FOOTER_CREDIT,
        "base_image_uri": BASE_IMAGE_URI,
        "base_image_label": BASE_IMAGE_LABEL,
        "base_image_attribution": BASE_IMAGE_ATTRIBUTION,
        "base_image_attribution_url": BASE_IMAGE_ATTRIBUTION_URL,
        "primary_color": PRIMARY_COLOR,
        "accent_color": ACCENT_COLOR,
        "privacy_notice": PRIVACY_NOTICE,
    }
