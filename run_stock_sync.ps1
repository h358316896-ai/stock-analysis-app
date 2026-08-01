$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$log = Join-Path $repo "stock-sync.log"
$python = "python"

Set-Location -LiteralPath $repo
"[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Stock sync started" | Add-Content -LiteralPath $log -Encoding UTF8

try {
    $syncOutput = & $python -u sync_stock_names.py --market cn 2>&1
    $syncExitCode = $LASTEXITCODE
    $syncOutput | ForEach-Object {
        $_ | Out-File -LiteralPath $log -Append -Encoding utf8
        Write-Output $_
    }
    if ($syncExitCode -ne 0) {
        throw "Stock sync exited with code $syncExitCode"
    }

    & $python -m py_compile stock_names.py sync_stock_names.py
    if ($LASTEXITCODE -ne 0) {
        throw "Generated module validation failed"
    }

    & git add -- stock_names.py
    & git diff --cached --quiet -- stock_names.py
    if ($LASTEXITCODE -eq 0) {
        "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] No stock-list changes" |
            Add-Content -LiteralPath $log -Encoding UTF8
        exit 0
    }

    & git commit -m "chore: sync stock names"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not commit synchronized stock list"
    }

    $ssh = "C:/Windows/System32/OpenSSH/ssh.exe"
    $key = (Join-Path $env:USERPROFILE ".ssh/id_ed25519").Replace("\", "/")
    $knownHosts = (Join-Path $env:USERPROFILE ".ssh/known_hosts").Replace("\", "/")
    $env:GIT_SSH_COMMAND = "$ssh -i $key -o UserKnownHostsFile=$knownHosts -o BatchMode=yes"
    & git push git@github.com:h358316896-ai/stock-analysis-app.git main
    if ($LASTEXITCODE -ne 0) {
        throw "Could not push synchronized stock list"
    }

    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Stock sync completed and pushed" |
        Add-Content -LiteralPath $log -Encoding UTF8
}
catch {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] FAILED: $($_.Exception.Message)" |
        Add-Content -LiteralPath $log -Encoding UTF8
    exit 1
}
