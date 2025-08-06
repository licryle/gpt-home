import caldav
from caldav.elements import dav, cdav
from datetime import datetime, timedelta
import os
import re

from .base import AssistantRoute

class CalendarRoute(AssistantRoute):
    @classmethod
    def utterances(self):
        return [
            "schedule a meeting",
            "what's on my calendar",
            "add an event",
            "what is left to do today"
        ]

    async def handle(self, text, **kwargs):
        url = os.getenv('CALDAV_URL')
        username = os.getenv('CALDAV_USERNAME')
        password = os.getenv('CALDAV_PASSWORD')

        if not url or not username or not password:
            return "CalDAV server credentials are not properly set in environment variables."

        try:
            client = caldav.DAVClient(url, username=username, password=password)
            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                return "No calendars found."

            calendar = calendars[0]  # Use the first found calendar

            task_create_match = re.search(r'\b(?:add|create)\s+a?\s+task\s+called\s+(.+)', text, re.IGNORECASE)
            task_delete_match = re.search(r'\b(?:delete|remove)\s+(a )?task\s+called\s+(\w+)', text, re.IGNORECASE)
            task_update_match = re.search(r'\b(?:update|change|modify)\s+(a )?task\s+called\s+(\w+)\s+to\s+(\w+)', text, re.IGNORECASE)
            tasks_query_match = re.search(r'\b(left|to do|to-do|what else)\b', text, re.IGNORECASE)
            completed_tasks_query_match = re.search(r'\bcompleted\s+tasks\b', text, re.IGNORECASE)

            if task_create_match:
                task_name = task_create_match.group(1).strip()
                task = calendar.add_todo(f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VTODO
SUMMARY:{task_name}
STATUS:NEEDS-ACTION
END:VTODO
END:VCALENDAR
""")
                return f"Task '{task_name}' created successfully."

            elif task_update_match:
                task_name = task_update_match.group(2)
                new_task_name = task_update_match.group(3)
                tasks = calendar.todos()
                for task in tasks:
                    if task_name.lower() in task.instance.vtodo.summary.value.lower():
                        task.instance.vtodo.summary.value = new_task_name
                        task.save()
                        return f"Task '{task_name}' updated to '{new_task_name}' successfully."

            elif task_delete_match:
                task_name = task_delete_match.group(1)
                tasks = calendar.todos()
                for task in tasks:
                    if task_name.lower() in task.instance.vtodo.summary.value.lower():
                        task.delete()
                        return f"Task '{task_name}' deleted successfully."

            if tasks_query_match:
                tasks = calendar.todos()
                pending_task_details = []
                for task in tasks:
                    if task.vobject_instance.vtodo.status.value != "COMPLETED":
                        summary = task.vobject_instance.vtodo.summary.value
                        status = task.vobject_instance.vtodo.status.value
                        pending_task_details.append(f"'{summary}' (Status: {status})")
                if pending_task_details:
                    return "Your pending tasks are: " + ", ".join(pending_task_details)
                else:
                    return "You have no pending tasks."

            elif completed_tasks_query_match:
                tasks = calendar.todos()
                completed_task_details = []
                for task in tasks:
                    if task.vobject_instance.vtodo.status.value == "COMPLETED":
                        summary = task.vobject_instance.vtodo.summary.value
                        completed_task_details.append(f"'{summary}'")
                if completed_task_details:
                    return "Your completed tasks are: " + ", ".join(completed_task_details)
                else:
                    return "You have no completed tasks."

            create_match = re.search(r'\b(?:add|create|schedule)\s+an?\s+(event|appointment)\s+called\s+(\w+)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})', text, re.IGNORECASE)
            update_match = re.search(r'\b(?:update|change|modify)\s+the\s+(event|appointment)\s+called\s+(\w+)\s+to\s+(\w+)\s+on\s+(\d{4}-\d{2}-\d{2})\s+at\s+(\d{1,2}:\d{2})', text, re.IGNORECASE)
            delete_match = re.search(r'\b(?:delete|remove|cancel)\s+the\s+(event|appointment)\s+called\s+(\w+)', text, re.IGNORECASE)
            next_event_match = re.search(r"\bwhat'? ?i?s\s+my\s+next\s+(event|appointment)\b", text, re.IGNORECASE)
            calendar_query_match = re.search(r"\bwhat'? ?i?s\s+on\s+my\s+calendar\b", text, re.IGNORECASE)

            if create_match:
                event_name = create_match.group(1)
                event_time = datetime.strptime(f"{create_match.group(2)} {create_match.group(3)}", "%Y-%m-%d %H:%M")
                event_start = event_time.strftime("%Y%m%dT%H%M%S")
                event_end = (event_time + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")  # Assuming 1 hour duration

                event = calendar.add_event(f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:{event_name}
DTSTART:{event_start}
DTEND:{event_end}
END:VEVENT
END:VCALENDAR
""")
                return f"Event '{event_name}' created successfully."

            elif update_match:
                event_name = update_match.group(2)
                new_event_name = update_match.group(3)
                event_time = datetime.strptime(f"{update_match.group(4)} {update_match.group(5)}", "%Y-%m-%d %H:%M")
                event_start = event_time.strftime("%Y%m%dT%H%M%S")
                event_end = (event_time + timedelta(hours=1)).strftime("%Y%m%dT%H%M%S")  # Assuming 1 hour duration

                events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=365), event=True, expand=True)  # Search within the next year
                for event in events:
                    if event_name.lower() in event.instance.vevent.summary.value.lower():
                        event.instance.vevent.summary.value = new_event_name
                        event.instance.vevent.dtstart.value = event_start
                        event.instance.vevent.dtend.value = event_end
                        event.save()
                        return f"Event '{event_name}' updated to '{new_event_name}' successfully."

            elif delete_match:
                event_name = delete_match.group(1)
                events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=365), event=True, expand=True)  # Search within the next year
                for event in events:
                    if event_name.lower() in event.instance.vevent.summary.value.lower():
                        event.delete()
                        return f"Event '{event_name}' deleted successfully."

            elif next_event_match:
                events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=30), event=True, expand=True)  # Next 30 days
                if events:
                    next_event = events[0]
                    summary = next_event.vobject_instance.vevent.summary.value
                    start_time = next_event.vobject_instance.vevent.dtstart.value
                    return f"Your next event is '{summary}' on {start_time.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' ')}"
                else:
                    return "No upcoming events found."

            elif calendar_query_match:
                events = calendar.search(start=datetime.now(), end=datetime.now() + timedelta(days=30), event=True, expand=True)  # Next 30 days
                if events:
                    event_details = []
                    for event in events:
                        summary = event.vobject_instance.vevent.summary.value
                        start_time = event.vobject_instance.vevent.dtstart.value
                        formatted_start_time = start_time.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' ')
                        event_details.append(f"'{summary}' on {formatted_start_time}")
                    return "Your upcoming events are: " + ", ".join(event_details)
                else:
                    return "No events on your calendar for the next 30 days."
        except caldav.lib.error.AuthorizationError:
            return "Authorization failure: Please check your username and password."
        except caldav.lib.error.NotFoundError:
            return "Resource not found: Check the specified CalDAV URL."
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

        return "No valid CalDAV command found."