@echo off
rem bt-test.ps1 runs without changing the PowerShell script policy
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bt-test.ps1" %*
