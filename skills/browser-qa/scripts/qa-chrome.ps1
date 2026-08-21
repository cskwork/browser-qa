# Launch (or reuse) a Chrome with CDP open, on a profile of its own.
#   powershell -File qa-chrome.ps1 [-Port 9333] [-Url about:blank]
param([int]$Port = 9333, [string]$Url = "about:blank",
      [string]$Profile = "$env:USERPROFILE\.superqa\qa-chrome-profile")

$probe = "http://127.0.0.1:$Port/json/version"
try { Invoke-RestMethod -Uri $probe -TimeoutSec 2 | Out-Null
      Write-Host "reusing Chrome on http://127.0.0.1:$Port"; exit 0 } catch {}

$candidates = @(
  "$env:USERPROFILE\.agent-browser\browsers\chrome-*\chrome-win64\chrome.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
)
$chrome = $candidates | ForEach-Object { Get-Item $_ -ErrorAction SilentlyContinue } |
          Select-Object -First 1
if (-not $chrome) { Write-Error "no Chrome found; set -Chrome path"; exit 1 }

New-Item -ItemType Directory -Force -Path $Profile | Out-Null
Start-Process -FilePath $chrome.FullName -ArgumentList `
  "--remote-debugging-port=$Port", "--user-data-dir=$Profile",
  "--no-first-run", "--no-default-browser-check", $Url

foreach ($i in 1..30) {
  try { Invoke-RestMethod -Uri $probe -TimeoutSec 2 | Out-Null
        Write-Host "Chrome ready on http://127.0.0.1:$Port (profile: $Profile)"; exit 0 } catch {}
  Start-Sleep -Milliseconds 500
}
Write-Error "Chrome did not open CDP on $Port"; exit 1
