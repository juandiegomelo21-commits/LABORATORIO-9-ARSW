# Ejecuta una prueba de carga sobre la infraestructura simulada en local.
#   - Cada "VM" es un proceso FibonacciApp fijado (afinidad de CPU) a Nucleos núcleos lógicos distintos.
#   - El balanceador (balanceador.js) reparte las peticiones entre las VMs y hace el health probe.
#   - Se lanzan $Paralelos ejecuciones de newman (-n 10) en paralelo, igual que en el enunciado.
#   - Se mide el % de CPU de cada VM cada 2 s (100% = todos los núcleos asignados a esa VM ocupados).
# Uso:
#   .\simulacion\prueba.ps1 -Nodos 4 -Paralelos 4 -Etiqueta h4_x4
#   .\simulacion\prueba.ps1 -Nodos 1 -Nucleos 2 -Paralelos 2 -Etiqueta v_2nucleos_x2
#   .\simulacion\prueba.ps1 -Nodos 4 -Paralelos 4 -Etiqueta demo -Visible   (abre la consola del balanceador, útil para el video)
param(
  [int]$Nodos = 4,
  [int]$Paralelos = 4,
  [int]$Nucleos = 1,
  [int]$Iteraciones = 10,
  [string]$Etiqueta = "prueba",
  [switch]$Visible
)
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$App = Join-Path $Repo "FibonacciApp"
$Out = Join-Path $Repo "results\simulacion\$Etiqueta"
New-Item -ItemType Directory -Force $Out | Out-Null
Get-ChildItem $Out -File | Remove-Item -Force

# Núcleos lógicos 1,3,5,7 = un núcleo físico distinto por VM (CPU de 4 núcleos / 8 hilos).
# El balanceador y newman quedan en los núcleos 0,2,4,6.
$CorePool = @(1, 3, 5, 7, 0, 2, 4, 6)
if ($Nodos * $Nucleos -gt 4) { throw "Solo hay 4 núcleos físicos para las VMs" }

$procs = @()
for ($i = 1; $i -le $Nodos; $i++) {
  $env:PORT = 3100 + $i
  $p = Start-Process node -ArgumentList "FibonacciApp.js" -WorkingDirectory $App -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Out "VM$i.log") -RedirectStandardError (Join-Path $Out "VM$i.err")
  $mask = 0
  for ($c = 0; $c -lt $Nucleos; $c++) { $mask = $mask -bor (1 -shl $CorePool[($i - 1) * $Nucleos + $c]) }
  $p.ProcessorAffinity = [IntPtr]$mask
  $procs += [pscustomobject]@{ Name = "VM$i"; Proc = $p; Port = 3100 + $i }
}
Remove-Item Env:PORT

$env:BACKENDS = ($procs | ForEach-Object { "$($_.Name)=127.0.0.1:$($_.Port)" }) -join ","
$env:LB_PORT = 8090
$lbArgs = @{ FilePath = "node"; ArgumentList = "balanceador.js"; WorkingDirectory = $PSScriptRoot; PassThru = $true }
if ($Visible) {
  $lbArgs.ArgumentList = "/k node balanceador.js"; $lbArgs.FilePath = "cmd.exe"
} else {
  $lbArgs.WindowStyle = "Hidden"
  $lbArgs.RedirectStandardOutput = (Join-Path $Out "balanceador.log")
  $lbArgs.RedirectStandardError = (Join-Path $Out "balanceador.err")
}
$lb = Start-Process @lbArgs
Start-Sleep 2
Write-Host "Infraestructura: $Nodos VM(s) x $Nucleos núcleo(s) detrás del balanceador :8090"
Write-Host (Invoke-RestMethod http://127.0.0.1:8090/fibonacci/6)

# Monitor de CPU por VM (como la gráfica "Percentage CPU" de Azure Monitor)
$flag = Join-Path $Out "stop.flag"
$monitor = Start-Job -ArgumentList ($procs | ForEach-Object { $_.Proc.Id }), ($procs | ForEach-Object { $_.Name }), (Join-Path $Out "cpu.csv"), $flag, $Nucleos -ScriptBlock {
  param($ids, $names, $csv, $flag, $cores)
  "timestamp," + ($names -join ",") | Set-Content $csv -Encoding utf8
  $prev = @{}; foreach ($id in $ids) { $prev[$id] = (Get-Process -Id $id).TotalProcessorTime.TotalMilliseconds }
  $t = Get-Date
  while (-not (Test-Path $flag)) {
    Start-Sleep -Milliseconds 2000
    $now = Get-Date; $dt = ($now - $t).TotalMilliseconds; $t = $now
    $vals = foreach ($id in $ids) {
      $cur = (Get-Process -Id $id).TotalProcessorTime.TotalMilliseconds
      [math]::Round(100 * ($cur - $prev[$id]) / $dt / $cores, 1).ToString([cultureinfo]::InvariantCulture); $prev[$id] = $cur
    }
    ($now.ToUniversalTime().ToString("HH:mm:ss") + "," + ($vals -join ",")) | Add-Content $csv -Encoding utf8
  }
}

$col = Join-Path $PSScriptRoot "postman\ARSW_LOAD-BALANCING_AZURE.postman_collection.json"
$envf = Join-Path $PSScriptRoot "postman\local.postman_environment.json"
(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content (Join-Path $Out "inicio_utc.txt")
$news = for ($k = 1; $k -le $Paralelos; $k++) {
  Start-Process newman.cmd -ArgumentList "run `"$col`" -e `"$envf`" -n $Iteraciones --reporters cli,json --reporter-json-export `"$Out\proceso$k.json`" --color off" `
    -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Out "proceso$k.txt")
}
$news | Wait-Process
(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") | Set-Content (Join-Path $Out "fin_utc.txt")
Start-Sleep 4

Invoke-RestMethod http://127.0.0.1:8090/lb/status | ConvertTo-Json | Set-Content (Join-Path $Out "lb_status.json")
New-Item $flag | Out-Null; $monitor | Wait-Job | Remove-Job; Remove-Item $flag
$procs | ForEach-Object { Stop-Process -Id $_.Proc.Id -Force }
if (-not $Visible) { Stop-Process -Id $lb.Id -Force }
Get-Content (Join-Path $Out "lb_status.json")
python (Join-Path $Repo "results\scripts\resumen_newman.py") $Out
