$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "  Lumen" -ForegroundColor Cyan -NoNewline
Write-Host " - starting servers..." -ForegroundColor Gray
Write-Host ""

# Launch backend in its own PowerShell window.
# -PassThru returns the spawned process so we can track its PID.
$backCmd = @(
    '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "Write-Host '[Backend]' -ForegroundColor Cyan; " +
    "Set-Location '$root'; " +
    ".\venv\Scripts\Activate.ps1; " +
    "Set-Location backend; " +
    "python app.py"
)
$back = Start-Process powershell -ArgumentList $backCmd -PassThru

# Launch frontend in its own PowerShell window.
$frontCmd = @(
    '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "Write-Host '[Frontend]' -ForegroundColor Green; " +
    "Set-Location '$root\frontend'; " +
    "npm run dev"
)
$front = Start-Process powershell -ArgumentList $frontCmd -PassThru

Write-Host "  Backend  " -ForegroundColor Cyan -NoNewline
Write-Host "http://localhost:5000   (PID $($back.Id))" -ForegroundColor Gray
Write-Host "  Frontend " -ForegroundColor Green -NoNewline
Write-Host "http://localhost:5173   (PID $($front.Id))" -ForegroundColor Gray
Write-Host ""
Write-Host "  Press any key to stop both servers and close windows." -ForegroundColor Yellow
Write-Host ""

$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

Write-Host "  Stopping servers..." -ForegroundColor Red

# /T kills the entire process tree (python.exe + node.exe children included).
taskkill /F /T /PID $back.Id  2>$null | Out-Null
taskkill /F /T /PID $front.Id 2>$null | Out-Null

Write-Host "  Done." -ForegroundColor Green
Start-Sleep -Seconds 1
