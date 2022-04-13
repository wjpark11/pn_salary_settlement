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
    is_over_threshold,
    get_override_dict
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

print(settlement_yearmonth)
print(settlement_date)
