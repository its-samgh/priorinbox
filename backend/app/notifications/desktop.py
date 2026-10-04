import asyncio

from desktop_notifier import DesktopNotifier

from backend.app.models.schemas import Classification, IncomingMessage, Settings


class Notifier:
    def __init__(self) -> None:
        self.notifier = DesktopNotifier(app_name="PriorInbox")
        self.last_error: str | None = None

    async def send(
        self, message: IncomingMessage, result: Classification, settings: Settings
    ) -> bool:
        if not settings.notifications or not result.important:
            return False
        try:
            authorized = await asyncio.wait_for(self.notifier.request_authorisation(), timeout=3)
            if not authorized:
                self.last_error = "Desktop notifications are not authorized by this OS session"
                return False
            title = (
                f"Important message from {message.sender_display_name}"
                if settings.notification_previews
                else "Important message · PriorInbox"
            )
            body = (
                f"{message.text[:120]}\nReason: {result.reason}"
                if settings.notification_previews
                else "Open your local inbox to review."
            )
            await asyncio.wait_for(self.notifier.send(title=title, message=body), timeout=3)
            self.last_error = None
            return True
        except Exception:
            self.last_error = (
                "Desktop notification unavailable; check OS permission and session support"
            )
            return False
