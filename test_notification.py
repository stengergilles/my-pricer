"""
Test script for the cross-platform notification module.

- On desktop (Windows/Linux/macOS), it should show a notification using plyer.
- On Android (in a Kivy/P4A context), it will use pyjnius for native notifications.
- If all else fails, it will print to the console.

To run:
    python test_notification.py
"""

from stock_monitoring_app.utils.notification import send_notification

if __name__ == "__main__":
    import time
    send_notification(
        "Test Notification",
        "This is a test notification from the stock monitoring app.",
        app_name="NotificationTest"
    )
    # Wait a little to ensure notification is displayed before script exits (for plyer)
    time.sleep(3)
