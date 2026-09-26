[CmdletBinding()]
param(
    [string]$OutputPath = "",
    [string]$JobId = "",
    [ValidateRange(2, 60)]
    [int]$IntervalSeconds = 5,
    [ValidateRange(0, 86400)]
    [int]$DurationSeconds = 0
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $repoRoot "data/diagnostics/mineru-resources-$timestamp.csv"
}
$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $OutputPath) {
    throw "输出文件已存在，为避免覆盖请指定新路径：$OutputPath"
}
$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$jobRecordPath = ""
if (-not [string]::IsNullOrWhiteSpace($JobId)) {
    if ($JobId -notmatch "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$") {
        throw "非法任务 ID：$JobId"
    }
    $jobRecordPath = Join-Path $repoRoot "data/jobs/$JobId.json"
}

$logicalProcessorCount = [Environment]::ProcessorCount
$previousCpuTimes = @{}
$previousProcessSampleAt = $null
$runClock = [System.Diagnostics.Stopwatch]::StartNew()
$gpuQueryAvailable = $null -ne (Get-Command "nvidia-smi" -ErrorAction SilentlyContinue)
if (-not $gpuQueryAvailable) {
    Write-Warning "未找到 nvidia-smi；仍会记录系统和 MinerU 进程指标，GPU 列将为空。"
}
Write-Host "开始采样：$OutputPath（间隔 ${IntervalSeconds}s；Ctrl+C 停止）"

function Get-MineruProcessTree {
    $allProcesses = @(Get-CimInstance -ClassName Win32_Process)
    $seedProcesses = @(
        $allProcesses | Where-Object {
            $processName = [string]$_.Name
            $isMineruCli = $processName -match "^(?i:magic-pdf|mineru)(\.exe)?$"
            $isMineruPython = $processName -match '^(?i:python|pythonw)(\d+)?\.exe$' -and
                $_.CommandLine -match '(?i)(?:magic[-_]pdf|mineru)'
            $_.ProcessId -ne $PID -and ($isMineruCli -or $isMineruPython)
        }
    )

    $tracked = @{}
    foreach ($process in $seedProcesses) {
        $tracked[[string]$process.ProcessId] = $true
    }
    # The CLI launcher may spawn Python workers; include its descendants in the sample.
    do {
        $foundChild = $false
        foreach ($process in $allProcesses) {
            $processId = [string]$process.ProcessId
            $parentId = [string]$process.ParentProcessId
            if (-not $tracked.ContainsKey($processId) -and $tracked.ContainsKey($parentId)) {
                $tracked[$processId] = $true
                $foundChild = $true
            }
        }
    } while ($foundChild)

    return @($allProcesses | Where-Object { $tracked.ContainsKey([string]$_.ProcessId) })
}

function Get-SystemCpuPercent {
    try {
        $counter = Get-CimInstance -ClassName Win32_PerfFormattedData_PerfOS_Processor `
            -Filter "Name='_Total'"
        return [double]$counter.PercentProcessorTime
    }
    catch {
        return $null
    }
}

function Get-GpuMetrics {
    if (-not $gpuQueryAvailable) {
        return ""
    }
    try {
        $result = @(& nvidia-smi `
            --query-gpu=timestamp,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks.sm,power.draw `
            --format=csv,noheader,nounits 2>$null)
        if ($LASTEXITCODE -ne 0) {
            return ""
        }
        return (($result | ForEach-Object { ([string]$_).Trim() }) -join "; ")
    }
    catch {
        return ""
    }
}

function Get-JobProgress {
    if ([string]::IsNullOrWhiteSpace($jobRecordPath) -or
        -not (Test-Path -LiteralPath $jobRecordPath)) {
        return $null
    }
    try {
        $job = Get-Content -LiteralPath $jobRecordPath -Raw | ConvertFrom-Json
        $progress = $job.progress
        if ($null -eq $progress) {
            return $null
        }
        return [pscustomobject]@{
            JobStatus = [string]$job.status
            JobStep = [string]$job.step
            JobMessage = [string]$progress.message
            PageCurrent = $progress.page_current
            PageTotal = $progress.page_total
            MineruStage = [string]$progress.mineru_stage_progress.stage
            MineruStageCurrent = $progress.mineru_stage_progress.current
            MineruStageTotal = $progress.mineru_stage_progress.total
            MineruStageElapsedSeconds = $progress.mineru_stage_progress.elapsed_seconds
            MineruStageRemainingSeconds = $progress.mineru_stage_progress.estimated_remaining_seconds
            MineruSecondsPerItem = $progress.mineru_stage_progress.seconds_per_item
        }
    }
    catch {
        return $null
    }
}

while ($true) {
    $sampleStarted = [System.Diagnostics.Stopwatch]::StartNew()
    $now = [DateTime]::UtcNow
    $processSampleAt = $runClock.Elapsed.TotalSeconds
    $elapsedSeconds = if ($null -eq $previousProcessSampleAt) {
        0.0
    }
    else {
        $processSampleAt - [double]$previousProcessSampleAt
    }

    $processTree = @(Get-MineruProcessTree)
    $processRows = @()
    $treeCpuSeconds = 0.0
    $treeWorkingSetBytes = 0.0
    $hasProcessCpuSample = $false
    foreach ($process in $processTree) {
        $cpuTicks = [double]$process.KernelModeTime + [double]$process.UserModeTime
        $cpuSeconds = $null
        $cpuPercentOneCore = $null
        $key = [string]$process.ProcessId
        if ($elapsedSeconds -gt 0 -and $previousCpuTimes.ContainsKey($key)) {
            $deltaTicks = [Math]::Max(0.0, $cpuTicks - [double]$previousCpuTimes[$key])
            $cpuSeconds = $deltaTicks / 10000000.0
            $cpuPercentOneCore = [Math]::Round($cpuSeconds / $elapsedSeconds * 100.0, 1)
            $treeCpuSeconds += $cpuSeconds
            $hasProcessCpuSample = $true
        }
        $previousCpuTimes[$key] = $cpuTicks
        $workingSetBytes = [double]$process.WorkingSetSize
        $treeWorkingSetBytes += $workingSetBytes
        $processRows += [pscustomobject]@{
            pid = [int]$process.ProcessId
            name = [string]$process.Name
            cpu_percent_one_core = $cpuPercentOneCore
            working_set_mb = [Math]::Round($workingSetBytes / 1MB, 1)
        }
    }

    $treeCpuPercent = $null
    if ($hasProcessCpuSample) {
        # Report the process tree's share of total host capacity, normalized by logical CPUs.
        $treeCpuPercent = [Math]::Round(
            $treeCpuSeconds / $elapsedSeconds / $logicalProcessorCount * 100.0,
            1
        )
    }
    $jobProgress = Get-JobProgress
    $row = [pscustomobject]@{
        sample_utc = $now.ToString("o")
        sample_interval_seconds = if ($elapsedSeconds -gt 0) {
            [Math]::Round($elapsedSeconds, 3)
        }
        else {
            ""
        }
        system_cpu_percent = Get-SystemCpuPercent
        logical_processors = $logicalProcessorCount
        mineru_tree_cpu_percent_of_system = $treeCpuPercent
        mineru_tree_working_set_mb = [Math]::Round($treeWorkingSetBytes / 1MB, 1)
        mineru_processes = ConvertTo-Json -InputObject $processRows -Compress -Depth 4
        gpu_metrics_nvidia_smi = Get-GpuMetrics
        job_id = $JobId
        job_status = if ($jobProgress) { $jobProgress.JobStatus } else { "" }
        job_step = if ($jobProgress) { $jobProgress.JobStep } else { "" }
        job_message = if ($jobProgress) { $jobProgress.JobMessage } else { "" }
        page_current = if ($jobProgress) { $jobProgress.PageCurrent } else { "" }
        page_total = if ($jobProgress) { $jobProgress.PageTotal } else { "" }
        mineru_stage = if ($jobProgress) { $jobProgress.MineruStage } else { "" }
        mineru_stage_current = if ($jobProgress) { $jobProgress.MineruStageCurrent } else { "" }
        mineru_stage_total = if ($jobProgress) { $jobProgress.MineruStageTotal } else { "" }
        mineru_stage_elapsed_seconds = if ($jobProgress) { $jobProgress.MineruStageElapsedSeconds } else { "" }
        mineru_stage_remaining_seconds = if ($jobProgress) { $jobProgress.MineruStageRemainingSeconds } else { "" }
        mineru_seconds_per_item = if ($jobProgress) { $jobProgress.MineruSecondsPerItem } else { "" }
    }
    $row | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Append -Encoding UTF8
    $previousProcessSampleAt = $processSampleAt

    if ($jobProgress -and $jobProgress.JobStatus -in @("succeeded", "failed", "cancelled", "canceled")) {
        break
    }
    if ($DurationSeconds -gt 0 -and $runClock.Elapsed.TotalSeconds -ge $DurationSeconds) {
        break
    }
    $sleepMilliseconds = [Math]::Max(
        0,
        [int](($IntervalSeconds - $sampleStarted.Elapsed.TotalSeconds) * 1000)
    )
    if ($sleepMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $sleepMilliseconds
    }
}

Write-Host "采样结束。CSV：$OutputPath"
