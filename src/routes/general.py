
import asyncio
import litellm
from litellm import completion, check_valid_key
import traceback

from common import logger, load_settings

from .base import AssistantRoute

class GeneralRoute(AssistantRoute):

    @classmethod
    def utterances(cls):
        return [
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

    async def handle(self, text, **kwargs):
        # Load settings from settings.json
        settings = load_settings()
        max_tokens = settings.get("max_tokens")
        temperature = settings.get("temperature")
        model = settings.get("model")
        retries = 3

        for i in range(retries):
            try:
                response = completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": f"You are a helpful assistant. {settings.get('custom_instructions')}"},
                        {"role": "user", "content": f"Human: {text}\nAI:"}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                response_content = response.choices[0].message.content.strip()
                if response_content:  # Check if the response is not empty
                    return response_content
                else:
                    logger.warning(f"Retry {i+1}: Received empty response from LLM.")
            except litellm.exceptions.BadRequestError as e:
                logger.error(traceback.format_exc())
                return f"The API key you provided for `{model}` is not valid. Double check the API key corresponds to the model/provider you are trying to call."
            except Exception as e:
                logger.error(f"Error on try {i+1}")
                logger.debug(f"Error on try {i+1}: {e}")
                if i == retries - 1:  # If this was the last retry
                    return f"Something went wrong after {retries} retries. Please try again."
            await asyncio.sleep(0.5)  # Wait before retrying