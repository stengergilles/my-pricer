import platform
import os
import subprocess
import shutil

def send_notification(title, message, app_name="Stock Monitoring App", timeout=10):
    # Termux-specific notification
    if "TERMUX_VERSION" in os.environ:
        # Check if termux-notification command is available
        termux_notification_path = shutil.which("termux-notification")
        if termux_notification_path and _has_termux_api():
            try:
                subprocess.run([
                    termux_notification_path,
                    "--title", str(title),
                    "--content", str(message)
                ])
                return
            except Exception as e:
                print(f"Termux notification failed: {e}")
        else:
            print("Termux notification unavailable: 'termux-notification' command or Termux:API app is missing.")
    

    # --- Desktop platforms (fallback) ---
    try:
        from plyer import notification as plyer_notification
        

        # Check if 'notify' attribute exists and is not None before calling        
        if hasattr(plyer_notification, 'notify') and plyer_notification.notify is not None:
            plyer_notification.notify( # Moved to a new, indented line
                title=title,
                message=message,
                app_name=app_name,
                timeout=timeout
            )
            return
        # If plyer_notification.notify is None or doesn't exist,
        # the 'if' condition fails, and we'll fall through.
        # The existing 'except Exception: pass' will catch other potential issues
        # such as ImportError or errors from within a successful notify() call.
    except Exception:
        pass

    # --- Fallback: Print to console ---
    print(f"Notification: {title}\n{message}")

def _has_termux_api():
    try:
        out = subprocess.run(["termux-info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return out.returncode == 0
    except Exception:
        return False
