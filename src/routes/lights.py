from phue import Bridge
import os
import re
import traceback

from common import logger

from .base import AssistantRoute

class LightsRoute(AssistantRoute):

    @classmethod
    def utterances(cls):
        return [
            "turn on the lights",
            "switch off the lights",
            "dim the lights",
            "change the color of the lights",
            "set the lights to red"
        ]

    async def handle(self, text, **kwargs):
        bridge_ip = os.getenv('PHILIPS_HUE_BRIDGE_IP')
        username = os.getenv('PHILIPS_HUE_USERNAME')
        
        if bridge_ip and username:
            try:
                b = Bridge(bridge_ip, username)
                b.connect()

                # Turn on or off all lights
                on_off_pattern = r'(\b(turn|shut|cut|put)\s)?.*(on|off)\b'
                match = re.search(on_off_pattern, text, re.IGNORECASE)
                if match:
                    if 'on' in match.group(0):
                        b.set_group(0, 'on', True)
                        return "Turning on all lights."
                    else:
                        b.set_group(0, 'on', False)
                        return "Turning off all lights."

                # Change light color
                color_pattern = r'\b(red|green|blue|yellow|purple|orange|pink|white|black)\b'
                match = re.search(color_pattern, text, re.IGNORECASE)
                if match:
                    # convert color to hue value
                    color = {
                        'red': 0,
                        'green': 25500,
                        'blue': 46920,
                        'yellow': 12750,
                        'purple': 56100,
                        'orange': 6000,
                        'pink': 56100,  # Closest to purple for hue
                        'white': 15330,  # Closest to a neutral white
                    }.get(match.group(1).lower())
                    b.set_group(0, 'on', True)
                    b.set_group(0, 'hue', color)
                    return f"Changing lights {match.group(1)}."

                # Change light brightness
                brightness_pattern = r'(\b(dim|brighten)\b)?.*?\s.*?to\s(\d{1,3})\b'
                match = re.search(brightness_pattern, text, re.IGNORECASE)
                if match:
                    brightness = int(match.group(3))
                    b.set_group(0, 'on', True)
                    b.set_group(0, 'bri', brightness)
                    return f"Setting brightness to {brightness}."

                raise Exception("I'm sorry, I don't know how to handle that request.")
            except Exception as e:
                logger.error(f"Error: {traceback.format_exc()}")
                return f"Something went wrong: {e}"
        
        raise Exception("No philips hue bridge IP found. Please enter your bridge IP for Phillips Hue in the web interface or try reconnecting the service.")