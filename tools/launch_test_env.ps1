#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch the MC 26.3 dedicated server and/or client detached from the calling
    process tree, so that they survive the agent's tool-call cleanup.

.PARAMETER Target
    'server', 'client' or 'both'
#>
param(
    [ValidateSet('server', 'client', 'both')]
    [string]$Target = 'both'
)

$ErrorActionPreference = 'Stop'
$project = 'C:\Users\Administrator\Desktop\mod\FZMM-Mod-0.2.20-26.2'
$gradle = "$env:USERPROFILE\.gradle\wrapper\dists\gradle-9.5.1-bin\iq79hdu3mqx29lgffhp8bfmx\gradle-9.5.1\bin\gradle.bat"
$env:JAVA_HOME = 'C:\Program Files\Zulu\zulu-26'

function Start-Detached([string]$task, [string]$outFile, [string]$errFile) {
    $cmd = "`"$gradle`" $task --project-dir `"$project`" --console=plain --no-daemon"
    $p = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', $cmd `
        -WorkingDirectory $project `
        -RedirectStandardOutput $outFile `
        -RedirectStandardError $errFile `
        -WindowStyle Hidden `
        -PassThru
    Write-Output ("started {0} pid={1} -> {2}" -f $task, $p.Id, $outFile)
}

if ($Target -in @('server', 'both')) {
    Start-Detached 'runServer' "$project\run-server.out.log" "$project\run-server.err.log"
}
if ($Target -in @('client', 'both')) {
    Start-Detached 'runClientAuto' "$project\run-client.out.log" "$project\run-client.err.log"
}
