"""Test jobs for the Layer 8 app."""

from nautobot.apps.jobs import ChoiceVar, Job, register_jobs, JobButtonReceiver

from .helpers.tenant_api import fetch_buildings_list, get_building_data
from .helpers.auvik_api import (
    get_auvik_tenants,
    auvik_api,
    auvik_api_device,
    fetch_all_pages,
    load_auvik_tenants_from_orm,
)

# from .ssot_jobs.sync_tenant_api import BuildingDataSource

from .ssot_jobs.jobs import AuvikDataSource, Layer8DataSource

from .models import AuvikTenant, AuvikDeviceVendors, AuvikDeviceModels
from nautobot.dcim.models import Location, Device, Cable, Interface
from nautobot.ipam.models import IPAddressToInterface
from nautobot.extras.models import Status
from django.db.models import Q

name = "Wavenet App Jobs"


class LoadBuildings(Job):
    """Class to provide a job that loads buildings from the Tenant API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Buildings"
        description = "Load a building and it's rooms from the Tenant API and creates them as locations in Nautobot."

    building_id = ChoiceVar(description="Select a building to import", label="Building", choices=fetch_buildings_list)

    def run(self, building_id, get_building_data=get_building_data):
        """Run the job."""
        building_data = get_building_data(building_id)
        self.logger.info(f"Building Data: {building_data}")


class LoadAuvikTenants(Job):
    """Class to provide a job that loads Auvik tenants from the Auvik API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Auvik Tenants"
        description = "Load Auvik tenants from the Auvik API and create them as AuvikTenant objects in Nautobot."

    def run(self):
        """Run the job."""
        self.logger.info("Loading Auvik tenants...")

        auvik_tenants = get_auvik_tenants()
        for tenant in auvik_tenants.data:
            domain_prefix = tenant.attributes.domain_prefix
            tenant_id = tenant.id

            AuvikTenant.objects.update_or_create(auvik_tenant_id=tenant_id, defaults={"name": domain_prefix})
            self.logger.info(f"Loaded Auvik tenant: {domain_prefix} ({tenant_id})")

        self.logger.info("Auvik tenants loaded successfully.")


class LoadAuvikVendorsAndModels(Job):
    """Class to provide a job that loads Auvik vendors from the Auvik API."""

    class Meta:
        """Metadata for the job."""

        name = "Load Auvik Device Vendors and Models"
        description = "Load Auvik device vendors and models from the Auvik API and create them as AuvikDeviceVendors and AuvikDeviceModels objects in Nautobot."

    auvik_tenant_id = ChoiceVar(
        description="Select an Auvik tenant to import", label="Auvik Tenant", choices=load_auvik_tenants_from_orm
    )

    def run(self, auvik_tenant_id=None):
        """Run the job."""
        self.logger.info("Loading Auvik device vendors and models...")

        auvik_api_instance = auvik_api_device(auvik_api())
        try:
            auvik_tenant = AuvikTenant.objects.get(auvik_tenant_id=auvik_tenant_id)
            self.logger.info(f"Using Auvik tenant {auvik_tenant.name} with ID: {auvik_tenant.auvik_tenant_id}")
        except AuvikTenant.DoesNotExist:
            self.logger.error("Auvik tenant not found.")
            return

        params = {"tenants": auvik_tenant_id}

        try:
            auvik_devices = fetch_all_pages(auvik_api_instance, "read_multiple_device_info", **params)
        except Exception as e:
            self.logger.error(f"Failed to fetch Auvik devices: {e}")
            return

        vendor_names = []
        make_models = []

        for device in auvik_devices:
            vendor_name = getattr(device.attributes, "vendor_name", None)
            make_model = getattr(device.attributes, "make_model", None)

            if vendor_name not in vendor_names and vendor_name is not None:
                vendor_names.append(vendor_name)
                self.logger.info(f"Loaded Auvik device vendor: {vendor_name}")

            if make_model not in make_models and make_model is not None:
                make_models.append(make_model)
                self.logger.info(f"Loaded Auvik device model: {make_model}")

        for vendor in vendor_names:
            try:
                AuvikDeviceVendors.objects.update_or_create(
                    auvik_vendor_name=vendor, defaults={"auvik_vendor_name": vendor}
                )
                self.logger.info(f"Added/updated Auvik device vendor in Nautobot: {vendor}")
            except Exception as e:
                self.logger.error(f"Failed to add/update Auvik device vendor in Nautobot: {e}")

        for model in make_models:
            try:
                AuvikDeviceModels.objects.update_or_create(auvik_model_name=model, defaults={"auvik_model_name": model})
                self.logger.info(f"Added/updated Auvik device model in Nautobot: {model}")
            except Exception as e:
                self.logger.error(f"Failed to add/update Auvik device model in Nautobot: {e}")

        self.logger.info("Auvik device vendors and models loaded successfully.")


class SetPrimaryWanInterface(JobButtonReceiver):
    """Class to provide a job that sets the primary WAN interface on a device."""

    class Meta:
        """Metadata for the job."""

        name = "Set Primary WAN Interface"

    def receive_job_button(self, obj):
        """Run the job."""
        user = self.user
        self.logger.info(f"Setting primary WAN interface for location: ```{obj.__dict__}```")
        # Set the primary WAN interface here
        if not user.has_perm("dcim.change_interface"):
            self.logger.error(f"User {user} does not have permission to change interfaces.")
            return
        try:
            if (
                obj._custom_field_data.get("monitoring_profile")["monitoredBy"] is None
                or obj._custom_field_data.get("monitoring_profile")["monitoringFields"]["interfaceId"] is None
            ):
                self.logger.error(f"No monitoring profile set for location: {obj.id}")
                return
        except KeyError:
            self.logger.error(f"No monitoring profile set for location: {obj.id}")
            return
        try:
            location = Location.objects.get(name=obj.device.location.name)
            device = Device.objects.get(id=obj.device.id)
            device_auvik_id = device.custom_field_data.get("monitoring_profile")["monitoringFields"]["deviceId"]
            self.logger.info(f"Location found. ```{location.__dict__}```")
            location.custom_field_data.update(
                {
                    "monitoring_profile": {
                        "monitoredBy": "auvik",
                        "monitoringFields": {
                            "deviceId": device_auvik_id,
                            "wanInterfaceId": obj._custom_field_data.get("monitoring_profile")["monitoringFields"][
                                "interfaceId"
                            ],
                        },
                    }
                }
            )
            location.validated_save()
        except Location.DoesNotExist:
            self.logger.error(f"Location not found for location: {obj.id}")
            return
        except Device.DoesNotExist:
            self.logger.error(f"Device not found for location: {obj.id}")
            return
        except KeyError:
            self.logger.error(f"Monitoring profile not found for location: {obj.id}")
            return
        except Exception as e:
            self.logger.error(f"Failed to set primary WAN interface: {e}")
            return
        self.logger.info(
            f"Primary WAN interface set for location: {obj._custom_field_data.get('monitoring_profile')}, {obj.id}"
        )


class DecomissionDevice(JobButtonReceiver):
    """Class to provide a job that decomissions a device in a Connected building."""

    class Meta:
        """Metadata for the job."""

        name = "Decommission Device"
        descrpition = """
        This job marks a device as decommissioned by doing the following actions:
            -- Rename to `[decommed] <device_hostname>`
            -- Set status to `decommissioning`
            -- Update monitoring profile on device to `null`
            -- Remove primary IPV4 address from device
            -- Remove IP addresses from all interfaces
            -- Remove all cables terminating on device
        """

    def receive_job_button(self, obj):
        """Run the job."""
        user = self.user
        self.logger.info(f"Decomissioning this device: ```{obj.__dict__}```")
        if not user.has_perm("dcim.change_device"):
            self.logger.error(f"User {user} does not have permission to change devices.")
            return

        try:
            # Rename to [Decommed]...

            obj.name = f"[Decommed] {obj.name}"

            # Set status to decommissioning

            obj.status = Status.objects.get(name="Decommissioning")

            # Remove monitoring profile

            obj.custom_field_data.update({"monitoring_profile": {"monitored_by": None, "monitoring_fields": {}}})

            # Deallocate IP from device
            obj.primary_ip4 = None

            obj.validated_save()

            # Remove IPs from interfaces

            interfaces = Interface.objects.filter(device=obj.id)
            for interface in interfaces:
                interface_ips = IPAddressToInterface.objects.filter(interface=interface)
                for ip in interface_ips:
                    ip.delete()

        except Exception as e:
            print(f"Error while decomissioning {obj.name}: {str(e)}")
            return

        # Remove all connected cables

        try:
            connected_cables = Cable.objects.filter(
                Q(_termination_a_device_id=obj.id) | Q(_termination_b_device_id=obj.id)
            )
            for cable in connected_cables:
                cable.delete()
        except Exception as e:
            print(f"Error while removing connected cables for {obj.name}: {str(e)}")
            return

        return


jobs = [
    LoadAuvikTenants,
    # LoadBuildings,
    # BuildingDataSource,
    Layer8DataSource,
    AuvikDataSource,
    LoadAuvikVendorsAndModels,
    SetPrimaryWanInterface,
    DecomissionDevice,
]
register_jobs(*jobs)
