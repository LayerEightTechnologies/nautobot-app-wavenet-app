"""DiffSync adatper for Layer8."""

from diffsync import DiffSync
from diffsync.exceptions import ObjectAlreadyExists
from ..models.base import dcim
from nautobot.dcim.models import Location, DeviceType, Manufacturer
from ....models import AuvikTenantBuildingRelationship, AuvikTenant, AuvikDeviceModels, AuvikDeviceVendors
from ....helpers.auvik_api import auvik_api, auvik_api_network, auvik_api_device, auvik_api_interface, fetch_all_pages
import re


class AuvikAdapter(DiffSync):
    """DiffSync adapter using layer8_auvik_api_client to communicate to Auvik API."""

    namespace = dcim.Namespace
    vlangroup = dcim.VLANGroup
    vlan = dcim.VLAN
    prefix = dcim.Prefix
    ipaddr = dcim.IPAddress
    device = dcim.Device
    interface = dcim.Interface
    cable = dcim.Cable

    top_level = (
        "namespace",
        "vlangroup",
        "device",
        "cable",
    )

    def __init__(self, *args, job, sync=None, building_id, **kwargs):
        """Initialize AuvikAdapter."""
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.building_id = building_id
        self.auvik = auvik_api()
        try:
            self.building_name = Location.objects.get(
                id=AuvikTenantBuildingRelationship.objects.get(id=self.job.building_to_sync.id).building.id
            )
            self.auvik_tenant_id = AuvikTenant.objects.get(
                id=AuvikTenantBuildingRelationship.objects.get(id=self.job.building_to_sync.id).auvik_tenant_id
            ).auvik_tenant_id
        except Location.DoesNotExist:
            self.job.logger.error(f"Building ID {self.building_id} does not exist in Nautobot.")
            self.building_name = None
            return

        # Global data structures for storing device and interface information
        self.device_data = {}
        self.device_map = {}
        self.interface_data = {}

        try:
            self.job.logger.info("Retrieving devices from Auvik...")
            device_api_instance = auvik_api_device(self.auvik)
            auvik_tenant_id = self.auvik_tenant_id
            params = {
                "tenants": auvik_tenant_id,
                "page_first": 100,
            }
            devices = fetch_all_pages(device_api_instance, "read_multiple_device_info", **params)
            self.device_data = devices

            for device in devices:
                self.device_map[device.id] = device
        except Exception as err:
            self.job.logger.error(f"Error fetching devices from Auvik: {err}")

        try:
            self.job.logger.info("Retrieving interfaces from Auvik...")
            interface_api_instance = auvik_api_interface(self.auvik)
            auvik_tenant_id = self.auvik_tenant_id
            for device in self.device_data:
                device_id = device.id
                params_ethernet = {
                    "filter_parent_device": device_id,
                    "filter_interface_type": "ethernet",
                    "page_first": 1000,
                    "tenants": auvik_tenant_id,
                }
                interfaces_ethernet = fetch_all_pages(
                    interface_api_instance, "read_multiple_interface_info", **params_ethernet
                )

                params_link_aggregation = {
                    "filter_parent_device": device_id,
                    "filter_interface_type": "linkAggregation",
                    "page_first": 1000,
                    "tenants": auvik_tenant_id,
                }
                interfaces_link_aggregation = fetch_all_pages(
                    interface_api_instance, "read_multiple_interface_info", **params_link_aggregation
                )

                self.interface_data[device_id] = interfaces_ethernet + interfaces_link_aggregation
        except Exception as err:
            self.job.logger.error(f"Error fetching interfaces from Auvik: {err}")

    def load_namespaces(self):
        """Load namespace for building from Auvik."""
        self.job.logger.info(f"auvik_tenant_id: {self.job.building_to_sync}")
        self.job.logger.info("Loading namespaces from Auvik...")

        namespace = self.namespace(
            name=f"{self.building_name}",
            description=f"{self.building_name} namespace",
        )
        try:
            self.add(namespace)
            if self.job.debug:
                self.job.logger.info(f"Added Auvik Namespace: ```{namespace.__dict__}```")
        except ObjectAlreadyExists as err:
            self.job.logger.info(f"Namespace already exists: {err}")

    def load_vlangroups(self):
        """Load VLAN Group for building from Auvik."""
        self.job.logger.info("Loading VLAN Groups from Auvik...")
        vlangroup_name = f"{self.building_name} VLANs"
        vlangroup = self.vlangroup(
            name=vlangroup_name,
            location__name=self.building_name.name,
        )
        try:
            self.add(vlangroup)
            if self.job.debug:
                self.job.logger.info(f"Added Auvik VLAN Group: ```{vlangroup.__dict__}```")
        except ObjectAlreadyExists as err:
            self.job.logger.info(f"VLAN Group already exists: {err}")

    def load_vlans(self):
        """Load VLANs for building from Auvik API."""
        self.job.logger.info("Loading VLANs from Auvik...")
        api_instance = auvik_api_network(self.auvik)
        auvik_tenant_id = self.auvik_tenant_id
        params = {
            "filter_network_type": "vlan",
            "tenants": auvik_tenant_id,
            "page_first": 100,
        }
        auvik_vlans = fetch_all_pages(api_instance, "read_multiple_network_info", **params)

        for _vlan in auvik_vlans:
            vlan_name = getattr(_vlan.attributes, "network_name", None)
            if vlan_name is None or vlan_name == "":
                vlan_name = getattr(_vlan.attributes, "description", None)
                if vlan_name is None or vlan_name == "":
                    if self.job.debug:
                        self.job.logger.error("VLAN name is not set in Auvik. Skipping.")
                    continue
            try:
                vlan_id = int(getattr(_vlan.attributes, "description").split()[1])
            except ValueError:
                if self.job.debug:
                    self.job.logger.error("VLAN ID is not a valid integer. Skipping.")
                continue
            if self.job.debug:
                self.job.logger.info(f"Loading VLAN: {vlan_name} with ID {vlan_id}")

            vlan = self.vlan(
                name=vlan_name,
                vid=vlan_id,
                vlangroup=f"{self.building_name} VLANs",
                location__name=self.building_name.name,
            )
            try:
                self.add(vlan)
                _vlangroup = self.get(self.vlangroup, f"{self.building_name} VLANs")
                _vlangroup.add_child(vlan)
                if self.job.debug:
                    self.job.logger.info(f"Added Auvik VLAN: ```{vlan.__dict__}```")
            except ObjectAlreadyExists as err:
                self.job.logger.info(f"VLAN already exists: {err}")

    def load_prefixes(self):
        """Load prefixes for building from Auvik API."""
        self.job.logger.info("Loading prefixes from Auvik...")
        api_instance = auvik_api_network(self.auvik)
        auvik_tenant_id = self.auvik_tenant_id
        params = {
            "filter_network_type": "routed",
            "tenants": auvik_tenant_id,
            "page_first": 100,
        }
        auvik_prefixes = fetch_all_pages(api_instance, "read_multiple_network_info", **params)

        for _prefix in auvik_prefixes:
            prefix_name = getattr(_prefix.attributes, "description", None)
            prefix_description = getattr(_prefix.attributes, "network_name", None)
            if self.job.debug:
                self.job.logger.info(f"Loading Prefix: {prefix_name}")

            prefix = self.prefix(
                prefix=prefix_name,
                description=prefix_description,
                namespace=f"{self.building_name}",
                status="active",
                type="network",
            )
            try:
                self.add(prefix)
                _namespace = self.get(self.namespace, f"{self.building_name}")
                _namespace.add_child(prefix)
                if self.job.debug:
                    self.job.logger.info(f"Added Auvik Prefix: ```{prefix.__dict__}```")
            except ObjectAlreadyExists as err:
                self.job.logger.info(f"Prefix already exists: {err}")

    def load_devices(self):
        """Load devices for building from Auvik API."""
        self.job.logger.info("Loading devices from Auvik...")
        auvik_devices = self.device_data

        # Create a dictionary of device names to device IDs for use in creating device interconnections
        device_names = {}

        if self.job.debug:
            self.job.logger.info("Loading devices from Auvik API.")

        for _device in auvik_devices:
            device_names[_device.id] = _device.attributes.device_name
            if self.job.debug:
                self.job.logger.info(f"Loading Device: {_device.attributes.device_name}")

            # TODO: We need to force an error instead of continuing if a device make or model cannot be
            # found in Nautobot. This is to ensure that we don't skip devices that are missing this information.
            # We should also create a map of devices that have been skipped, so we can also skip trying to import interfaces for them.
            # Log errors even if we're not in debug mode, to make it clear why the sync is failing.
            if _device.attributes.make_model is None or _device.attributes.vendor_name is None:
                if self.job.debug:
                    self.job.logger.warning(
                        f"Device {_device.attributes.device_name} does not have a vendor or model in Auvik. Skipping. Device attributes received from Auvik: f{_device.attributes}"
                    )
                continue

            try:
                _dt = DeviceType.objects.get(
                    id=AuvikDeviceModels.objects.get(
                        auvik_model_name=_device.attributes.make_model
                    ).nautobot_device_type_id
                )
            except DeviceType.DoesNotExist:
                if self.job.debug:
                    self.job.logger.warning(
                        f"Device Type for {_device.attributes.make_model} does not exist in Nautobot. Skipping device {_device.attributes.device_name}."
                    )
                continue
            except AuvikDeviceModels.DoesNotExist:
                if self.job.debug:
                    self.job.logger.warning(
                        f"Mapping for Auvik model {_device.attributes.make_model} does not exist in Nautobot. Skipping device {_device.attributes.device_name}."
                    )
                continue
            try:
                _dmanufacturer = Manufacturer.objects.get(
                    id=AuvikDeviceVendors.objects.get(
                        auvik_vendor_name=_device.attributes.vendor_name
                    ).nautobot_manufacturer_id
                )
            except Manufacturer.DoesNotExist:
                if self.job.debug:
                    self.job.logger.warning(
                        f"Manufacturer for {_device.attributes.vendor_name} does not exist in Nautobot. Skipping device {_device.attributes.device_name}."
                    )
                continue
            except AuvikDeviceVendors.DoesNotExist:
                if self.job.debug:
                    self.job.logger.warning(
                        f"Mapping for Auvik vendor {_device.attributes.vendor_name} does not exist in Nautobot. Skipping device {_device.attributes.device_name}."
                    )
                continue

            monitoring_profile = {
                "monitoredBy": "auvik",
                "deviceHostname": _device.attributes.device_name,
                "monitoringFields": {
                    "deviceId": _device.id,
                    "deviceSerialNumber": _device.attributes.serial_number,
                },
            }

            role = "Unknown"

            if "CorS".lower() in _device.attributes.device_name.lower():
                role = "Core Switch"
            elif "Dist".lower() in _device.attributes.device_name.lower():
                role = "Distribution Switch"
            elif "-AP".lower() in _device.attributes.device_name.lower():
                role = "Wireless Access Point"
            elif (
                "CorR".lower() in _device.attributes.device_name.lower()
                or "CorF".lower() in _device.attributes.device_name.lower()
            ):
                role = "Core Gateway"
            elif (
                "AccS".lower() in _device.attributes.device_name.lower()
                or "VSS".lower() in _device.attributes.device_name.lower()
            ):
                role = "Access Switch"
            elif (
                "UPS".lower() in _device.attributes.device_name.lower()
                or "-PP".lower() in _device.attributes.device_name.lower()
                or "APTS".lower() in _device.attributes.device_name.lower()
                or "CorPP".lower() in _device.attributes.device_name.lower()
            ):
                role = "UPS"
            try:
                device = self.device(
                    name=_device.attributes.device_name,
                    device_type=_dt.__str__(),
                    manufacturer=_dmanufacturer.__str__(),
                    location__name=self.building_name.name,
                    serial=_device.attributes.serial_number,
                    monitoring_profile=monitoring_profile,
                    role=role,
                )
                self.add(device)
            except ObjectAlreadyExists as err:
                self.job.logger.error(
                    f"Device already imported from Auvik - this is a duplicate: {device.name} ({device.serial}), Err: ({err})"
                )
                continue

            # # Pull interface list from Auvik API to populate device connections dictionary
            # # This will be used to create device interconnections later
            # params = {
            #     "device_id": _device.id,
            # }
            # device_interfaces = fetch_all_pages(api_instance, "read_multiple_interfaces", device_id=_device.id)

            # Load mgmt0 interface for every device
            interface = self.interface(
                name="mgmt0",
                description="Management Interface",
                device__name=_device.attributes.device_name,
                device__location__name=self.building_name.name,
                type="virtual",
                status="Active",
                mgmt_only=True,
            )
            self.add(interface)
            device.add_child(interface)

            # Load IP Address for mgmt0 interface

            if _device.attributes.ip_addresses is not None:
                regex = r"10\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|[0-9])\.10\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]?|[0-9])"
                for _ip in _device.attributes.ip_addresses:
                    match = re.search(regex, _ip)
                    if match:
                        try:
                            self.job.logger.info(f"Found IP Mgmt Address: {_ip}, adding to DiffSync.")
                            _mgmt_ip = match.group()
                            ipaddr = self.ipaddr(
                                address=_mgmt_ip,
                                namespace=self.building_name.name,
                                interface__name="mgmt0",
                                status="Active",
                                device=_device.attributes.device_name,
                            )
                            self.add(ipaddr)
                            interface.add_child(ipaddr)

                        except ObjectAlreadyExists as err:
                            self.job.logger.info(f"IP Address already added to DiffSync, skipping: {err}")

            if self.job.debug:
                self.job.logger.info(f"Added Auvik Device: ```{device.__dict__}```")

        if self.job.debug:
            identifiers = tuple(device.get_identifiers() for device in self.get_all("device"))
            print(f"Device Identifiers for DiffSync: ```{identifiers}```")

    # Implementation of (parent) load_devices, (-> child) load_interfaces and (-> child) load_ipaddrs methods
    # We are going to load the interfaces for every device, and we're going to create interfaces that haven't already been created
    # by the device type template.

    def load_interfaces(self):
        """Load interfaces for building from Auvik API."""
        self.job.logger.info("Loading interfaces from Auvik...")
        for device_id, interfaces in self.interface_data.items():
            for interface in interfaces:
                interface_name = interface.attributes.interface_name
                if interface_name == "me0":
                    continue

                interface_type = interface.attributes.interface_type
                if interface_type == "ethernet":
                    interface_type = "1000base-t"
                elif interface_type == "linkAggregation":
                    interface_type = "virtual"

                device_name = self.device_map[device_id].attributes.device_name
                device = self.get(
                    self.device, f"{device_name}__{self.building_name.name}"
                ) 

                monitoring_profile = {
                    "monitoredBy": "auvik",
                    "monitoringFields": {
                        "interfaceId": interface.id,
                    },
                }
                try:
                    # Load interface for every device
                    interface = self.interface(
                        name=interface_name,
                        device__name=device_name,
                        device__location__name=self.building_name.name,
                        type=interface_type,
                        monitoring_profile=monitoring_profile,
                        status="Active",
                    )
                    self.add(interface)
                    device.add_child(interface)

                    if self.job.debug:
                        self.job.logger.info(f"Added Auvik Interface: ```{interface.__dict__}```")
                except ObjectAlreadyExists as err:
                    self.job.logger.info(f"Interface already exists: {err}, skipping {interface.__dict__}")

                # # Load IP Address for every interface
                # if interface.attributes.ip_addresses is not None:
                #     for _ip in interface.attributes.ip_addresses:
                #         ipaddr = self.ipaddr(
                #             address=_ip,
                #             namespace=self.building_name.name,
                #             interface__name=interface_name,
                #             status="Active",
                #             device=device_name,
                #         )
                #         self.add(ipaddr)
                #         interface.add_child(ipaddr)

    def load_cables(self):
        """Load cables for building from Auvik API."""
        self.job.logger.info("Loading cables from Auvik...")
        interface_connections = self.get_interface_connections()
        for _connection in interface_connections:
            try:
                cable = self.cable(
                    from_device=_connection["from"]["device_name"],
                    from_interface=_connection["from"]["interface_name"],
                    to_device=_connection["to"]["device_name"],
                    to_interface=_connection["to"]["interface_name"],
                )
                self.add(cable)
                if self.job.debug:
                    self.job.logger.info(f"Added Auvik Cable: ```{cable.__dict__}```")
            except ObjectAlreadyExists as err:
                self.job.logger.info(f"Cable already exists: {err}")

    def find_device_id_for_interface(self, interface_id, processed_data):
        """
        Search through processed_data to find the device_id for a given interface_id.

        :param interface_id: The interface ID for which to find the device ID.
        :param processed_data: The processed data structure containing device and interface information.
        :return: The device_id that the interface belongs to, or None if not found.
        """
        for device_id, interfaces in processed_data.items():
            if interface_id in interfaces:
                return device_id
        return None

    def get_interface_connections(self):
        """Get interface connections from Auvik API data."""
        devices = self.device_data
        device_info = {}
        device_interfaces = {}
        device_interface_names = {}

        # Populate data from API
        for device in devices:
            device_id = device.id
            device_name = device.attributes.device_name
            device_interfaces[device_id] = []

            device_info[device_id] = {
                "device_name": device_name,
                "device_id": device_id,
                "interfaces": [],
            }

            interfaces = self.interface_data[device_id]

            for interface in interfaces:
                device_interface_names[interface.id] = {
                    "name": interface.attributes.interface_name,
                    "device_id": device_id,
                    "device_name": device_name,
                }
                device_interfaces[device_id].append(interface)

        # Process the interfaces to build the connections
        for device in devices:
            device_id = device.id
            device_name = device.attributes.device_name

            for interface in device_interfaces[device_id]:
                connected_to = []
                for connected_to_id in interface.relationships.connected_to.data:
                    # Only consider interfaces that are in the device_interface_names dictionary
                    if connected_to_id.id in device_interface_names:
                        connected_to.append(
                            {
                                "connected_interface_id": connected_to_id.id,
                                "connected_interface_name": device_interface_names.get(connected_to_id.id, "Unknown")[
                                    "name"
                                ],
                                "connected_device_id": device_interface_names.get(connected_to_id.id, "Unknown")[
                                    "device_id"
                                ],
                                "connected_device_name": device_interface_names.get(connected_to_id.id, "Unknown")[
                                    "device_name"
                                ],
                            }
                        )
                # Only add interfaces that have exactly one connection
                # Ignore interfaces without connections
                # Ignore interfaces with multiple connections because they don't represent physical connections (cables)
                if len(connected_to) == 1:
                    device_info[device_id]["interfaces"].append(
                        {
                            "interface_id": interface.id,
                            "interface_name": interface.attributes.interface_name,
                            "connected_to": connected_to,
                        }
                    )

        # Consolidate the connections
        device_connections = []
        for device_id, device_data in device_info.items():
            for interface in device_data["interfaces"]:
                # Ignore me0 interface as this is not a physical connection
                if interface["interface_name"] == "me0":
                    continue
                # If a physical interface is connected to me0, find the correct connection
                if interface["connected_to"][0]["connected_interface_name"] == "me0":
                    correct_connected_to = next(
                        (iface for iface in device_data["interfaces"] if iface["interface_name"] == "me0"),
                        None,
                    )
                    if correct_connected_to is None:
                        continue
                    else:
                        correct_connected_to = correct_connected_to["connected_to"]
                    interface["connected_to"] = correct_connected_to
                device_connections.append(
                    {
                        "from": {
                            "device_id": device_id,
                            "device_name": device_data["device_name"],
                            "interface_id": interface["interface_id"],
                            "interface_name": interface["interface_name"],
                        },
                        "to": {
                            "device_id": interface["connected_to"][0]["connected_device_id"],
                            "device_name": interface["connected_to"][0]["connected_device_name"],
                            "interface_id": interface["connected_to"][0]["connected_interface_id"],
                            "interface_name": interface["connected_to"][0]["connected_interface_name"],
                        },
                    }
                )

        # Remove duplicates from the connections, regardless of direction
        seen = set()
        unique_connections = []
        duplicates_found = 0

        for connection in device_connections:
            conn_tuple = frozenset(
                {
                    (
                        connection["from"]["device_id"],
                        connection["from"]["interface_id"],
                    ),
                    (connection["to"]["device_id"], connection["to"]["interface_id"]),
                }
            )
            if conn_tuple not in seen:
                seen.add(conn_tuple)
                unique_connections.append(connection)
            else:
                duplicates_found += 1
                pass

        return unique_connections

    # def get_interface_connections(self):
    #     """Get interface connections from Auvik API."""
    #     # Pull devices for building (based on tenant ID) from Auvik API
    #     processed_data = {}

    #     # api_instance_devices = auvik_api_device(self.auvik)
    #     # auvik_tenant_id = AuvikTenant.objects.get(id=self.job.building_to_sync).auvik_tenant_id
    #     # params = {
    #     #     "tenants": auvik_tenant_id,
    #     #     "page_first": 1000,
    #     # }
    #     # devices = fetch_all_pages(api_instance_devices, "read_multiple_device_info", **params)
    #     devices = self.device_data

    #     # For each device, pull interfaces and connected_to interfaces from Auvik API
    #     device_names = {}
    #     for device in devices:
    #         device_id = device.id
    #         device_name = device.attributes.device_name
    #         device_names[device_id] = device_name

    #         # api_instance_interfaces = auvik_api_interface(self.auvik)
    #         # params = {
    #         #     "filter_parent_device": device_id,
    #         #     "filter_interface_type": "ethernet",
    #         #     "page_first": 1000,
    #         # }
    #         # interfaces = fetch_all_pages(api_instance_interfaces, "read_multiple_interface_info", **params)
    #         interfaces = self.interface_data[device_id]

    #         for interface in interfaces:
    #             if interface.relationships.connected_to.data:
    #                 device_id = interface.relationships.parent_device.data.id
    #                 interface_id = interface.id
    #                 interface_name = interface.attributes.interface_name

    #                 # Initialize the device in the dictionary if it doesn't already exist
    #                 if device_id not in processed_data:
    #                     processed_data[device_id] = {}

    #                 # Store the connected interface IDs within the structured dictionary
    #                 for connected_interface in interface.relationships.connected_to.data:
    #                     connected_interface_id = connected_interface.id
    #                     if interface_id not in processed_data[device_id]:
    #                         processed_data[device_id][interface_id] = {
    #                             "interface_name": interface_name,
    #                             "connected_to": [],
    #                         }

    #                     processed_data[device_id][interface_id]["connected_to"].append(connected_interface_id)

    #     # Create a dictionary of interface names for use in creating device interconnections
    #     interface_names = {}
    #     for device_id, interfaces in processed_data.items():
    #         for interface_id, interface_details in interfaces.items():
    #             interface_names[interface_id] = interface_details["interface_name"]

    #     connections = []
    #     processed_connections = set()

    #     # Create a list of connections based on the processed data
    #     for device_id, interfaces in processed_data.items():
    #         for interface_id, interface_details in interfaces.items():
    #             from_device_id = device_id
    #             from_device_name = device_names.get(device_id, "Unknown")
    #             from_interface_id = interface_id
    #             from_interface_name = interface_names.get(interface_id, "Unknown")

    #             for connected_interface_id in interface_details["connected_to"]:
    #                 to_device_id = self.find_device_id_for_interface(connected_interface_id, processed_data)
    #                 to_device_name = device_names.get(to_device_id, "Unknown")
    #                 to_interface_id = connected_interface_id
    #                 to_interface_name = interface_names.get(connected_interface_id, "Unknown")

    #                 # Create a sorted tuple of interface IDs as a unique identifier for the connection
    #                 connection_identifier = tuple(sorted([from_interface_id, to_interface_id]))

    #                 if connection_identifier not in processed_connections:
    #                     processed_connections.add(connection_identifier)

    #                     connection = {
    #                         "from": {
    #                             "device_id": from_device_id,
    #                             "device_name": from_device_name,
    #                             "interface_id": from_interface_id,
    #                             "interface_name": from_interface_name,
    #                         },
    #                         "to": {
    #                             "device_id": to_device_id,
    #                             "device_name": to_device_name,
    #                             "interface_id": to_interface_id,
    #                             "interface_name": to_interface_name,
    #                         },
    #                     }

    #                     # Add the connection to the list
    #                     connections.append(connection)

    #     # Merge connections where there are multiple records for the same device pair
    #     # (where one connection is represented by two pairs, each including an arbitrary "me0" interface)
    #     connections_dict = {}
    #     for connection in connections:
    #         from_id, to_id = connection["from"]["interface_id"], connection["to"]["interface_id"]

    #         if from_id is None or to_id is None:
    #             continue

    #         device_pair = tuple(sorted([from_id, to_id]))

    #         if device_pair not in connections_dict:
    #             connections_dict[device_pair] = []

    #         connections_dict[device_pair].append(connection)

    #     merged_connections = []
    #     for device_pair, pair_connections in connections_dict.items():
    #         merged_conn = {"from": {}, "to": {}}
    #         for conn in pair_connections:
    #             if conn["from"]["interface_name"] != "me0" and conn["from"]["device_id"] is not None:
    #                 merged_conn["from"] = conn["from"]
    #             if conn["to"]["interface_name"] != "me0" and conn["to"]["device_id"] is not None:
    #                 merged_conn["to"] = conn["to"]

    #         if merged_conn["from"] and merged_conn["to"]:
    #             merged_connections.append(merged_conn)

    #     connections = merged_connections

    #     return connections

    def load(self):
        """Load data from Auvik."""
        self.load_namespaces()
        self.load_vlangroups()
        self.load_vlans()
        self.load_prefixes()
        self.load_devices()
        self.load_interfaces()
        self.load_cables()
