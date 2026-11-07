"""Google sign-in with read-only scopes. Run this module once to sign in."""
import os
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

SIGN_IN_COMMAND = "uv run python -m integrations.google_auth"


class GoogleAuthError(Exception):
    """Sign-in problem; the message is shown to the user."""


def config_dir():
    return Path(
        os.getenv("PERSONAL_AGENT_CONFIG_DIR", "~/.config/personal-agent")
    ).expanduser()


def save_token(credentials):
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "token.json"

    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(credentials.to_json())

    os.chmod(path, 0o600)


def get_credentials():
    """Return valid credentials, refreshing the saved token if needed."""
    path = config_dir() / "token.json"

    if not path.exists():
        raise GoogleAuthError(f"Not signed in to Google. Run: {SIGN_IN_COMMAND}")

    credentials = Credentials.from_authorized_user_file(str(path), SCOPES)

    if credentials.valid:
        return credentials

    if credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError:
            raise GoogleAuthError(
                f"Google sign-in expired. Sign in again: {SIGN_IN_COMMAND}"
            )

        save_token(credentials)
        return credentials

    raise GoogleAuthError(
        f"Google sign-in expired. Sign in again: {SIGN_IN_COMMAND}"
    )


def sign_in():
    """Open the browser once and save a token."""
    secrets = config_dir() / "credentials.json"

    if not secrets.exists():
        raise GoogleAuthError(
            f"Missing {secrets}. Download credentials.json from your Google "
            "Cloud project (see the README) and put it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    credentials = flow.run_local_server(port=0)
    save_token(credentials)

    return credentials


if __name__ == "__main__":
    try:
        sign_in()
    except GoogleAuthError as error:
        raise SystemExit(str(error))

    print(f"Signed in. Token saved to {config_dir() / 'token.json'}")
