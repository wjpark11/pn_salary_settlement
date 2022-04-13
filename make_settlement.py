import re
import psycopg2

from settlemant_class import SalaryData, AttData, MemberSalary
from utils import (
    dictfetchall,
    get_salary_data_sql,
    get_unsettled_salary_sql,
    get_attandance_sql,
    get_training_fee_sql,
    get_member_info_sql,
    get_override_members,    
    get_override_dict,
    get_additional_override
)
from db_cred import (
    HOST,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DJANGO_DB_NAME,
    DJANGO_DB_USER,
    DJANGO_DB_PASSWORD
)

XLSM_TEMPLATE = 'salary_settlement_template.xlsm'

# user input - settlement yearmonth, settlement date
settlement_yearmonth = ''
settlement_date = ''
while not re.search(r'\d{4}-[01]\d', settlement_yearmonth):
    settlement_yearmonth = input('settlement yearmonth?(yyyy-mm): ')

while not re.search(r'\d{4}-[01]\d', settlement_date):
    settlement_date = input('settlement date?(yyyy-mm-dd): ')

# get infos from db
with psycopg2.connect(
    host=HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD) as conn:

    cursor = conn.cursor()

    cursor.execute(get_attandance_sql(settlement_yearmonth+'-01'))
    settlement_att_data = dictfetchall(cursor)

    cursor.execute(get_attandance_sql(settlement_date))
    firstday_att_data = dictfetchall(cursor)

    cursor.execute(get_salary_data_sql(settlement_yearmonth))
    salary_data_list = dictfetchall(cursor)

    cursor.execute(get_training_fee_sql(settlement_yearmonth))
    training_fee_list = dictfetchall(cursor)

    cursor.execute(get_unsettled_salary_sql(settlement_yearmonth))
    unsettled_salary_list = dictfetchall(cursor)

with psycopg2.connect(
    host=HOST,
    dbname=DJANGO_DB_NAME,
    user=DJANGO_DB_USER,
    password=DJANGO_DB_PASSWORD) as conn2:

    cursor2 = conn2.cursor()

    cursor2.execute(get_member_info_sql())
    member_info_list = dictfetchall(cursor2)

settlement_att = [AttData(**item) for item in settlement_att_data]
firstday_att = [AttData(**item) for item in firstday_att_data]
salary_data = [SalaryData(**item) for item in salary_data_list]


override_members = get_override_members(settlement_att, firstday_att)
override_dict = get_override_dict(
    override_members, salary_data, settlement_yearmonth)

# set class variable - override dict
MemberSalary.override_members = override_dict

# set report members
training_fee_members = set([data['frid'] for data in training_fee_list])
salary_members = set([data.frid for data in salary_data])
firstday_members = set([data.frid for data in firstday_att])

report_members =\
     list(training_fee_members.union(salary_members, firstday_members))
report_members.sort()

# make MemberSalary list
member_name_dict = {d['member_id']:d['name'] for d in member_info_list}
att_1st_dict = {a.frid:a.m_position for a in firstday_att}
att_settlement_dict = {a.frid:a.m_position for a in settlement_att}
training_fee_dict = {t['frid']:t['fee'] for t in training_fee_list}
unsettled_dict = {u['frid']:u['salary'] for u in unsettled_salary_list}
additional_override_dict = get_additional_override(salary_data)
salary_list = []

for frid in report_members:    
    
    member_salary_data = MemberSalary(
        frid = frid,
        frname = member_name_dict[frid],
        m_position_1st = att_1st_dict[frid] if frid in att_1st_dict.keys() else 'Termination',
        m_position_settlement= att_settlement_dict[frid] if frid in att_settlement_dict.keys() else 'Termination',
        override_rate= override_dict[frid] if frid in override_dict.keys() else 0,
        signup_list=[data for data in salary_data if data.frid==frid],
        team_signup_list=[data for data in salary_data if frid in data.treecode],
        training_fee = training_fee_dict[frid] if frid in training_fee_dict.keys() else 0,
        unsettled_salary = unsettled_dict[frid] if frid in unsettled_dict.keys() else 0,
        additional_override = additional_override_dict[frid] if frid in additional_override_dict.keys() else 0
    )
    salary_list.append(member_salary_data)


for data in salary_list:
    print(data)