@echo off
chcp 65001 >nul
setlocal
rem Project root = this script's folder (portable)
set "ROOT=%~dp0"

echo ==================================================
echo    0号仓库库存管理系统 - 一键启动
echo ==================================================
echo.

rem ---------- 0. environment precheck: Python 3.11+ & Node 18+ ----------
set "PY_OK=0"
set "NODE_OK=0"
where python >nul 2>&1
if errorlevel 1 goto :no_python
python -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)" >nul 2>&1
if not errorlevel 1 set "PY_OK=1"
:no_python
where node >nul 2>&1
if errorlevel 1 goto :no_node
for /f "tokens=* delims=v" %%v in ('node --version 2^>nul') do set "NODE_VER=%%v"
for /f "tokens=1 delims=." %%a in ("%NODE_VER%") do set "NODE_MAJOR=%%a"
if defined NODE_MAJOR if %NODE_MAJOR% GEQ 18 set "NODE_OK=1"
:no_node

if "%PY_OK%"=="1" goto :py_ok
echo.
echo [提示] 未检测到 Python 3.11 或更高版本，无法启动后端。
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $r=[System.Windows.Forms.MessageBox]::Show('未检测到 Python 3.11+，请先安装 Python 后再启动本系统。`n`n是否立即打开 Python 官方下载页？','0号仓库库存管理系统 - 环境检测','YesNo','Warning'); if($r -eq 'Yes'){Start-Process 'https://www.python.org/downloads/'}"
goto :err_env
:py_ok
if "%NODE_OK%"=="1" goto :node_ok
echo.
echo [提示] 未检测到 Node.js 18 或更高版本，无法启动前端。
powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $r=[System.Windows.Forms.MessageBox]::Show('未检测到 Node.js 18+，请先安装 Node.js 后再启动本系统。`n`n是否立即打开 Node.js 官方下载页？','0号仓库库存管理系统 - 环境检测','YesNo','Warning'); if($r -eq 'Yes'){Start-Process 'https://nodejs.org/'}"
goto :err_env
:node_ok

rem ---------- 0b. create desktop shortcut (first run) ----------
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $d=$ws.SpecialFolders('Desktop'); $p=Join-Path $d '0号仓库库存管理系统.lnk'; if(Test-Path $p){exit 0}else{exit 1}" >nul 2>&1
if not errorlevel 1 goto :sc_ok
echo.
echo [SETUP] 首次运行：在桌面创建快捷方式「0号仓库库存管理系统」...
powershell -NoProfile -Command "$ws=New-Object -ComObject WScript.Shell; $d=$ws.SpecialFolders('Desktop'); $sc=$ws.CreateShortcut((Join-Path $d '0号仓库库存管理系统.lnk')); $sc.TargetPath='%ROOT%start.bat'; $sc.WorkingDirectory='%ROOT%'; $sc.IconLocation='%SystemRoot%\System32\shell32.dll,14'; $sc.Description='0号仓库库存管理系统'; $sc.Save()"
echo [OK] 桌面快捷方式已创建。
:sc_ok

rem ---------- 1. check backend port 8000 ----------
set "BE_RUNNING=0"
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul 2>&1
if errorlevel 1 goto :be_free
echo [OK] 后端已在运行 (8000)。
set "BE_RUNNING=1"
:be_free

rem ---------- 2. check frontend port 5173 ----------
set "FE_RUNNING=0"
netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul 2>&1
if errorlevel 1 goto :fe_free
echo [OK] 前端已在运行 (5173)。
set "FE_RUNNING=1"
:fe_free

rem ---------- 2b. both already running -> just open browser ----------
if not "%BE_RUNNING%"=="1" goto :need_setup
if not "%FE_RUNNING%"=="1" goto :need_setup
echo.
echo [OK] 前后端均已运行，无需重复启动。
goto :open_browser
:need_setup

rem ---------- 3. backend deps (first run) ----------
if exist "%ROOT%backend\venv\Scripts\python.exe" goto :be_deps_ok
echo [SETUP] 首次运行：创建后端虚拟环境并安装依赖...
cd /d "%ROOT%backend"
python -m venv venv
if errorlevel 1 goto :err_venv
"%ROOT%backend\venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 goto :err_pip
echo [DONE] 后端依赖安装完成。
:be_deps_ok

rem ---------- 4. frontend deps (first run) ----------
if exist "%ROOT%frontend\node_modules" goto :fe_deps_ok
echo [SETUP] 首次运行：安装前端依赖 (npm install)，可能需要几分钟...
cd /d "%ROOT%frontend"
call npm install
if errorlevel 1 goto :err_npm
echo [DONE] 前端依赖安装完成。
:fe_deps_ok

rem ---------- 5. auto-pull-up backend if not running ----------
if "%BE_RUNNING%"=="1" goto :be_started
echo [START] 启动后端 http://localhost:8000
cd /d "%ROOT%backend"
rem inject PYTHONHOME if known runtime exists (fixes missing stdlib on this machine)
if exist "E:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.522\runtime\python311\Lib" (
  set "PYTHONHOME=E:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.522\runtime\python311"
  echo [INFO] 已注入 PYTHONHOME 运行环境。
)
start "Inventory-Backend(8000)" /min "%ROOT%backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
set "BE_RUNNING=1"
:be_started

rem ---------- 6. auto-pull-up frontend if not running ----------
if "%FE_RUNNING%"=="1" goto :fe_started
echo [START] 启动前端 http://localhost:5173
cd /d "%ROOT%frontend"
start "Inventory-Frontend(5173)" /min node "%ROOT%frontend\node_modules\vite\bin\vite.js"
set "FE_RUNNING=1"
:fe_started

rem ---------- 7. wait backend ready (HTTP probe) ----------
echo.
echo [WAIT] 等待后端就绪...
set /a BE_TRY=0
:be_wait
set /a BE_TRY+=1
powershell -NoProfile -Command "try{(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs' -UseBasicParsing -TimeoutSec 1)|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto :be_ready
if %BE_TRY% GEQ 40 goto :be_timeout
ping -n 2 127.0.0.1 >nul
goto :be_wait
:be_ready
echo [OK] 后端就绪。
goto :be_wait_done
:be_timeout
echo [WARN] 后端尚未就绪，可能仍在启动中。
:be_wait_done

rem ---------- 8. wait frontend ready (port probe) ----------
echo [WAIT] 等待前端就绪...
set /a FE_TRY=0
:fe_wait
set /a FE_TRY+=1
netstat -ano | findstr /r /c:":5173 .*LISTENING" >nul 2>&1
if not errorlevel 1 goto :fe_ready
if %FE_TRY% GEQ 40 goto :fe_timeout
ping -n 2 127.0.0.1 >nul
goto :fe_wait
:fe_ready
echo [OK] 前端就绪。
goto :fe_wait_done
:fe_timeout
echo [WARN] 前端尚未就绪，可能仍在启动中。
:fe_wait_done

:open_browser
echo.
echo ==================================================
echo   系统已就绪！
echo     前端:   http://localhost:5173
echo     后端:   http://localhost:8000/docs
echo   浏览器将自动打开，请稍候...
echo ==================================================
echo.
start "" http://localhost:5173
pause
exit /b 0

:err_env
echo.
echo [ERROR] 环境检测未通过，请按提示安装所需软件后，再双击本脚本启动。
pause
exit /b 1

:err_venv
echo [ERROR] 创建虚拟环境失败。请确认 Python 3.11+ 已安装并加入 PATH。
pause
exit /b 1

:err_pip
echo [ERROR] 后端依赖安装失败。请检查网络后重试。
pause
exit /b 1

:err_npm
echo [ERROR] 前端依赖安装失败。请检查网络后重试。
pause
exit /b 1
