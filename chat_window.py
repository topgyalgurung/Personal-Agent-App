"""Show the chat page in a native window. Run by app.py as a subprocess."""
import sys

import webview


def main(url):
    webview.create_window("Personal Agent", url, width=460, height=640)
    webview.start()


if __name__ == "__main__":
    main(sys.argv[1])
