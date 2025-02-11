from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuImportButton, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Wavenet App",
        weight=1000,
        groups=(
            NavMenuGroup(
                weight=100,
                name="Cables",
                items=(
                    NavMenuItem(
                        link="plugins:layer8_app:cable_create",
                        name="Floodwired Connections",
                        permissions=["dcim.add_cable"],
                    ),
                ),
            ),
        ),
    ),
)