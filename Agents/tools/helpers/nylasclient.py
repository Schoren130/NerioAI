import requests
import json
from datetime import datetime, timezone

# nero

nylas_calendar_grant = "988eae66-6033-488b-a7d4-6a8c9b48a2ad"
nylas_email_grant = "08f76fe9-1d3e-4e37-bacb-ca82137ac4f2"

calendar_ids = [
    "AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AvKghTot1vkK3M6ve0ED0RQAAAAB64AAA"
]
user_email = "nero@mbenediktf.de"
user_name = "Nerio"
nylas_country = "eu"


# Benedikt

"""nylas_calendar_grant = "d1e7cc44-2a85-4343-9090-e68fda1ca811"
nylas_email_grant = "bca58880-1df8-4287-8ec5-bef2d699f25c"

calendar_ids = [
    "10d6d6be-145f-4372-82d0-a8ef00c559c6"
]
user_email = "dev@mbenediktf.de"
user_name = "Nerio"
nylas_country = "eu"
"""
base_url = f"https://api.{nylas_country}.nylas.com/v3"
url_availability = f"{base_url}/calendars/availability"
url_get_calendars = f"{base_url}/grants/{nylas_calendar_grant}/calendars"
url_get_events = f"{base_url}/grants/{nylas_calendar_grant}/events"
url_create_event = url_get_events
url_get_email = f"{base_url}/grants/{nylas_email_grant}/messages"
url_send_email = f"{base_url}/grants/{nylas_email_grant}/messages/send"


class NylasClient:
    def __init__(self, token):
        self.headers = {
            'Accept': 'application/json, application/gzip',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

    def send_request(self, method, url, payload={}):
        response = requests.request(
            method, url, headers=self.headers, data=payload)
        return response.status_code, response.json()

    def get_availability(
            self,
            start_time,
            end_time,
            interval_minutes=30,
            duration_minutes=30,
            round_to=15):
        # TODO: Implement availability checking
        payload = json.dumps({
            "participants": [
                {
                    "email": user_email,
                    "calendar_ids": calendar_ids
                }
            ],
            "start_time": start_time,
            "end_time": end_time,
            "interval_minutes": interval_minutes,
            "duration_minutes": duration_minutes,
            "round_to": round_to
        })
        status, response = self.send_request("POST", url_availability, payload)
        if status != 200:
            print(f"HTTP Error: {status}")
            return False
        print(response)
        return False

    def get_calendar_list(self):
        status, response = self.send_request("GET", url_get_calendars)
        if status != 200:
            print(f"HTTP Error: {status}")
            return False
        print(response)
        return False

    def get_email(
            self,
            index=0,
            from_filter=None,
            received_after_filter=None,
            unread_filter=None,
            subject_filter=None):
        url = f"{url_get_email}?limit={index+1}"
        if from_filter:
            url += f"&from={from_filter}"
        if received_after_filter:
            url += f"&received_after={received_after_filter}"
        if unread_filter:
            url += "&unread=true"
        if subject_filter:
            url += f"&subject={subject_filter}"
        status, response = self.send_request("GET", url)
        if status != 200:
            print(f"HTTP Error: {status}\n{response}")
            return f"Error fetching email: {response}"
        raw_email = response.get('data', [])
        try:
            return raw_email[index]['snippet'], raw_email[index]['id'], raw_email[index]["from"][0]["email"], raw_email[index]["subject"]
        except IndexError:
            return "Keine Emails gefunden."

    def send_email(self, to_address, subject, body, reply_to=None):
        payload = json.dumps({
            "subject": subject,
            "body": body,
            "to": [
                {
                    "email": to_address
                }
            ],
            "from": [
                {
                    "name": user_name,
                    "email": user_email
                }
            ],
            "reply_to_message_id": reply_to
        })
        status, response = self.send_request("POST", url_send_email, payload)
        if status != 200:
            print(f"HTTP Error: {status}\n{response}")
            return False
        return True

    def mark_email_as_read(self):
        # TODO: Implement marking email as read functionality
        return False

    def flag_email(self):
        # TODO: Implement flagging email functionality
        return False

    def get_events(
            self,
            calendar_ids,
            start_time=None,
            end_time=None,
            request_limit=5):
        
        utc_string_start = start_time
        dt_start = datetime.strptime(utc_string_start, "%Y-%m-%dT%H:%M:%SZ")
        dt_start = dt_start.replace(tzinfo=timezone.utc)  # UTC-Zeitzone hinzufügen
        startstamp = int(dt_start.timestamp())

        utc_string_end = end_time
        dt_end = datetime.strptime(utc_string_end, "%Y-%m-%dT%H:%M:%SZ")
        dt_end = dt_end.replace(tzinfo=timezone.utc)  # UTC-Zeitzone hinzufügen
        endstamp = int(dt_end.timestamp())

        print("Startzeit_get:", startstamp)
        print("Endzeit_get:", endstamp)

        start_time = startstamp
        end_time = endstamp

        events = []
        for calendar_id in calendar_ids:
            url = f"{url_get_events}?calendar_id={calendar_id}"
            url += f"&limit={request_limit}"
            if start_time and end_time:
                url += f"&start={start_time}&end={end_time}"
            status, response = self.send_request("GET", url)
            if status != 200:
                print(f"HTTP Error: {status}\n{response}")
                continue
            raw_events = response.get('data', [])
            for raw_event in raw_events:
                event = {
                    "title": raw_event['title'],
                    "location": raw_event.get('location', 'N/A'),
                    "description": raw_event.get('description', 'N/A'),
                    "time_format": raw_event['when']['object'],
                }
                if event["time_format"] == "timespan":
                    event['start'] = raw_event['when']['start_time']
                    event['end'] = raw_event['when']['end_time']
                    event['time_format'] = "timespan"
                elif event["time_format"] == "datespan":
                    event['start'] = raw_event['when']['start_date']
                    event['end'] = raw_event['when']['end_date']
                    event['time_format'] = "datespan"
                elif event["time_format"] == "date":
                    event['start'] = raw_event['when']['date']
                    event['end'] = raw_event['when']['date']
                    event['time_format'] = "date"
                else:
                    print(f"Unknown time format: {event['time_format']}")
                    continue

                start_utc = datetime.fromtimestamp(event['start'], tz=timezone.utc)
                event['start'] = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

                end_utc = datetime.fromtimestamp(event['end'], tz=timezone.utc)
                event['end'] = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

                events.append(event)
        print("Kalendereinträge gelesen")
        print(events)
        return events

    def create_event(
            self,
            calendar_id,
            title, start_time,
            end_time,
            location="",
            description=""):
        
        utc_string_start = start_time
        dt_start = datetime.strptime(utc_string_start, "%Y-%m-%dT%H:%M:%SZ")
        dt_start = dt_start.replace(tzinfo=timezone.utc)  # UTC-Zeitzone hinzufügen
        startstamp = int(dt_start.timestamp())

        utc_string_end = end_time
        dt_end = datetime.strptime(utc_string_end, "%Y-%m-%dT%H:%M:%SZ")
        dt_end = dt_end.replace(tzinfo=timezone.utc)  # UTC-Zeitzone hinzufügen
        endstamp = int(dt_end.timestamp())

        print("Startzeit:", startstamp)
        print("Endzeit:", endstamp)

        url = f"{url_get_events}?calendar_id={calendar_id}"
        payload = json.dumps({
            "title": title,
            "busy": True,
            "description": description,
            "when": {
                "start_time": startstamp,
                "end_time": endstamp,
                "start_timezone": "Europe/Berlin",
                "end_timezone": "Europe/Berlin"
            },
            "location": location
        })
        status, _ = self.send_request("POST", url, payload)
        if status != 200:
            print(f"HTTP Error: {status}")
            return False
        print("Kalendereintrag erstellt")
        print(payload)
        return True


token = "nyk_v0_6TpmBjhlAbANowY0Cf6lbJAHA4jPNspS495Za9tu1q6ACxaqiOQnuRQ6UcbFfdl3"  # noqa: E501
nylasClient = NylasClient(token)
