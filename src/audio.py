import asyncio
import pyttsx3
import speech_recognition as sr
from concurrent.futures import ThreadPoolExecutor

# TTS
from gtts import gTTS
from io import BytesIO
from pygame import mixer

from config import load_settings, logger


class AudioAssistant:
    def __init__(self):
        self.speech_engine = pyttsx3.init()
        self.speech_engine.setProperty('rate', 150)  # Set speech rate
        self.speech_engine.setProperty('volume', 1)  # Set volume level (0.0 to 1.0)
        self.speech_engine.setProperty('alsa_device', 'hw:Headphones,0')
        self._listening_task = None
        self._listening_callback = None

        self.speak_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor()

        # Initialize the speech recognition engine
        self.speech_recognition = sr.Recognizer()
        self.speech_recognition.energy_threshold = 4000  # tweak depending on mic
        self.speech_recognition.dynamic_energy_threshold = True
        self.speech_recognition.pause_threshold = 0.5  # Adjust pause threshold for better recognition
        self.speech_recognition.non_speaking_duration = 0.5  # Adjust non-speaking duration for better recognition
        self.loop = asyncio.get_event_loop()
    
    def _recognize_audio(self, recognizer, audio):
        text = None

        try:
            logger.debug(f"Audio captured, processing... {audio}")
            text = self.speech_recognition.recognize_google(audio)
            logger.debug(f"Audio to text: {text}")
        except sr.UnknownValueError:
            logger.info("Could not understand audio, waiting for a new phrase...")
        except Exception as e:
            logger.info("The audio to text server couldn't be contacted")
            logger.debug(f"The audio to text server couldn't be contacted: {e}")
            text = "The audio to text server couldn't be contacted"

        if text is not None:
            self._listening_callback(text)

    def start_listening(self, callback):
        self._listening_callback = callback
        logger.debug("start_listening")

        if (self._listening_task is None):
            with sr.Microphone() as source:
                logger.debug("adjust ambient noise")
                self.speech_recognition.adjust_for_ambient_noise(source, duration=1)

            logger.debug("start background listening")
            self._listening_task = self.speech_recognition.listen_in_background(sr.Microphone(), self._recognize_audio)
    
    def stop_listening(self):
        if (self._listening_task is not None):
            self._listening_task(wait_for_stop=False)
            self._listening_task = None

    async def speak(self, text, stop_event=asyncio.Event()):
        settings = load_settings()
        speech_engine = settings.get("speechEngine", "pyttsx3")

        try:
            async with self.speak_lock:
                def _speak():
                    if speech_engine == 'gtts':
                        mp3_fp = BytesIO()
                        tts = gTTS(text, lang='en')
                        tts.write_to_fp(mp3_fp)
                        mixer.init()
                        mp3_fp.seek(0)
                        mixer.music.load(mp3_fp, "mp3")
                        mixer.music.play()
                    else:
                        self.speech_engine.say(text)
                        self.speech_engine.runAndWait()

                await self.loop.run_in_executor(self.executor, _speak)
                stop_event.set()
        except Exception as e:
            logger.error(f"Couldn't TTS: {e}")
            logger.debug(f"Couldn't TTS: {traceback.format_exc()}")