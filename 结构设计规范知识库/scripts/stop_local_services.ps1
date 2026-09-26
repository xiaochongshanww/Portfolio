[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "High")]
param(
    [int[]]$Ports = @(8000, 5173, 5174, 5175)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path.TrimEnd("\", "/")
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$vitePath = (Join-Path $projectRoot "frontend\node_modules\vite\bin\vite.js").Replace("/", "\")
$configuredPorts = @{
    8000 = "api"
    5173 = "vite"
    5174 = "vite"
    5175 = "vite"
}
$listenersByProcess = @{}
$verifiedProcessIds = [System.Collections.Generic.HashSet[int]]::new()
$seenProcessIds = [System.Collections.Generic.HashSet[int]]::new()

foreach ($listener in (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue)) {
    $port = [int]$listener.LocalPort
    if ($configuredPorts.ContainsKey($port)) {
        $ownerId = [int]$listener.OwningProcess
        if (-not $listenersByProcess.ContainsKey($ownerId)) {
            $listenersByProcess[$ownerId] = [System.Collections.Generic.List[int]]::new()
        }
        $listenersByProcess[$ownerId].Add($port)
    }
}

$selectedPorts = @($Ports | Select-Object -Unique)
foreach ($port in $selectedPorts) {
    if (-not $configuredPorts.ContainsKey($port)) {
        Write-Warning "Port $port is not a configured project service port; skipped."
    }
}

foreach ($processInfo in (Get-CimInstance Win32_Process)) {
    $processId = [int]$processInfo.ProcessId
    $commandLine = [string]$processInfo.CommandLine
    $serviceName = $null
    $requestedPort = $null

    $isProjectApi = [string]::Equals(
        $processInfo.ExecutablePath,
        $pythonPath,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -and $commandLine -match "(?i)(-m\s+|--module\s+)?uvicorn\s+src\.app\.main:app(?:\s|$)"
    $normalizedCommandLine = $commandLine.Replace("/", "\")
    $viteArgumentPattern = '(?i)(?:^|\s)"?' + [regex]::Escape($vitePath) + '"?(?=\s|$)'
    $isProjectVite = [string]::Equals(
        $processInfo.Name,
        "node.exe",
        [System.StringComparison]::OrdinalIgnoreCase
    ) -and $normalizedCommandLine -match $viteArgumentPattern

    if ($isProjectApi) {
        $serviceName = "api"
        $requestedPort = 8000
        if ($commandLine -match "(?i)--port(?:\s+|=)(\d+)") {
            $requestedPort = [int]$Matches[1]
        }
    }
    elseif ($isProjectVite) {
        $serviceName = "vite"
        $requestedPort = 5173
        if ($commandLine -match "(?i)--port(?:\s+|=)(\d+)") {
            $requestedPort = [int]$Matches[1]
        }
    }
    else {
        continue
    }

    $verifiedProcessIds.Add($processId) | Out-Null
    $listeningPorts = @()
    if ($listenersByProcess.ContainsKey($processId)) {
        $listeningPorts = @($listenersByProcess[$processId])
    }

    $matchedPort = $null
    $matchedPort = $listeningPorts | Where-Object {
        ($selectedPorts -contains $_) -and ($configuredPorts[$_] -eq $serviceName)
    } | Select-Object -First 1
    if ($null -eq $matchedPort -and
        $selectedPorts -contains $requestedPort -and
        $configuredPorts[$requestedPort] -eq $serviceName) {
        $matchedPort = $requestedPort
    }

    if ($null -eq $matchedPort) {
        continue
    }
    if (-not $seenProcessIds.Add($processId)) {
        continue
    }

    $state = if ($listeningPorts -contains $matchedPort) { "listener" } else { "orphan process, no listener" }
    $target = "$serviceName $state on port $matchedPort (PID $processId, $($processInfo.Name))"
    if ($PSCmdlet.ShouldProcess($target, "Stop the process tree")) {
        $taskkill = Join-Path $env:SystemRoot "System32\taskkill.exe"
        & $taskkill /PID $processId /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to stop PID $processId (taskkill exit code $LASTEXITCODE)."
        }
        Write-Output "Stopped $target."
    }
}

foreach ($ownerId in $listenersByProcess.Keys) {
    if ($verifiedProcessIds.Contains([int]$ownerId)) {
        continue
    }
    foreach ($port in $listenersByProcess[$ownerId]) {
        if ($selectedPorts -contains $port) {
            $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId" -ErrorAction SilentlyContinue
            if ($null -ne $processInfo) {
                Write-Warning "Port $port is owned by $($processInfo.Name) PID $ownerId, which cannot be verified as this project's service; skipped."
            }
        }
    }
}

if ($seenProcessIds.Count -eq 0) {
    Write-Output "No matching project service processes found on the selected ports."
}
