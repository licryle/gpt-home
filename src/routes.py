from semantic_router.layer import RouteLayer
import semantic_router.encoders as encoders
from semantic_router.encoders import HuggingFaceEncoder
from semantic_router import Route

from actions import *

API_KEY = ""




logger.info(f"Initializing encoder, this may take time")

try:
    encoder = HuggingFaceEncoder(model_name="all-MiniLM-L6-v2")
except Exception as e:
    logger.debug(f"Error initializing encoder: {e}")

logger.info(f"Encoder: {encoder}")
if encoder is not None:
    logger.info("Encoder initialized")
else:
    logger.error("Encoder not initialized")

# Define routes
alarm_route = Route(
    name="alarm_reminder_action",
    utterances=[
        "set an alarm",
        "wake me up",
        "remind me in"
    ]
)

spotify_route = Route(
    name="spotify_action",
    utterances=[
        "play some music",
        "next song",
        "pause the music",
        "play earth wind and fire on Spotify",
        "play my playlist"
    ]
)

weather_route = Route(
    name="open_weather_action",
    utterances=[
        "how's the weather today?",
        "tell me the weather",
        "what is the temperature",
        "is it going to rain",
        "what is the weather like in New York"
    ]
)

lights_route = Route(
    name="philips_hue_action",
    utterances=[
        "turn on the lights",
        "switch off the lights",
        "dim the lights",
        "change the color of the lights",
        "set the lights to red"
    ]
)

calendar_route = Route(
    name="caldav_action",
    utterances=[
        "schedule a meeting",
        "what's on my calendar",
        "add an event",
        "what is left to do today"
    ]
)

general_route = Route(
    name="llm_action",
    utterances=[
        "how's it going",
        "tell me a joke",
        "what's the time",
        "how are you",
        "what is the meaning of life",
        "what is the capital of France",
        "what is the difference between Python 2 and Python 3",
        "what is the best programming language",
        "who was the first president of the United States",
        "what is the largest mammal"
    ]
)

routes = [alarm_route, spotify_route, weather_route, lights_route, calendar_route, general_route]

# Initialize RouteLayer with the encoder and routes
rl = RouteLayer(encoder=encoder, routes=routes)

class ActionRouter:
    def __init__(self):
        self.route_layer = rl

    def resolve(self, text):
        logger.info(f"Resolving text: {text}")
        try:
            result = self.route_layer(text)
            action_name = result.name if result else "llm_action"
            logger.info(f"Resolved action: {action_name}")
            return action_name
        except Exception as e:
            logger.error(f"Error resolving text: {e}")
            return "llm_action"

class Action:
    def __init__(self, action_name, text):
        self.action_name = action_name
        self.text = text

    async def perform(self, **kwargs):
        try:
            action_func = globals()[self.action_name]
            logger.info(f"Performing action: {self.action_name} with text: {self.text}")
            return await action_func(self.text, **kwargs)
        except KeyError:
            logger.warning(f"Action {self.action_name} not found. Falling back to llm_action.")
            action_func = globals()["llm_action"]
            return await action_func(self.text, **kwargs)
        except Exception as e:
            logger.error(f"Error performing action {self.action_name}: {e}")
            return "Action failed due to an error."

async def action_router(text: str, router=ActionRouter()):
    try:
        action_name = router.resolve(text)
        act = Action(action_name, text)
        return await act.perform()
    except Exception as e:
        logger.error(f"Error in action_router: {e}")
        return "Action routing failed due to an error."



def my_log_handler(record):
    # This function will be called on every log record
    if record.levelno >= logging.ERROR and "Exception occurred" in record.getMessage():
        logger.error("Caught semantic-router exception log:", record.getMessage())
        # You could raise, store, or handle the error here
    # Optionally, return False to prevent further propagation

class CustomHandler(logging.Handler):
    def emit(self, record):
        my_log_handler(record)

sem_logger = logging.getLogger("semantic_router.utils.logger")
sem_logger.addHandler(CustomHandler())
sem_logger.setLevel(logging.ERROR)
