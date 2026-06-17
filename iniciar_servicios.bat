@echo off
echo.
echo ============================================================
echo   ECODRONES - Iniciando servicios de base de datos
echo ============================================================
echo.

REM Verificar que Docker este corriendo
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta corriendo. Abrilo antes de continuar.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM MONGODB
REM ---------------------------------------------------------------
echo [1/3] Iniciando MongoDB...

docker start mongodb >nul 2>&1
if %errorlevel% equ 0 (
    echo       Contenedor 'mongodb' reanudado.
) else (
    docker run -d --name mongodb -p 27017:27017 mongo:latest >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Contenedor nuevo 'mongodb' creado y arrancado.
    ) else (
        echo       [AVISO] Puerto 27017 ya ocupado. MongoDB ya esta corriendo.
    )
)

REM ---------------------------------------------------------------
REM NEO4J
REM ---------------------------------------------------------------
echo.
echo [2/3] Iniciando Neo4j...

docker start neo4j >nul 2>&1
if %errorlevel% equ 0 (
    echo       Contenedor 'neo4j' reanudado.
) else (
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Contenedor nuevo 'neo4j' creado y arrancado.
    ) else (
        echo       [ERROR] No se pudo iniciar Neo4j. Puerto ocupado o error de Docker.
    )
)

REM ---------------------------------------------------------------
REM Esperar que Neo4j este listo (hasta 90 segundos)
REM ---------------------------------------------------------------
echo.
echo Esperando que Neo4j este listo...
set /a intentos=0
:esperar_neo4j
set /a intentos+=1
if %intentos% gtr 18 (
    echo [ERROR] Neo4j no respondio despues de 90 segundos.
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul
docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Esperando Neo4j... intento %intentos%/18
    goto esperar_neo4j
)
echo       Neo4j listo.

REM ---------------------------------------------------------------
REM CARGAR GRAFO EN NEO4J
REM ---------------------------------------------------------------
echo.
echo [3/3] Cargando ecosistema en Neo4j...
python cargar_neo4j.py
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al cargar el grafo. Verificar conexion con Neo4j.
    pause
    exit /b 1
)

REM ---------------------------------------------------------------
REM LANZAR SIMULADOR, MONITOR, WATCHDOG Y DASHBOARD EN VENTANAS SEPARADAS
REM ---------------------------------------------------------------
echo.
echo Lanzando simulador de drones...
start "EcoDrones - Simulador" cmd /k "python simulador_continuo.py"

echo Lanzando monitor de alertas...
start "EcoDrones - Monitor" cmd /k "python monitor_alertas.py"

echo.
echo ============================================================
echo   Todo en marcha. Se abrieron 2 ventanas:
echo     - Simulador de drones
echo     - Monitor de alertas
echo   Neo4j Browser: http://localhost:7474
echo ============================================================
echo.
echo   El sistema esta corriendo. Esta ventana lo mantiene activo.
echo   NO la cierres si queres que todo siga funcionando.
echo.
:menu
echo --------------------------------------------------------
echo   [D] Abrir dashboard visual (Flet)
echo   [R] Reiniciar servicios (Docker y Python)
echo   [Q] DETENER todo y salir
echo --------------------------------------------------------
choice /c DRQ /n /m "Tu eleccion: "

if %errorlevel% equ 3 goto detener_todo
if %errorlevel% equ 2 goto reiniciar_todo
if %errorlevel% equ 1 goto abrir_dashboard
goto menu

:abrir_dashboard
echo Abriendo dashboard...
start "EcoDrones - Dashboard" cmd /k "python dashboard.py"
echo Dashboard abierto. El sistema sigue corriendo.
echo.
goto menu

:reiniciar_todo
echo.
echo Reiniciando servicios...

REM 1. Detener procesos Python
taskkill /fi "WindowTitle eq EcoDrones - Simulador*" /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Monitor*"   /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Dashboard*" /f >nul 2>&1
echo       Procesos Python detenidos.

REM 2. Detener contenedores Docker
docker stop mongodb neo4j >nul 2>&1
echo       Contenedores Docker detenidos.

REM 3. Iniciar MongoDB
echo.
echo [1/3] Iniciando MongoDB...
docker start mongodb >nul 2>&1
if %errorlevel% equ 0 (
    echo       Contenedor 'mongodb' reanudado.
) else (
    docker run -d --name mongodb -p 27017:27017 mongo:latest >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Contenedor nuevo 'mongodb' creado y arrancado.
    ) else (
        echo       [AVISO] Puerto 27017 ya ocupado o error.
    )
)

REM 4. Iniciar Neo4j
echo.
echo [2/3] Iniciando Neo4j...
docker start neo4j >nul 2>&1
if %errorlevel% equ 0 (
    echo       Contenedor 'neo4j' reanudado.
) else (
    docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Contenedor nuevo 'neo4j' creado y arrancado.
    ) else (
        echo       [ERROR] No se pudo iniciar Neo4j.
    )
)

REM 5. Esperar que Neo4j este listo
echo.
echo Esperando que Neo4j este listo...
set /a intentos_restart=0
:esperar_neo4j_loop_restart
set /a intentos_restart+=1
if %intentos_restart% gtr 18 (
    echo [ERROR] Neo4j no respondio despues de 90 segundos durante el reinicio.
    pause
    goto menu
)
timeout /t 5 /nobreak >nul
docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Esperando Neo4j... intento %intentos_restart%/18
    goto esperar_neo4j_loop_restart
)
echo       Neo4j listo.

REM 6. Cargar grafo en Neo4j
echo.
echo [3/3] Cargando ecosistema en Neo4j...
python cargar_neo4j.py
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al cargar el grafo.
    pause
    goto menu
)

REM 7. Lanzar simulador y monitor
echo.
echo Lanzando simulador de drones...
start "EcoDrones - Simulador" cmd /k "python simulador_continuo.py"

echo Lanzando monitor de alertas...
start "EcoDrones - Monitor" cmd /k "python monitor_alertas.py"

echo.
echo Servicios reiniciados.
goto menu

:detener_todo
echo.
echo ============================================================
echo   Deteniendo TODOS los servicios...
echo ============================================================

REM Matar procesos Python
taskkill /fi "WindowTitle eq EcoDrones - Simulador*" /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Monitor*"   /f >nul 2>&1
taskkill /fi "WindowTitle eq EcoDrones - Dashboard*" /f >nul 2>&1
echo   [OK] Procesos Python detenidos.

REM Detener contenedores Docker
docker stop mongodb >nul 2>&1
echo   [OK] MongoDB detenido.
docker stop neo4j >nul 2>&1
echo   [OK] Neo4j detenido.

REM Fallback: buscar por puerto si los nombres no coinciden
for /f "tokens=*" %%i in ('docker ps -q --filter "publish=27017" 2^>nul') do docker stop %%i >nul 2>&1
for /f "tokens=*" %%i in ('docker ps -q --filter "publish=7687" 2^>nul') do docker stop %%i >nul 2>&1

echo.
echo   Todos los servicios fueron detenidos correctamente.
echo.
pause
exit /b 0
