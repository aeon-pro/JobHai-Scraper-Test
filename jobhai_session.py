"""Private JobHai session and recruiter-contact client.

This module is the only place that handles JobHai session credentials.  Build
distributions should contain the PyArmor-generated version of this module, not
this source file.
"""

import argparse
import getpass
import json
import re
import uuid

import keyring
import requests
from keyring.errors import KeyringError, PasswordDeleteError


API_BASE_URL = "https://api.jobhai.com"
WEB_BASE_URL = "https://www.jobhai.com"
KEYRING_SERVICE = "jobhai-jaipur-scraper"
KEYRING_ACCOUNT = "contact-session"
NOT_AVAILABLE = "Not available"


class SessionError(RuntimeError):
    """Raised when a usable JobHai session cannot be created or loaded."""


def _transaction_id():
    return f"JS-WEB-{uuid.uuid4()}"


def _headers(device_id, access_token=None):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Language": "en",
        "source": "WEB",
        "device-source": "Desktop",
        "device-id": device_id,
        "deviceId": device_id,
        "Origin": WEB_BASE_URL,
        "Referer": f"{WEB_BASE_URL}/",
        "x-transaction-id": _transaction_id(),
    }
    if access_token:
        headers["Authorization"] = access_token

    return headers


def _response_data(response, fallback_message):
    try:
        return response.json()
    except ValueError as exc:
        raise SessionError(fallback_message) from exc


def _normalise_phone(number):
    digits = re.sub(r"\D", "", str(number or ""))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91 {digits}"
    return NOT_AVAILABLE


def _save_credentials(credentials):
    try:
        keyring.set_password(
            KEYRING_SERVICE,
            KEYRING_ACCOUNT,
            json.dumps(credentials, separators=(",", ":")),
        )
    except KeyringError as exc:
        raise SessionError(
            "The operating-system credential store is unavailable"
        ) from exc


def _load_credentials():
    try:
        payload = keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    except KeyringError as exc:
        raise SessionError(
            "The operating-system credential store is unavailable"
        ) from exc

    if not payload:
        raise SessionError(
            "No saved JobHai session; run `python -m jobhai_session setup` first"
        )

    try:
        credentials = json.loads(payload)
        access_token = credentials["access_token"]
        access_id = credentials["access_id"]
        device_id = credentials["device_id"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SessionError(
            "The saved JobHai session is invalid; run setup again"
        ) from exc

    if not all((access_token, access_id, device_id)):
        raise SessionError(
            "The saved JobHai session is incomplete; run setup again"
        )

    return {
        "access_token": str(access_token),
        "access_id": str(access_id),
        "device_id": str(device_id),
    }


def setup_session(phone=None):
    """Perform OTP login and save the resulting session in the OS keyring."""

    phone = (phone or input("JobHai account phone: ")).strip()
    if not re.fullmatch(r"[6-9]\d{9}", phone):
        raise SessionError("Enter a valid 10-digit Indian phone number")

    device_id = str(uuid.uuid4())
    session = requests.Session()
    try:
        send_response = session.post(
            f"{API_BASE_URL}/auth/jobseeker/v3/send_otp",
            headers=_headers(device_id),
            json={"phone": phone},
            timeout=30,
        )
        send_response.raise_for_status()
        send_data = _response_data(send_response, "OTP request returned invalid data")
        if send_data.get("status") is False:
            message = (
                send_data.get("error")
                or send_data.get("message")
                or "OTP request failed"
            )
            raise SessionError(message)

        otp = getpass.getpass("JobHai OTP: ").strip()
        verify_response = session.post(
            f"{API_BASE_URL}/auth/jobseeker/v2/verify_otp",
            headers=_headers(device_id),
            json={"phone": phone, "otp": otp},
            timeout=30,
        )
        verify_response.raise_for_status()
        verify_data = _response_data(
            verify_response,
            "OTP verification returned invalid data",
        )
        if not verify_data.get("status"):
            message = (
                verify_data.get("error")
                or verify_data.get("message")
                or "OTP verification failed"
            )
            raise SessionError(message)

        user_data = verify_data.get("data") or {}
        access_token = user_data.get("token")
        access_id = str(user_data.get("user_id") or "")
        if not access_token or not access_id:
            raise SessionError("JobHai login response did not contain a session")

        _save_credentials(
            {
                "access_token": access_token,
                "access_id": access_id,
                "device_id": device_id,
            }
        )
    except requests.RequestException as exc:
        raise SessionError(f"JobHai login failed: {exc}") from exc
    finally:
        session.close()


def has_saved_session():
    try:
        return bool(keyring.get_password(KEYRING_SERVICE, KEYRING_ACCOUNT))
    except KeyringError as exc:
        raise SessionError(
            "The operating-system credential store is unavailable"
        ) from exc


def clear_saved_session():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_ACCOUNT)
    except PasswordDeleteError:
        return False
    except KeyringError as exc:
        raise SessionError(
            "The operating-system credential store is unavailable"
        ) from exc
    return True


class ContactClient:
    """Authenticated client that does not expose its credential material."""

    def __init__(self, credentials):
        self._session = requests.Session()
        self._headers = _headers(
            credentials["device_id"],
            access_token=credentials["access_token"],
        )
        for name, value in {
            "access_token": credentials["access_token"],
            "access_id": credentials["access_id"],
            "deviceId": credentials["device_id"],
        }.items():
            self._session.cookies.set(name, value, domain=".jobhai.com", path="/")

    def _post(self, url, payload):
        headers = dict(self._headers)
        headers["x-transaction-id"] = _transaction_id()
        response = self._session.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code in {401, 403}:
            raise SessionError(
                "The saved JobHai session expired; run setup again"
            )
        response.raise_for_status()
        return response

    def fetch_recruiter_contact(self, job_id):
        try:
            call_response = self._post(
                f"{API_BASE_URL}/jobs/v3/call",
                {"job_id": job_id},
            )
            call_data = call_response.json().get("data") or {}
            if not call_data.get("call_allowed"):
                return NOT_AVAILABLE, NOT_AVAILABLE

            encrypted_contact = call_data.get("job_contact")
            if not encrypted_contact:
                return NOT_AVAILABLE, NOT_AVAILABLE

            decrypt_response = self._post(
                f"{WEB_BASE_URL}/v1/utils/getInfo",
                {"number": encrypted_contact},
            )
            contact_data = decrypt_response.json().get("data") or {}
        except SessionError:
            raise
        except (requests.RequestException, TypeError, ValueError):
            return NOT_AVAILABLE, NOT_AVAILABLE

        phone = _normalise_phone(contact_data.get("number"))
        email = str(contact_data.get("email") or NOT_AVAILABLE).strip()
        return phone, email or NOT_AVAILABLE

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def open_contact_client():
    """Return a contact client backed by the saved OS-keyring session."""

    return ContactClient(_load_credentials())


def main():
    parser = argparse.ArgumentParser(
        description="Set up the private JobHai session used by the scraper."
    )
    parser.add_argument(
        "command",
        choices=("setup", "status", "clear"),
        help="Create, check, or remove the saved session",
    )
    args = parser.parse_args()

    try:
        if args.command == "setup":
            setup_session()
            print("JobHai session saved in the operating-system credential store")
        elif args.command == "status":
            state = "configured" if has_saved_session() else "not configured"
            print(f"JobHai session is {state}")
        elif clear_saved_session():
            print("Saved JobHai session removed")
        else:
            print("No saved JobHai session was found")
    except SessionError as exc:
        parser.error(str(exc))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
