"""Jobs for Layer8 integration with SSoT App."""

from django.urls import reverse
from nautobot.extras.jobs import BooleanVar, ChoiceVar
from nautobot_ssot.jobs.base import DataSource, DataMapping

from .diffsync.adapters.layer8 import Layer8Adapter
from .diffsync.adapters.auvik import AuvikAdapter
from .diffsync.adapters.nautobot import NautobotAdapter, NautobotAuvikAdapter

import openapi_client

import layer8_auvik_api_client

from ..helpers.auvik_api import get_auvik_credentials
from ..helpers.get_m2m_token import get_api_token
from ..models import AuvikTenantBuildingRelationship

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


class Layer8DataSource(DataSource):
    """Class to provide a data source for Layer8 integration with SSoT App."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)
    bulk_import = BooleanVar(description="Enable using bulk create option for object creation.", default=False)

    class Meta:
        """Metadata for the data source."""

        name = "Layer8 Data Source"
        data_source = "Layer8"
        description = "Data source for Layer8 integration with SSoT App."
        has_sensitive_variables = False

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


class AuvikDataSource(DataSource):
    """Class to provide a data source for Auvik integration with SSoT App."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)
    building_to_sync = ChoiceVar(
        description="Choose a building to synchronize from Auvik. <br /><small>Note: building must already be mapped to an Auvik Tenant in the <a href='/admin/layer8_app/auviktenantbuildingrelationship/'>admin section</a>.</small>",
        choices=AuvikTenantBuildingRelationship.objects.values_list("auvik_tenant_id", "building__name"),
    )

    class Meta:
        """Metadata for the data source."""

        name = "Auvik Data Source"
        data_source = "Auvik"
        description = """
        <h2>Data source for Auvik integration with SSoT App.</h2> 
        This data source will pull data from the Auvik API and synchronize it with Nautobot.<br /><br />
        Records that will be synced include:
        <ul>
            <li>Networks</li>
            <ul>
                <li>VLANs</li>
                <li>Prefixes</li>
                <li>IP Addresses</li>
            </ul>
            <li>Devices</li>
            <li>Interfaces</li>
            <ul>
                <li>Interface Connections</li>
            </ul>
        """
        has_sensitive_variables = False

    # Get the Auvik Tenant Building Relationship
    # AuvikTenantBuildingRelationship.objects.get(building_id=(Location.objects.get(name="Record Hall - Hatton")))
    # Location.objects.get(id=AuvikTenantBuildingRelationship.objects.get(auvik_tenant_id=(AuvikTenant.objects.get(name="wnrecordhall"))).building_id)

    # @classmethod
    # def data_mappings(cls):
    #     """List describing the data mappings involved in this DataSource."""
    #     return (
    #         DataMapping(
    #             "Tenants",
    #             "https://api.auvik.com/v1/tenants",
    #             "Auvik Tenants",
    #             reverse("layer8_app:auviktenant_list"),
    #         ),
    #     )

    def load_source_adapter(self):
        """Load data from Auvik into DiffSync models."""
        if self.debug:
            self.logger.info("Connecting to Auvik API...")
        client = auvik_api()
        self.source_adapter = AuvikAdapter(
            job=self, sync=self.sync, api_client=client, building_id=self.building_to_sync
        )
        if self.debug:
            self.logger.info("Loading data from Auvik API.")
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load data from Nautobot into DiffSync models."""
        self.target_adapter = NautobotAuvikAdapter(job=self, sync=self.sync)
        if self.debug:
            self.logger.info("Loading data from Nautobot.")
        self.target_adapter.load()

    def run(  # pylint: disable=arguments-differ, too-many-arguments
        self, dryrun, memory_profiling, debug, building_to_sync, *args, **kwargs
    ):
        """Perform data syncrhonization."""
        self.debug = debug
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        self.building_to_sync = building_to_sync
        super().run(
            dryrun=self.dryrun,
            memory_profiling=self.memory_profiling,
            building_to_sync=self.building_to_sync,
            *args,
            **kwargs,
        )


jobs = [Layer8DataSource, AuvikDataSource]
