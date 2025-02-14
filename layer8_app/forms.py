"""Forms for the Layer 8 application."""

from django import forms
import re
from nautobot.apps.forms import BootstrapMixin
from nautobot.apps.forms import APISelect, DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.core.forms.fields import ExpandableNameField
from nautobot.core.forms.constants import ALPHANUMERIC_EXPANSION_PATTERN
from nautobot.core.forms.utils import expand_alphanumeric_pattern
from nautobot.dcim.models import Device, Interface, Location, DeviceType, LocationType


class CommaSeparatedExpandableNameField(ExpandableNameField):
    """
    A subclass of ExpandableNameField that supports comma separated lists.

    Example: 'Gi1/0, Gi1/1, Gi0/[1-3], Gi0/[5-7]'
             => ['Gi1/0', 'Gi1/1', 'Gi0/1', 'Gi0/2', 'Gi0/3', 'Gi0/5', 'Gi0/6']
    """

    def __init__(self, *args, **kwargs):
        """Update help_text to include comma separated examples."""
        super().__init__(*args, **kwargs)
        self.help_text = """
            Provide a comma-separated list of names. Alphanumeric ranges are supported for bulk creation.
            Examples:
            <ul>
                <li><code>Gi1/0, Gi1/1, Gi0/[1-3], Gi0/[5-7]</code></li>
                <li><code>[ge,xe]-0/0/[0-9]</code></li>
                <li><code>e[0-3][a-d,f]</code></li>
            </ul>
        """

    def to_python(self, value):
        """Convert the input string into a list of interface names."""
        if not value:
            return []

        tokens = [token.strip() for token in value.split(",") if token.strip()]
        names = []
        for token in tokens:
            if re.search(ALPHANUMERIC_EXPANSION_PATTERN, token):
                names.extend(list(expand_alphanumeric_pattern(token)))
            else:
                names.append(token)
        return names


class CableCreationForm(BootstrapMixin, forms.Form):
    """Form for creating a series of new cables between a device and a patch panel."""

    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="1. On this device: ",
        required=True,
        query_params={"role__n": "Patch Panel"},
    )

    device_interface = DynamicModelMultipleChoiceField(
        queryset=Interface.objects.all(),
        label="2. Connect these interfaces:",
        required=True,
        query_params={
            "device_id": "$device",
            "kind": "physical",
            "cable__isnull": True,
        },  # When device changes, filter interfaces for that device.
    )

    # device_interface = CommaSeparatedExpandableNameField(
    #     label="2. Connect these interfaces:",
    #     required=True,
    # )

    patch_panel = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="3. To this patch panel:",
        required=True,
        query_params={"role": "Patch Panel"},  # Filter patch panels by location of the device.
    )

    def __init__(self, *args, **kwargs):
        """Update the queryset for device_interface and patch_panel based on the device and patch_panel_id."""
        device_id = kwargs.pop("device_id", None)
        patch_panel_id = kwargs.pop("patch_panel_id", None)
        super().__init__(*args, **kwargs)
        if device_id:
            self.fields["device_interface"].queryset = Interface.objects.filter(device_id=device_id)
        if patch_panel_id:
            self.fields["patch_panel"].queryset = Device.objects.exclude(id=patch_panel_id)


class ExpandableCableCreationForm(BootstrapMixin, forms.Form):
    """Form for creating a series of new cables between a device and a patch panel."""

    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="1. On this device: ",
        required=True,
        query_params={"role__n": "Patch Panel"},
    )

    # device_interface = DynamicModelMultipleChoiceField(
    #     queryset=Interface.objects.all(),
    #     label="2. Connect these interfaces:",
    #     required=True,
    #     query_params={
    #         "device_id": "$device",
    #         "kind": "physical",
    #         "cable__isnull": True,
    #     },  # When device changes, filter interfaces for that device.
    # )

    device_interface = CommaSeparatedExpandableNameField(
        label="2. Connect these interfaces:",
        required=True,
    )

    patch_panel = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="3. To this patch panel:",
        required=True,
        query_params={"role": "Patch Panel"},  # Filter patch panels by location of the device.
    )

    def __init__(self, *args, **kwargs):
        """Update the queryset for device_interface and patch_panel based on the device and patch_panel_id."""
        device_id = kwargs.pop("device_id", None)
        patch_panel_id = kwargs.pop("patch_panel_id", None)
        super().__init__(*args, **kwargs)
        if device_id:
            self.fields["device_interface"].queryset = Interface.objects.filter(device_id=device_id)
        if patch_panel_id:
            self.fields["patch_panel"].queryset = Device.objects.exclude(id=patch_panel_id)


class PatchPanelCreationForm(BootstrapMixin, forms.Form):
    """Form for creating a new patch panel in each room of a building."""

    building = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        label="1. In all rooms this building:",
        required=True,
        depth=0,
        query_params={"location_type": LocationType.objects.get(name="Building").pk},
    )

    patch_panel_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        label="2. Create Patch Panel of Type:",
        required=True,
        query_params={"model__ic": "patch"},
    )

    if_exists = forms.BooleanField(
        label="Only create patch panel if the room does not already have one?",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        """Update the initial values for building, patch_panel_type, and if_exists."""
        building = kwargs.pop("building", None)
        patch_panel_type = kwargs.pop("patch_panel_type", None)
        if_exists = kwargs.pop("if_exists", True)
        super().__init__(*args, **kwargs)
        self.fields["if_exists"].initial = if_exists
