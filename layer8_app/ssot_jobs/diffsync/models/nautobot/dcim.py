"""DiffSyncModel DCIM subclasses for Nautobot data sync."""

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Location as OrmLocation
from nautobot.dcim.models import LocationType as OrmLocationType
from nautobot.ipam.models import Namespace as OrmNamespace
from nautobot.extras.models import Status as OrmStatus
from nautobot.ipam.models import VLANGroup as OrmVLANGroup
from nautobot.ipam.models import VLAN as OrmVLAN
from nautobot.ipam.models import Prefix as OrmPrefix
from nautobot.dcim.models import Device as OrmDevice
from nautobot.dcim.models import DeviceType as OrmDeviceType
from nautobot.dcim.models import Manufacturer as OrmManufacturer
from nautobot.dcim.models import Cable as OrmCable
from nautobot.extras.models import Role as OrmRole
from nautobot.dcim.models import Interface as OrmInterface
from nautobot.ipam.models import IPAddress as OrmIPAddress
from nautobot.ipam.models import IPAddressToInterface


from ..base.dcim import Building
from ..base.dcim import Room
from ..base.dcim import Namespace
from ..base.dcim import VLANGroup
from ..base.dcim import VLAN
from ..base.dcim import Prefix
from ..base.dcim import Device
from ..base.dcim import Interface
from ..base.dcim import IPAddress
from ..base.dcim import Cable


class NautobotBuilding(Building):
    """Nautobot Building model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Building object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Building: {ids['name']}")
        loc_type = OrmLocationType.objects.get_or_create(name="Building")[0]
        status = OrmStatus.objects.get(name="Planned")
        new_building = OrmLocation(name=ids["name"], status=status, location_type=loc_type)
        new_building.validated_save()
        if attrs.get("external_id"):
            new_building.custom_field_data.update({"external_id": attrs["external_id"]})
            # TODO: Add technical_reference to custom fields
            # TODO: Add longitude and latitude values to building
            new_building.validated_save()
        diffsync.building_map[ids["name"]] = new_building.id
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Building object in Nautobot."""
        _building = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Building: {_building.name}")
        """
        Only update status if status__name is Old Building, indicating a retired
        building, otherwise leave as is
        """
        if attrs.get("status__name"):
            _building.status = OrmStatus.objects.get(name=attrs["status__name"])
        if attrs.get("longitude"):
            _building.longitude = attrs["longitude"]
        if attrs.get("latitude"):
            _building.latitude = attrs["latitude"]
        if attrs.get("technical_reference"):
            _building.custom_field_data.update({"technical_reference": attrs["technical_reference"]})
        if attrs.get("external_id"):
            _building.custom_field_data.update({"external_id": attrs["external_id"]})
        _building.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Building object in Nautobot."""
        # _building = OrmLocation.objects.get(id=self.uuid)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Building: {_building.name}")
        # _building.delete()
        # return super().delete()
        pass


class NautobotRoom(Room):
    """Nautobot Room model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Room object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Room: {ids['name']}")
        try:
            loc_type = OrmLocationType.objects.get_or_create(name="Room")[0]
            status = OrmStatus.objects.get(name="Planned")
            new_room = OrmLocation(name=ids["name"], status=status, location_type=loc_type)
            # new_room.validated_save()
            if ids.get("external_id"):
                new_room.custom_field_data.update({"external_id": ids["external_id"]})
                # new_room.validated_save()
            if ids.get("parent__name"):
                parent = OrmLocation.objects.get(name=ids["parent__name"])
                new_room.parent = parent
                # new_room.validated_save()
            new_room.validated_save()
            if ids["parent__name"] not in diffsync.room_map:
                diffsync.room_map[ids["parent__name"]] = {}
            diffsync.room_map[ids["parent__name"]][ids["name"]] = new_room.id
        except ValidationError as e:
            diffsync.job.logger.error(
                f"Failed to create Room: {e} - {ids['name']} - {ids['parent__name']} - {ids['external_id']}"
            )
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Room object in Nautobot."""
        _room = OrmLocation.objects.get(id=self.uuid)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Room: {_room.name}")
        # We wouldn't update any room fields, perhaps just the status if the room is marked as inactive?
        if attrs.get("status__name"):
            if attrs["status__name"] == "Retired":
                _room.status = OrmStatus.objects.get(name="Retired")
        _room.validated_save()
        return super().update(attrs)

    def delete(self):
        """
        Delete Room object in Nautobot.

        This would require a check to see if there are any dependent objects (e.g., devices)
        If there are dependent objects, we would need to re-assign the dependent objects to another location,
        such as the parent building. Perhaps we would need to modify the status of the device to indicate that
        the device was in a deleted room.
        """
        # _room = OrmLocation.objects.get(id=self.uuid)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Room: {_room.name}")
        # _room.delete()
        # return super().delete()
        pass


class NautobotNamespace(Namespace):
    """Nautobot Namespace model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Namespace object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Namespace: {ids['name']}")
        try:
            new_namespace = OrmNamespace(name=ids["name"], description=attrs.get("description"))
            new_namespace.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(f"Failed to create Namespace: {e} - {ids['name']} - {attrs['description']}")
            return None
        # diffsync.namespace_map[ids["name"]] = new_namespace.id
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Namespace object in Nautobot."""
        _namespace = OrmNamespace.objects.get(name=self.name)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Namespace: {_namespace.name}")
        if attrs.get("description"):
            _namespace.description = attrs["description"]
        _namespace.validated_save()
        return super().update(attrs)

    def delete(self):
        """Delete Namespace object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete namespaces and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _namespace = OrmNamespace.objects.get(name=self.name)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Namespace: {_namespace.name}")
        # _namespace.delete()
        # return super().delete()
        pass


class NautobotVLANGroup(VLANGroup):
    """Nautobot VLANGroup model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create VLANGroup object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating VLANGroup: {ids['name']}")
        try:
            new_vlangroup_location = OrmLocation.objects.get(name=attrs["location__name"])
            new_vlangroup = OrmVLANGroup(name=ids["name"], location=new_vlangroup_location)
            new_vlangroup.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(f"Failed to create VLANGroup: {e} - {ids['name']}")
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update VLANGroup object in Nautobot."""
        _vlangroup = OrmVLANGroup.objects.get(name=self.name)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating VLANGroup: {_vlangroup.name}")
            return None
        return super().update(attrs)

    def delete(self):
        """Delete VLANGroup object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete VLANGroups and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _vlangroup = OrmVLANGroup.objects.get(name=self.name)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting VLANGroup: {_vlangroup.name}")
        # _vlangroup.delete()
        # return super().delete()
        pass


class NautobotVLAN(VLAN):
    """Nautobot VLAN model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create VLAN object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating VLAN: {ids['name']}")

        try:
            vlan_group = OrmVLANGroup.objects.get(name=ids["vlangroup"])
            status = OrmStatus.objects.get(name="Active")
            location = OrmLocation.objects.get(name=attrs["location__name"])
            new_vlan = OrmVLAN(
                name=ids["name"], vid=ids["vid"], vlan_group=vlan_group, status=status, location=location
            )
            new_vlan.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(f"Failed to create VLAN: {e} - {ids['name']}")
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update VLAN object in Nautobot."""
        _vlan = OrmVLAN.objects.get(name=self.name)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating VLAN: {_vlan.name}")
        return super().update(attrs)

    def delete(self):
        """Delete VLAN object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete VLANs and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _vlan = OrmVLAN.objects.get(name=self.name)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting VLAN: {_vlan.name}")
        # _vlan.delete()
        # return super().delete()
        pass


class NautobotPrefix(Prefix):
    """Nautobot Prefix model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Prefix object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Prefix: {ids['prefix']}")

        try:
            namespace = OrmNamespace.objects.get(name=ids["namespace"])
            status = OrmStatus.objects.get(name="Active")
            new_prefix = OrmPrefix(
                prefix=ids["prefix"],
                namespace=namespace,
                type=attrs["type"],
                status=status,
                description=attrs["description"],
            )
            new_prefix.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(f"Failed to create Prefix: {e} - {ids['prefix']}")
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Prefix object in Nautobot."""
        try:
            if self.diffsync.job.debug:
                self.diffsync.job.logger.info(f"Attempting to update prefix: {self.prefix}")
            _prefix = OrmPrefix.objects.get(prefix=self.prefix, namespace=self.namespace)
            if self.diffsync.job.debug:
                self.diffsync.job.logger.info(f"Retrieved Nautobot existing prefix: {_prefix.prefix}")
        except Exception as e:
            if self.diffsync.job.debug:
                self.diffsync.job.logger.info(f"Error when updating prefix: {self.prefix}, {e}")
            return None
        return super().update(attrs)

    def delete(self):
        """Delete Prefix object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete Prefixes and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _prefix = OrmPrefix.objects.get(prefix=self.prefix)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Prefix: {_prefix.prefix}")
        # _prefix.delete()
        # return super().delete()
        pass


class NautobotDevice(Device):
    """Nautobot Device model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Device object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating Device: {ids['name']}")
        try:
            location = OrmLocation.objects.get(name=ids["location__name"])
            status = OrmStatus.objects.get(name="Active")
            manufacturer = OrmManufacturer.objects.get(name=attrs["manufacturer"])
            device_type = OrmDeviceType.objects.get(model=attrs["device_type"], manufacturer=manufacturer)
            new_device = OrmDevice(
                name=ids["name"],
                device_type=device_type,
                location=location,
                status=status,
            )
            if attrs.get("serial") and attrs["serial"] is not None:
                new_device.serial = attrs["serial"]
            if attrs.get("monitoring_profile"):
                new_device.custom_field_data.update({"monitoring_profile": attrs["monitoring_profile"]})
            if attrs.get("role"):
                role = OrmRole.objects.get_or_create(name=attrs["role"])[0]
                role.content_types.add(ContentType.objects.get_for_model(OrmDevice))
                new_device.role = role
            new_device.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(f"Failed to create Device: {e} - {ids['name']}")
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Device object in Nautobot."""
        self.diffsync.job.logger.info(f"Attempting device update in Nautobot for device with name: {self.name} ")
        try:
            _device = OrmDevice.objects.get(name=self.name)
            if self.diffsync.job.debug:
                self.diffsync.job.logger.info(f"Updating Device: {_device.name}")
            # TODO - Add logic to update monitoring profile
            if attrs.get("monitoring_profile"):
                _device.custom_field_data.update({"monitoring_profile": attrs["monitoring_profile"]})
                _device.validated_save()
                if self.diffsync.job.debug:
                    self.diffsync.job.logger.info(
                        f"Updated monitoring profile for device: {_device.name}: ```{attrs['monitoring_profile']}```"
                    )
            return super().update(attrs)
        except Exception as e:
            self.diffsync.job.logger.error(
                f"Failed to update Device monitoring profile for {_device.name}: {e} - {_device}"
            )

    def delete(self):
        """Delete Device object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete Devices and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _device = OrmDevice.objects.get(name=self.name)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Device: {_device.name}")
        # _device.delete()
        # return super().delete()
        pass


class NautobotInterface(Interface):
    """Nautobot Interface model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Interface object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(
                f"Creating Interface if it doesn't already exist: {ids['name']} - {ids['device__name']} - {ids['device__location__name']}"
            )

        try:
            existing_interface = OrmInterface.objects.get(
                name=ids["name"], device__name=ids["device__name"], device__location__name=ids["device__location__name"]
            )
            if attrs.get("monitoring_profile"):
                existing_interface.custom_field_data.update({"monitoring_profile": attrs["monitoring_profile"]})
                existing_interface.validated_save()
                if diffsync.job.debug:
                    diffsync.job.logger.info(
                        f"Updated monitoring profile for existing interface: {existing_interface.name} on {existing_interface.device.name} at {existing_interface.device.location.name}: ```{attrs['monitoring_profile']}```"
                    )
            if diffsync.job.debug:
                diffsync.job.logger.info(
                    f"Interface already exists: {existing_interface.name}, potentially from Device Type template, not attempting to create again"
                )
        except OrmInterface.DoesNotExist:
            try:
                device = OrmDevice.objects.get(name=ids["device__name"], location__name=ids["device__location__name"])
                status = OrmStatus.objects.get(name=attrs["status"])
                if ids["name"] != "mgmt0":
                    status = OrmStatus.objects.get(
                        name="Planned"
                    )  # Set status to Planned for new interfaces from Auvik, because they will need to be validated.
                if attrs["description"] is None:
                    attrs["description"] = (
                        "Interface created by Auvik Sync, please validate and update/remove interface status and this notice once complete."
                    )
                new_interface = OrmInterface(
                    name=ids["name"],
                    device=device,
                    description=attrs["description"],
                    mgmt_only=attrs["mgmt_only"],
                    status=status,
                    type=attrs["type"],
                )
                if attrs.get("monitoring_profile"):
                    new_interface.custom_field_data.update({"monitoring_profile": attrs["monitoring_profile"]})
                new_interface.validated_save()
                if diffsync.job.debug:
                    diffsync.job.logger.info(f"Interface does not already exist, created: {ids['name']}")
            except ValidationError as e:
                diffsync.job.logger.error(f"Failed to create Interface: {e} - {ids['name']}")
                return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Interface object in Nautobot."""
        try:
            _interface = OrmInterface.objects.get(
                name=self.name, device__name=self.device__name, device__location__name=self.device__location__name
            )
        except OrmInterface.DoesNotExist:
            self.diffsync.job.logger.error(
                f"Failed to update Interface: {self.name} on {self.device__name} at {self.device__location__name}"
            )
            return None
        self.diffsync.job.logger.info("Running interface update, hopefully with monitoring profile")
        if attrs.get("monitoring_profile"):
            self.diffsync.job.logger.info("Updating monitoring profile")
            _interface.custom_field_data.update({"monitoring_profile": attrs["monitoring_profile"]})
            _interface.validated_save()
            if self.diffsync.job.debug:
                self.diffsync.job.logger.info(
                    f"Updated monitoring profile for interface: {_interface.name} on {_interface.device.name} at {_interface.device.location.name}: ```{attrs['monitoring_profile']}```"
                )
        else:
            self.diffsync.job.logger.info("No monitoring profile to update")
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info("NOT Updating Anything else on existing interface")
        return super().update(attrs)

    def delete(self):
        """Delete Interface object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete Interfaces and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _interface = OrmInterface.objects.get(name=self.name)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Interface: {_interface.name}")
        # _interface.delete()
        # return super().delete()
        pass


class NautobotIPAddress(IPAddress):
    """Nautobot IPAddress model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create IPAddress object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(f"Creating IPAddress: {ids['address']}")

        try:
            namespace = OrmNamespace.objects.get(name=ids["namespace"])
            status = OrmStatus.objects.get(name=attrs["status"])
            try:
                existing_ip = OrmIPAddress.objects.get(address=ids["address"])
                ipaddress = existing_ip
                diffsync.job.logger.info(f"IPAddress already exists: {existing_ip.address}, skipping")
            except OrmIPAddress.DoesNotExist:
                try:
                    new_ipaddress = OrmIPAddress(
                        address=ids["address"],
                        namespace=namespace,
                        status=status,
                    )
                    new_ipaddress.validated_save()
                    ipaddress = new_ipaddress

                except ValidationError as e:
                    diffsync.job.logger.error(f"Failed to create IPAddress: {e} - {ids['address']}")
                    return None

                except Exception as e:
                    diffsync.job.logger.error(f"Failed to create IPAddress: {e} - {ids['address']}")
                    return None
        except Exception as e:
            diffsync.job.logger.error(f"Failed to create IPAddress: {e} - {ids['address']}")
            return None

        try:
            ip_interface = OrmInterface.objects.get(name=attrs["interface__name"], device__name=attrs["device"])
            diffsync.job.logger.info(f"Assigning IP to interface: {ip_interface.name}")
            assign_ip = IPAddressToInterface.objects.create(
                ip_address=ipaddress, interface=ip_interface, vm_interface=None
            )
            assign_ip.validated_save()
            assign_ip.interface.device.primary_ip4 = ipaddress
            assign_ip.interface.device.validated_save()
        except Exception as e:
            diffsync.job.logger.error(f"Failed to assign IP to interface / set primary_ip4: {e}")

        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update IPAddress object in Nautobot."""
        _ipaddress = OrmIPAddress.objects.get(address=self.address)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating IPAddress: {_ipaddress.address}")
        return super().update(attrs)

    def delete(self):
        """Delete IPAddress object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete IPAddresses and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _ipaddress = OrmIPAddress.objects.get(address=self.address)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting IPAddress: {_ipaddress.address}")
        # _ipaddress.delete()
        # return super().delete()
        pass


class NautobotCable(Cable):
    """Nautobot Cable model."""

    @classmethod
    def create(cls, diffsync, ids, attrs):
        """Create Cable object in Nautobot."""
        if diffsync.job.debug:
            diffsync.job.logger.info(
                f"Creating Cable: {ids['from_device']}:{ids['from_interface']} <-> {ids['to_device']}:{ids['to_interface']}"
            )

        try:
            from_device = OrmDevice.objects.get(name=ids["from_device"])
        except OrmDevice.DoesNotExist:
            diffsync.job.logger.error(f"Failed to create Cable: Device {ids['from_device']} not found.")
            return None
        try:
            from_interface = OrmInterface.objects.get(name=ids["from_interface"], device=from_device)
        except OrmInterface.DoesNotExist:
            diffsync.job.logger.error(
                f"Failed to create Cable: Interface {ids['from_interface']} not found on Device {ids['from_device']}"
            )
            return None
        try:
            to_device = OrmDevice.objects.get(name=ids["to_device"])
        except OrmDevice.DoesNotExist:
            diffsync.job.logger.error(f"Failed to create Cable: Device {ids['to_device']} not found.")
            return None
        try:
            to_interface = OrmInterface.objects.get(name=ids["to_interface"], device=to_device)
        except OrmInterface.DoesNotExist:
            diffsync.job.logger.error(
                f"Failed to create Cable: Interface {ids['to_interface']} not found on Device {ids['to_device']}"
            )
            return None
        try:
            new_cable = OrmCable(
                termination_a_type=ContentType.objects.get(app_label="dcim", model="interface"),
                termination_a_id=from_interface.id,
                termination_b_type=ContentType.objects.get(app_label="dcim", model="interface"),
                termination_b_id=to_interface.id,
                status=OrmStatus.objects.get(name="Connected"),
            )
            new_cable.validated_save()
        except ValidationError as e:
            diffsync.job.logger.error(
                f"Failed to create Cable: {e} - {ids['from_device']}:{ids['from_interface']} <-> {ids['to_device']}:{ids['to_interface']}"
            )
            return None
        return super().create(ids=ids, diffsync=diffsync, attrs=attrs)

    def update(self, attrs):
        """Update Cable object in Nautobot."""
        _cable = OrmCable.objects.get(termination_a_id=self.termination_a_id, termination_b_id=self.termination_b_id)
        if self.diffsync.job.debug:
            self.diffsync.job.logger.info(f"Updating Cable: {_cable}")
        return super().update(attrs)

    def delete(self):
        """Delete Cable object in Nautobot."""
        # Disabled for now, as we probably a) don't want to delete Cables and b) would have to
        # delete them after all dependent objects are deleted.
        #
        # _cable = OrmCable.objects.get(termination_a_id=self.termination_a_id, termination_b_id=self.termination_b_id)
        # if self.diffsync.job.debug:
        #     self.diffsync.job.logger.info(f"Deleting Cable: {_cable}")
        # _cable.delete()
        # return super().delete()
        pass
