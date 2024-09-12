import re

import psycopg2
import xlwings as xw

from settlemant_class import SalaryData, AttData, MemberSalary
from utils import (
    dictfetchall,
    get_salary_data_sql,
    get_unsettled_salary_sql,
    get_bonus_sql,
    get_attandance_sql,
    get_workday_sql,
    get_training_fee_sql,
    get_member_info_sql,
    get_override_members,
    get_override_dict,
)
from db_cred import (
    HOST,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DJANGO_DB_NAME,
    DJANGO_DB_USER,
    DJANGO_DB_PASSWORD,
)

XLSM_TEMPLATE = "salary_settlement_template.xlsm"

# user input - settlement yearmonth, settlement date
settlement_yearmonth = ""
settlement_date = ""
while not re.search(r"\d{4}-[01]\d", settlement_yearmonth):
    settlement_yearmonth = input("settlement yearmonth?(yyyy-mm): ")

while not re.search(r"\d{4}-[01]\d", settlement_date):
    settlement_date = input("settlement date?(yyyy-mm-dd): ")

# get infos from db
with psycopg2.connect(
    host=HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
) as conn:
    cursor = conn.cursor()

    cursor.execute(get_attandance_sql(settlement_yearmonth + "-01"))
    firstday_att_data = dictfetchall(cursor)

    cursor.execute(get_attandance_sql(settlement_date))
    settlement_att_data = dictfetchall(cursor)

    cursor.execute(get_workday_sql(settlement_yearmonth))
    workday_data = dictfetchall(cursor)

    cursor.execute(get_salary_data_sql(settlement_yearmonth))
    salary_data_list = dictfetchall(cursor)

    cursor.execute(get_training_fee_sql(settlement_yearmonth))
    training_fee_list = dictfetchall(cursor)

    cursor.execute(get_unsettled_salary_sql(settlement_yearmonth))
    unsettled_salary_list = dictfetchall(cursor)

    cursor.execute(get_bonus_sql(settlement_yearmonth))
    bonus_list = dictfetchall(cursor)

with psycopg2.connect(
    host=HOST, dbname=DJANGO_DB_NAME, user=DJANGO_DB_USER, password=DJANGO_DB_PASSWORD
) as conn2:
    cursor2 = conn2.cursor()

    cursor2.execute(get_member_info_sql())
    member_info_list = dictfetchall(cursor2)

settlement_att = [AttData(**item) for item in settlement_att_data]
firstday_att = [AttData(**item) for item in firstday_att_data]
salary_data = [SalaryData(**item) for item in salary_data_list]


override_members = get_override_members(settlement_att, firstday_att)
override_dict = get_override_dict(override_members, salary_data, settlement_yearmonth)

# set class variable - override dict
MemberSalary.override_members = override_dict

# set report members
training_fee_members = set([data["frid"] for data in training_fee_list])
salary_members = set([data.frid for data in salary_data])
firstday_members = set([data.frid for data in firstday_att])

report_members = list(training_fee_members.union(salary_members, firstday_members))
report_members.sort()

# make MemberSalary list
member_name_dict = {d["member_id"]: d["name"] for d in member_info_list}
att_1st_dict = {a.frid: a.m_position for a in firstday_att}
att_settlement_dict = {a.frid: a.m_position for a in settlement_att}
training_fee_dict = {t["frid"]: t["fee"] for t in training_fee_list}
unsettled_dict = {u["frid"]: u["salary"] for u in unsettled_salary_list}
bonus_dict = {b["frid"]: b["bonus"] for b in bonus_list}
workday_dict = {w["frid"]: w["workday"] for w in workday_data}
salary_list = []

for frid in report_members:
    member_salary_data = MemberSalary(
        frid=frid,
        frname=member_name_dict[frid],
        m_position_1st=att_1st_dict[frid]
        if frid in att_1st_dict.keys()
        else "Termination",
        m_position_settlement=att_settlement_dict[frid]
        if frid in att_settlement_dict.keys()
        else "Termination",
        override_rate=override_dict[frid] if frid in override_dict.keys() else 0,
        signup_list=[data for data in salary_data if data.frid == frid],
        team_signup_list=[data for data in salary_data if frid in data.treecode],
        training_fee=training_fee_dict[frid] if frid in training_fee_dict.keys() else 0,
        unsettled_salary=unsettled_dict[frid] if frid in unsettled_dict.keys() else 0,
        bonus_salary=bonus_dict[frid] if frid in bonus_dict.keys() else 0,
        workday=workday_dict[frid] if frid in workday_dict.keys() else 0,
    )
    salary_list.append(member_salary_data)


# fill data to xlsm template
wb = xw.Book(XLSM_TEMPLATE)
setting_sheet = wb.sheets["setting"]
member_info_sheet = wb.sheets["members"]
unsettled_salary_sheet = wb.sheets["unsettled"]
bonus_sheet = wb.sheets["bonus"]
training_fee_sheet = wb.sheets["training_fee"]
main_data_sheet = wb.sheets["data"]
override_sheet = wb.sheets["override"]
total_sheet = wb.sheets["종합"]

# fill setting_sheet
[year, month] = [int(item) for item in settlement_yearmonth.split("-")]
setting_sheet.range("B1").value = year
setting_sheet.range("D1").value = month
setting_sheet.range("A3").value = f"정산시점: {settlement_date}"
setting_sheet.range("H3").value = f'1일 시점: {settlement_yearmonth+"-01"}'

settlement_att_sheet_data = []
firstday_att_sheet_data = []
for att_data in settlement_att:
    settlement_att_sheet_data.append(att_data.info_tuple())
for att_data in firstday_att:
    firstday_att_sheet_data.append(att_data.info_tuple())

setting_sheet.range("A5").value = settlement_att_sheet_data
setting_sheet.range("H5").value = firstday_att_sheet_data

# fill member_info_sheet
member_info_sheet_data = []
for member_info in member_info_list:
    info = (
        member_info["member_id"],
        member_info["id_num"],
        member_info["name"],
        member_info["bank_id"],
        member_info["bank_name"],
        member_info["account_number"],
        member_info["account_name"],
        member_info["email"],
    )
    member_info_sheet_data.append(info)
member_info_sheet.range("A2").value = member_info_sheet_data

# fill unsettled_salary_sheet
unsettled_salary_sheet_data = []
for unsettled_salary in unsettled_salary_list:
    unsettled_info = (
        unsettled_salary["frid"],
        "",
        unsettled_salary["salary"],
        unsettled_salary["memo"],
    )
    unsettled_salary_sheet_data.append(unsettled_info)
unsettled_salary_sheet.range("A2").value = unsettled_salary_sheet_data

# fill bonus_sheet
bonus_sheet_data = []
for bonus in bonus_list:
    bonus_info = (
        bonus["frid"],
        "",
        bonus["bonus"],
        bonus["memo"],
    )
    bonus_sheet_data.append(bonus_info)
bonus_sheet.range("A2").value = bonus_sheet_data


# fill training_fee_sheet
training_fee_sheet_data = []
for training_fee in training_fee_list:
    fee_info = (
        training_fee["frid"],
        training_fee["frname"],
        training_fee["days"],
        training_fee["fee"],
    )
    training_fee_sheet_data.append(fee_info)
training_fee_sheet.range("A2").value = training_fee_sheet_data


main_data_list = []
for data in salary_data:
    main_data_list.append(data.info_tuple())

main_data_sheet.range("A2").value = main_data_list

# fill override sheet
override_membersalary_list = filter(
    lambda x: x.frid in override_dict.keys(), salary_list
)
override_sheet_data = []
override_sheet_down_data = []
for override_membersalary in override_membersalary_list:
    override_sheet_data.append(
        (
            override_membersalary.frid,
            override_membersalary.frname,
            override_membersalary.m_position_settlement,
            override_membersalary.get_team_salary(),
            override_membersalary.get_team_submit_amount(settlement_yearmonth),
            override_membersalary.override_rate,
            override_membersalary.get_full_override(),
            override_membersalary.get_distributed_override(),
            override_membersalary.get_attendance_rate(),
            override_membersalary.get_final_override(),
        )
    )
    if override_membersalary.get_down_override():
        for k, v in override_membersalary.get_down_override().items():
            override_sheet_down_data.append((override_membersalary.frid, k, v))


override_sheet.range("A2").value = override_sheet_data
override_sheet.range("L2").value = override_sheet_down_data


# fill 종합 sheet
data_list = []
for data in salary_list:
    data_list.append(data.info_tuple())

total_sheet.range("A5").value = data_list


wb.save(f"급여정산({settlement_yearmonth})-{settlement_date}.xlsm")
