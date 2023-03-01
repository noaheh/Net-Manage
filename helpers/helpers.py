#!/usr/bin/env python3

'''
A library of generic helper functions for dynamic runbooks.
'''

import ansible_runner
import numpy as np
import os
import pandas as pd
import requests
import sqlite3 as sl
import sys
import time
import yaml
from datetime import datetime as dt
from getpass import getpass


def ansible_create_collectors_df(hostgroups, collectors):
    '''
    Creates a dataframe where the index is the selected collectors and each row
    contains a comma-delimited string of selected hostgroups.

    Args:
        hostgroups (list):          A comma-delimited list of hostgroups.
        collectors (list):          One or more collectors, comma-delimited

    Returns:
        df_collectors (DataFrame):  A DataFrame created from test_file
    '''
    df_data = list()
    for c in collectors:
        df_data.append([c, ','.join(hostgroups)])
        df_collectors = pd.DataFrame(data=df_data, columns=['collector',
                                                            'hostgroups'])
    df_collectors = df_collectors.set_index('collector')

    return df_collectors


def ansible_create_vars_df(hostgroups, private_data_dir):
    '''
    This function is created to be used with the maintenance tests notebooks.
    It reads all of the host groups from the 'df_test', gets the ansible
    variables for each group from the host file, creates a dataframe containing
    the variables, then returns it.
    Args:
        hostgroups (list):      A list of hostgroups.
        private_data_dir (str): The path to the Ansible private_data_dir.
                                It is the path that the 'inventory' folder
                                is in. The default is the current folder.
    Returns:
        df_vars (DataFrame):    A dataframe containing the group variables
    '''
    host_vars = dict()

    for g in hostgroups:
        group_vars = ansible_get_host_variables(g, private_data_dir)
        host_vars[g] = group_vars

    # Create a dictionary to store the variable data for each group
    df_data = dict()
    df_data['host_group'] = list()

    # Iterate through the keys for each group in 'host_vars', adding it as a
    # key to 'df_data'
    for key, value in host_vars.items():
        for k in value:
            if k != 'ansible_user' and k != 'ansible_password':
                df_data[k] = list()

    # Iterate through 'host_vars', populating 'df_data'
    for key, value in host_vars.items():
        df_data['host_group'].append(key)
        for item in df_data:
            if item != 'host_group':
                result = value.get(item)
                df_data[item].append(result)

    df_vars = pd.DataFrame.from_dict(df_data)

    df_vars = df_vars.set_index('host_group')

    return df_vars


def ansible_get_all_hostgroup_os(private_data_dir):
    '''
    Gets the Ansible OS for every hostgroup.

    Args:
        private_data_dir (str): The path to the Ansible private_data_dir. This
                                is the path that the 'inventory' folder is in.
                                The default is the current folder.

    Returns:
        groups_os (dict):       The Ansible variables for all host groups
    '''
    # Get all group variables
    groups_vars = ansible_get_all_host_variables(private_data_dir)

    groups_os = dict()

    for key, value in groups_vars.items():
        group_vars = value.get('vars')
        if group_vars and group_vars.get('ansible_network_os'):
            groups_os[key] = value['vars']['ansible_network_os']

    return groups_os


def ansible_get_all_host_variables(private_data_dir):
    '''
    Gets the Ansible variables for all hostgroups in the inventory.

    Args:
        private_data_dir (str): The path to the Ansible private_data_dir. This
                                is the path that the 'inventory' folder is in.
                                The default is the current folder.

    Returns:
        groups_vars (dict):     The Ansible variables for all host groups
    '''
    # Read the contents of the playbook into a dictionary
    with open(f'{private_data_dir}/inventory/hosts') as f:
        groups_vars = yaml.load(f, Loader=yaml.FullLoader)
    return groups_vars


def check_dir_existence(dir_path):
    '''
    Checks whether a directory exists.

    Args:
        dir_path (str): The path to the directory

    Returns:
        exists (bool):  A boolean to indicate whether the directory exists
    '''
    try:
        os.listdir(dir_path)
        exists = True
    except Exception:
        exists = False
    return exists


def convert_mask_to_cidr(netmask):
    '''
    Converts a subnet mask to CIDR notation.

    Args:
        netmask (str):  A subnet mask in xxx.xxx.xxx.xxx format

    Returns:
        cidr (str):     The number of bits in the subnet mask (CIDR)
    '''
    cidr = sum(bin(int(x)).count('1') for x in netmask.split('.'))
    return cidr


def create_dir(dir_path):
    '''
    Creates a directory

    Args:
        dir_path (str): The path to the directory

    Returns:
        None
    '''
    os.mkdir(dir_path)


def define_supported_validation_tables():
    '''
    Returns a list of tables that are supported for validation

    Args:
        None

    Returns:
        supported_tables (dict): A list of supported tables
    '''
    supported_tables = dict()

    supported_tables['MERAKI_GET_ORG_DEVICE_STATUSES'] = dict()
    supported_tables['MERAKI_GET_ORG_DEVICE_STATUSES']['status'] = 'online'

    supported_tables['F5_POOL_AVAILABILITY'] = dict()
    supported_tables['F5_POOL_AVAILABILITY']['availability'] = 'available'

    supported_tables['F5_POOL_MEMBER_AVAILABILITY'] = dict()
    supported_tables['F5_POOL_MEMBER_AVAILABILITY']['pool_member_state'] = \
        'available'

    supported_tables['F5_VIP_AVAILABILITY'] = dict()
    supported_tables['F5_VIP_AVAILABILITY']['availability'] = 'available'

    return supported_tables


def get_database_tables(db_path):
    '''
    Gets all of the tables out of the database.

    Args:
        db_path (str): The path to the database

    Returns:
        tables (list): A list of tables
    '''
    # sqlite_schema used to be named sqlite_master. This method tries the new
    # name but will fail back to the old name if the user is on an older
    # version
    name_old = 'master'
    name_new = 'schema'
    con = connect_to_db(db_path)
    query1 = f'''select name from sqlite_{name_new}
                 where type = "table" and name not like "sqlite_%"'''
    query2 = f'''select name from sqlite_{name_old}
                 where type = "table" and name not like "sqlite_%"'''
    try:
        df_tables = pd.read_sql(query1, con)
    except Exception:
        df_tables = pd.read_sql(query2, con)
    tables = df_tables['name'].to_list()
    return tables


def ansible_get_hostgroup():
    '''
    Gets the Ansible hostgroup

    Args:
        None

    Returns:
        hostgroup (str): The Ansible hostgroup
    '''
    host_group = input('Enter the name of the host group in the hosts file: ')
    return host_group


def ansible_get_host_variables(host_group, private_data_dir):
    '''
    Gets the variables for a host or host group in the hosts file.

    Args:
        host_group (str):       The name of the host group
        private_data_dir (str): The path to the Ansible private_data_dir. This
                                is the path that the 'inventory' folder is in.
                                The default is the current folder.

    Returns:
        group_vars (dict):      The host group variables
    '''
    # Read the contents of the playbook into a dictionary
    with open(f'{private_data_dir}/inventory/hosts') as f:
        hosts = yaml.load(f, Loader=yaml.FullLoader)

    group_vars = hosts[host_group]['vars']

    return group_vars


def ansible_get_hostgroup_devices(hostgroup, host_files, quiet=True):
    '''
    Gets the devices inside an Ansible inventory hostgroup.
    Args:
        hostgroup (str):   The Ansible hostgroup
        host_files (list): The path to one or more Ansible host files
                           (I.e., ['inventory/hosts'])
        quiet (bool):      Whether to output the entire graph.
    Returns:
        devices (list):  A list of devices in the hostgroup
    '''
    graph = ansible_runner.interface.get_inventory('graph',
                                                   host_files,
                                                   quiet=True)
    graph = str(graph)
    for item in graph.split('@'):
        if hostgroup in item:
            item = item.split(':')[-1]
            item = item.split('|--')[1:-1]
            devices = [i.split('\\')[0] for i in item]
            break
    return devices


def ansible_group_hostgroups_by_os(private_data_dir):
    '''
    Finds the ansible_network_os for all hostgroups that have defined it in the
    variables, then organizes the hostgroups by os. For example:

    groups_os['cisco.asa.asa'] = [asa_group_1]
    groups_os['cisco.nxos.nxos'] = [nxos_group_1, nxos_group_2]

    Args:
        private_data_dir (str): The path to the Ansible private_data_dir. This
                                is the path that the 'inventory' folder is in.
                                The default is the current folder.

    Returns:
        hostgroup_by_os (dict): A dictionary containing the hostgroups, grouped
                                by OS.
    '''
    # Get the OS for all Ansible hostgroups
    groups_os = ansible_get_all_hostgroup_os(private_data_dir)

    # Extract the OS and create dict for all hostgroups that have defined it
    groups_by_os = dict()
    for key, value in groups_os.items():
        if not groups_by_os.get(value):
            groups_by_os[value] = list()
        groups_by_os[value].append(key)
    return groups_by_os


def define_collectors(hostgroup):
    '''
    Creates a list of collectors.

    Args:
        hostgroup (str):    The name of the hostgroup

    Returns:
        available (dict):   The collectors supported by the hostgroup
    '''
    # TODO: Find a more dynamic way to create this dictionary
    collectors = {'arp_table': ['bigip',
                                'cisco.ios.ios',
                                'cisco.nxos.nxos',
                                'paloaltonetworks.panos'],
                  'bgp_neighbors': ['cisco.nxos.nxos'],
                  'cam_table': ['cisco.ios.ios', 'cisco.nxos.nxos'],
                  'f5_node_availability': ['bigip'],
                  'f5_pool_availability': ['bigip'],
                  'f5_pool_member_availability': ['bigip'],
                  'f5_pool_summary': ['bigip'],
                  'f5_vip_availability': ['bigip'],
                  'f5_vip_destinations': ['bigip'],
                  'f5_vip_summary': ['bigip'],
                  'infoblox_get_networks': ['infoblox_nios'],
                  'infoblox_get_network_containers': ['infoblox_nios'],
                  'infoblox_get_networks_parent_containers': ['infoblox_nios'],
                  'infoblox_get_vlan_ranges': ['infoblox_nios'],
                  'interface_description': ['bigip',
                                            'cisco.ios.ios',
                                            'cisco.nxos.nxos'],
                  'interface_ip_addresses': ['cisco.asa.asa',
                                             'cisco.ios.ios',
                                             'cisco.nxos.nxos',
                                             'paloaltonetworks.panos'],
                  'interface_status': ['cisco.nxos.nxos'],
                  'interface_summary': ['bigip', 'cisco.nxos.nxos'],
                  'inventory_nxos': ['cisco.nxos.nxos'],
                  'meraki_get_network_clients': ['meraki'],
                  'meraki_get_network_devices': ['meraki'],
                  'meraki_get_network_device_statuses': ['meraki'],
                  'meraki_get_organizations': ['meraki'],
                  'meraki_get_org_devices': ['meraki'],
                  'meraki_get_org_device_statuses': ['meraki'],
                  'meraki_get_org_networks': ['meraki'],
                  'meraki_get_switch_port_statuses': ['meraki'],
                  'meraki_get_switch_lldp_neighbors': ['meraki'],
                  'meraki_get_switch_port_usages': ['meraki'],
                  'netbox_get_ipam_prefixes': ['netbox'],
                  'port_channel_data': ['cisco.nxos.nxos'],
                  'vlan_database': ['cisco.nxos.nxos'],
                  'vpc_state': ['cisco.nxos.nxos'],
                  'vrfs': ['cisco.nxos.nxos']}

    available = list()
    for key, value in collectors.items():
        if hostgroup in value:
            available.append(key)
    return available


def f5_create_authentication_token(device,
                                   username,
                                   password,
                                   loginProviderName='tmos',
                                   verify=True):
    '''
    Creates an authentication token to use for F5 REST API calls.

    Args:
        device (str):               The device name or IP address
        username (str):             The user's username
        password (str):             The user's password
        loginProviderName (str):    The value to use for 'loginProviderName'.
                                    Defaults to 'tmos'. It should only need to
                                    be changed if F5 documentation or support
                                    says it is necessary.
        verify (bool):              Whether to verify certs. Defaults to
                                    'True'. Should only be set to 'False' if it
                                    is a dev environment or the F5 is using
                                    self-signed certificates.
    '''
    # Create the URL used for creating the authentication token
    url = f'{device}/mgmt/shared/authn/login'

    # Request the token
    content = {'username': username,
               'password': password,
               'loginProviderName': loginProviderName}
    response = requests.post(url, json=content, verify=verify)
    token = response.json()['token']['token']

    # Sleep for 1.5 seconds. This is required due to F5 bug ID1108181
    # https://cdn.f5.com/product/bugtracker/ID1108181.html
    time.sleep(1.5)

    # Return the token
    return token


def get_creds(prompt=str()):
    '''
    Gets the username and password to use for authentication.

    Args:
        prompt (str):   A one-word description to use inside the prompt. For
                        example, if prompt == 'device', then the user would
                        be presented with the full prompt of:
                        'Enter the username to use for device authentication.'
                        If no prompt is passed to the function, then the
                        generic prompt will be used.

    Returns:
        username (str): The username
        password (str): The password
    '''
    username = get_username(prompt)
    password = get_password(prompt)
    return username, password


def ansible_get_hostgroups(inventories, quiet=True):
    '''
    Gets the devices inside an Ansible inventory hostgroup.
    Args:
        inventories (list): The path to one or more Ansible host files
                            (I.e., ['inventory/hosts'])
        quiet (bool):       Whether to output the entire graph.
    Returns:
        devices (list):  A list of devices in the hostgroup
    '''
    graph = ansible_runner.interface.get_inventory('graph',
                                                   inventories,
                                                   quiet=True)
    graph = str(graph).strip("('")
    # graph = list(filter(None, graph))
    hostgroups = list()
    graph = list(filter(None, graph.split('@')))
    # TODO: Write a better parser
    for item in graph:
        hostgroup = item.split(':')[0]
        hostgroups.append(hostgroup)
    return hostgroups


def connect_to_db(db):
    '''
    Opens a connection to the sqlite database.

    Args:
        db (str):   Path to the database

    Returns:
        con (ob):   Connection to the database
    '''
    try:
        con = sl.connect(db)
    except Exception as e:
        if str(e) == 'unable to open database file':
            print(f'Cannot connect to db "{db}". Does directory exist?')
            sys.exit()
        else:
            print(f'Caught exception "{str(e)}"')
            sys.exit()
    return con


def get_first_last_timestamp(db_path, table, col_name):
    '''
    Gets the first and last timestamp from a database table for each unique
    entry in a column.

    Args:
        db_path (str):  The path to the database
        table (str):    The table name
        col_name (str): The column name to search by ('device', 'networkId',
                        etc)

    Returns:
        df_stamps (df): A DataFrame containing the first and last timestamp for
                        each unique device
    '''
    df_data = dict()
    df_data[col_name] = list()
    df_data['first_ts'] = list()
    df_data['last_ts'] = list()

    # Get the unique entries for col_name (usually a device name, MAC address,
    # etc). This is necessary since the first timestamp in the table won't
    # always have all the entries for that table (devices might be added or
    # removed, ARP tables might change, and so on)
    con = sl.connect(db_path)
    query = f'select distinct {col_name} from {table}'
    df_uniques = pd.read_sql(query, con)
    uniques = df_uniques[col_name].to_list()

    # Create a dictionary to store the first and last timestamps for col_name.
    # This will be used to create df_stamps
    # df_data = dict()

    query = f'select distinct timestamp from {table}'
    timestamps = pd.read_sql(query, con)['timestamp'].to_list()

    for unique in uniques:
        stamps = list()
        for ts in timestamps:
            query = f'''select timestamp from {table}
                        where timestamp = "{ts}" and {col_name} = "{unique}"'''
            for item in pd.read_sql(query, con)['timestamp'].to_list():
                stamps.append(item)
        df_data[col_name].append(unique)
        df_data['first_ts'].append(stamps[0])
        df_data['last_ts'].append(stamps[-1])

    # This is an alternative way to collect the first and last timestamps for
    # each col_name. It does not utilize an index (assuming the table has one),
    # but the speed was about the same. I am leaving it here to do more
    # testing with in the future.

    # for unique in uniques:
    #     query = f'''select distinct timestamp from {table}
    #                 where {col_name} = "{unique}"'''
    #     df_stamps = pd.read_sql(query, con)
    #     stamps = df_stamps['timestamp'].to_list()
    #     df_data[col_name].append(unique)
    #     df_data['first_ts'].append(stamps[0])
    #     df_data['last_ts'].append(stamps[-1])
    con.close()

    df_stamps = pd.DataFrame.from_dict(df_data)

    return df_stamps


def get_username(prompt=str()):
    '''
    Gets the username to use for authentication

    Args:
        prompt (str):   A one-word description to use inside the prompt. For
                        example, if prompt == 'device', then the user would
                        be presented with the full prompt of:
                        'Enter the username to use for device authentication.'
                        If no prompt is passed to the function, then the
                        generic prompt will be used.

    Returns:
        username (str): The username
    '''
    # Create the full prompt
    if not prompt:
        f_prompt = 'Enter the username to use for authentication: '
    else:
        f_prompt = f'Enter the username to use for {prompt} authentication: '

    # Get the user's username
    username = input(f_prompt)

    return username


def get_password(prompt=str()):
    '''
    Gets the password to use for authentication

    Args:
        prompt (str):   A one-word description to use inside the prompt. For
                        example, if prompt == 'device', then the user would
                        be presented with the full prompt of:
                        'Enter the username to use for device authentication.'
                        If no prompt is passed to the function, then the
                        generic prompt will be used.

    Returns:
        password (str): The password
    '''
    # Create the full prompt
    if not prompt:
        f_prompt = 'Enter the password to use for authentication: '
    else:
        f_prompt = f'Enter the password to use for {prompt} authentication: '

    # Get the user's password and have them type it twice for verification
    pass1 = str()
    pass2 = None
    while pass1 != pass2:
        pass1 = getpass(f_prompt)
        pass2 = getpass('Confirm your password: ')
        if pass1 != pass2:
            print('Error: Passwords do not match.')
    password = pass1

    return password


def meraki_get_api_key():
    '''
    Gets the Meraki API key

    Args:
        None

    Returns:
        api_key (str):  The user's API key
    '''
    api_key = getpass('Enter your Meraki API key: ')
    return api_key


def move_cols_to_end(df, cols):
    '''
    Moves one or more columns on a dataframe to be the end. For example,
    if the dataframe columns are ['A', 'C', B'], then this function can be
    used to re-order them to ['A', 'B', 'C']

    Args:
        df (DataFrame): The Pandas dataframe to re-order.
        cols (list):    A list of one or more columns to move. If more than one
                        column is specified, then they will be added to the end
                        in the order that is in the list.

    Returns:
        df (DataFrame): The re-ordered DataFrame

    '''
    for c in cols:
        df[c] = df.pop(c)
    return df


def read_table(db_path, table):
    '''
    Reads all columns for the latest timestamp from a database table.

    Args:
        db_path (str):  The full path to the database
        table (str):    The table name

    Returns:
        df (df):        A Pandas dataframe containing the data
    '''
    con = connect_to_db(db_path)
    df_ts = pd.read_sql(f'select timestamp from {table} limit 1', con)
    ts = df_ts['timestamp'].to_list()[-1]
    df = pd.read_sql(f'select * from {table} where timestamp = "{ts}"', con)
    con.close()
    return df


def set_dependencies(selected):
    '''
    Ensures that dependent collectors are added to the selection. For example,
    collecting 'f5_vip_destinations' requires collecting 'f5_vip_availability'.
    If a user has selected the former without selecting the latter, then this
    function adds the latter (in the proper order) to the selection.

    TODO: Currently, all dependencies are within the same hostgroup. By that I
          mean, F5 collectors are dependent on other F5 collectors, Meraki
          collectors are dependent on other Meraki collectors, and so on.
          It is possible that at some point collectors will be dependent on
          hostgroups that the user did not select. If that happens, this
          function will need to be modified accordingly.

    Args:
        selected (list): The list of selected collectors

    Returns:
        selected (list): The updated list of selected collectors
    '''
    s = selected
    if 'interface_summary' in s:
        pos = s.index('interface_summary')
        if 'cam_table' not in s:
            s.insert(pos, 'cam_table')
        if 'interface_description' not in s:
            s.insert(pos, 'interface_description')
        if 'interface_status' not in s:
            s.insert(pos, 'interface_status')
    if 'get_device_statuses' in s:
        pos1 = s.index('get_device_statuses')
        if 'get_organizations' in s:
            pos2 = s.index('get_organizations')
            if pos2 > pos1:
                del s[pos2]
                s.insert(pos1, 'get_organizations')
        else:
            s.insert(pos1, 'get_organizations')

    if 'interface_summary' in s:
        if 'cam_table' in s:
            pos = s.index('cam_table')
            del s[pos]
        s.insert(0, 'cam_table')

    if 'f5_get_vip_destinations' in s:
        if 'f5_get_vip_availability' in s:
            pos = s.index('f5_get_vip_availability')
            del s[pos]
        s.insert(0, 'f5_vip_availability')

    if 'infoblox_get_networks_parent_containers' in s:
        if 'infoblox_get_networks' in s:
            pos = s.index('infoblox_get_networks')
            del s[pos]
        pos = s.insert(0, 'infoblox_get_networks')
        if 'infoblox_get_network_containers' in s:
            pos = s.index('infoblox_get_network_containers')
            del s[pos]
        pos = s.insert(0, 'infoblox_get_network_containers')

    if 'meraki_get_device_statuses' in s:
        if 'meraki_get_organizations' in s:
            pos = s.index('meraki_get_organizations')
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    if 'meraki_get_network_device_statuses' in s:
        if 'meraki_get_org_device_statuses' in s:
            pos = s.index('meraki_get_org_device_statuses')
            del s[pos]
        s.insert(0, 'meraki_get_org_device_statuses')

    if 'meraki_get_network_devices' in s:
        if 'meraki_get_organizations' in s:
            pos = s.index('meraki_get_organizations')
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    if 'meraki_get_org_devices' in s:
        if 'meraki_get_organizations' in s:
            pos = s.index('meraki_get_organizations')
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    if 'meraki_get_org_device_statuses' in s:
        if 'meraki_get_org_networks' in s:
            pos = s.index('meraki_get_org_networks')
            del s[pos]
        s.insert(0, 'meraki_get_org_networks')

    if 'meraki_get_org_networks' in s:
        if 'meraki_get_organizations' in s:
            pos = s.index('meraki_get_organizations')
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    if 'meraki_get_switch_lldp_neighbors' in s:
        dependencies = ['meraki_get_switch_port_statuses']
        for d in dependencies:
            if d in s:
                pos = s.index(d)
                del s[pos]
        for d in dependencies:
            s.insert(0, d)

    if 'meraki_get_switch_port_usages' in s:
        if 'meraki_get_switch_port_statuses' in s:
            pos = s.index('meraki_get_switch_port_statuses')
            del s[pos]
        s.insert(0, 'meraki_get_switch_port_statuses')

    if 'meraki_get_switch_port_statuses' in s:
        if 'meraki_get_org_devices' in s:
            pos = s.index('meraki_get_org_devices')
            del s[pos]
        s.insert(0, 'meraki_get_org_devices')
        if 'meraki_get_organizations' in s:
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    if 'meraki_get_vpn_statuses' in s:
        if 'meraki_get_organizations' in s:
            pos = s.index('meraki_get_organizations')
            del s[pos]
        s.insert(0, 'meraki_get_organizations')

    # Remove duplicate collectors from 's'
    non_dups = list()
    for item in s:
        if item not in non_dups:
            non_dups.append(item)
    s = non_dups

    selected = s
    return s


def set_filepath(filepath):
    '''
    Creates a filename with the date and time added to a path the user
    provides. The function assumes the last "." in a filename is the extension.

    Args:
        filepath (str):     The base filepath. Do not include the date; that
                            will be added dynamically at runtime.

    Returns:
        filepath (str):     The full path to the modified filename.
    '''
    # Convert '~' to the user's home folder
    if '~' in filepath:
        filepath = filepath.replace('~', os.path.expanduser('~'))
    # Set the prefix in YYYY-MM-DD_HHmm format
    prefix = dt.now().strftime("%Y-%m-%d_%H%M")
    # Extract the base path to the filename
    filepath = filepath.split('/')
    filename = filepath[-1]
    if len(filepath) > 2:
        filepath = '/'.join(filepath[:-1])
    else:
        filepath = filepath[0]
    # Extract the filename and extension from 'filepath'
    filename = filename.split('.')
    extension = filename[-1]
    if len(filename) > 2:
        filename = '.'.join(filename[:-1])
    else:
        filename = filename[0]
    # Return the modified filename
    filepath = f'{filepath}/{prefix}_{filename}.{extension}'
    return filepath


def suppress_extravars(extravars):
    '''
    ansible_runner.run stores extravars to a file named 'extravars' then saves
    it to the local drive. The file is unencrypted, so any sensitive data, like
    usernames and password, are stored in plain text.

    People have complained about this for years. Finally, starting in version
    2.x, the devs added the 'suppress_env_files' arg. This keeps extravars from
    being stored locally.

    The sole purpose of this function is to ensure that legacy Ansible-Runner
    commands add that argument. *All ansible_runner.run args should be passed
    to this function, no exceptions.*

    If they do not use extravars, then just pass an empty dict.
    This will ensure the functions are secure if someone adds extravars to them
    later.

    Args:
        extravars (dict):       A dictionary containing the extravars. If your
                                function does not use it, then pass an empty
                                dict instead.

    Returns: extravars (dict):  'extravars' with the 'suppress_env_files' key.
    '''
    # TODO: Finish this function. (Note: I thought about adding a check to
    #       manually delete any files in extravars at beginning and end of
    #       each run, but users might not want that.)


def get_net_manage_path():
    '''
    Set the absolute path to the Net-Manage repository.

    Args:
        None

    Returns:
        nm_path (str):  The absolute path to the Net-Manage repository.
    '''
    nm_path = input("Enter the absolute path to the Net-Manage repository: ")
    nm_path = os.path.expanduser(nm_path)
    return nm_path


def set_vars():
    '''
    Prompts the user for the required variables for running collectors and
    validators. Several defaults are presented.

    Note: The 'inventories' argument is a list of inventory file. Right now,
          the function statically defines it as
          ['private_data_dir/inventory/hosts']. If people want to use different
          file names or more than one file name, that functionality can be
          added later.

    Args:
        None

    Returns:
        api_key, db_path, inventories, nm_path, out_path, private_data_dir
    '''
    default_db = f'{str(dt.now()).split()[0]}.db'
    default_nm_path = '~/source/repos/InsightSSG/Net-Manage/'

    db = input(f'Enter the name of the database: [{default_db}]')
    nm_path = input(f'Enter path to Net-Manage repository [{default_nm_path}]')
    private_data_dir = input('Enter the path to the private data directory:')

    default_out_path = f'{private_data_dir}/output'
    out_path = input(f'Enter the path to store results: [{default_out_path}]')

    api_key = meraki_get_api_key()

    if not db:
        db = default_db
    if not nm_path:
        nm_path = default_nm_path
    if not out_path:
        out_path = default_out_path

    db = os.path.expanduser(db)
    nm_path = os.path.expanduser(nm_path)
    out_path = os.path.expanduser(out_path)
    private_data_dir = os.path.expanduser(private_data_dir)
    db_path = f'{out_path}/{db}'

    # TODO: Add support for a custom inventory file name
    # TODO: Add support for more than one inventory file (Ansible-Runner
    #       supports that, but I am not sure how common it is)
    inventories = [f'{private_data_dir}/inventory/hosts']

    return api_key, db, db_path, inventories, nm_path, \
        out_path, private_data_dir


def get_tests_file():
    '''
    Set the absolute path to the Net-Manage repository.

    Args:
        None

    Returns:
        t)path (str):   The absolute path to the file containing tests to run.
    '''
    t_file = input("Enter the absolute path to the Net-Manage repository: ")
    t_file = os.path.expanduser(t_file)
    return t_file


def get_user_meraki_input():
    '''
    Gets and parses user input when they select collectors for Meraki
    organizations.

    Args:
        None

    Returns:
        orgs (list):        A list of one or more organizations. Defaults to
                            an empty list.
        networks (list):    A list of one or more networks. Defaults to an
                            empty list.
        macs (list):        A list of one or more MAC addresses. Partial
                            addresses are accepted. Defaults to an empty list.
        timestamp (int):    The lookback timespan in seconds. Defaults to
                            1 day (86400 seconds). If a user has an * between
                            numbers, it will multiply them. It does not perform
                            any other calculation (addition, subtraction, etc).
        per_age (int):      The number of results to return per page. Defaults
                            to 10. I recommend leaving it at 10, since
                            increasing the number of results can reduce
                            performance. However, you might try increasing it
                            when working with large datasets.
        total_pages (int):  The total number of pages to return. Defaults to
                            '-1' (which is the equivalent of 'all')
    '''
    orgs = input('Enter a comma-delimited list of organizations to query: ')\
        or list()
    if orgs:
        orgs = [_.strip() for _ in orgs.split(',')]

    networks = input('Enter a comma-delimited list of networks to query: ')\
        or list()
    if networks:
        networks = [_.strip() for _ in networks.split(',')]

    macs = input('Enter a comma-delimited list of MAC addresses: ') or list()
    if macs:
        macs = [_.strip() for _ in macs.split(',')]

    timespan = input('Enter the lookback timespan in seconds: ') or '86400'
    timespan = np.prod([int(_) for _ in timespan.split('*')])

    per_page = int(input('Enter the number of results per page: ') or 10)

    total_pages = input('Enter the total number of pages to return: ') or 'all'
    if total_pages[0].isdigit() or total_pages[0] == '-':
        total_pages = int(total_pages)

    return orgs, networks, macs, timespan, per_page, total_pages


def meraki_check_api_enablement(db_path, org):
    '''
    Queries the database to find if API access is enabled.

    Args:
        db_path (str):  The path to the database to store results
        org (str):      The organization to check API access for.
    '''
    enabled = False

    query = ['SELECT timestamp, api from MERAKI_GET_ORGANIZATIONS',
             f'WHERE org_id = "{org}"',
             'ORDER BY timestamp DESC',
             'limit 1']
    query = ' '.join(query)

    con = sl.connect(db_path)
    result = pd.read_sql(query, con)

    con.close()

    if result['api'].to_list()[0] == 'True':
        enabled = True

    return enabled


def meraki_map_network_to_organization(db_path, network):
    '''
    Gets the organization ID for a network.

    Args:
        network (str):  A network ID
        db_path (str):  The path to the database

    Returns:
        org_id (str):   The organization ID
    '''
    query = f'''SELECT distinct timestamp, organizationId
                FROM MERAKI_GET_ORG_NETWORKS
                WHERE id = "{network}"
                ORDER BY timestamp desc
                LIMIT 1
             '''
    con = sl.connect(db_path)
    result = pd.read_sql(query, con)
    con.close()

    org_id = result['organizationId'].to_list()[0]

    return org_id


def meraki_parse_organizations(db_path, orgs=list(), table=str()):
    '''
    Parses a list of organizations that are passed to certain Meraki
    collectors.

    Args:
        db_path (str):          The path to the database to store results
        orgs (list):            One or more organization IDs. If none are
                                specified, then the networks for all orgs
                                will be returned.
        table (str):            The database table to query

    Returns:
        organizations (list):   A list of organizations
    '''
    con = sl.connect(db_path)
    organizations = list()
    if orgs:
        for org in orgs:
            df_orgs = pd.read_sql(f'select distinct org_id from {table} \
                where org_id = "{org}"', con)
            organizations.append(df_orgs['org_id'].to_list().pop())
    else:
        df_orgs = pd.read_sql(f'select distinct org_id from {table}', con)
        for org in df_orgs['org_id'].to_list():
            organizations.append(org)
    con.close()

    return organizations


def sql_get_table_schema(db_path, table):
    '''
    Gets the schema of a table

    Args:
        db_path (str):      The path to the database
        table (str):        The table from which to get the schema

    Returns:
        df_schema (obj):    The table schema. If the table does not exist then
                            an empty dataframe will be returned.
    '''
    query = f'pragma table_info("{table}")'

    con = sl.connect(db_path)
    df_schema = pd.read_sql(query, con)

    return df_schema


def validate_table(table, db_path, diff_col):
    '''
    Validates a table, based on the columns that the user passes to the
    function.

    Args:
        table (str): The table to validate
        db_path (str): The path to the database
        diff_col (list): The column to diff. It should contain two items:
                         item1: The column to diff (I.e., status)
                         item2: The expected state (I.e., online)
    '''
    # Get the first and last timestamps from the table
    con = sl.connect(db_path)
    query = f'select distinct timestamp from {table}'
    df_stamps = pd.read_sql(query, con)
    stamps = df_stamps['timestamp'].to_list()
    first_ts = stamps[0]
    last_ts = stamps[-1]

    # Execute the queries and diff the results
    query1 = f'{diff_col[0]} = "{diff_col[1]}" and timestamp = "{first_ts}"'
    query2 = f'{diff_col[0]} = "{diff_col[1]}" and timestamp = "{last_ts}"'
    query = f'''select *
                from {table}
                where {query1}
                except
                select *
                from {table}
                where {query2}
                '''
    df_diff = pd.read_sql(query, con)
    return df_diff