#!/usr/bin/env bash
# Uso: tiempos.sh <host:puerto> <archivo_salida.csv>
# Mide el tiempo de respuesta de /fibonacci/n para n = 1000000..1090000 (paso 7)
HOST=$1; OUT=$2
echo "nth,http_code,time_total_s,size_bytes,start_utc" > "$OUT"
for n in 1000000 1010000 1020000 1030000 1040000 1050000 1060000 1070000 1080000 1090000; do
  start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  r=$(curl -s -o /dev/null -m 300 -w "%{http_code},%{time_total},%{size_download}" "http://$HOST/fibonacci/$n")
  echo "$n,$r,$start" | tee -a "$OUT"
done
