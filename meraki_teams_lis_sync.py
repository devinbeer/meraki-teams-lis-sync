import os
import meraki
from dotenv import load_dotenv
import subprocess
from pathlib import Path
import json

load_dotenv()


def get_meraki_bssids():
    dashboard = meraki.DashboardAPI(suppress_logging=True)

    org_id = os.getenv('MERAKI_ORGANIZATION_ID')
    if not org_id:
        raise ValueError("Missing MERAKI_ORGANIZATION_ID environment variable.")

    try:
        tag = 'VAIGS'
        devices = dashboard.organizations.getOrganizationDevices(
            organizationId=org_id,
            productTypes=['wireless'],
            tags=[tag],
            total_pages='all'
        )
        
        serials = [d['serial'] for d in devices]
        if not serials:
            print(f"No wireless devices found with tag '{tag}'.")
            return
        
        response = dashboard.wireless.getOrganizationWirelessSsidsStatusesByDevice(organizationId=org_id, serials=serials, total_pages='all')
        devices = response['items'] if isinstance(response, dict) else response
        bssid_list = []
        for device in devices:
            ap_name = device.get('name')
            for bss in device.get('basicServiceSets', []):
                ssid = bss.get('ssid', {}).get('name')
                bssid = bss.get('bssid').replace(':','-').upper() # Formats BSSIDs as 'XX-XX-XX-XX-XX-XX' for Teams
                band = bss.get('radio', {}).get('band')

                bssid_list.append([bssid, ap_name+' - '+ssid+' - '+band+'Ghz'])

    except meraki.APIError as e:
        print(f"Meraki API Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return bssid_list


def get_teams_bssids():
    script = Path(__file__).resolve().parent / 'Get-TeamsLisBssids.ps1'
    try:
        result = subprocess.run(['pwsh-preview', '-File', str(script)], capture_output=True, text=True)
        output = result.stdout.splitlines()[9:] # Drop PowerShell output lines before the list of BSSIDs

    except subprocess.CalledProcessError as e:
        print(f"PowerShell exited with code {e.returncode}: {e.stderr}")
    except FileNotFoundError:
        print("'pwsh' was not found on PATH.")

    bssid_list = []
    for entry in output:
        if len(entry) > 1:
            bssid = entry.split(' ', 1)[0]
            description = entry.split(' ', 1)[1]
        else:
            continue
        bssid_list.append([bssid, description])

    return bssid_list


def compare_existing_bssids():
    diff_meraki = [item for item in meraki_bssids if item not in teams_bssids]
    return diff_meraki


def add_bssid_locations():
    # Appends Teams LIS civic address IDs onto each BSSID entry based on AP naming scheme
    new_bssids_list = compare_existing_bssids()

    # Obtain location IDs from environment variables
    loc_edu = os.getenv('TEAMS_LOCATION_ID_1')
    loc_gs = os.getenv('TEAMS_LOCATION_ID_2')
    if not loc_edu or loc_gs:
        raise ValueError("Missing TEAMS_LOCATION_ID environment variable.")
    
    for bssid in new_bssids_list:
        if "di" in bssid[1]:
            bssid.append(loc_edu)
        elif "234" in bssid[1]:
            bssid.append(loc_gs)
        else:
            bssid.append('')
    return new_bssids_list


def update_teams_bssids():
    new_bssids = add_bssid_locations()

    if new_bssids:
        try:
            result = subprocess.run(
                ['pwsh-preview', '-NoProfile', '-File', 'Update-TeamsLisBssids.ps1'],
                input=json.dumps(new_bssids),
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"PowerShell exited with code {e.returncode}: {e.stderr}")
    else:
        print("No new BSSIDs are present.")

        
meraki_bssids = get_meraki_bssids()
teams_bssids = get_teams_bssids()
new_bssids = compare_existing_bssids()

update_teams_bssids()


# TODO
# - Create powershell function to remove BSSIDs not present in Meraki