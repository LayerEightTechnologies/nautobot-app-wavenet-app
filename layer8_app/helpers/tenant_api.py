"""Helper functions for interacting with the Wavenet Gateway Tenant API."""

import requests

from requests.exceptions import RequestException

from .get_m2m_token import get_api_token

import openapi_client
from openapi_client.rest import ApiException

configuration = openapi_client.Configuration(host="https://bcs-api.wavenetuk.com/v2.5.6")


def fetch_buildings_list(get_api_token=get_api_token, configuration=configuration):
    """Fetch list of buildings from the Tenant API."""
    api_token = get_api_token()
    with openapi_client.ApiClient(
        configuration, header_name="Authorization", header_value=f"Bearer {api_token}"
    ) as api_client:
        api_instance = openapi_client.DefaultApi(api_client)

        try:
            api_response = api_instance.get_buildings_with_operator(
                page_size=1000,
                order_by="building_name ASC",
                # fields="id, building_name, building_operator",
                status="Live Building",
            )
            dropdown_values = [
                (item["id"], item["building_name"] + " (" + str(item["operator"]["operator_name"]) + ")")
                for item in api_response["buildings"]["items"]
            ]
            return dropdown_values
        except ApiException as e:
            print("Exception when calling DefaultApi->get_buildings_with_operator: %s\n" % e)
            return []

    # headers = {"Authorization": f"Bearer {api_token}"}
    # response = requests.get(
    #     "https://bcs-api.wavenetuk.com/v2.5.6/buildings/withoperator?page_size=1000&order_by=building_name ASC&fields=id, building_name, building_operator&status=Live Building",
    #     headers=headers,
    #     timeout=60,
    # )
    # if response.status_code == 200:
    #     data = response.json()
    #     dropdown_values = [
    #         (item["id"], item["building_name"] + " (" + str(item["operator"]["operator_name"]) + ")")
    #         for item in data["buildings"]["items"]
    #     ]
    #     return dropdown_values
    # else:
    # return []


def get_building_data(building_id):
    """Get building data from the Tenant API."""
    gateway_api_token = get_api_token()
    auth_header = {"Authorization": f"Bearer {gateway_api_token}"}
    try:
        response = requests.get(
            f"https://bcs-api.wavenetuk.com/v2.5.6/buildings/{building_id}", headers=auth_header, timeout=60
        )
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
        data = response.json()
        return data
    except RequestException as e:
        # Handle HTTP and connection errors
        raise Exception(f"HTTP request failed: {e}")
    except ValueError:
        # Handle JSON decoding errors
        raise Exception("Failed to parse JSON response.")
