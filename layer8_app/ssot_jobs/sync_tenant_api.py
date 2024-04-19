"""Nautobot SSOT App jobs for the Layer 8 app."""

from typing import Optional, Mapping, List, Annotated
from uuid import UUID
from django.contrib.contenttypes.models import ContentType
from django.templatetags.static import static
from django.urls import reverse

from nautobot.dcim.models import Location, LocationType
from nautobot.apps.jobs import Job, StringVar, register_jobs
from nautobot.extras.models import Status

from diffsync import DiffSync
from diffsync.enum import DiffSyncFlags
from diffsync.exceptions import ObjectNotCreated

import openapi_client
from openapi_client.rest import ApiException

from nautobot_ssot.contrib import NautobotModel, NautobotAdapter, CustomFieldAnnotation
from nautobot_ssot.jobs.base import DataMapping, DataSource, DataTarget, DataSyncBaseJob

from ..helpers.get_m2m_token import get_api_token


def tenant_api(get_api_token=get_api_token):
    """Return the authenticated API client for the Tenant API."""
    api_token = get_api_token()
    configuration = openapi_client.Configuration(host="https://bcs-api.wavenetuk.com/v2.5.6")
    api_client = openapi_client.ApiClient(
        configuration, header_name="Authorization", header_value=f"Bearer {api_token}"
    )
    api_instance = openapi_client.DefaultApi(api_client)
    return api_instance


name = "Wavenet App SSoT Jobs"  # pylint:disable=invalid-name
building_location_type = LocationType.objects.get_or_create(name="Building")[0]


# Step 1 - Data Modeling for Building
class BuildingModel(NautobotModel):
    """DiffSync model for Buildings."""

    _model = Location
    _modelname = "location"
    _identifiers = ("external_id", "location_type__name")
    _attributes = ("name", "status__name")

    external_id: Annotated[int, CustomFieldAnnotation(key="external_id")]
    name: str
    location_type__name: str
    status__name: str = "Planned"


# Step 2.1 - Nautobot Adapter
class MySSoTNautobotAdapter(NautobotAdapter):
    """DiffSync adapter for Nautobot."""

    location = BuildingModel
    top_level = ("location",)


# Step 2.2 - Remote Adapter
class MySSoTRemoteAdapter(DiffSync):
    """DiffSync adapter for remote system."""

    location = BuildingModel
    top_level = ("location",)

    def __init__(self, *args, api_client, **kwargs):
        """Initialize the adapter."""
        super().__init__(*args, **kwargs)
        self.api_client = api_client

    def load(self):
        """Load data from the remote system."""
        try:
            buildings_data = self.api_client.get_buildings(page_size=1000, status="Live Building")
            buildings_list = buildings_data["buildings"]["items"]
            for building in buildings_list:
                if building["status"] == "Live Building":
                    building["status"] = "Active"
                else:
                    building["status"] = "Planned"

                loaded_building = self.location(
                    external_id=int(building["id"]),
                    name=building["building_name"],
                    location_type__name="Building",
                    status__name=building["status"],
                )
                self.add(loaded_building)
        except ApiException as e:
            raise Exception(f"Failed to load data from remote system: {e}")


# Step 3 - The Job
class BuildingDataSource(DataSource):
    """SSoT Job class for synchronizing building data."""

    class Meta:
        """Metadata for the job."""

        name = "Building Data Source"
        description = "Synchronizes building records from a remote system into Nautobot."

    # # Custom fields to be handled in NautobotAdapter
    # location_custom_fields = {
    #     "external_id": StringVar(),
    #     "location_type": StringVar(default="building"),
    # }

    def load_source_adapter(self):
        """Load the source adapter."""
        self.source_adapter = MySSoTRemoteAdapter(api_client=tenant_api())
        self.source_adapter.load()
        return self.source_adapter

    def load_target_adapter(self):
        """Load the target adapter."""
        self.target_adapter = MySSoTNautobotAdapter(job=self)
        self.target_adapter.load()
        return self.target_adapter

    def run(self, dryrun, memory_profiling, *args, **kwargs):
        """Run the job."""
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        super().run(dryrun=self.dryrun, memory_profiling=self.memory_profiling, *args, **kwargs)

    # def sync_data(self, memory_profiling):
    #     """Sync the data."""
    #     source_adapter = self.load_source_adapter()
    #     target_adapter = self.load_target_adapter()
    #     diff = source_adapter.diff_from(target_adapter)
    #     self.sync.diff = diff.dict()
    #     self.sync.save()
    #     self.logger.info(msg=diff.summary())
    #     if not self.kwargs["dry_run"]:
    #         try:
    #             target_adapter.sync_from(source_adapter)
    #         except ObjectNotCreated as err:
    #             self.logger.debug(msg=f"Unable to create object. {err}")
    #         self.logger.info(msg="Sync Completed")


jobs = [BuildingDataSource]
