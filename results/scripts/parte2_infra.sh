#!/usr/bin/env bash
# Uso: parte2_infra.sh base                     -> grupo, VNet, NSG, IP pública y balanceador (backend pool, probe, reglas)
#      parte2_infra.sh vm <VM> <zona> [sin-ip]  -> VM en la zona indicada dentro del backend pool, con IP pública
#                                                  zone-redundant (o sin IP: Azure for Students permite solo 3 IPs por región)
# Crea con Azure CLI la infraestructura de la Parte 2 (escalabilidad horizontal).
set -euo pipefail
export MSYS_NO_PATHCONV=1  # evita que Git Bash convierta los IDs /subscriptions/... en rutas de Windows
RG=LOAD_BALANCING_LAB; LOC=chilecentral; SIZE=Standard_DS1_v2; ADMIN=scalability_lab
DIR=$(cd "$(dirname "$0")" && pwd)
winpath() { cygpath -w "$1" 2>/dev/null || echo "$1"; }

base() {
  az group create -n $RG -l $LOC -o none
  az network vnet create -g $RG -n lab-vnet --address-prefix 10.0.0.0/16 \
    --subnet-name lab-subnet --subnet-prefix 10.0.0.0/24 -o none
  az network nsg create -g $RG -n lab-nsg -o none
  for r in "ssh 22 1000" "app 3000 1010" "http 80 1020"; do
    set -- $r
    az network nsg rule create -g $RG --nsg-name lab-nsg -n allow-$1 --priority $3 \
      --destination-port-ranges $2 --protocol Tcp --access Allow -o none
  done
  az network public-ip create -g $RG -n lb-ip --sku Standard --zone 1 2 3 --allocation-method Static -o none
  az network lb create -g $RG -n lab-lb --sku Standard --public-ip-address lb-ip \
    --frontend-ip-name lb-frontend --backend-pool-name lb-backend -o none
  az network lb probe create -g $RG --lb-name lab-lb -n lb-probe --protocol Http --port 3000 --path / -o none
  az network lb rule create -g $RG --lb-name lab-lb -n lb-rule --protocol Tcp --frontend-port 80 --backend-port 3000 \
    --frontend-ip-name lb-frontend --backend-pool-name lb-backend --probe-name lb-probe --disable-outbound-snat true -o none
  # Salida a internet (git clone, npm) para las VMs sin IP pública
  az network lb outbound-rule create -g $RG --lb-name lab-lb -n lb-outbound --frontend-ip-configs lb-frontend \
    --protocol All --address-pool lb-backend -o none
  az network public-ip show -g $RG -n lb-ip --query ipAddress -o tsv
}

vm() {
  VM=$1; ZONE=$2; IP=(--public-ip-address $VM-ip)
  if [ "${3:-}" = sin-ip ]; then IP=(); else
    az network public-ip create -g $RG -n $VM-ip --sku Standard --zone 1 2 3 --allocation-method Static -o none
  fi
  az network nic create -g $RG -n $VM-nic --vnet-name lab-vnet --subnet lab-subnet --network-security-group lab-nsg \
    "${IP[@]}" --lb-name lab-lb --lb-address-pools lb-backend -o none
  az vm create -g $RG -n $VM --zone $ZONE --size $SIZE --image Ubuntu2204 --nics $VM-nic \
    --admin-username $ADMIN --ssh-key-values "$(winpath ~/.ssh/id_ed25519.pub)" \
    --custom-data "$(winpath "$DIR/parte2_cloud-init.yaml")" -o none
  az network nic show -g $RG -n $VM-nic --query ipConfigurations[0].privateIPAddress -o tsv
}

"$@"
