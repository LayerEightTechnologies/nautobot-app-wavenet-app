from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from nautobot.dcim.models import Cable, Interface, Location, Device
from nautobot.extras.models import Status, Role
from .forms import CableCreationForm, ExpandableCableCreationForm, PatchPanelCreationForm


class CableCreateView(FormView):
    template_name = "layer8_app/cable_create.html"
    form_class = CableCreationForm
    success_url = reverse_lazy("plugins:layer8_app:cable_create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        device_id = self.request.GET.get("device")
        patch_panel_id = self.request.GET.get("patch_panel")

        if device_id:
            kwargs["device_id"] = device_id

        if patch_panel_id:
            kwargs["patch_panel"] = patch_panel_id

        return kwargs

    def form_valid(self, form):
        # Get the list of interfaces selected on the device
        device_interfaces = form.cleaned_data["device_interface"]
        # Get the patch panel device selected by the user.
        patch_panel = form.cleaned_data["patch_panel"]

        for device_interface in device_interfaces:
            # Query for the first available physical interface on the patch panel
            # that does not already have a cable connected.
            # Note: Depending on your Nautobot version and configuration,
            # you may need to use patch_panel.interface_set or patch_panel.interfaces.
            available_patch_interface = patch_panel.interfaces.filter(cable__isnull=True).first()

            if not available_patch_interface:
                form.add_error("patch_panel", "No available interfaces on the selected patch panel.")
                return self.form_invalid(form)

            # Get Cable Instance for "Connected" status:
            new_cable_status = Status.objects.get(name="Connected")

            # Create a Cable object connecting the selected device interface (termination A)
            # to the available patch panel interface (termination B).
            Cable.objects.create(
                termination_a=device_interface,
                termination_b=available_patch_interface,
                # Optionally, add any additional required fields such as type, status, etc.
                status=new_cable_status,
            )

        patch_panel_url = patch_panel.get_absolute_url()
        message = mark_safe(
            f"Floodwired connections created successfully. <a href='{patch_panel_url}interfaces'>View Patch Panel</a>."
        )
        messages.success(self.request, message)

        return super().form_valid(form)


class ExpandableCableCreateView(FormView):
    template_name = "layer8_app/cable_create.html"
    form_class = ExpandableCableCreationForm
    success_url = reverse_lazy("plugins:layer8_app:cable_create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        device_id = self.request.GET.get("device")
        patch_panel_id = self.request.GET.get("patch_panel")

        if device_id:
            kwargs["device_id"] = device_id

        if patch_panel_id:
            kwargs["patch_panel"] = patch_panel_id

        return kwargs

    def form_valid(self, form):
        device = form.cleaned_data["device"]
        # Get the list of interfaces selected on the device
        device_interfaces = form.cleaned_data["device_interface"]
        # Get the patch panel device selected by the user.
        patch_panel = form.cleaned_data["patch_panel"]

        for device_interface in device_interfaces:
            # Check if the selected device interface exists
            try:
                device_interface = Interface.objects.get(name=device_interface, device=device)
            except:
                form.add_error("device_interface", f"Interface {device_interface} does not exist on device {device}.")
                return self.form_invalid(form)

            # Check if the selected device interface already has a cable connected.

            if device_interface.cable:
                form.add_error("device_interface", f"Interface {device_interface} already has a cable connected.")
                return self.form_invalid(form)

            # Query for the first available physical interface on the patch panel
            # that does not already have a cable connected.
            # Note: Depending on your Nautobot version and configuration,
            # you may need to use patch_panel.interface_set or patch_panel.interfaces.
            available_patch_interface = patch_panel.interfaces.filter(cable__isnull=True).first()

            if not available_patch_interface:
                form.add_error("patch_panel", "No available interfaces on the selected patch panel.")
                return self.form_invalid(form)

            # Get Cable Instance for "Connected" status:
            new_cable_status = Status.objects.get(name="Connected")

            # Create a Cable object connecting the selected device interface (termination A)
            # to the available patch panel interface (termination B).
            Cable.objects.create(
                termination_a=device_interface,
                termination_b=available_patch_interface,
                # Optionally, add any additional required fields such as type, status, etc.
                status=new_cable_status,
            )

        patch_panel_url = patch_panel.get_absolute_url()
        message = mark_safe(
            f"Floodwired connections created successfully. <a href='{patch_panel_url}interfaces'>View Patch Panel</a>."
        )
        messages.success(self.request, message)

        return super().form_valid(form)


class PatchPanelCreateView(FormView):
    template_name = "layer8_app/patch_panel_create.html"
    form_class = PatchPanelCreationForm
    success_url = reverse_lazy("plugins:layer8_app:patch_panel_create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        building = self.request.GET.get("building")
        patch_panel_type_id = self.request.GET.get("patch_panel_type")
        if_exists = self.request.GET.get("if_exists")

        if building:
            kwargs["building"] = building

        if patch_panel_type_id:
            kwargs["patch_panel_type"] = patch_panel_type_id

        if if_exists:
            kwargs["if_exists"] = if_exists

        return kwargs

    def form_valid(self, form):
        building = form.cleaned_data["building"]
        patch_panel_type = form.cleaned_data["patch_panel_type"]
        if_exists = form.cleaned_data["if_exists"]

        active_status = Status.objects.get(name="Active")
        patch_panel_role = Role.objects.get(name="Patch Panel")

        rooms = Location.objects.filter(parent=building, location_type__name="Room")

        created_count = 0
        skipped_count = 0

        for room in rooms:
            existing_patch_panel = Device.objects.filter(
                location=room,
                role=patch_panel_role,
            )

            if existing_patch_panel.exists() and if_exists:
                skipped_count += 1
                continue

            Device.objects.create(
                name=f"{building.name}-{room.name}-Patch-Panel",
                location=room,
                device_type=patch_panel_type,
                role=patch_panel_role,
                status=active_status,
            )
            created_count += 1

        message = mark_safe(
            f"Patch panels created for {created_count} rooms; {skipped_count} rooms were skipped. <a href='/dcim/devices/?location={building.name}&role=Patch%20Panel'>View Building Patch Panels</a>."
        )
        messages.success(self.request, message)

        return super().form_valid(form)
