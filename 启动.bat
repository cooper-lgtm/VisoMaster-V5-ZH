@echo off
setlocal enableextensions

REM ==== 根目录自动探测（脚本同目录） ====
set "ROOT_DIR=%~dp0"

REM ==== 虚拟环境 & 主程序 ====
set "PYTHON_ENV=%ROOT_DIR%\wzf311"
set "PYEXE=%PYTHON_ENV%\python.exe"
set "APP_ENTRY=%ROOT_DIR%\main.py"

REM ==== 其余保持不变 ====
set PYTHONHOME=
set PYTHONPATH=
set PYTHONEXECUTABLE=%PYEXE%
set PYTHONWEXECUTABLE=%PYTHON_ENV%\pythonw.exe
set PYTHON_BIN_PATH=%PYEXE%
set PYTHON_LIB_PATH=%PYTHON_ENV%\Lib\site-packages

set "TORCH_LIB=%PYTHON_ENV%\Lib\site-packages\torch\lib"
set "CUDA_BIN=%PYTHON_ENV%\Library\bin"
set "TRT_BIN=%ROOT_DIR%\TensorRT-10.13.0.35\bin"
set "TRT_LIB=%ROOT_DIR%\TensorRT-10.13.0.35\lib"
set "FFMPEG_BIN=%ROOT_DIR%\ffmpeg\bin"

set "PATH=%PYTHON_ENV%;%PYTHON_ENV%\Scripts;%FFMPEG_BIN%;%TORCH_LIB%;%CUDA_BIN%;%TRT_BIN%;%TRT_LIB%;%PATH%"

REM ==== 启动 VisoMaster ====
"%PYEXE%" "%APP_ENTRY%"

pause
endlocal
