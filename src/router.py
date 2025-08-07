import logging
from common import logger

from routes import routes_dict, GeneralRoute # import all routes from the package

from semantic_router.layer import RouteLayer
import semantic_router.encoders as encoders
from semantic_router.encoders import HuggingFaceEncoder

class Router:
    encoder = None
    route_layer = None
    routes_dict = None

    def __init__(self, encoderModelName, routes_dict):
        self.routes_dict = routes_dict

        # Initialize the encoder
        self._initEncoder(encoderModelName)
        
        # Initialize RouteLayer with the encoder and routes
        available_routes = [r.route() for c, r in routes_dict.items()]
        logger.debug(f"Routes available: {available_routes}")

        print(self.encoder)
        self.route_layer = RouteLayer(encoder=self.encoder, routes=available_routes)

    def _initEncoder(self, encoderModelName):
        # Init encoderLogging
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

        # Load and Init Encoder
        self.encoder = HuggingFaceEncoder(model_name=encoderModelName)

    def isReady(self):
        return self.encoder is not None and self.route_layer is not None
    
    def resolveRoute(self, text):
        if not self.isReady():
            raise ValueError("Router is not ready. Encoder or route layer is not initialized.")

        try:
            r = self.route_layer(text)
            if r is None:
                raise ValueError("No route found for the given text.")
    
            logger.info(f"Resolved route: {r}, {self.routes_dict[r.name]}")
            
        except Exception as e:
            logger.error(f"Error resolving text, defaulting to GenericLLM: {e}")
            return GeneralRoute()

        return self.routes_dict[r.name]()

class AssistantRouter(Router):
    def __init__(self, encoderModelName):
        super().__init__(encoderModelName, routes_dict)