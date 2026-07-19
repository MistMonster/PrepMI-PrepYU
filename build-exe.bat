@echo off
python -m pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm PrepMI-PrepYU.spec
