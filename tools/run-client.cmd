@echo off
REM Launches the MC 26.3 client and auto-joins the local test server.
REM Keep this file pure ASCII: cmd.exe parses .bat files using the system OEM
REM code page (GBK on zh-CN), so any non-ASCII character corrupts the script.
set JAVA_HOME=C:\Program Files\Zulu\zulu-26
cd /d C:\Users\Administrator\Desktop\mod\FZMM-Mod-0.2.20-26.2
call "C:\Users\Administrator\.gradle\wrapper\dists\gradle-9.5.1-bin\iq79hdu3mqx29lgffhp8bfmx\gradle-9.5.1\bin\gradle.bat" runClientAuto --project-dir "C:\Users\Administrator\Desktop\mod\FZMM-Mod-0.2.20-26.2" --console=plain --no-daemon
