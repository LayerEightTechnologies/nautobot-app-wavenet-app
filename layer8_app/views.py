from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views.generic.edit import FormView
from nautobot.dcim.models import Cable, Interface
from nautobot.extras.models import Status
from .forms import CableCreationForm

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
            available_patch_interface = patch_panel.interfaces.filter(
                cable__isnull=True
            ).first()

            if not available_patch_interface:
                form.add_error(
                    "patch_panel", 
                    "No available interfaces on the selected patch panel."
                )
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
    
