#!/usr/bin/env bash
# Uso: carga.sh <carpeta_postman relativa al repo> <num_procesos_paralelos> <etiqueta>
# Lanza N ejecuciones paralelas de newman (-n 10) y guarda un reporte JSON por proceso.
PARTE=$1; N=$2; TAG=$3
DIR=$(cd "$(dirname "$0")/../.." && (pwd -W 2>/dev/null || pwd))
PM="$DIR/$PARTE"
OUT="$DIR/results/newman/$TAG"; mkdir -p "$OUT"
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/inicio_utc.txt"
for i in $(seq 1 "$N"); do
  newman run "$PM/ARSW_LOAD-BALANCING_AZURE.postman_collection.json" \
    -e "$PM/[ARSW_LOAD-BALANCING_AZURE].postman_environment.json" -n 10 \
    --reporters cli,json --reporter-json-export "$OUT/proceso$i.json" > "$OUT/proceso$i.txt" 2>&1 &
done
wait
date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT/fin_utc.txt"
