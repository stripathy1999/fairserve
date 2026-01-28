$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Starting FairServe Services..." -ForegroundColor Green

# 1. Zone 2 API (Port 8080)
Write-Host "Launching Zone 2 API (Port 8080)..."
Start-Process -FilePath "python" -ArgumentList "-m api.app" -WindowStyle Minimized

# 2. Zone 1 API (Port 8081)
Write-Host "Launching Zone 1 API (Port 8081)..."
Start-Process -FilePath "python" -ArgumentList "-m api.main" -WindowStyle Minimized

# 3. Live Data Processor
Write-Host "Launching Live Data Processor..."
Start-Process -FilePath "python" -ArgumentList "intake/process_live.py" -WindowStyle Minimized

# 4. Discord Bot
Write-Host "Launching Discord Bot..."
Start-Process -FilePath "python" -ArgumentList "trigger/discord_bot.py" -WindowStyle Minimized

# 5. AgentIQ
Write-Host "Launching AgentIQ (Port 8005)..."
Start-Process -FilePath "nat" -ArgumentList "serve --config_file agentiq/configs/fairserve_workflow.yml --port 8005" -WindowStyle Minimized

Write-Host "All services started!" -ForegroundColor Cyan
Write-Host "Press any key to exit this launcher (services will keep running)..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
