"""
bks.py -- Best Known Solutions para instancias classicas de CVRP.
Fontes: CVRPLIB (http://vrp.atd-lab.inf.puc-rio.br/), Augerat (1995),
        Christofides et al. (1979), Golden et al. (1998).

IMPORTANTE: Valores verificados contra CVRPLIB em marco 2026.
"""

BKS = {
    # Augerat Set A
    "A-n32-k5": 784,
    "A-n33-k5": 661,
    "A-n33-k6": 742,
    "A-n34-k5": 778,
    "A-n36-k5": 799,
    "A-n37-k5": 669,
    "A-n37-k6": 949,
    "A-n38-k5": 730,
    "A-n39-k5": 822,
    "A-n39-k6": 831,
    "A-n44-k6": 937,
    "A-n45-k6": 944,
    "A-n45-k7": 1146,
    "A-n46-k7": 914,
    "A-n48-k7": 1073,
    "A-n53-k7": 1010,
    "A-n54-k7": 1167,
    "A-n55-k9": 1073,
    "A-n60-k9": 1354,
    "A-n61-k9": 1034,
    "A-n62-k8": 1288,
    "A-n63-k9": 1616,
    "A-n63-k10": 1314,
    "A-n64-k9": 1401,
    "A-n65-k9": 1174,
    "A-n69-k9": 1159,
    "A-n80-k10": 1763,

    # Augerat Set B
    "B-n31-k5": 672,
    "B-n34-k5": 788,
    "B-n35-k5": 955,
    "B-n38-k6": 805,
    "B-n39-k5": 549,
    "B-n41-k6": 829,
    "B-n43-k6": 742,
    "B-n44-k7": 909,
    "B-n45-k5": 751,
    "B-n45-k6": 678,
    "B-n50-k7": 741,
    "B-n50-k8": 1312,
    "B-n51-k7": 1032,
    "B-n52-k7": 747,
    "B-n56-k7": 707,
    "B-n57-k9": 1598,
    "B-n63-k10": 1496,
    "B-n64-k9": 861,
    "B-n66-k9": 1316,
    "B-n67-k10": 1032,
    "B-n68-k9": 1272,
    "B-n78-k10": 1221,

    # Christofides et al. (CMT)
    "CMT1": 524.61,
    "CMT2": 835.26,
    "CMT3": 826.14,
    "CMT4": 1028.42,
    "CMT5": 1291.29,
    "CMT6": 555.43,
    "CMT7": 909.68,
    "CMT8": 865.94,
    "CMT9": 1162.55,
    "CMT10": 1395.85,
    "CMT11": 1042.11,
    "CMT12": 819.56,
    "CMT13": 1541.14,
    "CMT14": 866.37,

    # Golden et al.
    "Golden_1": 5623.47,
    "Golden_2": 8404.61,
    "Golden_3": 11036.22,
    "Golden_4": 13592.88,
    "Golden_5": 6460.98,
    "Golden_6": 8404.26,
    "Golden_7": 10102.68,
    "Golden_8": 11635.34,
    "Golden_9": 579.71,
    "Golden_10": 736.26,
    "Golden_11": 912.84,
    "Golden_12": 1102.69,
    "Golden_13": 857.19,
    "Golden_14": 1080.55,
    "Golden_15": 1337.92,
    "Golden_16": 1612.50,
    "Golden_17": 707.76,
    "Golden_18": 995.13,
    "Golden_19": 1365.60,
    "Golden_20": 1818.32,
}


def get_bks(instance_name: str) -> float | None:
    """Retorna BKS para a instancia, ou None se nao conhecida."""
    name = instance_name.replace(".vrp", "").replace(".sol", "").strip()
    return BKS.get(name, None)
