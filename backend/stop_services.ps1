$ErrorActionPreference = "SilentlyContinue"
Write-Host "Stopping FairServe Services..." -ForegroundColor Yellow

# Function to kill process by port
function Kill-Port($port) {
    $connections = Get-NetTCPConnection -LocalPort $port
    foreach ($conn in $connections) {
        $pid_val = $conn.OwningProcess
        if ($pid_val -gt 0) {
            $proc = Get-Process -Id $pid_val
            if ($proc) {
                Write-Host "Killing process on port $port (PID: $pid_val, Name: $($proc.ProcessName))..."
                Stop-Process -Id $pid_val -Force
            }
        }
    }
}

# Function to kill python scripts by name
function Kill-Script($scriptName) {
    # Use WMI to find command lines containing the script name
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$scriptName*" }
    foreach ($p in $procs) {
        Write-Host "Killing script $scriptName (PID: $($p.ProcessId))..."
        Stop-Process -Id $p.ProcessId -Force
    }
}

# 1. Stop APIs and AgentIQ (Port based)
Kill-Port 8080 # Zone 2 API
Kill-Port 8081 # Zone 1 API
Kill-Port 8005 # AgentIQ

# 2. Stop Background Workers (Script name based)
Kill-Script "intake/process_live.py"
Kill-Script "trigger/discord_bot.py"

Write-Host "Cleanup complete." -ForegroundColor Green
