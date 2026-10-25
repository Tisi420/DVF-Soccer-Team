# Instala el entorno del proyecto DVF en una PC nueva (sesión 63).
#
#   1. Busca Python 3.10 (con el lanzador "py" de Windows o "python").
#   2. Crea el venv en env\ (si no existe) e instala requirements.txt.
#   3. Corre scripts\verificar_entorno.py: tiene que terminar con "Listo para entrenar".
#
# Uso (desde la raíz del proyecto descomprimido, en PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
#
# Si no tenés Python 3.10: https://www.python.org/downloads/release/python-31011/
# (instalador de Windows, marcar "Add python.exe to PATH").

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
	$v = & py -3.10 --version 2>$null
	if ($LASTEXITCODE -eq 0) { $py = @("py", "-3.10") }
}
if (-not $py -and (Get-Command python -ErrorAction SilentlyContinue)) {
	$v = & python --version 2>&1
	if ($v -match "3\.10\.") { $py = @("python") }
	else { Write-Warning "Se encontró $v; el proyecto se probó con Python 3.10. Sigo igual, pero TensorFlow o pymunk pueden fallar." ; $py = @("python") }
}
if (-not $py) { throw "No encontré Python. Instalá Python 3.10 (ver la cabecera de este script) y volvé a correrlo." }

if (-not (Test-Path "env\Scripts\python.exe")) {
	"Creando el venv en env\ ..."
	if ($py.Length -gt 1) { & $py[0] $py[1] -m venv env } else { & $py[0] -m venv env }
	if (-not (Test-Path "env\Scripts\python.exe")) { throw "No se pudo crear el venv en env\." }
}
"Instalando paquetes (puede tardar varios minutos: TensorFlow pesa ~500 MB) ..."
& "env\Scripts\python.exe" -m pip install --upgrade pip
& "env\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de paquetes (ver el error de pip arriba)." }

"Verificando el entorno ..."
& "env\Scripts\python.exe" scripts\verificar_entorno.py
