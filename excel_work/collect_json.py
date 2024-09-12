import json
from openpyxl import Workbook

files = [
    "elementary_schools.json",
    "etc_schools.json",
    "high_schools.json",
    "middle_schools.json",
    "special_schools.json",
]


with open("./elementary_schools.json", encoding="utf-8") as file:
    data = json.load(file)
    wb = Workbook()
    ws = wb.active

    ws.append(
        [
            "school",
            "province",
            "address1",
            "address2",
            "longitude",
            "latitude",
            "tel",
            "fax",
        ]
    )
    for data in data["list"]:
        try:
            ws.append(
                [
                    data["SCHUL_NM"],
                    data["ADRCD_NM"],
                    data["ADRES_BRKDN"],
                    data["DTLAD_BRKDN"],
                    data["LGTUD"],
                    data["LTTUD"],
                    data["USER_TELNO"],
                    data["PERC_FAXNO"],
                ]
            )
        except:
            print(data["SCHUL_NM"])

    wb.save("./test.xlsx")
