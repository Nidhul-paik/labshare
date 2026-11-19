@echo off
rem Start LabShare (client). Extra arguments are passed through, e.g.  scripts\client.bat --help
setlocal
set "ROOT=%~dp0.."
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%ROOT%\run_labshare.py" client %*
) else (
    python "%ROOT%\run_labshare.py" client %*
)
endlocal
