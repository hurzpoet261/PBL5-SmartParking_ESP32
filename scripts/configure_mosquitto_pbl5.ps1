$conf = 'C:\Program Files\Mosquitto\mosquitto.conf'
$backup = 'C:\Program Files\Mosquitto\mosquitto.conf.pbl5-backup'

if (!(Test-Path -LiteralPath $conf)) {
    throw "Mosquitto config not found: $conf"
}

if (!(Test-Path -LiteralPath $backup)) {
    Copy-Item -LiteralPath $conf -Destination $backup
    Write-Host "Backed up config to $backup"
}

$text = Get-Content -LiteralPath $conf -Raw
if ($text -notmatch 'PBL5 Smart Parking local MQTT') {
    Add-Content -LiteralPath $conf -Value ''
    Add-Content -LiteralPath $conf -Value '# PBL5 Smart Parking local MQTT'
    Add-Content -LiteralPath $conf -Value 'listener 1883 0.0.0.0'
    Add-Content -LiteralPath $conf -Value 'allow_anonymous true'
    Write-Host 'Added PBL5 MQTT LAN listener.'
} else {
    Write-Host 'PBL5 MQTT LAN listener already exists.'
}

Restart-Service mosquitto -Force
Start-Sleep -Seconds 2
netstat -ano | findstr ':1883'
