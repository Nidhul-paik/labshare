@echo off
rem Start LabShare (host). Extra arguments are passed through, e.g.  scripts\host.bat --help
setlocal
set "ROOT=%~dp0.."
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%ROOT%\run_labshare.py" host %*
) else (
    python "%ROOT%\run_labshare.py" host %*
)
endlocal
