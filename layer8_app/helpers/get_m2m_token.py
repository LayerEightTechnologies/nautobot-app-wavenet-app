"""Utility to get OAuth M2M token for Wavenet Gateway APIs."""

import requests

from django.core.exceptions import ObjectDoesNotExist
from requests.exceptions import RequestException

from nautobot.extras.models import Secret


def get_api_token():
    """Get the API token from the Nautobot Jobs Gateway."""
    auth_token_secret_name = "Nautobot Jobs Gateway M2M Token Auth"

    try:
        auth_token_secret_object = Secret.objects.get(name=auth_token_secret_name)
    except ObjectDoesNotExist:
        raise Exception(f"Secret '{auth_token_secret_name}' not found.")

    try:
        auth_token = auth_token_secret_object.get_value()
    except Exception as e:
        raise Exception(f"Failed to retrieve value for secret '{auth_token_secret_name}': {e}")

    if not auth_token:
        raise Exception(f"Secret '{auth_token_secret_name}' is empty.")

    auth_header = {"Authorization": f"{auth_token}"}
    try:
        response = requests.get(
            "https://n8n.gateway.wavenet.co.uk/webhook/gateway-m2m-credential", headers=auth_header, timeout=60
        )
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
        data = response.json()
        return data["access_token"]
    except RequestException as e:
        # Handle HTTP and connection errors
        raise Exception(f"HTTP request failed: {e}")
    except ValueError:
        # Handle JSON decoding errors
        raise Exception("Failed to parse JSON response.")
