import json
import os
import stat
from datetime import datetime, timedelta, timezone

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from integrations import google_auth
from integrations.google_auth import GoogleAuthError, get_credentials


@pytest.fixture(autouse=True)
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PERSONAL_AGENT_CONFIG_DIR", str(tmp_path))
    return tmp_path


def write_token(config_dir, expiry):
    token = {
        "token": "access-1",
        "refresh_token": "refresh-1",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "id",
        "client_secret": "secret",
        "scopes": google_auth.SCOPES,
        "expiry": expiry.replace(tzinfo=None).isoformat() + "Z",
    }
    (config_dir / "token.json").write_text(json.dumps(token))


def now():
    return datetime.now(timezone.utc)


def test_only_read_only_scopes_are_requested():
    assert all(scope.endswith(".readonly") for scope in google_auth.SCOPES)
    assert len(google_auth.SCOPES) == 2


def test_valid_saved_token_is_loaded_without_a_browser(config_dir, monkeypatch):
    write_token(config_dir, now() + timedelta(hours=1))
    monkeypatch.setattr(google_auth, "InstalledAppFlow", None)

    assert get_credentials().token == "access-1"


def test_expired_token_is_refreshed_and_saved(config_dir, monkeypatch):
    write_token(config_dir, now() - timedelta(hours=1))

    def fake_refresh(self, request):
        self.token = "access-2"
        self.expiry = datetime.now() + timedelta(hours=1)

    monkeypatch.setattr(Credentials, "refresh", fake_refresh)

    assert get_credentials().token == "access-2"
    saved = json.loads((config_dir / "token.json").read_text())
    assert saved["token"] == "access-2"


def test_saved_token_file_is_private(config_dir, monkeypatch):
    write_token(config_dir, now() - timedelta(hours=1))
    monkeypatch.setattr(
        Credentials, "refresh", lambda self, request: setattr(self, "token", "x")
    )

    get_credentials()

    mode = stat.S_IMODE(os.stat(config_dir / "token.json").st_mode)
    assert mode == 0o600


def test_not_signed_in_says_how_to_sign_in():
    with pytest.raises(GoogleAuthError, match="python -m integrations.google_auth"):
        get_credentials()


def test_failed_refresh_says_how_to_sign_in(config_dir, monkeypatch):
    write_token(config_dir, now() - timedelta(hours=1))

    def fail(self, request):
        raise RefreshError("revoked")

    monkeypatch.setattr(Credentials, "refresh", fail)

    with pytest.raises(GoogleAuthError, match="Sign in again"):
        get_credentials()


def test_sign_in_without_credentials_json_explains_setup():
    with pytest.raises(GoogleAuthError, match="credentials.json"):
        google_auth.sign_in()


def test_sign_in_saves_token_with_private_mode(config_dir, monkeypatch):
    (config_dir / "credentials.json").write_text("{}")

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, path, scopes):
            assert scopes == google_auth.SCOPES
            return cls()

        def run_local_server(self, port=0):
            return Credentials(
                token="new", refresh_token="r", client_id="i",
                client_secret="s", token_uri="https://x",
                scopes=google_auth.SCOPES,
            )

    monkeypatch.setattr(google_auth, "InstalledAppFlow", FakeFlow)

    google_auth.sign_in()

    path = config_dir / "token.json"
    assert json.loads(path.read_text())["token"] == "new"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
