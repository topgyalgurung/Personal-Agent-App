import sys

import app


class FakeProcess:
    def __init__(self, returncode=0, running=False):
        self.returncode = returncode
        self.running = running
        self.terminated = False

    def poll(self):
        return None if self.running else self.returncode

    def wait(self):
        return self.returncode

    def terminate(self):
        self.terminated = True


def make_opener(process):
    opened, launched = [], []

    def popen(command):
        launched.append(command)
        return process

    opener = app.ChatOpener(
        "http://127.0.0.1:8000",
        popen=popen,
        open_browser=opened.append,
        run_in_background=lambda target: target(),
    )

    return opener, launched, opened


def test_opens_the_chat_window_in_a_separate_process():
    opener, launched, opened = make_opener(FakeProcess(returncode=0))

    opener.open()

    assert launched == [[sys.executable, str(app.WINDOW_SCRIPT), "http://127.0.0.1:8000"]]
    assert opened == []


def test_falls_back_to_the_browser_if_the_window_fails():
    opener, _, opened = make_opener(FakeProcess(returncode=1))

    opener.open()

    assert opened == ["http://127.0.0.1:8000"]


def test_does_not_open_a_second_window_while_one_is_running():
    opener, launched, _ = make_opener(FakeProcess(running=True))

    opener.open()
    opener.open()

    assert len(launched) == 1


def test_close_stops_a_running_window():
    process = FakeProcess(running=True)
    opener, _, _ = make_opener(process)
    opener.open()

    opener.close()

    assert process.terminated is True


def test_close_without_a_window_is_fine():
    opener, _, _ = make_opener(FakeProcess())

    opener.close()
