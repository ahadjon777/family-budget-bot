@echo off
REM Oilaviy harajatlar botini Windows'da ishga tushirish.
REM Bot kutilmaganda to'xtasa, 10 soniyadan keyin avtomatik qayta ishga tushadi.
chcp 65001 >nul
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo Virtual muhit topilmadi. Avval README.md dagi 3-4 qadamlarni bajaring.
    pause
    exit /b 1
)

if not exist .env (
    echo .env fayli topilmadi. .env.example dan nusxa olib, .env yarating.
    pause
    exit /b 1
)

:loop
echo [%date% %time%] Bot ishga tushmoqda...
venv\Scripts\python.exe main.py
if %errorlevel% equ 130 exit /b 0
if %errorlevel% equ 1 (
    echo Sozlamalarda xato bor. .env faylini tekshiring.
    pause
    exit /b 1
)
echo [%date% %time%] Bot to'xtadi. 10 soniyadan keyin qayta ishga tushadi (to'xtatish: Ctrl+C)...
timeout /t 10 /nobreak >nul
goto loop
