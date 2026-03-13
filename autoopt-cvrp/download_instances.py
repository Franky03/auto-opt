"""
download_instances.py -- Baixa instâncias CVRP clássicas no formato .vrp padrão.

Conjuntos e papéis:
  augerat_a (27) -- benchmark principal do paper
  augerat_b (22) -- held-out / generalização
  augerat_p (23) -- benchmark secundário
  eilon_e   (12) -- benchmark clássico histórico (Christofides & Eilon 1969)

Todas as instâncias estão no formato TSPLIB95 (.vrp) com BKS conhecidos.
Fontes: GitHub raw (giulianoxt, RomuloOliveira, VRP-REP/translator).

Uso: pip install requests
     python download_instances.py
"""

import os, time
import requests

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.path.join(SCRIPT_DIR, "instances")

# ---------------------------------------------------------------------------
# Listas de instâncias
# ---------------------------------------------------------------------------

AUGERAT_A = [
    "A-n32-k5","A-n33-k5","A-n33-k6","A-n34-k5","A-n36-k5",
    "A-n37-k5","A-n37-k6","A-n38-k5","A-n39-k5","A-n39-k6",
    "A-n44-k6","A-n45-k6","A-n45-k7","A-n46-k7","A-n48-k7",
    "A-n53-k7","A-n54-k7","A-n55-k9","A-n60-k9","A-n61-k9",
    "A-n62-k8","A-n63-k9","A-n63-k10","A-n64-k9","A-n65-k9",
    "A-n69-k9","A-n80-k10",
]

AUGERAT_B = [
    "B-n31-k5","B-n34-k5","B-n35-k5","B-n38-k6","B-n39-k5",
    "B-n41-k6","B-n43-k6","B-n44-k7","B-n45-k5","B-n45-k6",
    "B-n50-k7","B-n50-k8","B-n51-k7","B-n52-k7","B-n56-k7",
    "B-n57-k9","B-n63-k10","B-n64-k9","B-n66-k9","B-n67-k10",
    "B-n68-k9","B-n78-k10",
]

AUGERAT_P = [
    "P-n16-k8","P-n19-k2","P-n20-k2","P-n21-k2","P-n22-k2",
    "P-n22-k8","P-n23-k8","P-n40-k5","P-n45-k5","P-n50-k7",
    "P-n50-k8","P-n50-k10","P-n51-k10","P-n55-k7","P-n55-k10",
    "P-n55-k15","P-n60-k10","P-n60-k15","P-n65-k10","P-n70-k10",
    "P-n76-k4","P-n76-k5","P-n101-k4",
]

# Eilon E — conjunto clássico com BKS bem estabelecidos
EILON_E = [
    "E-n13-k4","E-n22-k4","E-n23-k3","E-n30-k3","E-n33-k4",
    "E-n51-k5","E-n76-k7","E-n76-k8","E-n76-k10","E-n76-k14",
    "E-n101-k8","E-n101-k14",
]

# ---------------------------------------------------------------------------
# URLs por conjunto — múltiplos mirrors em ordem de prioridade
# ---------------------------------------------------------------------------

VRP_REP_BASE = "https://raw.githubusercontent.com/VRP-REP/translator/master/data/original_instance"

URLS = {
    "augerat_a": [
        "https://raw.githubusercontent.com/giulianoxt/vehicle-routing-aco/master/augerat-a/{name}.vrp",
        "https://raw.githubusercontent.com/RomuloOliveira/monte-carlo-cvrp/master/input/Augerat/{name}.vrp",
        "https://raw.githubusercontent.com/mkalinowski/CVRP/master/dane/{name}.vrp",
        VRP_REP_BASE + "/VRPWEB/CVRP/Augerat%201995%20%E2%80%94%20Set%20A/{name}.vrp",
        VRP_REP_BASE + "/ATD-LAB/CVRP/Augerat%201995%20%E2%80%94%20Set%20A/{name}.vrp",
    ],
    "augerat_b": [
        "https://raw.githubusercontent.com/RomuloOliveira/monte-carlo-cvrp/master/input/Augerat/{name}.vrp",
        "https://raw.githubusercontent.com/giulianoxt/vehicle-routing-aco/master/augerat-b/{name}.vrp",
        VRP_REP_BASE + "/VRPWEB/CVRP/Augerat%201995%20%E2%80%94%20Set%20B/{name}.vrp",
        VRP_REP_BASE + "/ATD-LAB/CVRP/Augerat%201995%20%E2%80%94%20Set%20B/{name}.vrp",
    ],
    "augerat_p": [
        VRP_REP_BASE + "/VRPWEB/CVRP/Augerat%201995%20%E2%80%94%20Set%20P/{name}.vrp",
        VRP_REP_BASE + "/ATD-LAB/CVRP/Augerat%201995%20%E2%80%94%20Set%20P/{name}.vrp",
    ],
    "eilon_e": [
        VRP_REP_BASE + "/VRPWEB/CVRP/Christofides%20and%20Eilon%201969%20%E2%80%94%20Set%20E/{name}.vrp",
        VRP_REP_BASE + "/ATD-LAB/CVRP/Christofides%20and%20Eilon%201969%20%E2%80%94%20Set%20E/{name}.vrp",
    ],
}

# ---------------------------------------------------------------------------

def fetch(url: str, timeout: int = 20) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200 and len(r.content) > 50:
            sample = r.content[:500].decode("utf-8", errors="ignore")
            if any(k in sample for k in ("CVRP","DIMENSION","NODE_COORD","CAPACITY")):
                return r.content
    except requests.RequestException:
        pass
    return None


def download_set(set_name: str, names: list, url_templates: list) -> tuple:
    dest_dir = os.path.join(INSTANCES_DIR, set_name)
    os.makedirs(dest_dir, exist_ok=True)
    ok, falhas = 0, []

    for name in names:
        dest = os.path.join(dest_dir, f"{name}.vrp")
        if os.path.exists(dest) and os.path.getsize(dest) > 50:
            ok += 1
            continue
        success = False
        for tmpl in url_templates:
            data = fetch(tmpl.format(name=name))
            if data:
                with open(dest, "wb") as f:
                    f.write(data)
                print(f"  OK  {name}.vrp")
                ok += 1
                success = True
                break
            time.sleep(0.15)
        if not success:
            print(f"  FALHA  {name}.vrp")
            falhas.append(name)

    return ok, len(names), falhas


# ---------------------------------------------------------------------------

def download_all():
    os.makedirs(INSTANCES_DIR, exist_ok=True)
    report = []

    sets = [
        ("augerat_a", AUGERAT_A, "benchmark principal"),
        ("augerat_b", AUGERAT_B, "held-out / generalizacao"),
        ("augerat_p", AUGERAT_P, "benchmark secundario"),
        ("eilon_e",   EILON_E,   "benchmark classico historico"),
    ]

    print("Baixando instancias CVRP classicas...\n")
    for set_name, names, role in sets:
        print(f"[{set_name}]  ({len(names)} instancias -- {role})")
        ok, total, falhas = download_set(set_name, names, URLS[set_name])
        report.append((set_name, ok, total, falhas))
        print()

    print("=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    all_ok = True
    for set_name, ok, total, falhas in report:
        status = "completo" if ok == total else f"{ok}/{total}"
        print(f"  {set_name:12s}: {status}")
        if falhas:
            all_ok = False
            print(f"    faltando: {', '.join(falhas[:5])}" +
                  (f" ... +{len(falhas)-5}" if len(falhas) > 5 else ""))

    total_instances = sum(t for _, _, t, _ in report)
    total_ok        = sum(o for _, o, _, _ in report)
    print(f"\n  TOTAL: {total_ok}/{total_instances} instancias baixadas")

    if not all_ok:
        print(f"\nInstancias faltando -- baixe manualmente de:")
        print(f"  https://github.com/VRP-REP/translator/tree/master/data/original_instance/VRPWEB/CVRP/")
        print(f"  Coloque os .vrp nas pastas em: {INSTANCES_DIR}/")
    else:
        print(f"\nTudo baixado em: {INSTANCES_DIR}/")


if __name__ == "__main__":
    download_all()
