"""
Data migration: seeds Building and CostCenter tables from schemas.py constants.
Run once after 0003_building_costcenter.
"""
from django.db import migrations


# ── Source data (copied from schemas.py so the migration is self-contained) ──

_COST_CENTERS_ORDERED = [
    "JPN 202", "Koramangala", "EEE", "E-City", "Kalyan Nagar", "Mysore",
    "Coles Park", "Mahaveer Celese", "Hebbal", "CMR", "Prestige", "Manyata",
    "Hennur", "Mysore Frenza", "Kora-2", "JPN-Hotel", "Brigade", "Lang Ford",
    "Viman Nagar", "LRP", "General",
]

_BUILDING_GENERAL_CC = {
    "JPN 202":         None,
    "Koramangala":     "Koramangala 1 General",
    "EEE":             "EEE General",
    "E-City":          "E-CITY General",
    "Kalyan Nagar":    "KN General",
    "Mysore":          "Mysore General",
    "Coles Park":      "Cp General",
    "Mahaveer Celese": "MC General",
    "Hebbal":          "HB General",
    "CMR":             "CMR General",
    "Prestige":        None,
    "Manyata":         "MN General",
    "Hennur":          "Hennur General",
    "Mysore Frenza":   "Mf General",
    "Kora-2":          "Kora Building 2 General",
    "JPN-Hotel":       None,
    "Brigade":         None,
    "Lang Ford":       "LF General",
    "Viman Nagar":     "VN General",
    "LRP":             "LRP General",
    "General":         None,
}

_BUILDING_RENT_LEDGER = {
    "JPN 202":         "JPN 202 Rent A/c",
    "Koramangala":     "Kormangala 1 Rent A/c",
    "EEE":             "East End Enclave Rent",
    "E-City":          "ECity Rent",
    "Kalyan Nagar":    "Kalyan Nagar -Rent A/c",
    "Mysore":          "Mysore Rent A/c",
    "Coles Park":      "Coles Park Rent A/c",
    "Mahaveer Celese": "Mahaveer Rent A/c",
    "Hebbal":          "Hebbal Rent A/c",
    "CMR":             "Kasturi Nagar Rent A/c",
    "Prestige":        "Rent Waterford",
    "Manyata":         "Manyata Rent A/c",
    "Hennur":          "Hennur Rent",
    "Mysore Frenza":   "Mysore Firenza Rent A/C",
    "Kora-2":          "Kormangala 2 Rent A/c",
    "JPN-Hotel":       "JPN Hotel Rent A/c",
    "Brigade":         "Brigade Eldorado Rent",
    "Lang Ford":       "Langford Rent A/c",
    "Viman Nagar":     "Viman Nagar Rent",
    "LRP":             None,
    "General":         None,
}

# (display_name, tally_cc, building_group)
_UNIT_COLUMNS = [
    ("JPN 202",              "JPN 202",                  "JPN 202"),
    ("Koramangala-1",        "Kora -1",                  "Koramangala"),
    ("Koramangala-2",        "Kora -2",                  "Koramangala"),
    ("Koramangala-3",        "Kora -3",                  "Koramangala"),
    ("EEE 101",              "EEE 101",                  "EEE"),
    ("EEE 102",              "EEE 102",                  "EEE"),
    ("EEE 202",              "EEE 202",                  "EEE"),
    ("EEE 301",              "EEE 301",                  "EEE"),
    ("EEE 302",              "EEE 302",                  "EEE"),
    ("EEE 401",              "EEE 401",                  "EEE"),
    ("EEE 402",              "EEE 402",                  "EEE"),
    ("EEE 201",              "EEE 201",                  "EEE"),
    ("E-City",               "E-CITY General",           "E-City"),
    ("KN 101",               "KN 101",                   "Kalyan Nagar"),
    ("KN 102",               "KN 102",                   "Kalyan Nagar"),
    ("KN 103",               "KN 103",                   "Kalyan Nagar"),
    ("KN 201",               "KN 201",                   "Kalyan Nagar"),
    ("KN 202",               "KN 202",                   "Kalyan Nagar"),
    ("KN 203",               "KN 203",                   "Kalyan Nagar"),
    ("KN 301",               "KN 301",                   "Kalyan Nagar"),
    ("KN 302",               "KN 302",                   "Kalyan Nagar"),
    ("KN 303",               "KN 303",                   "Kalyan Nagar"),
    ("KN Pent House",        "Kn PentHouse",             "Kalyan Nagar"),
    ("Mysore 101",           "Mysore  101",              "Mysore"),
    ("Mysore 102",           "Mysore  102",              "Mysore"),
    ("Mysore 103",           "Mysore  103",              "Mysore"),
    ("Mysore 201",           "Mysore  201",              "Mysore"),
    ("Mysore 202",           "Mysore  202",              "Mysore"),
    ("Mysore 203",           "Mysore  203",              "Mysore"),
    ("Mysore 301",           "Mysore  301",              "Mysore"),
    ("CP 301",               "CP 301",                   "Coles Park"),
    ("CP 302",               "CP 302",                   "Coles Park"),
    ("CP 303",               "CP 303",                   "Coles Park"),
    ("CP 304",               "CP 304",                   "Coles Park"),
    ("CP 402",               "CP 402",                   "Coles Park"),
    ("MC 1004",              "MC 1004",                  "Mahaveer Celese"),
    ("MC 1104",              "MC 1104",                  "Mahaveer Celese"),
    ("MC 601",               "MC 601",                   "Mahaveer Celese"),
    ("MC 905",               "MC 905",                   "Mahaveer Celese"),
    ("HB 101",               "HB 101",                   "Hebbal"),
    ("HB 102",               "HB 102",                   "Hebbal"),
    ("HB 201",               "HB 201",                   "Hebbal"),
    ("HB 202",               "HB 202",                   "Hebbal"),
    ("HB 301",               "HB 301",                   "Hebbal"),
    ("HB 302",               "HB 302",                   "Hebbal"),
    ("HB 401",               "HB 401",                   "Hebbal"),
    ("HB 402",               "HB 402",                   "Hebbal"),
    ("HB 501",               "HB 501",                   "Hebbal"),
    ("HB 502",               "HB 502",                   "Hebbal"),
    ("CMR 201",              "CMR 201",                  "CMR"),
    ("CMR 202",              "CMR 202",                  "CMR"),
    ("CMR 203",              "CMR 203",                  "CMR"),
    ("CMR 204",              "CMR 204",                  "CMR"),
    ("CMR 205",              "CMR 205",                  "CMR"),
    ("CMR 206",              "CMR 206",                  "CMR"),
    ("CMR 301",              "CMR 301",                  "CMR"),
    ("CMR 302",              "CMR 302",                  "CMR"),
    ("CMR 303",              "CMR 303",                  "CMR"),
    ("CMR 304",              "CMR 304",                  "CMR"),
    ("CMR 305",              "CMR 305",                  "CMR"),
    ("CMR 306",              "CMR 306",                  "CMR"),
    ("CMR 401",              "CMR 401",                  "CMR"),
    ("CMR 402",              "CMR 402",                  "CMR"),
    ("CMR 403",              "CMR 403",                  "CMR"),
    ("CMR 404",              "CMR 404",                  "CMR"),
    ("CMR 405",              "CMR 405",                  "CMR"),
    ("CMR 406",              "CMR 406",                  "CMR"),
    ("Prestige 11013",       "Prestige Waterford 11013", "Prestige"),
    ("Prestige 12194",       "Prestige Waterford 12194", "Prestige"),
    ("MN 101",               "MN 101",                   "Manyata"),
    ("MN 201",               "MN 201",                   "Manyata"),
    ("MN 202",               "MN202",                    "Manyata"),
    ("MN 301",               "MN301",                    "Manyata"),
    ("MN 302",               "MN302",                    "Manyata"),
    ("MN 401",               "MN401",                    "Manyata"),
    ("MN 402",               "MN402",                    "Manyata"),
    ("MN 501",               "MN501",                    "Manyata"),
    ("MN 102",               "MN102",                    "Manyata"),
    ("HN 101",               "HN 101",                   "Hennur"),
    ("HN 201",               "HN 201",                   "Hennur"),
    ("HN 301",               "HN 301",                   "Hennur"),
    ("HN 401",               "HN 401",                   "Hennur"),
    ("HN 501",               "HN 501",                   "Hennur"),
    ("MF 101",               "MF 101",                   "Mysore Frenza"),
    ("MF 102",               "MF 102",                   "Mysore Frenza"),
    ("MF 201",               "MF 201",                   "Mysore Frenza"),
    ("MF 202",               "MF 202",                   "Mysore Frenza"),
    ("MF 301",               "MF 301",                   "Mysore Frenza"),
    ("MF 302",               "MF 302",                   "Mysore Frenza"),
    ("MF 401",               "MF 401",                   "Mysore Frenza"),
    ("Koramangala-New 001",  "Kora-001",                 "Kora-2"),
    ("Koramangala-New 101",  "Kora-101",                 "Kora-2"),
    ("Koramangala-New 102",  "Kora-102",                 "Kora-2"),
    ("Koramangala-New 103",  "Kora-103",                 "Kora-2"),
    ("Koramangala-New 104",  "Kora-104",                 "Kora-2"),
    ("Koramangala-New 201",  "Kora-201",                 "Kora-2"),
    ("Koramangala-New 202",  "Kora-202",                 "Kora-2"),
    ("Koramangala-New 203",  "Kora-203",                 "Kora-2"),
    ("Koramangala-New 204",  "Kora-204",                 "Kora-2"),
    ("Koramangala-New 301",  "Kora-301",                 "Kora-2"),
    ("Koramangala-New 302",  "Kora-302",                 "Kora-2"),
    ("Koramangala-New 303",  "Kora-303",                 "Kora-2"),
    ("Koramangala-New 402",  "Kora 402",                 "Kora-2"),
    ("Koramangala-New 404",  "Kora 404",                 "Kora-2"),
    ("Koramangala-New 503",  "Kora 503",                 "Kora-2"),
    ("Koramangala-New 504",  "Kora 504",                 "Kora-2"),
    ("JPN-Hotel",            "JPN Hotel",                "JPN-Hotel"),
    ("ED 701",               "ED 701",                   "Brigade"),
    ("LF 1",                 "LF 1 F",                   "Lang Ford"),
    ("LF 2",                 "LF 2 F",                   "Lang Ford"),
    ("LF 3",                 "LF 3 F",                   "Lang Ford"),
    ("VN 301",               "VN 301",                   "Viman Nagar"),
    ("VN 302",               "VN 302",                   "Viman Nagar"),
    ("VN 303",               "VN 303",                   "Viman Nagar"),
    ("VN 304",               "VN 304",                   "Viman Nagar"),
    ("VN 305",               "VN 305",                   "Viman Nagar"),
    ("VN 401",               "VN 401",                   "Viman Nagar"),
    ("VN 402",               "VN 402",                   "Viman Nagar"),
    ("VN 403",               "VN 403",                   "Viman Nagar"),
    ("VN 404",               "VN 404",                   "Viman Nagar"),
    ("VN 501",               "VN 501",                   "Viman Nagar"),
    ("VN 502",               "VN 502",                   "Viman Nagar"),
    ("LRP",                  "LRP General",              "LRP"),
    ("General Office",       None,                       "General"),
]


def seed_forward(apps, schema_editor):
    Building   = apps.get_model('mis_engine', 'Building')
    CostCenter = apps.get_model('mis_engine', 'CostCenter')

    # Create all buildings in column_order
    bldg_objs = {}
    for order, name in enumerate(_COST_CENTERS_ORDERED):
        b = Building.objects.create(
            display_name=name,
            general_cc=_BUILDING_GENERAL_CC.get(name),
            rent_ledger=_BUILDING_RENT_LEDGER.get(name),
            column_order=order,
            is_active=True,
        )
        bldg_objs[name] = b

    # Track column_order within each building
    cc_order_counter: dict[str, int] = {}

    for disp, tally_cc, bldg_name in _UNIT_COLUMNS:
        bldg_obj = bldg_objs.get(bldg_name)
        order = cc_order_counter.get(bldg_name, 0)
        cc_order_counter[bldg_name] = order + 1

        is_excluded = (
            tally_cc is None
            or (tally_cc is not None and "penthouse" in tally_cc.lower())
        )

        CostCenter.objects.create(
            building=bldg_obj,
            display_name=disp,
            tally_cc=tally_cc,
            column_order=order,
            is_excluded_from_split=is_excluded,
            is_active=True,
        )


def seed_reverse(apps, schema_editor):
    Building   = apps.get_model('mis_engine', 'Building')
    CostCenter = apps.get_model('mis_engine', 'CostCenter')
    CostCenter.objects.all().delete()
    Building.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mis_engine', '0003_building_costcenter'),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
