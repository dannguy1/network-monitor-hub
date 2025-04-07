import shlex # For safe quoting

def generate_uci_commands(config_section, options):
    """Generates a list of UCI set commands based on a dict of options.

    Args:
        config_section (str): The full UCI section path (e.g., 'network.lan', 'wireless.@wifi-iface[0]').
        options (dict): A dictionary where keys are option names and values are the desired values.
                      Values can be strings or lists (for UCI lists).

    Returns:
        list: A list of UCI command strings (e.g., ["uci set network.lan.proto='static'", ...]).
        list: An empty list if no options are provided.
    """
    commands = []
    if not options:
        return commands

    for option, value in options.items():
        if value is None:
            # How to handle None? Could mean delete the option.
            # commands.append(f"uci delete {config_section}.{option}")
            continue # Or simply skip setting it

        uci_path = f"{config_section}.{option}"
        
        if isinstance(value, list):
            # Handle UCI lists - requires clearing existing list first
            commands.append(f"uci delete {uci_path}")
            for item in value:
                # Ensure items in the list are properly quoted
                commands.append(f"uci add_list {uci_path}={shlex.quote(str(item))}")
        else:
            # Handle single values - ensure proper quoting
            commands.append(f"uci set {uci_path}={shlex.quote(str(value))}")

    return commands

# Example Usage:
# lan_options = {
#     'proto': 'static',
#     'ipaddr': '192.168.2.1',
#     'netmask': '255.255.255.0',
#     'dns': ['8.8.8.8', '1.1.1.1'] # Example list
# }
# lan_commands = generate_uci_commands('network.lan', lan_options)
# print(lan_commands)
# Expected output (or similar):
# ["uci set network.lan.proto='static'", 
#  "uci set network.lan.ipaddr='192.168.2.1'", 
#  "uci set network.lan.netmask='255.255.255.0'", 
#  "uci delete network.lan.dns", 
#  "uci add_list network.lan.dns='8.8.8.8'", 
#  "uci add_list network.lan.dns='1.1.1.1'"] 