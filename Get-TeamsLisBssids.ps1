Import-Module MicrosoftTeams

Write-Host "Launching Microsoft Teams authentication wrapper..."

try {
    Connect-MicrosoftTeams -DisableWAM
}
catch {
    Write-Host "[Error] Login attempt failed or authentication window was closed." -ForegroundColor Red
    Write-Host "Error Details: \$_" -ForegroundColor DarkGray
}

$TeamsBssids = Get-CsOnlineLisWirelessAccessPoint | Select-Object -Property BSSID, Description | Format-Table
$TeamsBssids