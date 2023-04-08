#!/usr/bin/env python3

'''
Define F5 collectors
'''

import ansible_runner
import ast
import pandas as pd
from helpers import helpers as hp


def convert_tmsh_output_to_dict(in_data):
    """Converts F5 'tmsh list' output to a Python dictionary.

    Parameters
    ----------
    in_data : str
        The output to convert to a dictionary.

    Returns
    ----------
    out : dict
        'in_data' formatted as a Python dictionary.

    Notes
    ----------
    F5 'tmsh list' output is close enough to a Python dictionary or JSON to be
    confusing, but in reality it is neither. However, it does follow certain
    rules.

    Rule 1: After the first line, the maximum number of elements is 2.

    Rule 2: If more than two words are in a line, then the second element will
            be wrapped in quotes. (e.g., 'vendor "F5 NETWORKS INC.")

    Rule 3: If a line contains a single word, then it is a member of an array.

    Rule 4: If a line contains a single word followed by '{ }', then '{ }'
            indicates an empty array.

    By combining these rules, we can create a relatively simple parser that
    will convert the output to a Python dictionary. It works like this:

    1. The rules listed above are used to format each line of the output into
       a form that is a valid part of a Python dictionary. For example, the
       line 'net vlan VLAN1 {' becomes, '"net vlan VLAN1": {'.

    2. Each line is added to a list.

    3. Any additional formatting is completed.

    4. The list is joined to create a string.

    5. A simple string.replace() inserts any commas that are missing between a
       '}' and a '"'. (It was easier to do it this way than to embed the logic
       inside the parser.)

    6. Formatting is finalized.

    7. ast.literal_eval is used to convert 'out' into a dictionary.

    Examples
    ----------
>>> in_data = '''net interface 1.0 {
...     if-index 542
...     mac-address 00:94:a1:91:23:44
...     media-active 1000SX-FD
...     media-max 1000T-FD
...     module-description "F5 Qualified Optic"
...     mtu 9198
...     serial N395NEY
...     vendor "F5 NETWORKS INC."
...     vendor-oui 009065
...     vendor-partnum OPT-0010
...     vendor-revision 00
... }'''
>>> output = convert_tmsh_output_to_dict(in_data)
>>> assert type(output) == dict()

    """
    # Convert the data to a list and strip all spaces.
    in_data = [_.strip() for _ in in_data.split('\n')]

    # Create a list to store each line of the formatted data. Begin the list
    # with a '{'.
    out = ['{']

    for line in in_data:
        # Format lines that look like the following:
        # 'net interface mgmt {'
        # 'net self BIGIQ {'
        # 'net vlan SERVERS {'
        if len(line.split('{')) > 1 and '}' not in line:
            line = line.replace(' {', '": {')
            line = f'"{line}'

        # Format lines that look like the following:
        # 'fwd-mode l3'
        # 'vendor "F5 NETWORKS INC."'
        # 'module-description "F5 Qualified Optic"'
        # 'tcp:ssh'
        # 'default'
        if '{' not in line and '}' not in line:
            if len(line.split()) > 1:
                if '"' in line:
                    line = line.split('"')
                    line = list(filter(None, line))
                    line = [_.strip() for _ in line]
                else:
                    line = line.split()
                line = [f'"{_}"' for _ in line]
                line = ': '.join(line)
                line = f'{line},'
            else:
                line = f'"{line}",'

        # Format lines that look like the following:
        # '2.0 { }'
        elif '{' in line and '}' in line:
            line = f'"{line.split()[0]}": [],'

        out.append(line)

    # Additional formatting needs to be done, so create a dictionary to store
    # the line numbers that require updates. Each key will be the line number
    # and the value will be the formatted line.
    replacements = dict()

    counter = 0
    for line in out:
        # Check each line to find out if it is a member of an array. If it is,
        # then do the following:
        # 1. Convert the leading or trailing '{' or '}' to a '[' or ']'.
        # 2. Insert a comma so ast.literal_eval can convert it to a list item.
        if '{' in line:
            if len(out[counter+1].split()) == 1:
                replacements[counter] = line.replace('{', '[')
        if '}' in line:
            if len(out[counter-1].split()) == 1:
                if '}' not in out[counter-1]:
                    replacements[counter] = line.replace('}', '],')
        counter += 1

    # Update 'out' with the data from 'replacements'.
    for key, value in replacements.items():
        out[key] = value

    # Add a trailing '}' to 'out'.
    out.append('}')

    # Convert 'out' to a string.
    out = ''.join(out)

    # Add a comma between '}' and '".
    out = out.replace('}"', '},"')

    # Convert 'out' to a dictionary
    out = ast.literal_eval(out)

    return out


def get_arp_table(username,
                  password,
                  host_group,
                  nm_path,
                  play_path,
                  private_data_dir,
                  validate_certs=True):
    """Get the ARP table on F5 LTMs.

    Parameters
    ----------
    username : str
        The username to login to devices.
    password : str
        The password to login to the device.
    host_group : str
        The Ansible inventory host group.
    nm_path : str
        The path to the Net-Manage repository.
    play_path : str
        The path to the playbooks directory.
    private_data_dir : str
        The path to the Ansible private data directory.
    validate_certs : bool, optional:
        Whether to validate SSL certificates.

    Returns
    ----------
    df : DataFrame
        A Pandas Dataframe containing the ARP table.
    """
    extravars = {'username': username,
                 'password': password,
                 'host_group': host_group,
                 'command': r'show net arp | grep -v "\\-\\-\\-\\-\|Net::Arp"'}

    if not validate_certs:
        extravars['validate_certs'] = 'no'

    playbook = f'{play_path}/f5_run_adhoc_command.yml'

    runner = ansible_runner.run(private_data_dir=private_data_dir,
                                playbook=playbook,
                                extravars=extravars,
                                suppress_env_files=True)

    # Create a list to store the ARP data for `df`.
    df_data = list()

    for event in runner.events:
        if event['event'] == 'runner_on_ok':
            event_data = event['event_data']
            device = event_data['remote_addr']

            output = event_data['res']['stdout_lines'][0]

            # Create the dataframe columns.
            columns = ['device'] + output[0].split()

            # Parse the output and add it to `df_data`
            for line in output[1:]:
                line = [device] + line.split()
                df_data.append(line)

    # Create `df`.
    df = pd.DataFrame(df_data, columns=columns).astype(str)

    # Get the MAC OUIs and add them to `df`
    df_macs = hp.find_mac_vendors(df['HWaddress'], nm_path)
    df['vendor'] = df_macs['vendor']

    return df


def get_self_ips(username,
                 password,
                 host_group,
                 play_path,
                 private_data_dir,
                 validate_certs=True):
    """Get the self IPs on F5 LTMs.

    Parameters
    ----------
    username : str
        The username to login to devices.
    password : str
        The password to login to the device.
    host_group : str
        The Ansible inventory host group.
    play_path : str
        The path to the playbooks directory.
    private_data_dir : str
        The path to the Ansible private data directory.
    validate_certs : bool, optional:
        Whether to validate SSL certificates.

    Returns
    ----------
    df : DataFrame
        A Pandas Dataframe containing the self IPs.
    """
    extravars = {'username': username,
                 'password': password,
                 'host_group': host_group,
                 'command': 'list net self /*/*'}

    if not validate_certs:
        extravars['validate_certs'] = 'no'

    playbook = f'{play_path}/f5_run_adhoc_command.yml'

    runner = ansible_runner.run(private_data_dir=private_data_dir,
                                playbook=playbook,
                                extravars=extravars,
                                suppress_env_files=True)

    # Create a dictionary to store each self IP.
    data = dict()

    # Create a dictionary to store the data for `df`
    df_data = dict()

    for event in runner.events:
        if event['event'] == 'runner_on_ok':
            event_data = event['event_data']
            device = event_data['remote_addr']
            data[device] = list()
            output = event_data['res']['stdout_lines'][0]

            # Parse the output and add it to `data``
            counter = 0
            for line in output:
                if line[:8] == 'net self':
                    block = list()
                    pos = counter
                    while output[pos][0] != '}':
                        block.append(output[pos])
                        pos += 1
                    block.append('}')

                    # Convert the block to a dictionary then flatten it.
                    # pprint(block)
                    block = '\n'.join(block)
                    block = convert_tmsh_output_to_dict(block)

                    for key, value in block.items():
                        self_name = key.split()[-1]
                        value['name'] = self_name

                    # Add the device name to `value`, then add `block` to
                    # `data`.
                    value['device'] = device
                    data[device].append(value)

                    # Add each key in `block` to `df_data`.
                    for key in value:
                        if not df_data.get(key):
                            df_data[key] = list()

                counter += 1

    # Iterate over `data`, adding the values to `df_data`.
    for key, value in data.items():
        for item in value:
            for k in df_data:
                df_data[k].append(item.get(k))

    # Create `df`.
    df = pd.DataFrame.from_dict(df_data).astype(str)

    # Make `device` the first column, then return `df`.
    col_1 = df.pop('device')
    df.insert(0, 'device', col_1)

    return df


def get_vlans(username,
              password,
              host_group,
              play_path,
              private_data_dir,
              validate_certs=True):
    """Gets the VLANs on F5 LTMs.

    Parameters
    ----------
    username : str
        The username to login to devices.
    password : str
        The password to login to the device.
    host_group : str
        The Ansible inventory host group.
    play_path : str
        The path to the playbooks directory.
    private_data_dir : str
        The path to the Ansible private data directory.
    validate_certs : bool, optional:
        Whether to validate SSL certificates.

    Returns
    ----------
    df : DataFrame
        A Pandas Dataframe containing the VLANs.
    """
    extravars = {'username': username,
                 'password': password,
                 'host_group': host_group,
                 'command': 'list net vlan /*/*'}

    if not validate_certs:
        extravars['validate_certs'] = 'no'

    playbook = f'{play_path}/f5_run_adhoc_command.yml'

    runner = ansible_runner.run(private_data_dir=private_data_dir,
                                playbook=playbook,
                                extravars=extravars,
                                suppress_env_files=True)

    # Create a dictionary to store each self IP.
    data = dict()

    # Create a dictionary to store the data for `df`
    df_data = dict()

    for event in runner.events:
        if event['event'] == 'runner_on_ok':
            event_data = event['event_data']
            device = event_data['remote_addr']
            data[device] = list()
            output = event_data['res']['stdout_lines'][0]

            # Parse the output and add it to `data``
            counter = 0
            for line in output:
                if line[:8] == 'net vlan':
                    block = list()
                    pos = counter
                    while output[pos][0] != '}':
                        block.append(output[pos])
                        pos += 1
                    block.append('}')

                    # Convert the block to a dictionary then flatten it.
                    # pprint(block)
                    block = '\n'.join(block)
                    block = convert_tmsh_output_to_dict(block)

                    for key, value in block.items():
                        self_name = key.split()[-1]
                        value['name'] = self_name

                    # Add the device name to `value`, then add `block` to
                    # `data`.
                    value['device'] = device
                    data[device].append(value)

                    # Add each key in `block` to `df_data`.
                    for key in value:
                        if not df_data.get(key):
                            df_data[key] = list()

                counter += 1

    # Iterate over `data`, adding the values to `df_data`.
    for key, value in data.items():
        for item in value:
            for k in df_data:
                df_data[k].append(item.get(k))

    # Create `df`.
    df = pd.DataFrame.from_dict(df_data).astype(str)

    # Make `device` the first column, then return `df`.
    col_1 = df.pop('device')
    df.insert(0, 'device', col_1)

    return df
