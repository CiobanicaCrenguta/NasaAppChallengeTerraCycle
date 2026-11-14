# Starts everything the phone app needs on this laptop: the local language model and the server.
#
#   .\start.ps1             start (or restart) both, wait until they answer, run the end-to-end check
#   .\start.ps1 -NoModel    server only; the app then matches questions on keywords
#   .\start.ps1 -NoCheck    skip the end-to-end check
#   .\start.ps1 -Stop       stop both
#
# Logs: ai\runs\serve.log and serve.err (model), backend\cache\server.log and server.err (server).
param([switch]$NoModel, [switch]$NoCheck, [switch]$Stop)

$root = $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'

function Stop-Port($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Wait-Url($url, $seconds) {
    $until = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $until) {
        try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { Start-Sleep -Seconds 2 }
    }
    return $false
}

Stop-Port 8000
Stop-Port 8001
if ($Stop) { 'Stopped.'; exit 0 }

if (-not $NoModel) {
    New-Item -ItemType Directory -Force "$root\ai\runs" | Out-Null
    Start-Process -FilePath "$root\ai\.venv\Scripts\python.exe" -WorkingDirectory "$root\ai" -WindowStyle Hidden `
        -ArgumentList '-m', 'uvicorn', 'serve:app', '--host', '127.0.0.1', '--port', '8001' `
        -RedirectStandardOutput "$root\ai\runs\serve.log" -RedirectStandardError "$root\ai\runs\serve.err"
}
New-Item -ItemType Directory -Force "$root\backend\cache" | Out-Null
Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" -WorkingDirectory "$root\backend" -WindowStyle Hidden `
    -ArgumentList '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000' `
    -RedirectStandardOutput "$root\backend\cache\server.log" -RedirectStandardError "$root\backend\cache\server.err"

if (Wait-Url 'http://127.0.0.1:8000/me' 60) { 'Server:  up on port 8000' }
else { 'Server:  DID NOT START. See backend\cache\server.err'; exit 1 }

if (-not $NoModel) {
    'Model:   loading (about half a minute)...'
    if (Wait-Url 'http://127.0.0.1:8001/health' 180) { 'Model:   up on port 8001' }
    else { 'Model:   DID NOT START. See ai\runs\serve.err. The app still works, on keywords.' }
}

if (-not $NoCheck) {
    ''
    & "$root\backend\.venv\Scripts\python.exe" "$root\backend\test_e2e.py" | Select-Object -Last 1
}

''
'Phone app, in another terminal:'
'  cd app'
'  npx expo start --go --localhost'
'Emulator: adb reverse tcp:8081 tcp:8081 ; adb reverse tcp:8000 tcp:8000'
