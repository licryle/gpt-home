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

        self.speak_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor()

        # Initialize the speech recognition engine
        self.speech_recognition = sr.Recognizer()
        self.loop = asyncio.get_event_loop()
    
    def recognize_audio(self, loop, state_task, stop_event):
        try:
            with sr.Microphone() as source:
                if source.stream is None:
                    logger.debug("Microphone not initialized.")
                    raise OSError("Microphone not initialized.")
                
                listening = False  # Initialize variable for feedback
                
                try:
                    audio = self.speech_recognition.listen(source, timeout=2, phrase_time_limit=15)
                    logger.debug(f"Audio captured, processing... {audio}")
                    text = self.speech_recognition.recognize_google(audio)
                    logger.debug(f"Audio to text: {text}")
                    
                    if text:  # If text is found, break the loop
                        state_task.cancel()
                        return text
                        
                except sr.WaitTimeoutError:
                    if listening:
                        logger.info("Still listening but timed out, waiting for phrase...")
                    else:
                        logger.info("Timed out, waiting for phrase to start...")
                        listening = True
                        
                except sr.UnknownValueError:
                    logger.info("Could not understand audio, waiting for a new phrase...")
                    listening = False
                        
        except sr.WaitTimeoutError:
            if source and source.stream:
                source.stream.close()
            raise asyncio.TimeoutError("Listening timed out.")
        except OSError as e:
            logger.debug(f"Microphone not available: {e}")
            raise OSError("Microphone not available.")

    async def listen(self, state_task, stop_event):
        text = await self.loop.run_in_executor(self.executor, self.recognize_audio, self.loop, state_task, stop_event)
        return text

    async def speak(self, text, stop_event=asyncio.Event()):
        settings = load_settings()
        speech_engine = settings.get("speechEngine", "pyttsx3")

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