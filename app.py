"""Menu-bar app: a local server plus a chat window opened from the menu."""
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import rumps
import uvicorn

import server


WINDOW_SCRIPT = Path(__file__).parent / "chat_window.py"
URL = f"http://{server.HOST}:{server.PORT}"


def run_in_thread(target):
    threading.Thread(target=target, daemon=True).start()


class ChatOpener:
    """Opens the chat window in its own process.

    rumps and pywebview both want the main thread, so the window runs
    separately. If it fails to start, the page opens in the browser.
    """

    def __init__(
        self,
        url,
        *,
        popen=subprocess.Popen,
        open_browser=webbrowser.open,
        run_in_background=run_in_thread,
    ):
        self.url = url
        self.popen = popen
        self.open_browser = open_browser
        self.run_in_background = run_in_background
        self.process = None

    def open(self):
        if self.process and self.process.poll() is None:
            return

        process = self.popen([sys.executable, str(WINDOW_SCRIPT), self.url])
        self.process = process

        def watch():
            if process.wait() != 0:
                self.open_browser(self.url)

        self.run_in_background(watch)

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()


class AgentApp(rumps.App):
    def __init__(self):
        super().__init__("Agent", title="🤖", quit_button=None)
        self.chat = ChatOpener(URL)
        self.menu = [
            rumps.MenuItem("Open chat", callback=self.open_chat),
            rumps.MenuItem("Quit", callback=self.quit),
        ]
        self.server = uvicorn.Server(
            uvicorn.Config(server.app, host=server.HOST, port=server.PORT)
        )
        run_in_thread(self.server.run)

    def open_chat(self, _):
        self.chat.open()

    def quit(self, _):
        self.chat.close()
        self.server.should_exit = True
        rumps.quit_application()


def hide_dock_icon():
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

    NSApplication.sharedApplication().setActivationPolicy_(
        NSApplicationActivationPolicyAccessory
    )


if __name__ == "__main__":
    hide_dock_icon()
    AgentApp().run()
