@echo off
echo.
echo ============================================================
echo   ECODRONES - Deteniendo TODOS los servicios
echo ============================================================
echo.

REM 1. Detener procesos Python (simulador, monitor, dashboard)
echo [1/3] Deteniendo procesos Python...
taskkill /fi "WindowTitle eq EcoDrones - Simulador*" /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Monitor*"   /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Dashboard*" /f >nul 2>&1
REM Matar cualquier proceso python que use nuestros scripts
taskkill /f /im python.exe /fi "WindowTitle eq *simulador*" >nul 2>&1
taskkill /f /im python.exe /fi "WindowTitle eq *monitor*" >nul 2>&1
taskkill /f /im python.exe /fi "WindowTitle eq *dashboard*" >nul 2>&1
echo       Procesos Python detenidos.

REM 2. Detener contenedor MongoDB
echo.
echo [2/3] Deteniendo MongoDB...
docker stop mongodb >nul 2>&1
if %errorlevel% equ 0 (
    echo       MongoDB detenido correctamente.
) else (
    REM Intentar por puerto por si el nombre es diferente
    for /f "tokens=*" %%i in ('docker ps -q --filter "publish=27017" 2^>nul') do (
        docker stop %%i >nul 2>&1
    )
    echo       MongoDB detenido (por puerto 27017).
)

REM 3. Detener contenedor Neo4j
echo.
echo [3/3] Deteniendo Neo4j...
docker stop neo4j >nul 2>&1
if %errorlevel% equ 0 (
    echo       Neo4j detenido correctamente.
) else (
    REM Intentar por puerto por si el nombre es diferente
    for /f "tokens=*" %%i in ('docker ps -q --filter "publish=7687" 2^>nul') do (
        docker stop %%i >nul 2>&1
    )
    echo       Neo4j detenido (por puerto 7687).
)

echo.
echo ============================================================
echo   Verificacion final:
echo ============================================================

REM Verificar que no quede nada corriendo
docker ps --filter "name=mongodb" --filter "name=neo4j" --format "  ⚠️ Aun corriendo: {{.Names}} ({{.Status}})" 2>nul
if %errorlevel% equ 0 (
    echo   ✅ Todos los contenedores detenidos.
)

echo.
echo   Los datos persisten en los volumenes Docker.
echo   Para reanudar, ejecuta iniciar_servicios.bat
echo.
pause
