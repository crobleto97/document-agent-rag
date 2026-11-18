"""The regulations the agent answers questions about.

EUR-Lex HTML for EU law (consolidated text where one exists) and the BOE open-data
API for Spanish law. To update a regulation to a newer consolidated version, change
its URL here and re-run the pipeline.
"""

EURLEX = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}"
BOE = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{id}/texto"

SOURCES = [
    {
        "id": "eu_561_2006",
        "name": "Regulation (EC) No 561/2006 (driving times, breaks and rest periods)",
        "short": "Reg. 561/2006",
        "format": "eurlex",
        "versions": {
            "en": EURLEX.format(lang="EN", celex="02006R0561-20241231"),
            "es": EURLEX.format(lang="ES", celex="02006R0561-20241231"),
        },
    },
    {
        "id": "eu_dir_2002_15",
        "name": "Directive 2002/15/EC (working time of mobile road transport workers)",
        "short": "Dir. 2002/15",
        "format": "eurlex",
        "versions": {
            "en": EURLEX.format(lang="EN", celex="32002L0015"),
            "es": EURLEX.format(lang="ES", celex="32002L0015"),
        },
    },
    {
        "id": "es_ley_15_2009",
        "name": "Ley 15/2009 del contrato de transporte terrestre de mercancías",
        "short": "Ley 15/2009",
        "format": "boe",
        "versions": {"es": BOE.format(id="BOE-A-2009-18004")},
    },
]
