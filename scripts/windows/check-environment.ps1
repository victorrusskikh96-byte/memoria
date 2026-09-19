[CmdletBinding()]
param(
    [string]$OutputPath
)

$ErrorActionPreference = "Continue"

function Command-Version([string]$Name, [string[]]$Arguments) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) { return "not found" }
    try {
        $result = & $Name @Arguments 2>&1 | Select-Object -First 1
        return [string]$result
    } catch {
        return "installed; version check failed"
    }
}

$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$wslStatus = if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    (wsl.exe --status 2>&1 | Out-String).Trim()
} else {
    "not found"
}

$report = [ordered]@{
    TimestampUtc = (Get-Date).ToUniversalTime().ToString("o")
    OperatingSystem = $os.Caption
    Version = $os.Version
    BuildNumber = $os.BuildNumber
    Architecture = $os.OSArchitecture
    MemoryGB = [math]::Round($computer.TotalPhysicalMemory / 1GB, 1)
    VirtualizationFirmwareEnabled = $cpu.VirtualizationFirmwareEnabled
    HypervisorPresent = $computer.HypervisorPresent
    Winget = Command-Version "winget" @("--version")
    Git = Command-Version "git" @("--version")
    Uv = Command-Version "uv" @("--version")
    Python = Command-Version "python" @("--version")
    Docker = Command-Version "docker" @("--version")
    DockerCompose = Command-Version "docker" @("compose", "version")
    WslStatus = $wslStatus
}

$text = $report.GetEnumerator() | ForEach-Object { "{0}: {1}" -f $_.Key, $_.Value }
$text | Write-Output

if ($OutputPath) {
    $directory = Split-Path -Parent $OutputPath
    if ($directory -and -not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $text | Set-Content -Path $OutputPath -Encoding UTF8
    Write-Output "Safe environment report saved to: $OutputPath"
}
