"""Genera las gráficas y capturas del laboratorio en images/resultados/.

Uso: python results/scripts/graficas.py
"""
import csv
import json
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
RES = REPO / "results"
OUT = REPO / "images" / "resultados"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(RES / "scripts"))
from resumen_newman import resumir  # noqa: E402


def leer_csv(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# 1. Parte 1 (Azure): tiempos de respuesta por n
plt.figure(figsize=(8, 4))
for nombre, etiqueta in [("parte1_tiempos_DS1_v2_p80.csv", "DS1_v2 (1 vCPU)"), ("parte1_tiempos_DS2_v2.csv", "DS2_v2 (2 vCPU)")]:
    filas = leer_csv(RES / nombre)
    plt.plot([int(r["nth"]) for r in filas], [float(r["time_total_s"]) for r in filas], marker="o", label=etiqueta)
plt.title("Parte 1 (Azure) - tiempo de respuesta de /fibonacci/n")
plt.xlabel("n"); plt.ylabel("segundos"); plt.grid(alpha=.3); plt.legend(); plt.tight_layout()
plt.savefig(OUT / "p1_tiempos_azure.png", dpi=110); plt.close()

# 2. Parte 1 (Azure): CPU de la VM
filas = [r for r in leer_csv(RES / "cpu" / "parte1_cpu_2026-10-30.csv") if num(r["max"]) is not None]
plt.figure(figsize=(9, 4))
plt.plot([r["timestamp"][11:16] for r in filas], [num(r["max"]) for r in filas], marker=".", label="CPU máx (%)")
plt.plot([r["timestamp"][11:16] for r in filas], [num(r["avg"]) for r in filas], marker=".", label="CPU prom (%)")
plt.axhline(70, color="red", ls="--", label="límite 70% del escenario")
plt.xticks(rotation=60, fontsize=7); plt.ylim(0, 105)
plt.title("Parte 1 (Azure Monitor) - Percentage CPU de VERTICAL-SCALABILITY (30-oct)")
plt.annotate("DS1_v2 (1 vCPU): tiempos + newman x2/x4", ("16:09", 101), fontsize=8)
plt.annotate("DS2_v2 (2 vCPU): ~50%\n(Node usa 1 de 2 núcleos)", ("16:52", 54), fontsize=8)
plt.annotate("de vuelta a DS1_v2", ("17:01", 101), fontsize=8)
plt.grid(alpha=.3); plt.legend(fontsize=8); plt.tight_layout()
plt.savefig(OUT / "p1_cpu_azure.png", dpi=110); plt.close()

# 3. Simulación: CPU por VM en cada prueba
SIM = RES / "simulacion"
pruebas = ["v1_1nucleo_x2", "v1_1nucleo_x4", "v2_2nucleos_x4", "h3_x2", "h4_x4"]
titulos = {
    "v1_1nucleo_x2": "1 VM / 1 núcleo - 2 newman",
    "v1_1nucleo_x4": "1 VM / 1 núcleo - 4 newman",
    "v2_2nucleos_x4": "1 VM / 2 núcleos (vertical) - 4 newman",
    "h3_x2": "3 VMs + balanceador - 2 newman",
    "h4_x4": "4 VMs + balanceador - 4 newman",
}
pruebas = [p for p in pruebas if (SIM / p / "lb_status.json").exists()]  # solo pruebas terminadas
fig, axs = plt.subplots(len(pruebas), 1, figsize=(9, 2.6 * len(pruebas)), squeeze=False)
for ax, p in zip(axs[:, 0], pruebas):
    filas = leer_csv(SIM / p / "cpu.csv")
    t = [i * 2 for i in range(len(filas))]
    for vm in [k for k in filas[0] if k != "timestamp"]:
        ax.plot(t, [num(r[vm]) or 0 for r in filas], label=vm, lw=1.2)
    ax.axhline(70, color="red", ls="--", lw=.8)
    ax.set_ylim(0, 105); ax.set_ylabel("% CPU"); ax.set_title(titulos[p], fontsize=10); ax.grid(alpha=.3)
    ax.legend(fontsize=7, loc="upper right", ncol=4)
axs[-1, 0].set_xlabel("segundos desde el inicio de la prueba")
fig.tight_layout(); fig.savefig(OUT / "sim_cpu_por_vm.png", dpi=110); plt.close(fig)

# 4. Comparativo Azure vertical vs simulación horizontal
azure = {
    "Azure DS1_v2 x2": "newman/p1_DS1_v2_x2_p80", "Azure DS1_v2 x4": "newman/p1_DS1_v2_x4_p80",
    "Azure DS2_v2 x2": "newman/p1_DS2_v2_x2", "Azure DS2_v2 x4": "newman/p1_DS2_v2_x4",
}
local = {titulos[p]: f"simulacion/{p}" for p in pruebas}
resumenes = {k: resumir(RES / v) for k, v in {**azure, **local}.items()}
(RES / "resumen_pruebas.json").write_text(json.dumps(resumenes, ensure_ascii=False, indent=1), encoding="utf-8")
nombres = list(resumenes)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
colores = ["#d9822b"] * len(azure) + ["#2b7bd9"] * len(local)
a1.barh(nombres, [100 * resumenes[n]["exitosas"] / resumenes[n]["total"] for n in nombres], color=colores)
a1.set_title("Peticiones exitosas (%)"); a1.set_xlim(0, 105); a1.invert_yaxis()
a2.barh(nombres, [(lambda r: (r["t_prom_s"] or 0))(resumenes[n]) for n in nombres], color=colores)
a2.set_title("Tiempo promedio de respuesta exitosa (s)"); a2.invert_yaxis(); a2.set_yticklabels([])
fig.suptitle("Naranja: escalado vertical en Azure  |  Azul: simulación local (vertical y horizontal)")
fig.tight_layout(); fig.savefig(OUT / "comparativo.png", dpi=110); plt.close(fig)


# 5. "Capturas" de consola: resumen de newman y bitácora del balanceador
def captura(texto, archivo, titulo):
    import re
    texto = re.sub(r"\[[0-9;]*m", "", texto)
    lineas = texto.splitlines()
    fig = plt.figure(figsize=(10, 0.19 * len(lineas) + 0.6))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.01, 0.995, titulo, color="#8fd18f", family="monospace", fontsize=9, va="top", weight="bold")
    fig.text(0.01, 0.99 - 0.35 / fig.get_figheight(), texto, color="#e0e0e0", family="monospace", fontsize=8, va="top")
    fig.savefig(OUT / archivo, dpi=110, facecolor=fig.get_facecolor()); plt.close(fig)


for p in [x for x in ("h4_x4", "v1_1nucleo_x4") if x in pruebas]:
    txt = (SIM / p / "proceso1.txt").read_text(encoding="utf-8", errors="replace")
    inicio = txt.find("┌")
    captura(txt[inicio:].strip(), f"newman_{p}.png", f"PS> newman run ... -n 10   ({titulos[p]}, proceso 1 de 4)")
if "h4_x4" in pruebas:
    log = (SIM / "h4_x4" / "balanceador.log").read_text(encoding="utf-8", errors="replace").splitlines()
    estado = (SIM / "h4_x4" / "lb_status.json").read_text(encoding="utf-8-sig")
    captura("\n".join(log[:34]) + "\n...\n\nGET /lb/status\n" + estado, "balanceador_h4_x4.png",
            "PS> node simulacion/balanceador.js   (4 VMs, 4 newman en paralelo)")

for n, r in resumenes.items():
    print(f"{n:42s} {r['exitosas']:>3}/{r['total']:<3} {r['tasa_exito']:>5}  prom={r['t_prom_s']}s  max={r['t_max_s']}s  "
          f"{r['inicio_utc'][11:19]}-{r['fin_utc'][11:19]}  {r['errores']}")
