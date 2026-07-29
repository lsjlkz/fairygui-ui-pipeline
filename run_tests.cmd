@echo off
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0" || exit /b 1

python scripts\verify_embedded_docs.py
if errorlevel 1 (
  set "EXIT_CODE=!ERRORLEVEL!"
  popd
  exit /b !EXIT_CODE!
)

python -m compileall -q scripts tests
if errorlevel 1 (
  set "EXIT_CODE=!ERRORLEVEL!"
  popd
  exit /b !EXIT_CODE!
)

python -m unittest discover -s tests -p "test_*.py"
set "EXIT_CODE=!ERRORLEVEL!"

popd
exit /b !EXIT_CODE!
