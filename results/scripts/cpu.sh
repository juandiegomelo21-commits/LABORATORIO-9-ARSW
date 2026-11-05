#!/usr/bin/env bash
# Uso: cpu.sh <resource_group> <vm> <inicio_utc> <fin_utc> <salida.csv>
# Descarga la métrica "Percentage CPU" (promedio y máximo por minuto) de Azure Monitor.
export MSYS_NO_PATHCONV=1  # evita que Git Bash convierta el ID /subscriptions/... en ruta de Windows
RG=$1; VM=$2; START=$3; END=$4; OUT=$5
ID=$(az vm show -g "$RG" -n "$VM" --query id -o tsv)
echo "timestamp,avg,max" > "$OUT"
az monitor metrics list --resource "$ID" --metric "Percentage CPU" --interval PT1M \
  --aggregation Average Maximum --start-time "$START" --end-time "$END" \
  --query "value[0].timeseries[0].data[].[timeStamp, average, maximum]" -o tsv | tr '\t' ',' >> "$OUT"
