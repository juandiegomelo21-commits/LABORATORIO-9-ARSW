"""Resume los reportes JSON de newman de una carpeta results/newman/<etiqueta>.

Uso: python resumen_newman.py <carpeta> [<carpeta> ...]
Imprime, por carpeta, las peticiones exitosas/fallidas, tiempos (min/prom/max) y errores.
"""
import json
import pathlib
import sys


def resumir(carpeta):
    carpeta = pathlib.Path(carpeta)
    ok, fallos, tiempos, errores = 0, 0, [], {}
    for rep in sorted(carpeta.glob("proceso*.json")):
        run = json.loads(rep.read_text(encoding="utf-8"))["run"]
        for ex in run["executions"]:
            err = ex.get("requestError")
            resp = ex.get("response")
            if err or not resp or resp.get("code") != 200:
                fallos += 1
                msg = (err or {}).get("code") or (err or {}).get("message") or f"HTTP {resp and resp.get('code')}"
                errores[msg] = errores.get(msg, 0) + 1
            else:
                ok += 1
                tiempos.append(resp["responseTime"] / 1000)
    total = ok + fallos
    inicio = (carpeta / "inicio_utc.txt").read_text().strip()
    fin = (carpeta / "fin_utc.txt").read_text().strip()
    return {
        "prueba": carpeta.name,
        "total": total,
        "exitosas": ok,
        "fallidas": fallos,
        "tasa_exito": f"{100 * ok / total:.0f}%" if total else "-",
        "t_min_s": round(min(tiempos), 2) if tiempos else None,
        "t_prom_s": round(sum(tiempos) / len(tiempos), 2) if tiempos else None,
        "t_max_s": round(max(tiempos), 2) if tiempos else None,
        "errores": errores,
        "inicio_utc": inicio,
        "fin_utc": fin,
    }


if __name__ == "__main__":
    for c in sys.argv[1:]:
        print(json.dumps(resumir(c), ensure_ascii=False))
