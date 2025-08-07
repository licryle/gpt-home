import aiohttp
import os
import subprocess
import traceback

from config import logger

from .base import AssistantRoute

class SpotifyRoute(AssistantRoute):

    @classmethod
    def utterances(cls):
        return [
            "play some music",
            "next song",
            "pause the music",
            "play earth wind and fire on Spotify",
            "play my playlist"
        ]

    async def handle(self, text, **kwargs):
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        if client_id and client_secret:
            try:
                async with aiohttp.ClientSession() as session:
                    ip = subprocess.run(["hostname", "-I"], capture_output=True).stdout.decode().split()[0]
                    response = await session.post(f"http://{ip}/spotify-control", json={"text": text})
                    if response.status == 200:
                        data = await response.json()
                        return data.get("message")
                    else:
                        content_text = await response.text()
                        logger.warning(content_text)
                        return f"Received a {response.status} status code. {content_text}"
            except Exception as e:
                logger.error(f"Error: {traceback.format_exc()}")
                raise Exception(f"Something went wrong: {e}")
        raise Exception("No client id or client secret found. Please provide the necessary credentials for Spotify in the web interface.")