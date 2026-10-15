# Meraki to Teams LIS Sync

Scripts that pull wireless access point (AP) BSSIDs from the Cisco Meraki Dashboard API and add them to the Microsoft Teams Location Information Service (LIS) as wireless access point entries, so Teams can associate each BSSID with an emergency (E911) location.

A Python script is the main entry point. It gathers BSSIDs from Meraki, reads the BSSIDs already in Teams, works out which are new, and hands those to a PowerShell script that writes them to Teams.

> **Personal use:** This repository is intended for personal use. It is shared as-is, is tailored to a specific environment, and is not designed or supported as a general-purpose tool.

> **Status:** Work in progress. See [Known Quirks](#known-quirks) and [Roadmap](#roadmap).

## How It Works

1. **Gather from Meraki** (`get_meraki_bssids()`): Lists wireless devices in the organization that carry a specific Meraki tag, then retrieves each device's SSID statuses. Every BSSID is formatted as `XX-XX-XX-XX-XX-XX` (the format Teams expects) and paired with a description built as `<AP name> - <SSID> - <band>Ghz`.
2. **Gather from Teams** (`get_teams_bssids()`): Runs `Get-TeamsLisBssids.ps1`, which connects to Teams and lists the existing LIS wireless access points (BSSID and description). Python parses the printed table into `[BSSID, description]` pairs.
3. **Compare** (`compare_existing_bssids()`): Keeps the Meraki entries whose `[BSSID, description]` pair is not already present in Teams.
4. **Assign locations** (`add_bssid_locations()`): Appends a Teams LIS location ID to each new entry, chosen by matching text in the description (see [Configuration](#configuration)).
5. **Push to Teams** (`update_teams_bssids()`): Sends the new entries as JSON over stdin to `Update-TeamsLisBssids.ps1`, which connects to Teams and, for each entry:
   - skips it if Teams already has that BSSID with the same description and location ID;
   - otherwise calls `Set-CsOnlineLisWirelessAccessPoint`, which creates the entry or replaces an existing entry with the same BSSID ([Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/teams/set-csonlineliswirelessaccesspoint));
   - prints `OK: <BSSID>` or `FAILED: <BSSID> - <error>`.

## Files

| File | Purpose |
|---|---|
| `meraki_teams_lis_sync.py` | Main script. Orchestrates the whole process. |
| `Get-TeamsLisBssids.ps1` | Connects to Teams and prints existing LIS BSSIDs and descriptions. |
| `Update-TeamsLisBssids.ps1` | Reads new BSSIDs as JSON from stdin and writes them to Teams. |

## Requirements

- Python 3 with the following packages:
  - [`meraki`](https://pypi.org/project/meraki/) (Meraki Dashboard API library)
  - `python-dotenv`
- PowerShell 7 available on `PATH` as `pwsh-preview` (see [Known Quirks](#known-quirks))
- The [MicrosoftTeams PowerShell module](https://learn.microsoft.com/en-us/powershell/module/teams/) (`Install-Module MicrosoftTeams`)
- A Meraki Dashboard API key with access to your organization
- A Teams account permitted to read and manage LIS wireless access points

## Configuration

The Python script loads settings from a `.env` file in the working directory:

```dotenv
MERAKI_DASHBOARD_API_KEY=your-meraki-api-key
MERAKI_ORGANIZATION_ID=your-meraki-organization-id
TEAMS_LOCATION_ID_1=your-first-teams-lis-location-guid
TEAMS_LOCATION_ID_2=your-second-teams-lis-location-guid
```

- `MERAKI_DASHBOARD_API_KEY` is read automatically by the Meraki library ([PyPI](https://pypi.org/project/meraki/)).
- `TEAMS_LOCATION_ID_*` are the GUIDs of existing Teams LIS locations.

Some values are currently hardcoded in `meraki_teams_lis_sync.py` and must be edited for your environment:

| What | Where | Current behavior |
|---|---|---|
| Meraki device tag | `tag` variable in `get_meraki_bssids()` | Only wireless devices with this tag are processed. |
| Location matching | `add_bssid_locations()` | Description containing `di` gets `TEAMS_LOCATION_ID_1`; containing `234` gets `TEAMS_LOCATION_ID_2`; anything else gets an empty location ID. |
| PowerShell executable | `get_teams_bssids()` and `update_teams_bssids()` | `pwsh-preview` |

## Usage

Run from the repository directory (see [Known Quirks](#known-quirks)):

```bash
python meraki_teams_lis_sync.py
```

You will be prompted to sign in to Microsoft Teams (twice, see below). If no new BSSIDs are found, the script prints `No new BSSIDs are present.` and does not call the update script.

## Known Quirks

- **Teams authentication is requested twice per run.** `Get-TeamsLisBssids.ps1` and `Update-TeamsLisBssids.ps1` each run in their own PowerShell process and each calls `Connect-MicrosoftTeams -DisableWAM`, so the sign-in prompt appears once per script. *This will be fixed in a future update.*
- **Teams output is parsed by line position.** `get_teams_bssids()` discards the first 9 lines of the Get script's output (sign-in messages and table header) and splits each remaining line on the first space. Changing the Get script's output, or a module or sign-in message that adds or removes lines, can break parsing.
- **Run from the repository directory.** The Get script is located relative to the Python file, but the Update script is referenced by a relative path, so the working directory must contain `Update-TeamsLisBssids.ps1`.
- **APs that match no location rule get an empty location ID.** `Set-CsOnlineLisWirelessAccessPoint` requires a location ID ([Microsoft Learn](https://learn.microsoft.com/en-us/powershell/module/teams/set-csonlineliswirelessaccesspoint)), so these entries are expected to be reported as `FAILED`.
- **Matching is on the exact description.** An entry is treated as new when either its BSSID or its description differs from what Teams returns. A changed description on an existing BSSID is therefore pushed as an update.
- **Site-specific settings are hardcoded** (tag, location matching rules, PowerShell executable name). See [Configuration](#configuration).

## Roadmap

- Fix the duplicate Teams authentication prompt.
- Add a PowerShell function to remove BSSIDs from Teams that are no longer present in Meraki. Until then, entries removed or renamed in Meraki are never deleted from Teams.
