"""
download_instances.py -- Baixa e organiza todas as instancias CVRP classicas.
Uso: python download_instances.py
"""

import os
import time

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR = os.path.join(SCRIPT_DIR, "instances")

# ---------------------------------------------------------------------------
# Definicao dos conjuntos de instancias
# ---------------------------------------------------------------------------

AUGERAT_A = [
    "A-n32-k5", "A-n33-k5", "A-n33-k6", "A-n34-k5", "A-n36-k5",
    "A-n37-k5", "A-n37-k6", "A-n38-k5", "A-n39-k5", "A-n39-k6",
    "A-n44-k6", "A-n45-k6", "A-n45-k7", "A-n46-k7", "A-n48-k7",
    "A-n53-k7", "A-n54-k7", "A-n55-k9", "A-n60-k9", "A-n61-k9",
    "A-n62-k8", "A-n63-k9", "A-n63-k10", "A-n64-k9", "A-n65-k9",
    "A-n69-k9", "A-n80-k10",
]

AUGERAT_B = [
    "B-n31-k5", "B-n34-k5", "B-n35-k5", "B-n38-k6", "B-n39-k5",
    "B-n41-k6", "B-n43-k6", "B-n44-k7", "B-n45-k5", "B-n45-k6",
    "B-n50-k7", "B-n50-k8", "B-n51-k7", "B-n52-k7", "B-n56-k7",
    "B-n57-k9", "B-n63-k10", "B-n64-k9", "B-n66-k9", "B-n67-k10",
    "B-n68-k9", "B-n78-k10",
]

CMT = [f"CMT{i}" for i in range(1, 15)]

GOLDEN = [f"Golden_{i}" for i in range(1, 21)]

# URLs candidatas para download
CVRPLIB_BASE = "http://vrp.atd-lab.inf.puc-rio.br/media/com_vrp/instances"

URLS = {
    "augerat_a": [
        f"{CVRPLIB_BASE}/A/{{name}}.vrp",
        "https://raw.githubusercontent.com/mastqe/cvrplib/master/instances/A/{name}.vrp",
    ],
    "augerat_b": [
        f"{CVRPLIB_BASE}/B/{{name}}.vrp",
        "https://raw.githubusercontent.com/mastqe/cvrplib/master/instances/B/{name}.vrp",
    ],
    "christofides": [
        f"{CVRPLIB_BASE}/CMT/{{name}}.vrp",
        "https://raw.githubusercontent.com/mastqe/cvrplib/master/instances/CMT/{name}.vrp",
    ],
    "golden": [
        f"{CVRPLIB_BASE}/Golden/{{name}}.vrp",
        "https://raw.githubusercontent.com/mastqe/cvrplib/master/instances/Golden/{name}.vrp",
    ],
}


def download_with_fallback(urls: list, dest_path: str) -> bool:
    """
    Tenta baixar de cada URL em ordem.
    Retorna True se conseguiu, False se todas falharam.
    """
    for url in urls:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 50:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
        except (requests.RequestException, IOError):
            continue
        time.sleep(0.5)
    return False


def download_set(set_name: str, instance_names: list, url_templates: list) -> tuple[int, int]:
    """Baixa um conjunto de instancias. Retorna (baixadas, total)."""
    dest_dir = os.path.join(INSTANCES_DIR, set_name)
    os.makedirs(dest_dir, exist_ok=True)

    downloaded = 0
    skipped = 0

    for name in instance_names:
        dest = os.path.join(dest_dir, f"{name}.vrp")
        if os.path.exists(dest):
            skipped += 1
            downloaded += 1
            continue

        urls = [t.format(name=name) for t in url_templates]
        if download_with_fallback(urls, dest):
            downloaded += 1
            print(f"  OK: {name}.vrp")
        else:
            print(f"  FALHA: {name}.vrp")

    return downloaded, len(instance_names)


def download_all():
    """Baixa todos os conjuntos de instancias."""
    os.makedirs(INSTANCES_DIR, exist_ok=True)

    sets = [
        ("augerat_a", AUGERAT_A, URLS["augerat_a"]),
        ("augerat_b", AUGERAT_B, URLS["augerat_b"]),
        ("christofides", CMT, URLS["christofides"]),
        ("golden", GOLDEN, URLS["golden"]),
    ]

    print("Baixando instancias CVRP classicas...\n")
    report = []

    for set_name, names, urls in sets:
        print(f"[{set_name}] ({len(names)} instancias)")
        ok, total = download_set(set_name, names, urls)
        report.append((set_name, ok, total))
        print()

    print("=" * 50)
    print("RELATORIO DE DOWNLOAD")
    print("=" * 50)
    all_ok = True
    for set_name, ok, total in report:
        status = "OK" if ok == total else "INCOMPLETO"
        print(f"  {set_name:15s}: {ok}/{total} instancias  [{status}]")
        if ok < total:
            all_ok = False

    if not all_ok:
        print("\nAlguns downloads falharam. Para baixar manualmente:")
        print(f"  1. Acesse http://vrp.atd-lab.inf.puc-rio.br/")
        print(f"  2. Baixe os arquivos .vrp faltantes")
        print(f"  3. Coloque-os na pasta correspondente em {INSTANCES_DIR}/")
    else:
        print(f"\nTodas as instancias baixadas em {INSTANCES_DIR}/")


if __name__ == "__main__":
    download_all()
