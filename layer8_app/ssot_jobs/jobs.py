"""Jobs for Layer8 integration with SSoT App."""

from django.urls import reverse
from nautobot.extras.jobs import BooleanVar
from nautobot_ssot.jobs.base import DataSource, DataMapping

from .diffsync.adapters.layer8 import Layer8Adapter
from .diffsync.adapters.nautobot import NautobotAdapter

import openapi_client
from ..helpers.get_m2m_token import get_api_token

name = "SSoT - Layer8"  # pylint:disable=invalid-name


def tenant_api(get_api_token=get_api_token):
    """Return the authenticated API client for the Tenant API."""
    api_token = get_api_token()
    configuration = openapi_client.Configuration(host="https://bcs-api.wavenetuk.com/v2.5.6")
    api_client = openapi_client.ApiClient(
        configuration, header_name="Authorization", header_value=f"Bearer {api_token}"
    )
    api_instance = openapi_client.DefaultApi(api_client)
    return api_instance


class Layer8DataSource(DataSource):
    """Class to provide a data source for Layer8 integration with SSoT App."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)
    bulk_import = BooleanVar(description="Enable using bulk create option for object creation.", default=False)

    class Meta:
        """Metadata for the data source."""

        name = "Layer8 Data Source"
        data_source = "Layer8"
        description = "Data source for Layer8 integration with SSoT App."

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataSource."""
        return (
            DataMapping(
                "Buildings",
                "https://bcs-api.wavenetuk.com/v2.5.6/buildings",
                "Locations",
                reverse("dcim:location_list"),
            ),
            DataMapping(
                "Rooms",
                "https://bcs-api.wavenetuk.com/v2.5.6/rooms",
                "Locations",
                reverse("dcim:location_list"),
            ),
        )

    def load_source_adapter(self):
        """Load data from Layer8 into DiffSync models."""
        if self.debug:
            self.logger.info("Connecting to Layer8 API...")
        client = tenant_api()
        self.source_adapter = Layer8Adapter(job=self, sync=self.sync, api_client=client)
        if self.debug:
            self.logger.info("Loading data from Layer8 API.")
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load data from Nautobot into DiffSync models."""
        self.target_adapter = NautobotAdapter(job=self, sync=self.sync)
        if self.debug:
            self.logger.info("Loading data from Nautobot.")
        self.target_adapter.load()

    def run(  # pylint: disable=arguments-differ, too-many-arguments
        self, dryrun, memory_profiling, debug, bulk_import, *args, **kwargs
    ):
        """Perform data syncrhonization."""
        self.bulk_import = bulk_import
        self.debug = debug
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        super().run(dryrun=self.dryrun, memory_profiling=self.memory_profiling, *args, **kwargs)


jobs = [Layer8DataSource]
