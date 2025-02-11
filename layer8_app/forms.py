from django import forms
from nautobot.apps.forms import BootstrapMixin
from nautobot.apps.forms import APISelect, DynamicModelChoiceField, DynamicModelMultipleChoiceField
from nautobot.dcim.models import Device, Interface, Location

class CableCreationForm(BootstrapMixin, forms.Form):
   
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="1. On this device: ",
        required=True,
    )
    
    device_interface = DynamicModelMultipleChoiceField(
        queryset=Interface.objects.all(),
        label="2. Connect these interfaces:",
        required=True,
        query_params={"device_id": "$device", "kind": "physical", "cable__isnull": True},  # When device changes, filter interfaces for that device.
    )
    
    patch_panel = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        label="3. To this patch panel:",
        required=True,
        query_params={"role": "Patch Panel"},  # Filter patch panels by location of the device.
    )
    
    def __init__(self, *args, **kwargs):
        device_id = kwargs.pop("device_id", None)
        patch_panel_id = kwargs.pop("patch_panel_id", None)
        super().__init__(*args, **kwargs)
        if device_id:
            self.fields["device_interface"].queryset = Interface.objects.filter(device_id=device_id)
        if patch_panel_id:
            self.fields["patch_panel"].queryset = Device.objects.exclude(id=patch_panel_id)
            
# class PatchPanelCreationForm(BootstrapMixin, forms.Form):
    
#     building = DynamicModelChoiceField(
#         queryset=Location.objects.all(),
#         label="1. At this building:",
#         required=True,
#         query={"location_type": "building"},
#     )
    
#     rooms = DynamicModelMultipleChoiceField(
#         queryset=Location.objects.all(),
#         label="2. In these rooms:",
#         required=True,
#         query_params={"parent_id": "$building", "location_type": "room"},
#     )
    
#     patch_panel_type = DynamicModelChoiceField(
#         queryset=DeviceType.objects.all(),
#         label="3. Patch Panel Type:",
#         required=True,
#         query_params={"role": "Patch Panel"},
#     )