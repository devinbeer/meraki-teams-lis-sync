Import-Module MicrosoftTeams

Write-Host "Launching Microsoft Teams authentication wrapper..."
try {
    Connect-MicrosoftTeams -DisableWAM
}
catch {
    Write-Host "[Error] Login attempt failed or authentication window was closed." -ForegroundColor Red
    Write-Host "Error Details: \$_" -ForegroundColor DarkGray
}

function Add-TeamsLisBssids {
    param([object[]]$Bssids)

    foreach ($item in $new_bssids) {
        $BSSID = $item[0]
        $Description = $item[1]
        $LocationID = $item[2]

        #"{0} | {1} | {2}" -f $BSSID, $Description, $LocationID
        $ExistingAP = Get-CsOnlineLisWirelessAccessPoint -BSSID $BSSID -ErrorAction SilentlyContinue
        if ($ExistingAP -and $ExistingAP.Description -eq $Description -and $ExistingAP.LocationID -eq $LocationID) {
            Write-Host "Complete duplicate match found; skipping BSSID." -ForegroundColor Gray
            }
        else {
            try {
                Set-CsOnlineLisWirelessAccessPoint -BSSID $BSSID -Description $Description -LocationId $LocationID -ErrorAction Stop
                "OK: $($BSSID)"
            } catch {
                "FAILED: $($BSSID) - $($_.Exception.Message)"
            }
        }
    }
}

$new_bssids = [Console]::In.ReadToEnd() | ConvertFrom-Json
Add-TeamsLisBssids