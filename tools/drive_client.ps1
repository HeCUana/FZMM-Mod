#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Drive the running Minecraft client and capture the screen.

.DESCRIPTION
    Minecraft 26.3 uses SDL3 for windowing, so WM_KEY messages are not enough;
    SendInput with hardware scan codes is used instead, which SDL picks up at the
    OS level.

.EXAMPLE
    .\tools\drive_client.ps1 -Action Capture -Output run\shots\main.png
    .\tools\drive_client.ps1 -Action Keys -Keys Z
#>
param(
    [ValidateSet('Capture', 'Keys', 'Click', 'Focus')]
    [string]$Action = 'Capture',
    [string]$Output = 'run\shots\shot.png',
    [string]$Keys = '',
    [int]$X = 0,
    [int]$Y = 0,
    [string]$WindowTitleLike = 'Minecraft'
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

    [DllImport("user32.dll", SetLastError = true)]
    static extern uint SendInput(uint n, INPUT[] inputs, int size);

    const uint INPUT_KEYBOARD = 1, KEYEVENTF_KEYUP = 0x0002, KEYEVENTF_SCANCODE = 0x0008;

    [StructLayout(LayoutKind.Sequential)]
    struct INPUT { public uint type; public InputUnion U; }
    [StructLayout(LayoutKind.Explicit)]
    struct InputUnion { [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)]
    struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }

    public static void Key(ushort scan, bool up) {
        var inputs = new INPUT[1];
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].U.ki.wScan = scan;
        inputs[0].U.ki.dwFlags = KEYEVENTF_SCANCODE | (up ? KEYEVENTF_KEYUP : 0);
        SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
    }

    public static void Click() {
        mouse_event(0x0002, 0, 0, 0, IntPtr.Zero);
        mouse_event(0x0004, 0, 0, 0, IntPtr.Zero);
    }
}
"@

# US layout scan codes for the keys we need
$ScanCodes = @{
    'Z' = 0x2C; 'Y' = 0x15; 'X' = 0x2B; 'W' = 0x11; 'A' = 0x1E; 'S' = 0x1F
    'Q' = 0x10; 'E' = 0x12; 'R' = 0x13; 'T' = 0x14; 'U' = 0x16; 'I' = 0x17
    'O' = 0x18; 'P' = 0x19; 'F' = 0x21; 'G' = 0x22; 'H' = 0x23; 'J' = 0x24
    'K' = 0x25; 'L' = 0x26
    'ENTER' = 0x1C; 'ESC' = 0x01; 'SPACE' = 0x39; 'TAB' = 0x0F
    '1' = 0x02; '2' = 0x03; '3' = 0x04; '4' = 0x05; '5' = 0x06; '6' = 0x07
    'DOWN' = 0x50; 'UP' = 0x48; 'LEFT' = 0x4B; 'RIGHT' = 0x4D
}

function Get-MinecraftWindow {
    $p = Get-Process java -ErrorAction SilentlyContinue |
         Where-Object { $_.MainWindowTitle -like "*$WindowTitleLike*" } |
         Select-Object -First 1
    if ($p) { return $p.MainWindowHandle }
    return [IntPtr]::Zero
}

function Save-Screen([string]$path) {
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output "saved $path ($($b.Width)x$($b.Height))"
}

switch ($Action) {
    'Focus' {
        $h = Get-MinecraftWindow
        if ($h -eq [IntPtr]::Zero) { Write-Output 'NO_WINDOW'; break }
        [void][Win]::ShowWindow($h, 9)   # SW_RESTORE
        [void][Win]::SetForegroundWindow($h)
        Start-Sleep -Milliseconds 700
        Write-Output ("FOCUSED foreground=" + [Win]::GetForegroundWindow() + " target=" + $h)
    }
    'Keys' {
        $h = Get-MinecraftWindow
        if ($h -eq [IntPtr]::Zero) { Write-Output 'NO_WINDOW'; break }
        [void][Win]::ShowWindow($h, 9)
        [void][Win]::SetForegroundWindow($h)
        Start-Sleep -Milliseconds 500
        foreach ($k in ($Keys -split '\s+' | Where-Object { $_ })) {
            $up = $k.ToUpper()
            if (-not $ScanCodes.ContainsKey($up)) { Write-Output "UNKNOWN_KEY $k"; continue }
            $code = [ushort]$ScanCodes[$up]
            [Win]::Key($code, $false)
            Start-Sleep -Milliseconds 60
            [Win]::Key($code, $true)
            Start-Sleep -Milliseconds 220
        }
        Write-Output ("SENT: " + $Keys)
    }
    'Click' {
        $h = Get-MinecraftWindow
        if ($h -eq [IntPtr]::Zero) { Write-Output 'NO_WINDOW'; break }
        [void][Win]::ShowWindow($h, 9)
        [void][Win]::SetForegroundWindow($h)
        Start-Sleep -Milliseconds 400
        [void][Win]::SetCursorPos($X, $Y)
        Start-Sleep -Milliseconds 150
        [Win]::Click()
        Write-Output ("CLICKED $X,$Y")
    }
    'Capture' {
        Save-Screen $Output
    }
}
