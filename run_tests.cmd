@echo off
setlocal
pushd "%~dp0"
python scripts\verify_embedded_docs.py
if errorlevel 1 (
  set EXIT_CODE=%ERRORLEVEL%
  popd
  exit /b %EXIT_CODE%
)
python -m unittest discover -s tests -p "test_*.py"
set EXIT_CODE=%ERRORLEVEL%
popd
exit /b %EXIT_CODE%
