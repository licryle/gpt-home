import aiohttp
from datetime import datetime, timedelta
import os
import re
import traceback

from weather_codes import weather_codes
from common import logger, load_settings

from .base import AssistantRoute
from .general import GeneralRoute

class WeatherRoute(AssistantRoute):

    @classmethod
    def utterances(cls):
        return [
            "how's the weather today?",
            "tell me the weather",
            "what is the temperature",
            "is it going to rain",
            "what is the weather like in New York"
        ]

    async def handle(self, text, **kwargs):
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            api_key = os.getenv('OPEN_WEATHER_API_KEY')
            settings = load_settings()
            async with aiohttp.ClientSession() as session:
                if re.search(r'(weather|temperature).*\sin\s', text, re.IGNORECASE):
                    city_match = re.search(r'in\s([\w\s]+)', text, re.IGNORECASE)
                    if city_match:
                        city = city_match.group(1).strip()

                    # Current weather
                    if not re.search(r'(forecast|future)', text, re.IGNORECASE):
                        coords = await self.coords_from_city(city, api_key)
                        if coords is None:
                            return f"No weather data available for {city}. Please check the city name and try again."
                        
                        if api_key:
                            response = await session.get(f"https://api.openweathermap.org/data/3.0/onecall?lat={coords.get('lat')}&lon={coords.get('lon')}&appid={api_key}&units=metric")
                            if response.status == 200:
                                json_response = await response.json()
                                logger.debug(f"Weather response: {json_response}")
                                weather = json_response.get('current').get('weather')[0].get('main')
                                temp = json_response.get('current').get('temp')
                                combined_response = f"It is currently {round(float(temp))} degrees and {weather.lower()} in {city}."
                                return await GeneralRoute().handle(
                                    text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                                    User's question: {text}\n\nCurrent time: {current_time}\n
                                    Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {json_response.get('current')}"""
                                )
                        
                        # Fallback to Open-Meteo
                        response = await session.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords.get('lat')}&longitude={coords.get('lon')}&current_weather=true&temperature_unit=celsius")
                        if response.status == 200:
                            json_response = await response.json()
                            weather_code = json_response.get('current_weather').get('weathercode')
                            temp = json_response.get('current_weather').get('temperature')
                            weather_description = weather_codes[str(weather_code)]['day']['description'] if datetime.now().hour < 18 else weather_codes[str(weather_code)]['night']['description']
                            combined_response = f"It is currently {round(float(temp))} degrees and {weather_description.lower()} in {city}."
                            return await GeneralRoute().handle(
                                    text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                                    User's question: {text}\n\nCurrent time: {current_time}\n
                                    Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {weather_description}"""
                            )

                    # Weather forecast
                    else:
                        coords = await self.coords_from_city(city, api_key)
                        tomorrow = datetime.now() + timedelta(days=1)
                        if coords is None:
                            return f"No weather data available for {city}. Please check the city name and try again."
                        
                        if api_key:
                            response = await session.get(f"https://api.openweathermap.org/data/3.0/onecall?lat={coords.get('lat')}&lon={coords.get('lon')}&appid={api_key}&units=imperial")
                            if response.status == 200:
                                json_response = await response.json()
                                # next few days
                                forecast = []
                                for day in json_response.get('daily'):
                                    forecast.append({
                                        'weather': day.get('weather')[0].get('main'),
                                        'temp': day.get('temp').get('day'),
                                        'date': datetime.fromtimestamp(day.get('dt')).strftime('%A')
                                    })
                                # tomorrow
                                tomorrow_forecast = list(filter(lambda x: x.get('date') == tomorrow.strftime('%A'), forecast))[0]
                                speech_responses = []
                                speech_responses.append(f"Tomorrow, it will be {tomorrow_forecast.get('temp')}\u00B0F and {tomorrow_forecast.get('weather')} in {city}.")
                                for day in forecast:
                                    if day.get('date') != tomorrow.strftime('%A'):
                                        speech_responses.append(f"On {day.get('date')}, it will be {round(float(day.get('temp')))} degrees and {day.get('weather').lower()} in {city}.")
                                combined_response = ' '.join(speech_responses)
                                return await GeneralRoute().handle(
                                    text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                                    User's question: {text}\n\nCurrent time: {current_time}\n
                                    Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {json_response.get('current')}"""
                                )
                        
                        # Fallback to Open-Meteo
                        response = await session.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords.get('lat')}&longitude={coords.get('lon')}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit")
                        if response.status == 200:
                            json_response = await response.json()
                            forecast = []
                            for day in json_response.get('daily'):
                                day_weather_code = day.get('weathercode')
                                day_weather_description = weather_codes[str(day_weather_code)]['day']['description'] if datetime.now().hour < 18 else weather_codes[str(day_weather_code)]['night']['description']
                                forecast.append({
                                    'temp_max': day.get('temperature_2m_max'),
                                    'temp_min': day.get('temperature_2m_min'),
                                    'weather_description': day_weather_description,
                                    'date': day.get('time')
                                })
                            tomorrow_forecast = list(filter(lambda x: x.get('date') == tomorrow.strftime('%Y-%m-%d'), forecast))[0]
                            speech_responses = []
                            speech_responses.append(f"Tomorrow, it will be between {tomorrow_forecast.get('temp_min')}\u00B0F and {tomorrow_forecast.get('temp_max')}\u00B0F and {tomorrow_forecast.get('weather_description').lower()} in {city}.")
                            for day in forecast:
                                if day.get('date') != tomorrow.strftime('%Y-%m-%d'):
                                    speech_responses.append(f"On {day.get('date')}, it will be between {day.get('temp_min')}\u00B0F and {day.get('temp_max')}\u00B0F and {day.get('weather_description').lower()} in {city}.")
                            combined_response = ' '.join(speech_responses)
                            return await GeneralRoute().handle(
                                    text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                                    User's question: {text}\n\nCurrent time: {current_time}\n
                                    Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {[day for day in forecast if day.get('weather_description')]}"""
                            )

                else:
                    # General weather based on environment variable zip code or IP address location
                    zip_code = settings.get('default_zip_code')
                    if zip_code:
                        city = await self.city_from_zip(zip_code)
                    else:
                        city = await self.city_from_ip()

                    coords = await self.coords_from_city(city, api_key)
                    if city is None:
                        return f"Could not determine your city based on your IP address. Please provide a city name."
                    if coords is None:
                        return f"No weather data available for {city}."
                    
                    if api_key:
                        response = await session.get(f"http://api.openweathermap.org/data/3.0/onecall?lat={coords.get('lat')}&lon={coords.get('lon')}&appid={api_key}&units=imperial")
                        if response.status == 200:
                            json_response = await response.json()
                            logger.debug(f"Weather response: {json_response}")
                            weather = json_response.get('current').get('weather')[0].get('main')
                            temp = json_response.get('current').get('temp')
                            combined_response = f"It is currently {round(float(temp))} degrees and {weather.lower()} in your location."
                            return await GeneralRoute().handle(
                                text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                                User's question: {text}\n\nCurrent time: {current_time}\n
                                Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {json_response.get('current')}"""
                            )
                    
                    # Fallback to Open-Meteo
                    response = await session.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords.get('lat')}&longitude={coords.get('lon')}&current_weather=true&temperature_unit=fahrenheit")
                    if response.status == 200:
                        json_response = await response.json()
                        weather_code = json_response.get('current_weather').get('weathercode')
                        temp = json_response.get('current_weather').get('temperature')
                        weather_description = weather_codes[str(weather_code)]['day']['description'] if datetime.now().hour < 18 else weather_codes[str(weather_code)]['night']['description']
                        combined_response = f"It is currently {round(float(temp))} degrees and {weather_description.lower()} in {city}."
                        return await GeneralRoute().handle(
                            text=f"""Provide a concise response to the user's question based on the weather data.  Do not summarize or respond to anything other than the question\n
                            User's question: {text}\n\nCurrent time: {current_time}\n
                            Response: {combined_response}\n\nIf the response is consistent with what the question is asking, return it. Otherwise, use the following weather data to answer the question: {weather_description}"""
                        )
            raise Exception("No Open Weather API key found. Please enter your API key for Open Weather in the web interface or try reconnecting the service.")

        except Exception as e:
            if '404' in str(e):
                return f"Weather information for {city} is not available."
            else:
                logger.error(f"Error: {traceback.format_exc()}")
                return f"Something went wrong. {e}"

    async def coords_from_city(self, city, api_key=None):
        async with aiohttp.ClientSession() as session:
            if api_key:
                response = await session.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={api_key}")
                if response.status == 200:
                    json_response = await response.json()
                    if len(json_response) > 0:
                        coords = {
                            "lat": json_response[0].get('lat'),
                            "lon": json_response[0].get('lon')
                        }
                    else:
                        return None
                    return coords
            
            # Fallback to Open-Meteo if no API key or OpenWeather fails
            response = await session.get(f"https://nominatim.openstreetmap.org/search?q={city}&format=json")
            if response.status == 200:
                json_response = await response.json()
                if len(json_response) > 0:
                    coords = {
                        "lat": float(json_response[0].get('lat')),
                        "lon": float(json_response[0].get('lon'))
                    }
                else:
                    return None
                return coords
        
    async def city_from_zip(self, zip_code: str, country_code: str = "us"):
        api_key = os.getenv('OPEN_WEATHER_API_KEY')
        if not api_key:
            logger.error("No API key provided for OpenWeatherMap.")
            return None

        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(
                    f"http://api.openweathermap.org/geo/1.0/zip?zip={zip_code},{country_code}&appid={api_key}"
                )
                if response.status == 200:
                    json_response = await response.json()
                    city = json_response.get('name')
                    return city
                else:
                    logger.error(f"Failed to retrieve city from zip code. Status: {response.status}")
            except Exception as e:
                logger.error(f"Error retrieving city from zip code: {traceback.format_exc()}")
        return None

    async def city_from_ip(self):
        async with aiohttp.ClientSession() as session:
            response = await session.get(f"https://ipinfo.io/json")
            if response.status == 200:
                json_response = await response.json()
                city = json_response.get('city')
                return city
        return None