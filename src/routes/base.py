from semantic_router import Route

class AssistantRoute:
    """
    Base class for all assistant routes.
    Each route should define its own utterances.
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def route(cls):
        return Route(
            name=cls.__name__,
            utterances=cls.utterances()
        )

    @classmethod
    def utterances(cls):
        return [
                "schedule a meeting",
                "what's on my calendar",
                "add an event",
                "what is left to do today"
            ]

    async def handle(self, text, **kwargs):
        raise NotImplementedError("Subclasses must implement this method.")