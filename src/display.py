import asyncio
import busio
import re
import struct
import subprocess
import textwrap
import traceback

from config import logger

try:
    from board import SCL, SDA
except ImportError  as e:
    logger.debug("Board not detected. Skipping... \n    Reason: {e}\n{traceback.format_exc()}")

try:
    import adafruit_ssd1306
except ImportError as e:
    logger.debug(f"Failed to import adafruit_ssd1306. Skipping...\n    Reason: {e}\n{traceback.format_exc()}")


class LCDScreen:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._display = self._initLCD()
    
    def is_available(self):
        return self._display is not None

    def _initLCD(self):
        try:
            # Create the I2C interface.
            i2c = busio.I2C(SCL, SDA)
            # Create the SSD1306 OLED class.
            # The first two parameters are the pixel width and pixel height. Change these
            # to the right size for your display
            display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
            # Alternatively, you can change the I2C address of the device with an addr parameter:
            # display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x31)
            # Set the display rotation to 180 degrees.
            display.rotation = 2
            # Clear the display. Always call show after changing pixels to make the display
            # update visible
            display.fill(0)
            # Display IP address
            ip_address = subprocess.check_output(["hostname", "-I"]).decode("utf-8").split(" ")[0]
            display.text(f"{ip_address}", 0, 0, 1)
            # Display CPU temperature in Celsius (e.g., 39°)
            cpu_temp = int(float(subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8").split("=")[1].split("'")[0]))
            temp_text_x = 100
            display.text(f"{cpu_temp}", temp_text_x, 0, 1)
            # degree symbol
            degree_x = 100 + len(f"{cpu_temp}") * 7 # Assuming each character is 7 pixels wide
            degree_y = 2
            LCDScreen.degree_symbol(display, degree_x, degree_y, 2, 1)
            c_x = degree_x + 7 # Assuming each character is 7 pixels wide
            display.text("C", c_x, 0, 1)
            # Show the updated display with the text.
            display.show()
            return display
        except Exception as e:
            logger.debug(f"Failed to initialize display, skipping...\n Reason: {e}\n{traceback.format_exc()}")
            return None


    async def updateLCD(self, text, stop_event=None):
        logger.info(f"Displaying text on LCD if present: {text}")

        if self._display is None:
            return  # Skip updating the display if it's not initialized
        
        delay = LCDScreen.calculate_delay(text)

        async with self._display_lock:
            if stop_event is None:
                stop_event = asyncio.Event()

            async def display_text(delay):
                i = 0
                while not (stop_event and stop_event.is_set()) and i < line_count:
                    if line_count > 2:
                        await display_lines(i, min(i + 2, line_count), delay)
                        i += 2
                    else:
                        await display_lines(0, line_count, delay)
                        break  # Exit the loop if less than or equal to 2 lines
                    await asyncio.sleep(0.02)  # Delay between pages

            async def display_lines(start, end, delay):
                self._display.fill_rect(0, 10, 128, 22, 0)
                # type out the text
                for i, line_index in enumerate(range(start, end)):
                    for j, char in enumerate(lines[line_index]):
                        if stop_event.is_set():
                            break
                        try:
                            self._display.text(char, j * 6, 10 + i * 10, 1)
                        except struct.error as e:
                            logger.error(f"Struct Error: {e}, skipping character {char}")
                            continue  # Skip the current character and continue with the next
                        self._display.show()
                        await asyncio.sleep(delay)

            # Clear the display
            self._display.fill(0)
            # Display IP address
            ip_address = subprocess.check_output(["hostname", "-I"]).decode("utf-8").split(" ")[0]
            self._display.text(f"{ip_address}", 0, 0, 1)
            # Display CPU temperature in Celsius (e.g., 39°)
            cpu_temp = int(float(subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8").split("=")[1].split("'")[0]))
            temp_text_x = 100
            self._display.text(f"{cpu_temp}", temp_text_x, 0, 1)
            # degree symbol
            degree_x = 100 + len(f"{cpu_temp}") * 7 # Assuming each character is 7 pixels wide
            degree_y = 2
            LCDScreen.degree_symbol(self._display, degree_x, degree_y, 2, 1)
            c_x = degree_x + 7 # Assuming each character is 7 pixels wide
            self._display.text("C", c_x, 0, 1)
            # Show the updated display with the text.
            self._display.show()
            # Line wrap the text
            lines = textwrap.fill(text, 21).split('\n')
            line_count = len(lines)
            display_task = asyncio.create_task(display_text(delay))



    async def display_state(self, state, stop_event):
        if self._display is None:
            return # Skip updating the display if it's not initialized
        async with self._display_lock:
            # if state 'Connecting', display the 'No Network' and CPU temperature
            if state == "Connecting":
                self._display.text("No Network", 0, 0, 1)
                # Display CPU temperature in Celsius (e.g., 39°)
                cpu_temp = int(float(subprocess.check_output(["vcgencmd", "measure_temp"]).decode("utf-8").split("=")[1].split("'")[0]))
                temp_text_x = 100
                self._display.text(f"{cpu_temp}", temp_text_x, 0, 1)
                # degree symbol
                degree_x = 100 + len(f"{cpu_temp}") * 7 # Assuming each character is 7 pixels wide
                degree_y = 2
                LCDScreen.degree_symbol(self._display, degree_x, degree_y, 2, 1)
                c_x = degree_x + 7 # Assuming each character is 7 pixels wide
                self._display.text("C", c_x, 0, 1)
                # Show the updated display with the text.
                self._display.show()
            while not stop_event.is_set():
                for i in range(4):
                    if stop_event.is_set():
                        break
                    self._display.fill_rect(0, 10, 128, 22, 0)
                    self._display.text(f"{state}" + '.' * i, 0, 20, 1)
                    self._display.show()
                    await asyncio.sleep(0.5)
    
    def display_no_api_key(self):
        self._display.fill(0)
        ip_address = subprocess.check_output(["hostname", "-I"]).decode("utf-8").split(" ")[0].strip()
        self._display.text("Missing API Key", 0, 0, 1)
        self._display.text("To update it, visit:", 0, 10, 1)
        if ip_address:
            self._display.text(f"{ip_address}/settings", 0, 20, 1)
        else:
            self._display.text("gpt-home.local/settings", 0, 20, 1)
        self._display.show()

    @staticmethod
    def calculate_delay(message):
        base_delay = 0.02
        extra_delay = 0.0
        
        # Patterns to look for
        patterns = [r": ", r"\. ", r"\? ", r"! ", r"\.{2,}", r", ", r"\n"]
        
        for pattern in patterns:
            extra_delay += (len(re.findall(pattern, message)) * 0.001)  # Add 0.001 seconds for each match

        return base_delay + extra_delay

    # Manually draw a degree symbol °
    @staticmethod
    def degree_symbol(display, x, y, radius, color):
        for i in range(x-radius, x+radius+1):
            for j in range(y-radius, y+radius+1):
                if (i-x)**2 + (j-y)**2 <= radius**2:
                    display.pixel(i, j, color)
                    # clear center of circle
                    if (i-x)**2 + (j-y)**2 <= (radius-1)**2:
                        display.pixel(i, j, 0)