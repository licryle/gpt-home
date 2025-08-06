import logging
from routes import routes_dict, route_classes, GeneralRoute # import all routes from the package

from common import logger

from semantic_router.layer import RouteLayer
import semantic_router.encoders as encoders
from semantic_router.encoders import HuggingFaceEncoder

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



# Initialize RouteLayer with the encoder and routes
rl = RouteLayer(encoder=encoder, routes=routes_dict)

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
            assistantRoute = route_classes[self.action_name]()
            logger.info(f"Performing action: {self.action_name} with text: {self.text}")
            return await assistantRoute.handle(self.text, **kwargs)
        except KeyError:
            logger.warning(f"Action {self.action_name} not found. Falling back to llm_action.")
            assistantRoute = GeneralRoute()
            return await assistantRoute.handle(self.text, **kwargs)
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
