# Layer8 App

## Overview

> A Nautobot Plugin App which implements workflows for synchronising Nautobot with the Auvik network monitoring platform by providing SSOT Jobs for the `nautobot-ssot` app.

### SSOT Jobs

The Layer8 App includes several SSOT (Single Source of Truth) jobs that facilitate the synchronization between Nautobot and Auvik. These jobs are located in the `ssot_jobs` folder and include:

- **Auvik to Nautobot Sync**: This job pulls data from Auvik and updates the corresponding records in Nautobot.
- **Nautobot to Auvik Sync**: This job pushes data from Nautobot to Auvik, ensuring both systems are in sync.
- **Auvik Data Validation**: This job validates the data received from Auvik to ensure it meets the required standards before updating Nautobot.

These jobs help maintain data consistency and accuracy between the two platforms, making network management more efficient.

### Additional Models

The Layer8 App also introduces several additional models to enhance the functionality of Nautobot. These models include:

- **AuvikDevice**: Represents a device managed by Auvik, including attributes such as device name, IP address, and status.
- **AuvikSite**: Represents a site or location within Auvik, including details like site name, address, and associated devices.
- **AuvikInterface**: Represents a network interface on an Auvik-managed device, including attributes such as interface name, type, and status.

These models provide a more comprehensive representation of the network infrastructure managed by Auvik, allowing for better integration and management within Nautobot.

### Installation

To install the Layer8 App, follow these general steps:

1. **Install the Plugin**: Add the Layer8 App to your Nautobot environment. This typically involves adding the plugin to your `local_requirements.txt` or `Pipfile`.

2. **Update Configuration**: Modify your `nautobot_config.py` to include the Layer8 App in the `PLUGINS` and `PLUGINS_CONFIG` settings.

3. **Run Migrations**: Apply the database migrations to create the necessary tables for the Layer8 App models.

4. **Restart Nautobot**: Restart the Nautobot services to load the new plugin.

For detailed instructions and exact steps, please refer to the [Nautobot Plugin Installation Documentation](https://nautobot.readthedocs.io/en/stable/plugins/).

Following these steps will ensure that the Layer8 App is properly installed and configured within your Nautobot environment.
