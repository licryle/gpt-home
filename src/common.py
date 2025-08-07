from dotenv import load_dotenv
from pathlib import Path
import litellm
import logging
import json


SOURCE_DIR = Path(__file__).parent
log_file_path = SOURCE_DIR / "events.log"

# Load .env file
load_dotenv(dotenv_path='frontend/.env')

# Add a new 'SUCCESS' logging level
logging.SUCCESS = 25  # Between INFO and WARNING
logging.addLevelName(logging.SUCCESS, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(logging.SUCCESS):
        self._log(logging.SUCCESS, message, args, **kws)

logging.Logger.success = success

logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(levelname)s:[%(asctime)s]: %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize the LiteLLM API key
with open("settings.json", "r") as f:
    settings = json.load(f)
    litellm.api_key = settings["litellm_api_key"]


def load_settings():
    settings_path = SOURCE_DIR / "settings.json"
    with open(settings_path, "r") as f:
        settings = json.load(f)
        return settings
