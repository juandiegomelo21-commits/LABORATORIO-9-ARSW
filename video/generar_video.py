"""Genera el video del laboratorio (sin voz) + el guion para dos voces.

Uso:  python video/generar_video.py
Salida: video/lab9_video.mp4, video/GUION.md, video/guion.srt
Requiere: Pillow, imageio-ffmpeg (pip install imageio-ffmpeg)
Las animaciones son repeticiones aceleradas de las pruebas reales, reconstruidas a partir de
results/simulacion/<prueba>/balanceador.log y cpu.csv (no son datos inventados).
"""
import csv
import pathlib
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
VID = ROOT / "video"
IMG = ROOT / "images" / "resultados"
SIM = ROOT / "results" / "simulacion"
W, H, FPS = 1920, 1080, 10
WPS = 2.3  # palabras por segundo de la narración (ritmo tranquilo)

F = "C:/Windows/Fonts/"
def font(name, size):
    return ImageFont.truetype(F + name, size)
SANS, BOLD, SEMI, MONO = "segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "consola.ttf"

BG, PANEL, TXT, MUTED = (15, 23, 42), (30, 41, 59), (226, 232, 240), (148, 163, 184)
BLUE, ORANGE, GREEN, RED, YELLOW = (56, 189, 248), (251, 146, 60), (74, 222, 128), (248, 113, 113), (250, 204, 21)


# ---------------------------------------------------------------- utilidades de dibujo
def lienzo(seccion, titulo, color=BLUE):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=color)
    d.text((80, 50), seccion.upper(), font=font(SEMI, 26), fill=color)
    d.text((80, 88), titulo, font=font(BOLD, 54), fill=TXT)
    d.text((W - 80, H - 50), "ARSW · Laboratorio 9 · Escalamiento vertical y horizontal", font=font(SANS, 22),
           fill=MUTED, anchor="rs")
    return im, d


def envolver(d, texto, fnt, ancho):
    lineas, linea = [], ""
    for p in texto.split():
        prueba = (linea + " " + p).strip()
        if d.textlength(prueba, font=fnt) <= ancho:
            linea = prueba
        else:
            lineas.append(linea); linea = p
    if linea:
        lineas.append(linea)
    return lineas


def viñetas(d, items, x, y, ancho, size=34, gap=18):
    fnt = font(SANS, size)
    for it in items:
        color = TXT
        if isinstance(it, tuple):
            it, color = it
        lineas = envolver(d, it, fnt, ancho - 40)
        d.ellipse([x, y + size * 0.45, x + 12, y + size * 0.45 + 12], fill=BLUE)
        for i, l in enumerate(lineas):
            d.text((x + 32, y), l, font=fnt, fill=color)
            y += int(size * 1.32)
        y += gap
    return y


def pegar(im, ruta, caja, fondo=(255, 255, 255)):
    x0, y0, x1, y1 = caja
    src = Image.open(ruta).convert("RGB")
    esc = min((x1 - x0 - 30) / src.width, (y1 - y0 - 30) / src.height)
    src = src.resize((int(src.width * esc), int(src.height * esc)), Image.LANCZOS)
    w, h = src.width + 30, src.height + 30
    cx, cy = x0 + (x1 - x0 - w) // 2, y0 + (y1 - y0 - h) // 2
    ImageDraw.Draw(im).rounded_rectangle([cx, cy, cx + w, cy + h], 16, fill=fondo)
    im.paste(src, (cx + 15, cy + 15))


def tabla(d, x, y, filas, anchos, size=28, alto=50, resaltar=()):
    fh, fb = font(SEMI, size), font(SANS, size)
    for i, fila in enumerate(filas):
        cx = x
        fondo = PANEL if i == 0 else ((44, 58, 82) if i in resaltar else (BG if i % 2 else (22, 32, 54)))
        d.rectangle([x, y, x + sum(anchos), y + alto], fill=fondo)
        for j, celda in enumerate(fila):
            color = TXT
            if isinstance(celda, tuple):
                celda, color = celda
            d.text((cx + 16, y + alto / 2), str(celda), font=fh if i == 0 or i in resaltar else fb, fill=color, anchor="lm")
            cx += anchos[j]
        y += alto
    return y


def terminal(d, x0, y0, x1, y1, lineas, titulo="", size=24):
    d.rounded_rectangle([x0, y0, x1, y1], 14, fill=(17, 17, 17))
    d.rounded_rectangle([x0, y0, x1, y0 + 44], 14, fill=(45, 45, 45))
    d.rectangle([x0, y0 + 30, x1, y0 + 44], fill=(45, 45, 45))
    for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([x0 + 18 + k * 26, y0 + 14, x0 + 34 + k * 26, y0 + 30], fill=c)
    d.text((x0 + 110, y0 + 22), titulo, font=font(SANS, 20), fill=(200, 200, 200), anchor="lm")
    fnt = font(MONO, size)
    y = y0 + 60
    for l in lineas:
        color = (220, 220, 220)
        if isinstance(l, tuple):
            l, color = l
        d.text((x0 + 20, y), l, font=fnt, fill=color)
        y += int(size * 1.3)


# ---------------------------------------------------------------- diapositivas
def s_portada():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 8], fill=BLUE)
    d.text((W / 2, 330), "Escuela Colombiana de Ingeniería Julio Garavito · ARSW", font=font(SEMI, 34), fill=BLUE, anchor="mm")
    d.text((W / 2, 450), "Laboratorio 9", font=font(BOLD, 96), fill=TXT, anchor="mm")
    d.text((W / 2, 560), "Escalamiento vertical y horizontal en Azure", font=font(SANS, 56), fill=TXT, anchor="mm")
    d.text((W / 2, 650), "FibonacciApp · Máquinas virtuales · Load Balancer · newman", font=font(SANS, 34), fill=MUTED, anchor="mm")
    for i, (t, c) in enumerate([("Parte 1 · Vertical (Azure)", ORANGE), ("Parte 2 · Horizontal (balanceador)", BLUE)]):
        x = W / 2 - 420 + i * 840 - 380
        d.rounded_rectangle([x, 760, x + 760, 840], 40, outline=c, width=3)
        d.text((x + 380, 800), t, font=font(SEMI, 34), fill=c, anchor="mm")
    return im


def s_escenario():
    im, d = lienzo("Parte 0", "Escenario de calidad: escalabilidad", ORANGE)
    d.rounded_rectangle([80, 200, 1840, 470], 20, fill=PANEL)
    lineas = envolver(d, "“Cuando un conjunto de usuarios consulta un enésimo número (superior a 1 000 000) de la secuencia "
                         "de Fibonacci de forma concurrente y el sistema se encuentra bajo condiciones normales de operación, "
                         "todas las peticiones deben ser respondidas y el consumo de CPU del sistema no puede superar el 70 %.”",
                      font(SANS, 38), 1680)
    for i, l in enumerate(lineas):
        d.text((120, 230 + i * 52), l, font=font(SANS, 38), fill=TXT)
    viñetas(d, ["Dos criterios: 100 % de peticiones respondidas y CPU ≤ 70 %.",
                "FibonacciApp: servicio Node/Express en el puerto 3000, GET /fibonacci/:n",
                "Calcula F(n) con un ciclo de n−1 sumas de enteros grandes (librería big-integer): muy costoso en CPU."],
            100, 510, 1700, 36)
    terminal(d, 1000, 760, 1840, 1000, ["$ curl http://<vm>:3000/fibonacci/6", ("The answer is 8", GREEN), "",
                                         "$ curl http://<vm>:3000/fibonacci/1000000", ("The answer is 195328212870775773163201494...", GREEN),
                                         ("(208 988 dígitos, ~9 s)", MUTED)], "bash")
    return im


def s_recursos():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "VM en Azure y recursos creados (P1–P2)", ORANGE)
    viñetas(d, ["VM VERTICAL-SCALABILITY · Ubuntu Server · región chilecentral · usuario scalability_lab · llave SSH",
                "B1ls/B2ms no estaban disponibles → equivalentes Standard_DS1_v2 (1 vCPU, 3.5 GiB) y DS2_v2 (2 vCPU, 7 GiB)"],
            80, 200, 1760, 32)
    filas = [["Recurso (6 en total)", "Para qué sirve"],
             ["Máquina virtual", "El cómputo (vCPU + RAM) donde corre Ubuntu y la app"],
             ["Disco administrado (SO)", "Almacenamiento persistente del sistema y la app"],
             ["Interfaz de red (NIC)", "Conecta la VM a la subred; IP privada, IP pública y NSG"],
             ["IP pública", "Dirección para entrar desde Internet (SSH y la app)"],
             ["Red virtual + subred", "Red privada aislada con direccionamiento propio"],
             ["Network Security Group", "Firewall: reglas de entrada/salida por puerto y protocolo"]]
    tabla(d, 80, 420, filas, [560, 1200], 30, 70)
    return im


def s_ssh():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "Instalación, SSH e Inbound port rule (P3)", ORANGE)
    viñetas(d, ["Node con nvm → git clone → npm install → forever start FibonacciApp.js",
                "Con “node FibonacciApp.js” la app muere al cerrar SSH: es hija de la shell y recibe SIGHUP. "
                "forever (o pm2/systemd) la desacopla de la terminal y la reinicia si se cae.",
                "El NSG niega por defecto todo el tráfico entrante desde Internet (solo se abrió el 22). "
                "Sin una regla que permita TCP 3000 los paquetes se descartan."],
            80, 210, 900, 33)
    terminal(d, 1040, 210, 1840, 620, ["scalability_lab@VERTICAL-SCALABILITY:~$",
                                       "  npm install forever -g",
                                       "  forever start FibonacciApp.js",
                                       "",
                                       "$ curl localhost:3000/fibonacci/6", ("The answer is 8", GREEN)], "ssh scalability_lab@68.211.144.189")
    tabla(d, 1040, 680, [["Regla de entrada", "Puerto", "Protocolo", "Acción"],
                         ["SSH", "22", "TCP", ("Allow", GREEN)],
                         ["FibonacciApp (nueva)", "3000", "TCP", ("Allow", GREEN)],
                         ["DenyAllInBound (defecto)", "*", "*", ("Deny", RED)]], [330, 140, 170, 160], 26, 60)
    return im


def s_tiempos():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "Tiempos de respuesta (P4)", ORANGE)
    ruta = ROOT / "results"
    def leer(n):
        with open(ruta / n, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    a, b = leer("parte1_tiempos_DS1_v2_p80.csv"), leer("parte1_tiempos_DS2_v2.csv")
    filas = [["n", "DS1_v2 (s)", "DS2_v2 (s)"]] + [[f"{int(x['nth']):,}".replace(",", " "), f"{float(x['time_total_s']):.2f}",
                                                    f"{float(y['time_total_s']):.2f}"] for x, y in zip(a, b)]
    filas.append(["Promedio", "9.26", "9.49"])
    tabla(d, 80, 200, filas, [260, 230, 230], 27, 54, resaltar=(11,))
    pegar(im, IMG / "p1_tiempos_azure.png", (860, 190, 1850, 640))
    viñetas(d, ["n−1 sumas con números de ~209 000 dígitos → costo ≈ cuadrático (~10¹¹ operaciones)",
                "big-integer es JavaScript puro, un objeto nuevo por suma, un solo hilo, sin memoización"],
            880, 680, 960, 30)
    return im


def s_cpu():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "Consumo de CPU – Azure Monitor (P5)", ORANGE)
    pegar(im, IMG / "p1_cpu_azure.png", (60, 180, 1290, 800))
    viñetas(d, [("DS1_v2: 85–100 %", ORANGE), "Cálculo 100 % CPU-bound, ocupa el único vCPU",
                ("DS2_v2: ~50 %", ORANGE), "Node ejecuta JS en un solo hilo: usa 1 de los 2 núcleos",
                ("Ambos superan el 70 %", RED)], 1320, 230, 540, 32)
    return im


def s_newman():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "Carga concurrente con newman (P6)", ORANGE)
    tabla(d, 80, 200, [["Prueba en Azure", "Exitosas", "Prom.", "Máx.", "Errores"],
                       ["DS1_v2 · 2 newman", "14/20 (70 %)", "12.4 s", "16.3 s", ("6 ECONNRESET", RED)],
                       ["DS1_v2 · 4 newman", "23/40 (58 %)", "24.3 s", "39.6 s", ("17 ECONNRESET", RED)],
                       ["DS2_v2 · 2 newman", "13/20 (65 %)", "11.6 s", "16.5 s", ("7 ECONNRESET", RED)],
                       ["DS2_v2 · 4 newman", "21/40 (52 %)", "23.9 s", "39.9 s", ("19 ECONNRESET", RED)]],
          [420, 280, 180, 180, 320], 30, 66)
    import re
    txt = (ROOT / "results/newman/p1_DS1_v2_x2_p80/proceso1.txt").read_text(encoding="utf-8", errors="replace")
    txt = re.sub(r"\[[0-9;]*m", "", txt)
    it = re.findall(r"GET (\S+) \[([^\]]+)\]", txt)
    lineas = [f"{k + 1:>2}  GET /fibonacci/1000000  [{r}]" for k, (_, r) in enumerate(it)]
    lineas = [(l, RED) if "errored" in l else l for l in lineas]
    prom = re.search(r"average response time: ([^\[]+)", txt).group(1).strip()
    terminal(d, 80, 560, 900, 1000, ["$ newman run ... -e ... -n 10   (proceso 1 de 2)"] + lineas +
             [(f"average response time: {prom}", MUTED)], "newman · Azure DS1_v2 · 68.211.144.189", 21)
    viñetas(d, ["Las peticiones hacen cola detrás del único hilo: 2 → 4 clientes duplica el tiempo",
                "ECONNRESET: Node cierra tarde las conexiones keep-alive (5 s) mientras el event loop está "
                "bloqueado; el cliente ya había reutilizado la conexión y pierde la petición"], 960, 570, 880, 31)
    return im


def s_tamanos():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "B1ls vs B2ms (P7)", ORANGE)
    tabla(d, 80, 210, [["", "B1ls", "B2ms", "DS1_v2 (usada)", "DS2_v2 (usada)"],
                       ["vCPU", "1", "2", "1", "2"], ["RAM", "0.5 GiB", "8 GiB", "3.5 GiB", "7 GiB"],
                       ["CPU base", "5 %", "60 % (de 200 %)", "100 %", "100 %"],
                       ["Costo aprox.", "~US$4/mes", "~US$60/mes", "~US$53/mes", "~US$107/mes"]],
          [300, 300, 340, 400, 400], 32, 72)
    viñetas(d, ["La serie B es “burstable”: acumula créditos de CPU por debajo del rendimiento base y los gasta en ráfagas.",
                "Con carga sostenida al 100 % una B1ls agota los créditos y queda limitada al 5 %; además 0.5 GiB es muy poco para Node + npm.",
                "B2ms: base mucho más alta, más memoria, ancho de banda e IOPS… a ~15 veces el precio."],
            80, 620, 1760, 33)
    return im


def s_concl_vertical():
    im, d = lienzo("Parte 1 · Escalabilidad vertical", "¿Sirvió escalar verticalmente? (P8–P12)", ORANGE)
    viñetas(d, [("P8 · No es buena solución: 1 → 2 vCPU no cambió el tiempo (9.26 s vs 9.49 s) ni la tasa de éxito; "
                 "se paga el doble por un núcleo ocioso.", TXT),
                "P8/P9 · El resize detiene y reinicia la VM: la app se cae, forever no arranca solo, se pierde la memoria y "
                "el disco temporal, puede cambiar la IP; hay un techo de tamaño y sigue siendo un único punto de falla.",
                "P10 · No hubo mejora real: la CPU bajó a ~50 % solo porque hay un núcleo más sin usar.",
                "P11 · Con 4 newman tampoco: 58 % (DS1_v2) vs 52 % (DS2_v2), tiempo promedio ~24 s en ambos."],
            80, 210, 1760, 34)
    d.rounded_rectangle([80, 800, 1840, 940], 20, fill=(69, 26, 26))
    d.text((960, 870), "P12 · Con escalamiento vertical NO se cumple el escenario de calidad", font=font(BOLD, 44), fill=RED, anchor="mm")
    return im


def s_azure_p2():
    im, d = lienzo("Parte 2 · Escalabilidad horizontal", "Infraestructura creada en Azure", BLUE)
    tabla(d, 80, 200, [["Recurso", "Configuración"],
                       ["Load Balancer lab-lb", "SKU Standard, público"],
                       ["IP pública lb-ip", "Standard · estática · zone-redundant (1,2,3)"],
                       ["Backend pool lb-backend", "NICs de VM1, VM2, VM3"],
                       ["Health probe lb-probe", "HTTP GET / puerto 3000"],
                       ["LB rule lb-rule", "TCP 80 → 3000 · sesión: None"],
                       ["VNet lab-vnet / lab-subnet", "10.0.0.0/16 · 10.0.0.0/24"],
                       ["NSG lab-nsg", "Allow 22, 80, 3000"],
                       ["VM1", "DS1_v2 · zona 1 · cloud-init instala la app"]], [560, 820], 29, 62)
    terminal(d, 80, 790, 1840, 1010, ["$ az vm create -g LOAD_BALANCING_LAB -n VM2 --zone 2 --size Standard_DS1_v2 ...",
                                      ("ERROR: (ReadOnlyDisabledSubscription) The subscription 'de1c9ae7-...' is disabled and", RED),
                                      ("therefore marked as read only. You cannot perform any write actions on this subscription", RED),
                                      ("→ Se agotaron los créditos de Azure for Students", YELLOW)], "Azure CLI")
    viñetas(d, ["Creado con Azure CLI (parte2_infra.sh + cloud-init)", "Evidencia: results/azure_evidencia/"], 1500, 230, 360, 28)
    return im


def s_simulacion():
    im, d = lienzo("Parte 2 · Escalabilidad horizontal", "Misma arquitectura, en local", BLUE)
    tabla(d, 80, 200, [["Azure", "Simulación local"],
                       ["VM de 1 vCPU con FibonacciApp", "Proceso node fijado a 1 núcleo físico (VM1→1, VM2→3, VM3→5, VM4→7)"],
                       ["Load Balancer + rule + pool", "balanceador.js: frontend :8090, round-robin"],
                       ["Health probe HTTP /", "GET / cada 5 s, fuera tras 2 fallos"],
                       ["Idle timeout 4 min", "Igual: 4 min sin datos → reset"],
                       ["Azure Monitor CPU", "% de CPU por proceso cada 2 s"],
                       ["Resize (vertical)", "Misma VM con 2 núcleos"]], [620, 1140], 28, 64)
    d.rounded_rectangle([80, 690, 1840, 1000], 20, fill=(20, 54, 40))
    d.text((120, 720), "Validación contra Azure", font=font(BOLD, 40), fill=GREEN)
    tabla(d, 120, 790, [["1 VM · 2 newman", "Exitosas", "Errores"],
                        ["Azure DS1_v2 (real)", "11/20", "9 ECONNRESET"],
                        ["Simulación local", "11/20", "9 ECONNRESET"]], [520, 300, 380], 30, 60)
    d.text((1500, 880), "Mismo\ncomportamiento", font=font(BOLD, 44), fill=GREEN, anchor="mm", align="center")
    return im


def s_comparativo():
    im, d = lienzo("Parte 2 · Resultados", "Vertical vs. horizontal (informe newman 1)", BLUE)
    pegar(im, IMG / "comparativo.png", (40, 180, 1880, 760))
    tabla(d, 80, 780, [["Prueba", "Exitosas", "Prom.", "Duración"],
                       ["1 VM · 1 núcleo · 2 newman", ("11/20 (55 %)", RED), "17.8 s", "3 m 08 s"],
                       ["3 VMs + balanceador · 2 newman", ("20/20 (100 %)", GREEN), "12.3 s", "2 m 07 s"],
                       ["4 VMs + balanceador · 4 newman", ("35/40 (88 %)", GREEN), "16.9 s", "2 m 58 s"]],
          [700, 360, 220, 260], 28, 56)
    return im


def s_cpu_vm():
    im, d = lienzo("Parte 2 · Resultados", "CPU de cada VM", BLUE)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pruebas = [("v2_2nucleos_x4", "1 VM / 2 núcleos (vertical) - 4 newman"), ("h3_x2", "3 VMs + balanceador - 2 newman"),
               ("h4_x4", "4 VMs + balanceador - 4 newman")]
    fig, axs = plt.subplots(3, 1, figsize=(11.4, 8.3), dpi=100)
    for ax, (p, t) in zip(axs, pruebas):
        with open(SIM / p / "cpu.csv", encoding="utf-8-sig") as f:
            filas = list(csv.DictReader(f))
        for vm in [k for k in filas[0] if k != "timestamp"]:
            ax.plot([i * 2 for i in range(len(filas))], [float(r[vm] or 0) for r in filas], label=vm, lw=1.3)
        ax.axhline(70, color="red", ls="--", lw=.8); ax.set_ylim(0, 105); ax.set_title(t, fontsize=11)
        ax.set_ylabel("% CPU"); ax.grid(alpha=.3); ax.legend(fontsize=8, loc="lower right", ncol=4)
    axs[-1].set_xlabel("segundos"); fig.tight_layout()
    tmp = VID / "_cpu_vm.png"; fig.savefig(tmp); plt.close(fig)
    pegar(im, tmp, (40, 165, 1240, 1030))
    viñetas(d, [("Vertical (2 núcleos): tope 50 %", ORANGE), "un núcleo al 100 %, el otro ocioso",
                ("Horizontal: cada VM usa su núcleo completo cuando tiene trabajo y descansa cuando no", BLUE),
                "3 VMs: 45 %, 65 % y 73 % de promedio", "4 VMs: 71–77 % cada una"], 1260, 220, 620, 31)
    return im


def s_costos():
    im, d = lienzo("Parte 2 · Resultados", "Costos (aprox., pay-as-you-go)", BLUE)
    tabla(d, 80, 210, [["Infraestructura", "Recursos", "Costo aprox."],
                       ["Vertical", "1 × DS2_v2 + IP pública", "≈ US$110/mes"],
                       ["Horizontal 3 nodos", "3 × DS1_v2 + LB Standard + IP", "≈ US$180/mes"],
                       ["Horizontal 4 nodos", "4 × DS1_v2 + LB + IP", "≈ US$235/mes"],
                       ["(Enunciado) 3 × B1ls", "3 × B1ls + LB + IPs", "≈ US$35/mes*"]], [480, 760, 420], 32, 76)
    viñetas(d, ["El horizontal es más caro por hora, pero es el único que cumple el requisito.",
                "Tolera la caída de una VM o de una zona completa (VMs en 3 zonas).",
                "Crece y decrece agregando o quitando nodos del backend pool, sin apagar el servicio.",
                ("* los B1ls se quedarían sin créditos de CPU con esta carga", MUTED)], 80, 640, 1760, 33)
    return im


def s_porque():
    im, d = lienzo("Parte 2 · Punto 3", "¿Por qué aumentó la tasa de éxito?", BLUE)
    viñetas(d, ["Una instancia de Node procesa una sola petición pesada a la vez.",
                "Con N instancias, cada una con su hilo y su núcleo, el balanceador manda cada petición a una distinta: "
                "se atienden en paralelo en lugar de hacer cola.",
                "Sin cola, el event loop no queda bloqueado mientras otro cliente espera → desaparecen los cierres "
                "keep-alive que causaban los ECONNRESET.",
                "4 VMs / 4 newman: 52 % → 88 % de éxito, 42.7 s → 16.9 s de promedio, la mitad de duración.",
                "Los 5 fallos restantes: el round-robin no sabe qué nodo está libre y a veces envía a uno ocupado; "
                "el health probe marca los nodos como caídos mientras calculan."], 80, 210, 1760, 35)
    d.rounded_rectangle([80, 860, 1840, 990], 20, fill=(20, 54, 40))
    d.text((960, 925), "Con nodos suficientes (3 VMs, 2 clientes) se respondieron TODAS las peticiones",
           font=font(BOLD, 40), fill=GREEN, anchor="mm")
    return im


def s_preguntas1():
    im, d = lienzo("Parte 2 · Preguntas", "Balanceadores, SKU, backend pool y health probe", BLUE)
    viñetas(d, ["Tipos: Load Balancer (capa 4, público o interno) · Application Gateway (capa 7, URL, TLS, WAF) · "
                "Front Door (capa 7 global) · Traffic Manager (DNS global) · Gateway LB (appliances).",
                "SKU = nivel del producto. Basic: sin zonas ni SLA, abierto por defecto (retirado). "
                "Standard (usado): hasta 1000 instancias, zone-redundant, SLA 99.99 %, seguro por defecto, reglas de salida.",
                "IP pública: es la única entrada desde Internet; las VMs quedan con IP privada y se pueden agregar o quitar "
                "sin que el cliente cambie de dirección.",
                "Backend pool: conjunto de VMs/NICs que reciben el tráfico; escalar horizontalmente = agregar miembros.",
                "Health probe: sondea cada instancia (TCP/HTTP/HTTPS); si falla deja de recibir flujos nuevos hasta que se recupere."],
            80, 200, 1760, 33)
    return im


def s_preguntas2():
    im, d = lienzo("Parte 2 · Preguntas", "Regla, sesión, VNet, zonas y NSG", BLUE)
    viñetas(d, ["LB rule: une frontend (IP:80), backend pool, puerto 3000, protocolo y probe.",
                "Persistencia: None (5-tupla) · Client IP (2-tupla) · Client IP + protocolo (3-tupla). Sirve si hay sesión en "
                "memoria, pero desbalancea la carga y ata clientes a un nodo → mejor una app sin estado.",
                "VNet: red privada aislada; address space 10.0.0.0/16; subnet = partición con su address range 10.0.0.0/24.",
                "Availability zones: datacenters independientes en la región; 3 zonas → caer un datacenter solo tumba 1 nodo. "
                "IP zone-redundant: se publica desde las 3 zonas y sobrevive a la caída de una.",
                "NSG: filtra tráfico con reglas priorizadas (22, 80, 3000 permitidos; el resto denegado)."],
            80, 200, 1760, 33)
    return im


def s_diagrama():
    im, d = lienzo("Parte 2", "Diagrama de despliegue", BLUE)
    def caja(x0, y0, x1, y1, titulo, sub="", color=BLUE, fill=PANEL):
        d.rounded_rectangle([x0, y0, x1, y1], 16, fill=fill, outline=color, width=3)
        d.text(((x0 + x1) / 2, y0 + 34), titulo, font=font(SEMI, 28), fill=TXT, anchor="mm")
        if sub:
            d.multiline_text(((x0 + x1) / 2, y0 + 64), sub, font=font(SANS, 22), fill=MUTED, anchor="ma", align="center")
    def flecha(x0, y0, x1, y1, color=MUTED):
        d.line([x0, y0, x1, y1], fill=color, width=4)
        d.polygon([(x1, y1), (x1 - 16, y1 - 9), (x1 - 16, y1 + 9)], fill=color)
    d.rounded_rectangle([420, 180, 1860, 1010], 20, outline=MUTED, width=2)
    d.text((440, 195), "Resource group LOAD_BALANCING_LAB · chilecentral", font=font(SANS, 24), fill=MUTED)
    caja(70, 520, 350, 660, "Cliente", "navegador / newman", MUTED)
    caja(470, 470, 760, 710, "IP pública", "lb-ip · Standard\nzone-redundant\n(zonas 1, 2, 3)")
    d.rounded_rectangle([820, 250, 1180, 950], 16, outline=BLUE, width=3)
    d.text((1000, 280), "Load Balancer lab-lb", font=font(SEMI, 26), fill=BLUE, anchor="mm")
    caja(850, 320, 1150, 450, "Frontend :80")
    caja(850, 480, 1150, 630, "LB rule", "80 → 3000\nsesión: None")
    caja(850, 660, 1150, 790, "Health probe", "HTTP GET / :3000")
    caja(850, 820, 1150, 930, "Backend pool")
    d.rounded_rectangle([1240, 250, 1830, 990], 16, outline=GREEN, width=2)
    d.text((1535, 275), "VNet 10.0.0.0/16 · subnet 10.0.0.0/24 · NSG", font=font(SANS, 22), fill=GREEN, anchor="mm")
    for i, (n, z, ip) in enumerate([("VM1", 1, "10.0.0.4"), ("VM2", 2, "10.0.0.5"), ("VM3", 3, "10.0.0.6"), ("VM4", 1, "10.0.0.7")]):
        y = 310 + i * 168
        caja(1290, y, 1780, y + 140, f"{n} · zona {z}", f"{ip} · Ubuntu · Node + forever\nFibonacciApp :3000", GREEN)
        flecha(1150, 875, 1290, y + 70, GREEN)
    flecha(350, 590, 470, 590); flecha(760, 590, 850, 385)
    d.text((410, 560), "HTTP :80", font=font(SANS, 22), fill=MUTED, anchor="mm")
    return im


def s_conclusion():
    im, d = lienzo("Conclusiones", "Resumen", BLUE)
    viñetas(d, [("Vertical: más vCPU no ayuda a una app de un solo hilo; reinicia la VM y no cumple el escenario.", ORANGE),
                ("Horizontal: más instancias + balanceador = peticiones en paralelo; con nodos suficientes se respondió el 100 %.", BLUE),
                "La CPU por VM sigue al 100 % mientras calcula, pero el promedio del sistema baja del 70 % y se reparte.",
                "Se escala agregando VMs al backend pool, sin apagar el servicio y con tolerancia a fallos por zonas.",
                ("Repositorio: github.com/juandiegomelo21-commits/LABORATORIO-9-ARSW", MUTED)], 80, 220, 1760, 38, 30)
    return im


# ---------------------------------------------------------------- animaciones (repetición de pruebas reales)
def seg(hms):
    h, m, s = map(int, hms.split(":"))
    return h * 3600 + m * 60 + s


def animacion(prueba, titulo, velocidad):
    log = [l.rstrip() for l in (SIM / prueba / "balanceador.log").read_text(encoding="utf-8", errors="replace").splitlines()]
    with open(SIM / prueba / "cpu.csv", encoding="utf-8-sig") as f:
        cpu = list(csv.DictReader(f))
    vms = [k for k in cpu[0] if k != "timestamp"]
    eventos = [(seg(l[:8]), l) for l in log if l[:2].isdigit()]
    t0 = eventos[1][0] if len(eventos) > 1 else eventos[0][0]
    t_fin = max(e[0] for e in eventos) + 2
    tcpu = [(seg(r["timestamp"]), r) for r in cpu]
    n_frames = int((t_fin - t0) / velocidad * FPS) + FPS * 3
    base, d0 = lienzo("Parte 2 · Repetición de la prueba real", titulo, BLUE)
    d0.text((80, 160), f"Reconstruida desde results/simulacion/{prueba}/ (bitácora del balanceador + CPU cada 2 s) · acelerada x{velocidad}",
            font=font(SANS, 24), fill=MUTED)
    colores = [BLUE, ORANGE, GREEN, (232, 121, 249)]

    def frame(i):
        t = t0 + i * velocidad / FPS
        im = base.copy(); d = ImageDraw.Draw(im)
        vis = [l for (ts, l) in eventos if ts <= t]
        lineas = []
        for l in vis[-26:]:
            c = (220, 220, 220)
            if " xx " in l: c = RED
            elif "NO responde" in l: c = YELLOW
            elif "SANO" in l: c = (180, 200, 120)
            elif " <- " in l: c = GREEN
            lineas.append((l[:78], c))
        terminal(d, 60, 210, 1160, 1020, lineas, "node simulacion/balanceador.js", 23)
        ok = sum(1 for l in vis if " <- " in l and "/fibonacci/1000000" in l)
        err = sum(1 for l in vis if " xx " in l)
        trans = int(t - t0)
        d.rounded_rectangle([1200, 210, 1860, 400], 16, fill=PANEL)
        d.text((1230, 240), "Tiempo real de la prueba", font=font(SANS, 26), fill=MUTED)
        d.text((1230, 280), f"{trans // 60}:{trans % 60:02d}", font=font(BOLD, 64), fill=TXT)
        d.text((1560, 240), "Respondidas", font=font(SANS, 26), fill=MUTED)
        d.text((1560, 280), str(ok), font=font(BOLD, 64), fill=GREEN)
        d.text((1730, 240), "Errores", font=font(SANS, 26), fill=MUTED)
        d.text((1730, 280), str(err), font=font(BOLD, 64), fill=RED if err else MUTED)
        fila = next((r for (ts, r) in reversed(tcpu) if ts <= t), cpu[0])
        d.text((1200, 430), "CPU por VM (núcleo asignado)", font=font(SEMI, 28), fill=TXT)
        alto = min(120, int(540 / len(vms)) - 20)
        for k, vm in enumerate(vms):
            y = 490 + k * (alto + 20)
            v = max(0.0, min(100.0, float(fila[vm] or 0)))
            enviadas = sum(1 for l in vis if l.endswith(f"-> {vm}") and "/fibonacci/1000000" in l)
            d.text((1200, y + alto / 2), vm, font=font(BOLD, 30), fill=colores[k % 4], anchor="lm")
            d.rounded_rectangle([1290, y, 1760, y + alto], 10, fill=(40, 52, 74))
            d.rounded_rectangle([1290, y, 1290 + int(470 * v / 100), y + alto], 10,
                                fill=RED if v > 70 else colores[k % 4])
            x70 = 1290 + int(470 * 0.7); d.line([x70, y - 4, x70, y + alto + 4], fill=(255, 255, 255), width=2)
            d.text((1775, y + alto / 2 - 14), f"{v:.0f}%", font=font(SEMI, 28), fill=TXT, anchor="lm")
            d.text((1775, y + alto / 2 + 18), f"{enviadas} pet.", font=font(SANS, 20), fill=MUTED, anchor="lm")
        return im

    return n_frames, frame


# ---------------------------------------------------------------- guion (voz 1 = Parte 1 + montaje Parte 2, voz 2 = pruebas, resultados, preguntas)
SEGMENTOS = [
    (1, s_portada, "Hola. Este es el laboratorio nueve de Arquitecturas de Software: escalamiento vertical y horizontal. "
     "En la primera parte mostramos el escalamiento vertical que hicimos en Azure, y en la segunda, el escalamiento horizontal con un balanceador de carga."),
    (1, s_escenario, "El escenario de calidad dice que, cuando varios usuarios piden al mismo tiempo un número de Fibonacci mayor a un millón, "
     "todas las peticiones deben responderse y la CPU no puede pasar del setenta por ciento. La aplicación es un servicio en Node que calcula "
     "el enésimo número con una función muy ineficiente: fibonacci de seis responde ocho, pero fibonacci de un millón tiene más de doscientos mil dígitos."),
    (1, s_recursos, "Creamos la máquina virtual VERTICAL-SCALABILITY con Ubuntu, en la región Chile Central. Como los tamaños B no estaban disponibles, "
     "usamos DS1 v2, con un vCPU, y luego DS2 v2, con dos. Junto con la VM, Azure crea cinco recursos más: el disco del sistema operativo, la interfaz de red, "
     "la IP pública, la red virtual con su subred y el grupo de seguridad de red, que funciona como firewall."),
    (1, s_ssh, "Instalamos Node con nvm, clonamos el repositorio y dejamos la aplicación corriendo con forever. Si la lanzamos solo con node, se cae al cerrar SSH, "
     "porque el proceso es hijo de la sesión y recibe la señal SIGHUP. Y hay que crear una regla de entrada para el puerto tres mil, porque el grupo de seguridad "
     "bloquea por defecto todo el tráfico que llega desde Internet."),
    (1, s_tiempos, "Medimos los tiempos para n entre un millón y un millón noventa mil. Cada petición tarda entre nueve y diez segundos, y casi lo mismo en la máquina de dos núcleos. "
     "Tarda tanto porque hace un millón de sumas con números de unos doscientos nueve mil dígitos, con una librería de enteros grandes escrita en JavaScript, "
     "en un solo hilo y sin reutilizar nada entre peticiones."),
    (1, s_cpu, "Esta es la métrica de CPU de Azure Monitor. Con un vCPU, la CPU llega casi al cien por ciento, porque el cálculo es puro procesamiento. "
     "Con dos vCPU se queda en cincuenta por ciento: Node ejecuta el JavaScript en un solo hilo, así que usa un núcleo y el otro queda sin hacer nada. "
     "En los dos casos, el núcleo que trabaja supera el setenta por ciento."),
    (1, s_newman, "Con newman lanzamos dos y luego cuatro ejecuciones en paralelo, de diez peticiones cada una. Con dos clientes solo se respondió entre el sesenta y cinco "
     "y el setenta por ciento, y con cuatro, alrededor de la mitad. El tiempo promedio se duplica, porque las peticiones hacen cola. Todos los fallos son ECONNRESET: "
     "mientras el único hilo está ocupado con la petición de otro cliente, Node cierra tarde las conexiones keep-alive, y el cliente pierde la petición que ya había enviado."),
    (1, s_tamanos, "Sobre los tamaños: B1ls tiene un vCPU y medio giga de RAM, y B2ms dos vCPU y ocho gigas, a unas quince veces el precio. Pero la diferencia importante "
     "es que la serie B es burstable: acumula créditos de CPU cuando está por debajo de su rendimiento base, y los gasta en ráfagas. Con una carga sostenida como esta, "
     "una B1ls se queda sin créditos y la limitan al cinco por ciento."),
    (1, s_concl_vertical, "Entonces, ¿aumentar el tamaño sirvió? No. Los tiempos y la tasa de éxito fueron prácticamente iguales, porque la aplicación no puede usar el segundo núcleo. "
     "Además, para cambiar el tamaño Azure reinicia la VM: el servicio se cae, forever no vuelve a arrancar solo, y seguimos con un único punto de falla. "
     "Con cuatro clientes tampoco mejoró. Conclusión: con escalamiento vertical no se cumple el escenario de calidad."),
    (1, s_azure_p2, "En la segunda parte construimos en Azure el balanceador de carga Standard, con su IP pública redundante entre zonas, el backend pool, el health probe, "
     "la regla de balanceo del puerto ochenta al tres mil, la red virtual, el grupo de seguridad y la primera máquina virtual. Al crear la segunda y la tercera, "
     "Azure respondió que la suscripción estaba deshabilitada: se habían acabado los créditos."),
    (1, s_simulacion, "Por eso reprodujimos la misma arquitectura en un computador local. Cada máquina virtual es un proceso de la aplicación fijado a un único núcleo del procesador, "
     "como una VM de un vCPU. Delante va un balanceador que reparte las peticiones en round robin, hace el health probe cada cinco segundos y tiene el mismo idle timeout "
     "de cuatro minutos que Azure. Para validarlo repetimos la prueba de una sola máquina, y dio exactamente lo mismo que en Azure: once de veinte, con nueve ECONNRESET."),
    (2, ("v1_1nucleo_x4", "1 VM · 1 núcleo · 4 newman en paralelo", 12),
     "Esta es la repetición acelerada de la prueba con una sola máquina y cuatro clientes. El núcleo está todo el tiempo cerca del cien por ciento, las peticiones hacen cola "
     "y van apareciendo los errores en rojo. Terminó con veintiuno de cuarenta respondidas, cuarenta y tres segundos de promedio y más de seis minutos de duración."),
    (2, ("h4_x4", "4 VMs + balanceador · 4 newman en paralelo", 5),
     "Ahora, la misma carga con cuatro máquinas detrás del balanceador. Cada petición va a una máquina distinta, las cuatro trabajan en paralelo, cada una con su núcleo, "
     "y casi no hay errores. También se ve que el health probe marca los nodos como no disponibles mientras calculan, porque no alcanzan a contestar. "
     "Resultado: treinta y cinco de cuarenta, diecisiete segundos de promedio, y la mitad del tiempo total."),
    (2, s_comparativo, "Este es el comparativo. En naranja, el escalamiento vertical en Azure; en azul, la simulación. Con una sola máquina, de uno o de dos núcleos, "
     "se responde alrededor de la mitad. Con tres máquinas y dos clientes se respondió el cien por ciento, con doce segundos de promedio, prácticamente lo que tarda una petición sola. "
     "Y con cuatro máquinas y cuatro clientes, el ochenta y ocho por ciento."),
    (2, s_cpu_vm, "Y esta es la CPU de cada máquina. Con escalamiento vertical a dos núcleos, la CPU se queda en cincuenta por ciento sin mejorar nada. Con escalamiento horizontal, "
     "cada máquina usa su núcleo completo cuando tiene trabajo y descansa cuando no, así que la carga se reparte entre todas."),
    (2, s_costos, "En costos, una DS2 v2 sale en unos ciento diez dólares al mes, y tres DS1 v2 con el balanceador, en unos ciento ochenta. El esquema horizontal es más caro por hora, "
     "pero es el único que cumple el requisito, tolera la caída de una máquina o de una zona completa, y crece agregando nodos sin apagar el servicio."),
    (2, s_porque, "¿Por qué aumenta la tasa de éxito? Porque cada instancia de Node solo atiende una petición pesada a la vez. Con más instancias, cada una con su propio hilo y su propio núcleo, "
     "las peticiones se procesan en paralelo en lugar de hacer cola, y desaparecen los cierres de conexión que causaban los errores. Los pocos fallos con cuatro máquinas pasan "
     "cuando el round robin manda una petición a un nodo que todavía está ocupado."),
    (2, s_preguntas1, "Ahora las preguntas. Azure tiene el Load Balancer de capa cuatro, público o interno; Application Gateway, de capa siete; y Front Door y Traffic Manager para balanceo global. "
     "El SKU es el nivel del producto: Basic, sin zonas ni SLA, y Standard, el que usamos, con zonas, SLA y seguro por defecto. El balanceador público necesita una IP pública "
     "porque es la única entrada al sistema. El backend pool es el conjunto de máquinas que reciben el tráfico, y el health probe revisa cuáles están sanas para no mandarle peticiones a una caída."),
    (2, s_preguntas2, "La regla de balanceo une el frontend, el pool, los puertos y el probe. La persistencia puede ser ninguna, por IP del cliente, o por IP y protocolo; pegar un cliente a un nodo "
     "ayuda con sesiones en memoria, pero desbalancea la carga, por eso es mejor una aplicación sin estado. La red virtual es la red privada, con su espacio de direcciones dividido en subredes. "
     "Las zonas de disponibilidad son datacenters independientes: con tres, la caída de uno solo tumba un nodo, y una IP zone-redundant sigue funcionando aunque caiga una zona. "
     "Y el grupo de seguridad filtra el tráfico permitido."),
    (2, s_diagrama, "Este es el diagrama de despliegue: el cliente llega a la IP pública del balanceador por el puerto ochenta, la regla lo envía al backend pool, y de ahí a las máquinas "
     "en tres zonas distintas, dentro de la misma red virtual y protegidas por el grupo de seguridad."),
    (2, s_conclusion, "En conclusión: el escalamiento vertical no resolvió el problema, porque la aplicación solo usa un núcleo. El escalamiento horizontal con un balanceador sí: "
     "con suficientes nodos se respondieron todas las peticiones. Todo el código, los datos y las gráficas están en el repositorio. Gracias."),
]


def mmss(t):
    return f"{int(t) // 60:02d}:{int(t) % 60:02d}"


def srt_t(t):
    return f"{int(t) // 3600:02d}:{int(t) % 3600 // 60:02d}:{int(t) % 60:02d},{int((t % 1) * 1000):03d}"


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    salida = VID / "lab9_video.mp4"
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                             "-pix_fmt", "yuv420p", "-r", "30", str(salida)], stdin=subprocess.PIPE)
    t, guion, srt = 0.0, [], []
    for idx, (voz, render, texto) in enumerate(SEGMENTOS, 1):
        narr = len(texto.split()) / WPS + 1.5
        if callable(render):
            dur = max(5.0, narr)
            data = render().tobytes()
            for _ in range(int(dur * FPS)):
                proc.stdin.write(data)
            nombre = render.__name__[2:]
        else:
            prueba, titulo, vel = render
            n, frame = animacion(prueba, titulo, vel)
            n = max(n, int(narr * FPS))
            for i in range(n):
                proc.stdin.write(frame(i).tobytes())
            dur = n / FPS
            nombre = f"repeticion_{prueba}"
        guion.append((idx, voz, t, t + dur, nombre, texto))
        srt.append(f"{idx}\n{srt_t(t + 0.3)} --> {srt_t(t + dur - 0.2)}\n[Voz {voz}] {texto}\n")
        print(f"{idx:2d} voz{voz} {mmss(t)}-{mmss(t + dur)} {nombre}", flush=True)
        t += dur
    proc.stdin.close(); proc.wait()

    md = ["# Guion del video – Laboratorio 9 (2 voces)", "",
          f"Video: `lab9_video.mp4` · duración {mmss(t)} · sin audio. **Voz 1** narra la Parte 1 y cómo se montó la Parte 2; "
          "**Voz 2** narra las pruebas de la Parte 2, los resultados y las preguntas.",
          "Cada bloque dura lo suficiente para leer el texto a ritmo tranquilo; `guion.srt` tiene los mismos textos con tiempos "
          "(se puede cargar en el reproductor o en el editor como subtítulos para leer mientras se graba).", ""]
    for voz in (1, 2):
        partes = [g for g in guion if g[1] == voz]
        md += [f"## Voz {voz} – {'Parte 1 (vertical, Azure) y montaje de la Parte 2' if voz == 1 else 'Parte 2: pruebas, resultados y preguntas'} "
               f"({mmss(partes[0][2])} – {mmss(partes[-1][3])})", ""]
        for idx, _, a, b, nombre, texto in partes:
            md += [f"**{mmss(a)} – {mmss(b)}** · _{nombre.replace('_', ' ')}_", "", texto, ""]
    (VID / "GUION.md").write_text("\n".join(md), encoding="utf-8")
    (VID / "guion.srt").write_text("\n".join(srt), encoding="utf-8")
    print("total", mmss(t), salida)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "previa":  # guarda PNGs de cada diapositiva para revisar
        (VID / "previa").mkdir(exist_ok=True)
        for idx, (_, render, _) in enumerate(SEGMENTOS, 1):
            if callable(render):
                render().save(VID / "previa" / f"{idx:02d}_{render.__name__}.png")
            else:
                n, frame = animacion(*render)
                frame(int(n * 0.6)).save(VID / "previa" / f"{idx:02d}_anim_{render[0]}.png")
    else:
        main()
