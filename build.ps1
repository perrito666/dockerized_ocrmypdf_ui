# build.ps1
# Ce script construit main.py en exécutable avec PyInstaller

# Installer PyInstaller si besoin
pip install --upgrade pyinstaller

# Nettoyer les anciens builds
Remove-Item -Recurse -Force dist, build, *.spec -ErrorAction SilentlyContinue

# Construire l'exécutable
pyinstaller --onefile --windowed main.py

Write-Host "Build Finished, the executable can be found in the folder 'dist'."