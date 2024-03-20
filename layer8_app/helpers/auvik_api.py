"""Helper functions for interacting with the Auvik API."""

import layer8_auvik_api_client
from layer8_auvik_api_client.rest import ApiException

from django.core.exceptions import ObjectDoesNotExist

from nautobot.extras.models import Secret


def get_auvik_credentials():
    """Get the Auvik API credentials from the Nautobot Secrets."""
    auvik_api_user_secret_name = "Auvik API Username"
    auvik_api_key_secret_name = "Auvik API Password"

    try:
        auvik_api_user_secret_object = Secret.objects.get(name=auvik_api_user_secret_name)
    except ObjectDoesNotExist:
        raise Exception(f"Secret '{auvik_api_user_secret_name}' not found.")

    try:
        auvik_api_key_secret_object = Secret.objects.get(name=auvik_api_key_secret_name)
    except ObjectDoesNotExist:
        raise Exception(f"Secret '{auvik_api_key_secret_name}' not found.")

    try:
        auvik_api_user = auvik_api_user_secret_object.get_value()
    except Exception as e:
        raise Exception(f"Failed to retrieve value for secret '{auvik_api_user_secret_name}': {e}")

    try:
        auvik_api_key = auvik_api_key_secret_object.get_value()
    except Exception as e:
        raise Exception(f"Failed to retrieve value for secret '{auvik_api_key_secret_name}': {e}")

    if not auvik_api_user:
        raise Exception(f"Secret '{auvik_api_user_secret_name}' is empty.")

    if not auvik_api_key:
        raise Exception(f"Secret '{auvik_api_key_secret_name}' is empty.")

    return auvik_api_user, auvik_api_key


def get_auvik_tenants():
    """Get the list of tenants from the Auvik API."""
    auvik_api_user, auvik_api_key = get_auvik_credentials()
    configuration = layer8_auvik_api_client.Configuration(
        host="https://auvikapi.eu1.my.auvik.com/v1",
        username=auvik_api_user,
        password=auvik_api_key,
    )
    with layer8_auvik_api_client.ApiClient(configuration) as api_client:
        api_instance = layer8_auvik_api_client.TenantsApi(api_client)

        try:
            api_response = api_instance.read_multiple_tenants()
            return api_response
        except ApiException as e:
            raise Exception(f"Failed to fetch tenants from Auvik API: {e}")
