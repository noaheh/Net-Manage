#!/usr/bin/env python3

'''
Define collectors and map them to the correct function in colletors.py.
'''

import argparse
import datetime as dt
import os
import pandas as pd
import readline
from collectors import cisco_asa_collectors as cac
from collectors import cisco_ios_collectors as cic
from collectors import collectors as cl
from collectors import f5_collectors as f5c
from collectors import infoblox_nios_collectors as nc
from collectors import meraki_collectors as mc
from collectors import netbox_collectors as nbc
from collectors import palo_alto_collectors as pac
from collectors import solarwinds_collectors as swc
from helpers import helpers as hp
# from tabulate import tabulate

# Protect creds by not writing history to .python_history
readline.write_history_file = lambda *args: None


def collect(collector,
            nm_path,
            private_data_dir,
            timestamp,
            ansible_os=str(),
            username=str(),
            password=str(),
            api_key=str(),
            hostgroup=str(),
            infoblox_host=str(),
            infoblox_user=str(),
            infoblox_pass=str(),
            infoblox_paging=True,
            nb_path=str(),
            nb_token=str(),
            networks=list(),
            play_path=str(),
            npm_group_id=str(),
            npm_group_name=str(),
            npm_password=str(),
            npm_username=str(),
            npm_server=str(),
            ansible_timeout='300',
            db_path=str(),
            validate_certs=True,
            orgs=list(),
            total_pages='all',
            idx_cols=list(),
            method=str(),
            macs=list(),
            per_page=1000,
            timespan=86400):
    '''
    This function calls the test that the user requested.

    Args:
        os (str):               The ansible_network_os variable
        collector (str):        The name of the test that the user requested
        username (str):         The username to login to devices
        password (str):         The password to login to devices
        host_group (str):       The inventory host group
        infoblox_host (str):    The host's IP address or FQDN
        infoblox_user (str):    The user's username
        infoblox_pass (str):    The user's password
        infoblox_paging (bool): Whether to perform paging. Defaults to True
        nb_path (str):          The path to the Netbox instance. Can be either
                                an IP or a URL. Must be preceded by 'http://'
                                or 'https://'.
        nb_token (str):         The API token to use for authentication.
        networks (list):        A list of Meraki networks to query
        play_path (str):        The path to the playbooks directory
        private_data_dir (str): The path to the Ansible private data directory
        nm_path (str):          The path to the Net-Manage repository
        interface (str):        The interface (defaults to all interfaces)
        validate_certs (bool):  Whether to validate SSL certs
        org (str):              The organization ID for Meraki collectors
        total_pages (str):      The number of pages to query. Used for some
                                Meraki collectors.
        idx_cols (list):        The list of columns to use for indexing the SQL
                                table. Note that this is NOT related to the
                                dataframe index; it is only applicable to SQL

        # Default parameters for certain Meraki API calls
        macs (list):            A list of one or more partial or complete MAC
                                addresses. This is used for certain collectors,
                                like 'meraki_get_network_clients'
        per_page (int):         The number of results per page. Meraki defaults
                                to 10. This function uses 1000. If performance
                                is depreciated, choose a lower value.
        timespan (int):         The lookback time in seconds. Meraki's default
                                timespan is 1 day (86400 seconds), so the same
                                default value is used in this function.

    '''
    # Create an empty DataFrame for when collectors return no resolts.
    result = pd.DataFrame()

    # Set the number of pages to return (for Meraki collectors).
    if total_pages == -1:
        total_pages = 'all'

    # Call 'silent' (invisible to user) functions to populate custom database
    # tables. For example, on F5s a view will be created that shows the pools,
    # associated VIPs (if applicable) and pool members (if applicable). This
    # shaves a significant amount of time off of troubleshooting.
    # if ansible_os == 'bigip':
    #     c_table = cl.f5_build_pool_table(username,
    #                                      password,
    #                                      hostgroup,
    #                                      play_path,
    #                                      private_data_dir,
    #                                      db_path,
    #                                      timestamp,
    #                                      validate_certs=False)
    #     add_to_db('f5_vip_summary',
    #               c_table,
    #               timestamp,
    #               db_path,
    #               method='replace')

    # Run collectors the user requested

    if ansible_os == 'bigip':
        if collector == 'arp_table':
            result = f5c.get_arp_table(username,
                                       password,
                                       hostgroup,
                                       nm_path,
                                       play_path,
                                       private_data_dir,
                                       validate_certs=validate_certs)

        if collector == 'interface_description':
            result = f5c.\
                get_interface_descriptions(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           play_path,
                                           private_data_dir,
                                           reverse_dns=False,
                                           validate_certs=validate_certs)

        if collector == 'interface_summary':
            result = f5c.get_interface_status(username,
                                              password,
                                              hostgroup,
                                              play_path,
                                              private_data_dir,
                                              validate_certs=validate_certs)

        if collector == 'node_availability':
            result = f5c.get_node_availability(username,
                                               password,
                                               hostgroup,
                                               play_path,
                                               private_data_dir,
                                               validate_certs=validate_certs)

        if collector == 'pool_availability':
            result = f5c.get_pool_availability(username,
                                               password,
                                               hostgroup,
                                               play_path,
                                               private_data_dir,
                                               validate_certs=validate_certs)

        if collector == 'pool_summary':
            result = f5c.get_pool_data(username,
                                       password,
                                       hostgroup,
                                       play_path,
                                       private_data_dir,
                                       validate_certs=validate_certs)

        if collector == 'pool_member_availability':
            result = f5c.\
                get_pool_member_availability(username,
                                             password,
                                             hostgroup,
                                             play_path,
                                             private_data_dir,
                                             validate_certs=validate_certs)

        if collector == 'self_ips':
            result = f5c.get_self_ips(username,
                                      password,
                                      hostgroup,
                                      play_path,
                                      private_data_dir,
                                      validate_certs=validate_certs)

        if collector == 'vip_availability':
            result = f5c.get_vip_availability(username,
                                              password,
                                              hostgroup,
                                              play_path,
                                              private_data_dir,
                                              validate_certs=validate_certs)

        if collector == 'vip_destinations':
            result = f5c.get_vip_destinations(db_path)

        # if collector == 'vip_summary':
        #     result = f5c.get_vip_data(username,
        #                               password,
        #                               hostgroup,
        #                               play_path,
        #                               private_data_dir,
        #                               validate_certs=validate_certs)

        if collector == 'vlans':
            result = f5c.get_vlans(username,
                                   password,
                                   hostgroup,
                                   play_path,
                                   private_data_dir,
                                   validate_certs=validate_certs)

        if collector == 'vlan_database':
            result = f5c.f5_get_vlan_db(username,
                                        password,
                                        hostgroup,
                                        play_path,
                                        private_data_dir,
                                        validate_certs=validate_certs)

    if collector == 'cam_table':
        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_get_cam_table(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           play_path,
                                           private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_cam_table(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           play_path,
                                           private_data_dir)

    if collector == 'config':
        if ansible_os == 'cisco.ios.ios':
            result = cic.get_config(username,
                                    password,
                                    hostgroup,
                                    play_path,
                                    private_data_dir)

    if collector == 'arp_table':
        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_get_arp_table(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           play_path,
                                           private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_arp_table(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           play_path,
                                           private_data_dir)

        if ansible_os == 'paloaltonetworks.panos':
            result = pac.get_arp_table(username,
                                       password,
                                       hostgroup,
                                       nm_path,
                                       private_data_dir)

    if collector == 'bgp_neighbors':
        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_bgp_neighbors(username,
                                               password,
                                               hostgroup,
                                               nm_path,
                                               play_path,
                                               private_data_dir)

    if collector == 'interface_description':
        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_get_interface_descriptions(username,
                                                        password,
                                                        hostgroup,
                                                        play_path,
                                                        private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_interface_descriptions(username,
                                                        password,
                                                        hostgroup,
                                                        play_path,
                                                        private_data_dir)

    if collector == 'infoblox_get_network_containers':
        result = nc.get_network_containers(infoblox_host,
                                           infoblox_user,
                                           infoblox_pass,
                                           infoblox_paging,
                                           validate_certs=validate_certs)

    if collector == 'infoblox_get_networks':
        result = nc.get_networks(infoblox_host,
                                 infoblox_user,
                                 infoblox_pass,
                                 infoblox_paging,
                                 validate_certs=validate_certs)

    if collector == 'infoblox_get_network_containers':
        result = nc.get_network_containers(infoblox_host,
                                           infoblox_user,
                                           infoblox_pass,
                                           infoblox_paging,
                                           validate_certs=validate_certs)

    if collector == 'infoblox_get_networks_parent_containers':
        result = nc.get_networks_parent_containers(db_path)

    if collector == 'infoblox_get_vlan_ranges':
        result = nc.get_vlan_ranges(infoblox_host,
                                    infoblox_user,
                                    infoblox_pass,
                                    infoblox_paging,
                                    validate_certs=validate_certs)

    if collector == 'infoblox_get_vlans':
        result = nc.get_vlans(infoblox_host,
                              infoblox_user,
                              infoblox_pass,
                              infoblox_paging,
                              validate_certs=validate_certs)

    if collector == 'interface_ip_addresses':
        if ansible_os == 'cisco.asa.asa':
            result = cac.get_interface_ips(username,
                                           password,
                                           hostgroup,
                                           play_path,
                                           private_data_dir)

        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_get_interface_ips(username,
                                               password,
                                               hostgroup,
                                               play_path,
                                               private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_interface_ips(username,
                                               password,
                                               hostgroup,
                                               play_path,
                                               private_data_dir)

        if ansible_os == 'paloaltonetworks.panos':
            result = pac.get_interface_ips(username,
                                           password,
                                           hostgroup,
                                           nm_path,
                                           private_data_dir)

    if collector == 'interface_status':
        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_interface_status(username,
                                                  password,
                                                  hostgroup,
                                                  play_path,
                                                  private_data_dir)

    if collector == 'interface_summary':
        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_interface_summary(db_path)

    if collector == 'find_uplink_by_ip':
        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_find_uplink_by_ip(username,
                                               password,
                                               hostgroup,
                                               play_path,
                                               private_data_dir)

    if collector == 'inventory_nxos':
        result = cl.nxos_get_inventory(username,
                                       password,
                                       hostgroup,
                                       play_path,
                                       private_data_dir)

    if collector == 'network_appliance_vlans':
        if ansible_os == 'meraki':
            mc.get_network_appliance_vlans(ansible_os,
                                           api_key,
                                           collector,
                                           db_path,
                                           timestamp,
                                           networks=networks,
                                           orgs=orgs)

    if collector == 'network_clients':
        if ansible_os == 'meraki':
            result = mc.meraki_get_network_clients(api_key,
                                                   networks,
                                                   macs=macs,
                                                   per_page=per_page,
                                                   timespan=timespan,
                                                   total_pages=total_pages)

    if collector == 'network_devices':
        if ansible_os == 'meraki':
            result = mc.meraki_get_network_devices(api_key,
                                                   db_path,
                                                   networks=networks,
                                                   orgs=orgs)

    if collector == 'network_device_statuses':
        if ansible_os == 'meraki':
            result = mc.meraki_get_network_device_statuses(db_path, networks)

    if collector == 'organizations':
        if ansible_os == 'meraki':
            result = mc.meraki_get_organizations(api_key)

    if collector == 'org_devices':
        if ansible_os == 'meraki':
            result = mc.meraki_get_org_devices(api_key, db_path, orgs=orgs)

    if collector == 'org_device_statuses':
        if ansible_os == 'meraki':
            tp = total_pages
            result, idx_cols = mc.meraki_get_org_device_statuses(api_key,
                                                                 db_path,
                                                                 orgs=orgs,
                                                                 total_pages=tp
                                                                 )

    if collector == 'org_networks':
        if ansible_os == 'meraki':
            result = mc.meraki_get_org_networks(api_key,
                                                db_path,
                                                orgs=orgs,
                                                use_db=True)

    if collector == 'switch_lldp_neighbors':
        if ansible_os == 'meraki':
            result = mc.meraki_get_switch_lldp_neighbors(db_path)

    if collector == 'switch_port_statuses':
        if ansible_os == 'meraki':
            result = mc.meraki_get_switch_port_statuses(api_key,
                                                        db_path,
                                                        networks)

    if collector == 'switch_port_usages':
        if ansible_os == 'meraki':
            result = mc.meraki_get_switch_port_usages(api_key,
                                                      db_path,
                                                      networks,
                                                      timestamp)

    if collector == 'netbox_get_ipam_prefixes':
        result = nbc.netbox_get_ipam_prefixes(nb_path, nb_token)

    if collector == 'ncm_serial_numbers':
        result = swc.get_ncm_serial_numbers(npm_server,
                                            npm_username,
                                            npm_password)

    if collector == 'npm_containers':
        result = swc.get_npm_containers(npm_server, npm_username, npm_password)

    if collector == 'npm_group_members':
        result = swc.get_npm_group_members(npm_server,
                                           npm_username,
                                           npm_password,
                                           npm_group_name)

    if collector == 'npm_group_names':
        result = swc.get_npm_group_names(npm_server,
                                         npm_username,
                                         npm_password)

    if collector == 'npm_node_ids':
        result = swc.get_npm_node_ids(npm_server, npm_username, npm_password)

    if collector == 'npm_node_ips':
        result = swc.get_npm_node_ips(npm_server, npm_username, npm_password)

    if collector == 'npm_node_machine_types':
        result = swc.get_npm_node_machine_types(npm_server,
                                                npm_username,
                                                npm_password)

    if collector == 'npm_node_os_versions':
        result = swc.get_npm_node_os_versions(npm_server,
                                              npm_username,
                                              npm_password)

    if collector == 'npm_node_vendors':
        result = swc.get_npm_node_vendors(npm_server,
                                          npm_username,
                                          npm_password)

    if collector == 'npm_nodes':
        result = swc.get_npm_nodes(npm_server, npm_username, npm_password)

    if collector == 'all_interfaces':
        if ansible_os == 'paloaltonetworks.panos':
            result = pac.get_all_interfaces(username,
                                            password,
                                            hostgroup,
                                            nm_path,
                                            private_data_dir)

    if collector == 'logical_interfaces':
        if ansible_os == 'paloaltonetworks.panos':
            result = pac.get_logical_interfaces(username,
                                                password,
                                                hostgroup,
                                                nm_path,
                                                private_data_dir)

    if collector == 'physical_interfaces':
        if ansible_os == 'paloaltonetworks.panos':
            result = pac.get_physical_interfaces(username,
                                                 password,
                                                 hostgroup,
                                                 nm_path,
                                                 private_data_dir)

    if collector == 'port_channel_data':
        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_port_channel_data(username,
                                                   password,
                                                   hostgroup,
                                                   play_path,
                                                   private_data_dir)

    if collector == 'vpc_state':
        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_vpc_state(username,
                                           password,
                                           hostgroup,
                                           play_path,
                                           private_data_dir)

    if collector == 'vlans':
        if ansible_os == 'cisco.ios.ios':
            result = cic.ios_get_vlan_db(username,
                                         password,
                                         hostgroup,
                                         play_path,
                                         private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_vlan_db(username,
                                         password,
                                         hostgroup,
                                         play_path,
                                         private_data_dir)

    if collector == 'vrfs':
        if ansible_os == 'cisco.ios.ios':
            result = cic.get_vrfs(username,
                                  password,
                                  hostgroup,
                                  play_path,
                                  private_data_dir)

        if ansible_os == 'cisco.nxos.nxos':
            result = cl.nxos_get_vrfs(username,
                                      password,
                                      hostgroup,
                                      play_path,
                                      private_data_dir)

    # Write the result to the database
    if len(result.columns.to_list()) > 0:
        table_name = f'{ansible_os.split(".")[-1]}_{collector}'
        add_to_db(collector,
                  table_name,
                  result,
                  timestamp,
                  db_path,
                  method,
                  idx_cols)

    return result


def add_to_db(collector,
              table_name,
              result,
              timestamp,
              db_path,
              method='append',
              idx_cols=list()):
    '''
    Adds the output of a collector to the database

    Args:
        collector (str):    The name of the collector
        result (DataFrame): The output of a collector
        timestamp (str):    The timestamp
        db_path (str):      The path to the database
        method (str):       What to do if the database already exists. Options
                            are 'append', 'fail', 'replace'. Defaults to
                            'append'.
        idx_cols (list):    The list of columns to use for indexing the table.
                            Note that this is NOT related to the dataframe
                            index; it is for indexing the sqlite database table

    Returns:
        None
    '''
    # Set the timestamp as the index of the dataframe (this is unrelated to
    # the 'idx_cols' arg)
    new_idx = list()
    for i in range(0, len(result)):
        new_idx.append(timestamp)

    # Display the output to the console
    result['timestamp'] = new_idx
    result = result.set_index('timestamp')

    # Check if the output directory exists. If it does not, then create it.
    exists = hp.check_dir_existence('/'.join(db_path.split('/')[:-1]))
    if not exists:
        hp.create_dir('/'.join(db_path.split('/')[:-1]))

    # Connect to the database
    con = hp.connect_to_db(db_path)
    cur = con.cursor()

    # Get the table schema. This also checks if the table exists, because the
    # length of 'schema' will be 0 if it hasn't been created yet.
    schema = hp.sql_get_table_schema(db_path, table_name)

    # If the table doesn't exist, create it. (Pandas will automatically create
    # the table, but doing it manually allows us to create an auto-incrementing
    # ID column))
    column_list = result.columns.to_list()
    if 'table_id' in column_list:
        column_list.remove('table_id')
        del result['table_id']
    columns = [f'"{c}"' for c in column_list]
    if len(schema) == 0 and len(result) > 0:
        fields = ',\n'.join(columns)
        cur.execute(f'''CREATE TABLE {table_name.upper()} (
                    table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp,
                    {fields}
                    )''')

    # Check if all of the columns in 'result' are in the table schema and add
    # them if they are not. This accounts for a common scenario that happens
    # when device output is inconsistent. For example, on Cisco NXOS devices
    # this command returns different rows if the device is using Layer 3 VPC.
    # 'show vpc brief | begin "vPC domain id" | end "vPC Peer-link status'
    # If the collector is run against devices using Layer 2 VPC, then run again
    # on devices using Layer 3 VPC, an additional column must be added or the
    # table insertion will fail.
    #
    # This scenario is very common, and it's not always possible to
    # future-proof collectors to account for it,
    if len(schema) >= 1:
        for col in column_list:
            if col not in schema['name'].to_list():
                cur.execute(f'ALTER TABLE {table_name} ADD COLUMN "{col}"')

    # from tabulate import tabulate
    # print(tabulate(result, headers='keys', tablefmt='psql'))

    # Add the dataframe to the database
    table = table_name.upper()
    result.to_sql(table, con, if_exists=method)

    # Create the SQL table index, if applicable
    if idx_cols:
        idx_name = f'idx_{table_name.lower()}'
        try:
            cur.execute(f'''CREATE INDEX {idx_name}
                            ON {table_name.upper()} ({','.join(idx_cols)})
                        ''')
        except Exception as e:
            print(f'Caught Exception: {str(e)}')

    con.commit()
    con.close()


def create_parser():
    '''
    Create command line arguments.

    Args:
        None

    Returns:
        args:   Parsed command line arguments
    '''
    # Create the parser for command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--database',
                        help='''The database name. Defaults to
                                YYYY-MM-DD.db.''',
                        default=f'{str(dt.datetime.now()).split()[0]}.db',
                        action='store'
                        )
    parser.add_argument('-o', '--out_dir',
                        help='''The directory to save output to (the filename
                                will be auto-generated). The database will also
                                be saved here.''',
                        default=os.path.expanduser('~/output'),
                        action='store'
                        )
    parser.add_argument('-u', '--username',
                        help='''The username for connecting to the devices. If
                                missing, script will prompt for it.''',
                        default=str(),
                        action='store'
                        )
    parser.add_argument('-P', '--password',
                        help='''The password for connecting to the devices.
                                This is included for external automation, but I
                                do not recommend using it when running the
                                script manually. If you do, then your password
                                could show up in the command history.''',
                        default=str(),
                        action='store'
                        )
    # requiredNamed = parser.add_argument_group('required named arguments')
    parser.add_argument('-c', '--collectors',
                        help='''A comma-delimited list of collectors to
                                run.''',
                        required=True,
                        action='store'
                        )
    parser.add_argument('-H', '--hostgroups',
                        help='A comma-delimited list of hostgroups',
                        default=str(),
                        action='store'
                        )
    parser.add_argument('-n', '--nm_path',
                        help='The path to the Net-Manage repository',
                        required=True,
                        action='store'
                        )
    parser.add_argument('-p', '--private_data_dir',
                        help='''The path to the Ansible private data
                                directory (I.e., the directory
                                containing the 'inventory' and 'env'
                                folders).''',
                        required=True,
                        action='store'
                        )
    args = parser.parse_args()
    return args


def arg_parser(args):
    '''
    Extract system args and assign variable names.

    Args:
        args (args):        Parsed command line arguments

    Returns:
        vars_dict (dict):   A dictionary containing arg variables
    '''
    # Set the collectors
    collectors = [c.strip() for c in args.collectors.split(',')]

    # Set the hostgroups
    hostgroups = [h.strip() for h in args.hostgroups.split(',')]

    # Set the nm_path, out_dir and private_data_dir
    nm_path = os.path.expanduser(args.nm_path)
    out_dir = os.path.expanduser(args.out_dir)
    private_data_dir = os.path.expanduser(args.private_data_dir)

    # Set the user credentials
    # TODO: Add support for using different credentials for each device or
    #       hostgroup. That is a common scenario.
    if args.username:
        username = args.username
    else:
        username = hp.get_username()
    if args.password:
        password = args.password
    else:
        password = hp.get_password()

    # Set the database path
    db = f'{out_dir}/{args.database}'

    return collectors, db, hostgroups, nm_path, out_dir, username, password,\
        private_data_dir
