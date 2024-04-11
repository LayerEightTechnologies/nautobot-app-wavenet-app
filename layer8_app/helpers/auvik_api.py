"""Helper functions for interacting with the Auvik API."""

import layer8_auvik_api_client
from layer8_auvik_api_client.rest import ApiException

from ..models import AuvikTenant

from django.core.exceptions import ObjectDoesNotExist

from nautobot.extras.models import Secret

from urllib.parse import urlparse, parse_qs

import re


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


def camel_case_to_snake_case(camel_case_str):
    """Convert camelCase string to snake_case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_case_str).lower()


def convert_query_params(query_params):
    """
    Convert query parameters from URL format to API method parameter format.

    Specifically:
    - Convert keys from 'filter[networkType]' to 'filter_network_type'.
    - Convert values for 'page_first' and 'page_last' to integers.

    :param query_params: The query parameters as a dictionary, result of parse_qs(parsed_url.query).
    :return: A dictionary with converted keys and appropriately cast values.
    """
    converted_params = {}
    for key, value in query_params.items():
        # Pre-process the key to replace brackets with underscores and then convert to snake_case
        pre_processed_key = key.replace("[", "_").replace("]", "")
        # Split the pre-processed key into parts and convert camelCase to snake_case
        parts = pre_processed_key.split("_")
        new_key = "_".join(camel_case_to_snake_case(part) for part in parts)

        # Attempt to convert numerical values for specific keys
        if new_key in ["page_first", "page_last"] and value:
            try:
                converted_params[new_key] = int(value[0])
            except ValueError:
                # If conversion fails, fallback to original value
                converted_params[new_key] = value[0]
        else:
            # Simplify to a single value if there's only one, otherwise keep as a list
            converted_params[new_key] = value[0] if len(value) == 1 else value

    return converted_params


def fetch_all_pages(api_instance, method_name, **kwargs):
    """
    Fetch all pages of data from the Auvik API for a given API instance and method.

    :param api_instance: The API instance to use.
    :param method_name: The method name as a string to call on the API instance for fetching data.
    :param kwargs: Keyword arguments to pass to the API method. These should include any filters and tenant IDs.
    :return: A list containing all items from all pages.
    """
    all_items = []
    next_page_url = None

    try:
        while True:
            if next_page_url:
                parsed_url = urlparse(next_page_url)
                query_params = parse_qs(parsed_url.query)
                converted_params = convert_query_params(query_params)
                kwargs.update(converted_params)
            else:
                converted_params = kwargs

            method_to_call = getattr(api_instance, method_name)
            print(f"Calling {method_name} with parameters: {converted_params}")
            api_response = method_to_call(**converted_params)

            all_items.extend(api_response.data)

            next_page_url = getattr(api_response.links, "next", None)

            if not next_page_url:
                break

    except ApiException as e:
        raise Exception(f"Failed to fetch data from Auvik API: {e}")

    return all_items


def auvik_api(get_credentials=get_auvik_credentials):
    """Return the authenticated API client for the Auvik API."""
    auvik_api_user, auvik_api_key = get_credentials()
    configuration = layer8_auvik_api_client.Configuration(
        host="https://auvikapi.eu1.my.auvik.com/v1",
        username=auvik_api_user,
        password=auvik_api_key,
    )
    api_client = layer8_auvik_api_client.ApiClient(configuration)
    return api_client


def auvik_api_network(api_client):
    """Return an API instance for the Auvik Network API."""
    api_instance = layer8_auvik_api_client.NetworkApi(api_client)
    return api_instance


def auvik_api_device(api_client):
    """Return an API instance for the Auvik Device API."""
    api_instance = layer8_auvik_api_client.DeviceApi(api_client)
    return api_instance


def auvik_api_interface(api_client):
    """Return an API instance for the Auvik Interface API."""
    api_instance = layer8_auvik_api_client.InterfaceApi(api_client)
    return api_instance


def load_auvik_tenants_from_orm():
    """Load Auvik tenants from the ORM."""
    tenants_list = AuvikTenant.objects.all()
    tenants_choices = [(tenant.auvik_tenant_id, tenant.name) for tenant in tenants_list]
    return tenants_choices
