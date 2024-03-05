"""Test jobs for the Layer 8 app."""

import requests

from django.core.exceptions import ObjectDoesNotExist
from requests.exceptions import RequestException

from nautobot.apps.jobs import ChoiceVar, IntegerVar, Job, register_jobs, StringVar
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


def fetch_buildings_list(get_api_token=get_api_token):
    """Fetch list of buildings from the Tenant API."""
    api_token = get_api_token()
    headers = {"Authorization": f"Bearer {api_token}"}
    response = requests.get(
        "https://bcs-api.wavenetuk.com/v2.5.6/buildings/withoperator?page_size=1000&order_by=building_name ASC&fields=id, building_name, building_operator&status=Live Building",
        headers=headers,
        timeout=60,
    )
    if response.status_code == 200:
        data = response.json()
        dropdown_values = [
            (item["id"], item["building_name"] + " (" + str(item["operator"]["operator_name"]) + ")")
            for item in data["buildings"]["items"]
        ]
        return dropdown_values
    else:
        raise Exception(f"Failed to fetch buildings list: {response.status_code}")
        return []


class LoadBuildings(Job):
    """Class to provide a job that loads buildings from the Tenant API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Buildings"
        description = "Load a building and it's rooms from the Tenant API and creates them as locations in Nautobot."

    building_id = ChoiceVar(description="Select a building to import", label="Building", choices=fetch_buildings_list)

    def get_building_data(self, building_id, gateway_api_token):
        """Get building data from the Tenant API."""
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

    def run(self, building_id, get_api_token=get_api_token, get_building_data=get_building_data):
        """Run the job."""
        gateway_api_token = get_api_token()
        self.logger.info(f"Building ID: {building_id} // API Token: {gateway_api_token}")
        building_data = get_building_data(self, building_id, gateway_api_token)
        self.logger.info(f"Building Data: {building_data}")


jobs = [LoadBuildings]
register_jobs(*jobs)
