"""Draft quote requests (Romanian) for every BOM line still marked QUOTE, grouped by supplier type.
Quantities come from the generated BOM, so this stays in sync with the CAD model.

Run: uv run python -m bom.quote_requests   -> bom/quote_requests_ro.md
"""

from __future__ import annotations

from pathlib import Path

from bom.build_bom import build
from geometry.oven_b import Params

OUT = Path(__file__).with_name("quote_requests_ro.md")

# item prefix in the BOM -> (supplier group, Romanian description)
MAP = {
    "ROCKWOOL ProRox": ("izolatii", "Saltea vată bazaltică cu plasă ROCKWOOL ProRox WM 960ES (sau WM 960), grosime 100 mm (sau 2 × 50 mm); "
                        "variantă cu plasă din inox, dacă este disponibilă"),
    "Superwool 6 mm": ("izolatii", "Superwool Plus (fibră bio-solubilă, AES) 6 mm, saltea sau hârtie, pentru garnituri de dilatație"),
    "Angle L50x50x5": ("metal", "Cornier oțel S235 L50×50×5 mm, debitat conform listei de mai jos"),
    "Threaded rod M12": ("feronerie", "Tijă filetată M12 zincată"),
    "Disc springs": ("feronerie", "Arcuri disc (șaibe Belleville) DIN 2093 pentru M12, diametru interior 12,2 mm"),
    "M12 nuts": ("feronerie", "Set piulițe M12 + șaibe mari; 8 șuruburi M10 × 30 cu piuliță și șaibă"),
    "M12 anchors": ("feronerie", "Ancore M12 pentru beton (chimice sau mecanice)"),
    "Pre-painted flat steel roofing sheet": ("metal", "Tablă plană vopsită (pentru acoperiș) 0,5 mm, culoare închisă, NU culoare aluminiu"),
    "Steel sheet 1 mm": ("metal", "Tablă neagră DC01 1 mm, debitată după DXF (2 panouri frontale/spate), opțional debitare laser"),
    "Self-drilling screws": ("feronerie", "Șuruburi autoforante pentru tablă, cu garnitură EPDM"),
    "Steel sheet 1 mm for door": ("metal", "Tablă neagră 1 mm pentru ușă (cutie 50 mm adâncime, după DXF) + 2 mânere din lemn"),
    "Black steel sheet 2 mm": ("metal", "Tablă neagră 2 mm pentru hotă (după DXF hood_parts), NU zincată, opțional îndoire"),
    "Stove pipe": ("cosuri", "Burlan/țeavă de fum din oțel negru Ø150 mm, 1 m, + căciulă de ploaie (NU zincat)"),
    "Heat-resistant paint": ("feronerie", "Vopsea rezistentă la temperatură (min. 600 °C) pentru cadru, hotă și burlan"),
    "Arch former": ("feronerie", "Placaj 18 mm (aprox. 1200 × 600 mm) + șipci 20 × 40 mm (6 × 1 m) + pene de lemn"),
}

GROUPS = {
    "izolatii": "Distribuitor de izolații tehnice (ROCKWOOL Technical Insulation / refractare)",
    "metal": "Depozit de metale / atelier de debitare (local)",
    "feronerie": "Magazin de bricolaj sau feronerie (Dedeman, Hornbach, Leroy Merlin, magazine locale)",
    "cosuri": "Magazin de șeminee și coșuri de fum",
}


def main():
    p = Params()
    _, ov, rows, priced = build()
    by_group: dict[str, list[str]] = {g: [] for g in GROUPS}
    for g, item, q, u, c, src, note in rows:
        if c != "QUOTE":
            continue
        key = next((k for k in sorted(MAP, key=len, reverse=True) if item.startswith(k)), None)
        if key is None:
            continue
        grp, desc = MAP[key]
        unit_ro = {"m2": "m²", "m": "m", "pcs": "buc", "set": "set", "rolls": "role"}.get(u, u)
        by_group[grp].append(f"- {desc}: **{f'{q:g}'.replace('.', ',')} {unit_ro}**")
    cut = []
    for pid in ("K-L", "K-R", "B-LF", "B-LB", "B-RF", "B-RB"):
        pt = next(x for x in ov.parts if x.pid == pid)
        bb = pt.solid.val().BoundingBox()
        cut.append(round(bb.ylen if pid.startswith("K-") else bb.zlen))
    lines = [
        "# Cereri de ofertă - cuptor pe lemne (generat de `bom/quote_requests.py`)", "",
        "Cuptor de pizza pe lemne, construit de o persoană fizică. Mai jos este câte un text de copiat "
        "în e-mail sau mesaj pentru fiecare tip de furnizor. Cantitățile provin din modelul CAD.", "",
        f"Total deja estimat din prețuri publice: {priced:.0f} USD. Bugetul total este de aproximativ 1000 USD.", "",
    ]
    for g, title in GROUPS.items():
        if not by_group[g]:
            continue
        lines += [f"## {title}", "", "> Bună ziua,", ">",
                  "> Vă rog să-mi trimiteți o ofertă de preț (cu TVA) și termenul de livrare/ridicare în [oraș] pentru:", ">"]
        lines += [f"> {x}" for x in by_group[g]]
        if g == "metal":
            lines += [">", f"> Debitare cornier: 2 × {cut[0]} mm, 4 × {cut[2]} mm, 4 × 100 mm (sau bare întregi, debitez eu).",
                      "> Fișierele DXF pentru tablă le pot trimite la cerere."]
        lines += [">", "> Mulțumesc,", "> [nume, telefon]", ""]
    lines += ["## Note", "",
              "- Nu folosiți tablă sau burlan **zincat** pentru hotă și coș (vapori de zinc la temperatură).",
              "- Tabla exterioară (carcasa) rămâne rece (sub 60 °C), deci acolo tabla vopsită sau zincată este acceptabilă.",
              "- Rezultatele (preț, magazin, dată) se trec în `materials/materials.yaml`, la `suppliers`, apoi se regenerează BOM-ul."]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
