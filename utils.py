from typing import List

import psycopg2

from settlemant_class import SalaryData, AttData, MemberSalary
from db_cred import (
    HOST,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DJANGO_DB_NAME,
    DJANGO_DB_USER,
    DJANGO_DB_PASSWORD
)


def dictfetchall(cursor) -> List[dict]:
    """Return all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def get_salary_data_sql(settlement_yearmonth: str) -> str:
    data_sql = f"SELECT * FROM monthlysalary2 WHERE salarymonth='{settlement_yearmonth}';"
    return data_sql


def get_unsettled_salary_sql(settlement_yearmonth: str) -> str:
    unsettled_salary_sql = f"""SELECT frid, salary
FROM unsettled_salary
WHERE is_settled = TRUE AND settled_yearmonth='{settlement_yearmonth}'
    """
    return unsettled_salary_sql


def get_attandance_sql(datestr: str) -> str:
    att_sql = f"""SELECT flid, frid, frname, m_position 
FROM attendance 
WHERE adate='{datestr}';"""
    return att_sql


def get_training_fee_sql(settlement_yearmonth: str) -> str:
    [year, month] = [int(item) for item in settlement_yearmonth.split('-')]
    if month == 1:
        year, month = year - 1, 12
    else:
        year, month = year, month - 1

    training_fee_sql = f"""SELECT 
    frid,
    frname,
    count(site) AS days,
    count(site)*50000 AS fee 
FROM attendance
WHERE 
    extract(year from adate)={year} 
    AND extract(month from adate)={month} 
    AND m_position='INTERN' 
    AND channel != 'X' 
GROUP BY frid, frname;
    """
    return training_fee_sql


def get_member_info_sql() -> str:
    member_info_sql = f"""SELECT 
 member_id, 
 id_num_1||'-'||id_num_2 as id_num, 
 name,  
 left(bank,3) AS bank_id, 
 substring(bank from '-\s(.*)') AS bank_name, 
 account_number,
 account_name, 
 email 
FROM member_user 
WHERE position=1
ORDER BY member_id;
    """
    return member_info_sql


def get_override_members(settlement_att: List[AttData], firstday_att: List[AttData]) -> List[tuple]:
    '''
    returns list of override member tuple (frid, m_position)
    '''
    supermembers_at_settlement = set([data.flid for data in settlement_att])
    override_members = [
        (data.frid, data.m_position) for data 
        in firstday_att 
        if data.m_position in ('TL', 'STL', 'D', 'SD')
        and data.frid in supermembers_at_settlement]
    return override_members


def is_over_threshold(
    frid: str,
    salary_data: List[SalaryData],
    threshold_amount: int,
    settlement_yearmonth: str) -> bool:

    # get year, month for last month
    [year, month] = [int(item) for item in settlement_yearmonth.split('-')]
    if month == 1:
        year, month = year - 1, 12
    else:
        year, month = year, month - 1

    last_month_team_submitamount = 0

    for data in salary_data:
        if data.submitstatus =='정기후원'\
            and data.signupdate.year == year\
            and data.signupdate.month == month\
            and data.m_position != 'INTERN'\
            and frid in data.treecode:
            last_month_team_submitamount += data.submitamount

    return last_month_team_submitamount >= threshold_amount


def get_override_dict(
        override_members: List[tuple],
        salary_data: List[SalaryData],
        settlement_yearmonth: str) -> dict:
    '''
    returns override dict: key = frid, value = override rate
    '''

    override_dict= dict()
    for member in override_members:
        if member[1] == 'TL':
            override_dict[member[0]] = 0.05
        elif member[1] == 'STL':
            override_dict[member[0]] = 0.1
        else:
            if is_over_threshold(member[0], salary_data, 8000000, settlement_yearmonth):
                override_dict[member[0]] = 0.25
            else:
                override_dict[member[0]] = 0.2

    return override_dict


def get_additional_override(salary_data: List[SalaryData]) -> dict:
    HA_team_withdrawal_data = [
        data.monthlycommission
        for data
        in salary_data
        if data.m_position!='INTERN' and data.w_status == '출금완료' and 'HA' in data.frid]
    
    return {'AM0001': sum(HA_team_withdrawal_data) * 0.05}



if __name__ == '__main__':    

    with psycopg2.connect(
        host=HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD) as conn:

        cursor = conn.cursor()

        cursor.execute(get_attandance_sql('2022-04-01'))
        settlement_att_data = dictfetchall(cursor)

        cursor.execute(get_attandance_sql('2022-04-10'))
        firstday_att_data = dictfetchall(cursor)

        cursor.execute(get_salary_data_sql('2022-04'))
        salary_data_list = dictfetchall(cursor)

        cursor.execute(get_training_fee_sql(2022, 3))
        training_fee_list = dictfetchall(cursor)


    settlement_att = [AttData(**item) for item in settlement_att_data]
    firstday_att = [AttData(**item) for item in firstday_att_data]
    salary_data = [SalaryData(**item) for item in salary_data_list]


    override_members = get_override_members(settlement_att, firstday_att)
    override_dict = get_override_dict(override_members, salary_data, '2022-04')

    MemberSalary.override_members = override_dict

    training_fee_members = set([data['frid'] for data in training_fee_list])
    salary_members = set([data.frid for data in salary_data])
    firstday_members = set([data.frid for data in firstday_att])

    # print(training_fee_members)
    # print(salary_members)
    # print(firstday_members)

    report_members = list(training_fee_members.union(salary_members, firstday_members))
    report_members.sort()

    print(report_members)

    am0001 = MemberSalary(
        frid='AM0001',
        frname='조성재',
        m_position_1st='SD',
        m_position_settlement='SD',
        override_rate=0.2,
        signup_list=[data for data in salary_data if data.frid=='AM0001'],
        team_signup_list=[data for data in salary_data if 'AM0001' in data.treecode],
        training_fee=0,
        unsettled_salary=0
    )

    print(am0001.get_full_override())
    print(am0001.get_down_override())
    print(am0001.get_final_override())
    print(get_additional_override(salary_data))
