from ..config import ResolvedConfig
from ..errors import SesameApiError
from ..http import HttpClient

_PUSH_ENDPOINT = "/private/notification/v1/external-push-notifications"


class NotificationsModule:
    """Push notifications — send push notifications to the Sesame HR mobile app."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def send_push(self, *, employee_id: str, title: str, message: str, application_id: str) -> bool:
        """Send a push notification to an employee's Sesame HR mobile app.
        Returns True on success, False on API error (graceful failure)."""
        try:
            self._http.post(
                _PUSH_ENDPOINT,
                {
                    "employeeId": employee_id,
                    "title": title,
                    "message": message,
                    "clickAction": "ApiPushNotificationSent",
                    "clickActionPayload": {
                        "id": application_id,
                        "employeeId": "",
                    },
                },
            )
            return True
        except SesameApiError:
            return False
