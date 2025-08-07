from datetime import datetime, timedelta
import time
import os
import re
from text2digits import text2digits
from threading import Timer
from datetime import datetime, timedelta
import subprocess

from .base import AssistantRoute

class AlarmRoute(AssistantRoute):
    alarms = {}

    @classmethod
    def utterances(cls):
        return [
            "set an alarm",
            "wake me up",
            "remind me in"
        ]

    async def handle(self, text, **kwargs):
        converter = text2digits.Text2Digits()
        text = converter.convert(text)

        set_match = re.search(
            r'\b(?:set|create|schedule|wake\s+me\s+up)\s+(?:an\s+)?alarm\b.*?\b(?:for|in|at)\s*(\d{1,2}:\d{2}|\d+\s*(?:minutes?|mins?|hours?|hrs?))\b' +
            r'|\bwake\s+me\s+up\b.*?\b(?:in|at)\s*(\d{1,2}:\d{2}|\d+\s*(?:minutes?|mins?|hours?|hrs?))\b',
            text, 
            re.IGNORECASE
        )
        delete_match = re.search(
            r'\b(?:delete|remove|cancel)\s+(?:an\s+)?alarm\b.*?\b(?:called|named)\s*(\w+)', 
            text, 
            re.IGNORECASE
        )
        snooze_match = re.search(
            r'\b(?:snooze|delay|postpone)\s+(?:an\s+)?alarm\b.*?\b(?:for|by)\s*(\d+\s*(?:minutes?|mins?))\b', 
            text, 
            re.IGNORECASE
        )
        remind_match = re.search(
            r'\b(?:remind)\s+(?:me)\s+(?:to|in)\s*(\d+\s*(?:minutes?|mins?|hours?|hrs?))\s+to\s*(.+)', 
            text, 
            re.IGNORECASE
        )

        if set_match:
            # Check which group captured the time expression
            time_expression = set_match.group(1) or set_match.group(2)
            if time_expression is None:
                return "No time specified for the alarm."
            minute, hour, dom, month, dow = self.parse_time_expression(time_expression)
            command = "aplay /usr/share/sounds/alarm.wav"
            comment = "Alarm"
            return self.set_alarm(command, minute, hour, dom, month, dow, comment)
        elif delete_match:
            comment = delete_match.group(1)
            return self.delete_alarm(comment)
        elif snooze_match:
            snooze_time = snooze_match.group(1)
            snooze_minutes = int(re.search(r'\d+', snooze_time).group())
            comment = "Alarm"
            return self.snooze_alarm(comment, snooze_minutes)
        elif remind_match:
            time_expression = remind_match.group(1)
            reminder_text = remind_match.group(2)
            if time_expression is None:
                return "No time specified for the reminder."
            minute, hour, dom, month, dow = self.parse_time_expression(time_expression)
            command = f"""
bash -c 'source /env/bin/activate && python -c "import pyttsx3; 
engine = pyttsx3.init(); 
engine.setProperty(\\"rate\\", 145); 
engine.say(\\"Reminder: {reminder_text}\\"); 
engine.runAndWait()"'
            """
            comment = "Reminder"
            return self.set_reminder(command, minute, hour, dom, month, dow, comment)
        else:
            return "Invalid command."
        
            
    def set_alarm(self, command, minute, hour, day_of_month, month, day_of_week, comment):
        now = datetime.now()
        alarm_time = now.replace(minute=minute, hour=hour, day=day_of_month, month=month, second=0, microsecond=0)
        
        if alarm_time < now:
            alarm_time += timedelta(days=1)
        
        delay = (alarm_time - now).total_seconds()
        timer = Timer(delay, lambda: subprocess.Popen(command, shell=True))
        timer.start()
        AlarmRoute.alarms[comment] = timer
        return "Alarm set successfully."

    def delete_alarm(self, comment):
        if comment in AlarmRoute.alarms:
            AlarmRoute.alarms[comment].cancel()
            del AlarmRoute.alarms[comment]
            return "Alarm deleted successfully."
        else:
            return "No such alarm to delete."

    def snooze_alarm(self, comment, snooze_minutes):
        if comment in AlarmRoute.alarms:
            AlarmRoute.alarms[comment].cancel()
            del AlarmRoute.alarms[comment]
            
            now = datetime.now()
            snooze_time = now + timedelta(minutes=snooze_minutes)
            delay = (snooze_time - now).total_seconds()
            command = "aplay /usr/share/sounds/alarm.wav"
            timer = Timer(delay, lambda: subprocess.Popen(command, shell=True))
            timer.start()
            AlarmRoute.alarms[comment] = timer
            return "Alarm snoozed successfully."
        else:
            return "No such alarm to snooze."

    def parse_time_expression(self, time_expression):
        if re.match(r'\d+:\d+', time_expression):  # HH:MM format
            hour, minute = map(int, time_expression.split(':'))
            return minute, hour, '*', '*', '*'
        elif re.match(r'\d+\s*minutes?', time_expression):  # N minutes from now
            minutes = int(re.search(r'\d+', time_expression).group())
            now = datetime.now() + timedelta(minutes=minutes)
            return now.minute, now.hour, now.day, now.month, '*'
        else:
            raise ValueError("Invalid time expression")

    def set_reminder(self, command, minute, hour, day_of_month, month, day_of_week, comment):
        now = datetime.now()
        reminder_time = now.replace(minute=minute, hour=hour, day=day_of_month, month=month, second=0, microsecond=0)
        
        if reminder_time < now:
            reminder_time += timedelta(days=1)
        
        delay = (reminder_time - now).total_seconds()
        Timer(delay, lambda: subprocess.Popen(command, shell=True)).start()
        return "Reminder set successfully."