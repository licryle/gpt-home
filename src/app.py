import asyncio
import contextlib
import requests
import string
import traceback

from config import load_settings, logger
from audio import AudioAssistant
from display import LCDScreen
from router import AssistantRouter
import speech_recognition as sr


class AssistantApp:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent tasks
        self._state_task = None
        self._speaker = None
        self._router = None
        self._display = None
        self._isRunning = False

    def start(self):
        asyncio.run(self._run())

    def stop(self):
        self._isRunning = False

    async def _run(self):
        loop = asyncio.get_running_loop()
        main_task = asyncio.create_task(self._main())

        try:
            await main_task
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("KeyboardInterrupt received, stopping the assistant...")
            self.stop()
            main_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await main_task
        finally:
            # Cancel all pending tasks except current one
            pending = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task(loop)]
            for task in pending:
                task.cancel()
            for task in pending:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def _main(self):
        await self._initialize()  # Wait for the event to be set

        self._isRunning = True

        settings = load_settings()
        keyword = settings.get("keyword").lower()
        await self._speaker.speak(f"Hello, I'm ready to help you. Call me {keyword}.")

        while self._isRunning:
            await asyncio.sleep(1)
            
        await self._speaker.speak("Shutting down, goodbye!")
        self._clean()

    async def _initialize(self):
        logger.info("Initializing Display")
        self._display = LCDScreen()
        if self._display.is_available():
            logger.success("Display initialized successfully")
            self._limited_task(self._safe_task(self._display.updateLCD("Booting up")))
        else:
            logger.error("No Display found")

        logger.info(f"Initializing Audio")
        self._speaker = AudioAssistant()
        logger.success(f"Audio initialized successfully")
        await self._speaker.speak("Booting up")

        logger.info(f"Initializing Assistant Router, this may take a while...")
        try:
            self._router = AssistantRouter("all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to initialize Assistant Router, Shutting down")
            logger.debug(f"Failed to initialize Assistant Router, Shutting down: {e}")
            return
        logger.success("Assistant Router initialized successfully")

        await self._check_network()
        self._check_api_key()

        try:
            self._speaker.start_listening(self._on_heard_sentence)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            logger.debug(f"An error occurred: {traceback.format_exc()}")
            await self._speaker.speak(f"Couldn't start assistant. An error occurred: {e}")
        logger.success("Listening for commands")
    
    def _clean(self):
        self._speaker.stop_listening()
    
    def _on_heard_sentence(self, text):
        asyncio.run(self._process_text(text))

    async def _process_text(self, text):
        logger.debug(f"Heard sentence: {text}")
        # Load settings from settings.json
        settings = load_settings()
        keyword = settings.get("keyword").lower()
        
        # Check if keyword is in text and respond
        if text:
            clean_text = text.lower().translate(str.maketrans('', '', string.punctuation))
            if keyword in clean_text:
                enable_heard = settings.get("sayHeard", True) == True
                actual_text = clean_text.split(keyword, 1)[1].strip()
                if actual_text:
                    heard_message = f"Heard: \"{actual_text}\""
                    logger.success(heard_message)
                    stop_event_heard = asyncio.Event()
                    stop_event_response = asyncio.Event()

                    # Resolve the route for the actual text
                    logger.info(f"Resolving route for: {actual_text}")
                    route = self._router.resolveRoute(actual_text)

                    # Create a task for Routing query, don't await it yet
                    query_task = asyncio.create_task(self._limited_task(route.handle(actual_text)))

                    if enable_heard:
                        await asyncio.gather(
                            self._limited_task(self._safe_task(self._speaker.speak("I'm on it", stop_event_heard))),
                            self._limited_task(self._safe_task(self._display.updateLCD(heard_message, stop_event=stop_event_heard)))
                        )

                    try:
                        response_message = await query_task
                    except Exception as e:
                        logger.error(f"An error occurred while processing the command: {e}")
                        logger.debug(f"An error occurred while processing the command: {traceback.format_exc()}")
                        response_message = f"An error occurred in the {route.__class__.__name__} module"
                    
                    # speak and display answer
                    response_task_speak = asyncio.create_task(self._limited_task(self._safe_task(self._speaker.speak(response_message, stop_event_response))))
                    response_task_lcd = asyncio.create_task(self._limited_task(self._safe_task(self._display.updateLCD(response_message, stop_event=stop_event_response))))

                    logger.success(response_message)
                    await asyncio.gather(response_task_speak, response_task_lcd)
            else:
                return  # Skip to the next iteration

    
    async def _loop(self):
        try:
            # Load settings from settings.json
            settings = load_settings()
            keyword = settings.get("keyword").lower()
            logger.info(f"Listening for keyword {keyword}")

            # Start displaying 'Listening'
            stop_event = asyncio.Event()
            state_task = asyncio.create_task(self._display.display_state("Listening", stop_event))

            text = None
            try:
                text = await self._speaker.listen(state_task, stop_event)
            except OSError as e:
                logger.error("Microphone not initialized or not available. Sleeping 2 seconds.")
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Listening failed")
                logger.debug(f"Listening failed: {traceback.format_exc()}")
                return

            # Stop displaying 'Listening'
            stop_event.set()
            if state_task:
                state_task.cancel()
                try:
                    await state_task
                except asyncio.CancelledError:
                    pass

            # Check if keyword is in text and respond
            if text:
                clean_text = text.lower().translate(str.maketrans('', '', string.punctuation))
                if keyword in clean_text:
                    enable_heard = settings.get("sayHeard", True) == True
                    actual_text = clean_text.split(keyword, 1)[1].strip()
                    if actual_text:
                        heard_message = f"Heard: \"{actual_text}\""
                        logger.success(heard_message)
                        stop_event_heard = asyncio.Event()
                        stop_event_response = asyncio.Event()

                        # Resolve the route for the actual text
                        logger.info(f"Resolving route for: {actual_text}")
                        route = self._router.resolveRoute(actual_text)

                        # Create a task for Routing query, don't await it yet
                        query_task = asyncio.create_task(self._limited_task(route.handle(text)))

                        if enable_heard:
                            await asyncio.gather(
                                self._limited_task(self._safe_task(self._speaker.speak("I'm on it", stop_event_heard))),
                                self._limited_task(self._safe_task(self._display.updateLCD(heard_message, stop_event=stop_event_heard)))
                            )

                        response_message = await query_task
                        
                        # Calculate time to speak and display
                        response_task_speak = asyncio.create_task(self._limited_task(self._safe_task(self._speaker.speak(response_message, stop_event_response))))
                        response_task_lcd = asyncio.create_task(self._limited_task(self._safe_task(self._display.updateLCD(response_message, stop_event=stop_event_response))))

                        logger.success(response_message)
                        await asyncio.gather(response_task_speak, response_task_lcd)
                        
                else:
                    return  # Skip to the next iteration
            else:
                return  # Skip to the next iteration
        except sr.UnknownValueError: # TODO move as it's only related to listening
            pass
        except sr.RequestError as e:
            error_message = f"Could not request results; {e}"
            await self._handle_error(error_message, state_task)
        except Exception as e:
            error_message = f"Something Went Wrong: {e}"
            await self._handle_error(error_message, state_task)

    async def _limited_task(self, task):
        async with self._semaphore:
            return await task

    async def _safe_task(self, task):
        try:
            await task
        except Exception as e:
            logger.error(f"Task failed")
            logger.debug(f"Task failed: {e}")

    def _check_api_key(self):
        settings = load_settings()
        api_key = settings.get("litellm_api_key")

        logger.info(f"Initialize system with LiteLLM API Key: {api_key}")

        if not api_key and self._display._is_available():
            self._display.display_no_api_key()

    async def _check_network(self):
        stop_event_init = asyncio.Event()
        state_task = asyncio.create_task(self._display.display_state("Connecting", stop_event_init))

        while not AssistantApp._is_network_connected():
            await asyncio.sleep(10)
            message = "Network not connected. Retrying in 10 seconds..."
            logger.error(message)
            await self._speaker.speak(message)

        stop_event_init.set()  # Signal to stop the 'Connecting' display
        state_task.cancel()  # Cancel the display task

    async def _handle_error(self, message, state_task):
        if state_task: 
            state_task.cancel()
        logger.critical(f"An error occurred: {message}\n{traceback.format_exc()}")
        message = message[:500]
        stop_event = asyncio.Event()
        lcd_task = asyncio.create_task(self._display.updateLCD(message, stop_event=stop_event))
        speak_task = asyncio.create_task(self._speaker.speak(message, stop_event))
        await speak_task
        lcd_task.cancel()

    @staticmethod
    def _is_network_connected():
        try:
            response = requests.get("http://www.google.com", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

if __name__ == "__main__":
    logger.info("Starting Assistant App")
    AssistantApp().start()