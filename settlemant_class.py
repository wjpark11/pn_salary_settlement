from typing import List, ClassVar
from collections import Counter
from dataclasses import dataclass
from datetime import date, time


@dataclass
class SalaryData:
    pnserial: str
    signupdate: date
    site: str
    applytime: time
    charity: str
    ahage: int
    submitstatus: str
    submitamount: int
    w_status: str
    withdrawamount: int
    frid: str
    frname: str
    m_position: str
    rate: float
    monthlycommission: int
    treecode: str
    salarymonth: str

    def get_down_override(self, frid:str, override_members: dict) -> dict:
        '''
        override_members: {frid: override_rate}
        '''
        tree_list = self.treecode.split('-')
        if not frid in tree_list or self.w_status != '출금완료':
            return dict()
        frid_index = tree_list.index(frid)
        submember_list = tree_list[frid_index+1:]
        for member in submember_list:
            if member in override_members.keys():
                return {member: self.monthlycommission * override_members[member]}
        
        return dict()


@dataclass
class AttData:
    frid: str
    frname: str
    m_position: str
    flid: str


@dataclass
class MemberSalary:
    override_members: ClassVar[dict]
    frid: str
    frname: str
    m_position_1st: str
    m_position_settlement: str
    override_rate: float
    signup_list: List[SalaryData]
    team_signup_list: List[SalaryData]
    training_fee: int
    unsettled_salary: int


    def get_settlement_signups(self) -> tuple:
        '''
        returns tuple (settlement_signups, salary_by_withdrawal)
        '''
        settlement_signups = 0
        salary_by_withdrawal = 0
        for signup in self.signup_list:
            if signup.w_status == '출금완료':
                settlement_signups += 1
                salary_by_withdrawal += signup.monthlycommission
        return settlement_signups, salary_by_withdrawal

    def get_full_override(self) -> int:
        team_salary = 0
        for signup in self.team_signup_list:
            if signup.w_status == '출금완료' and signup.m_position != 'INTERN':
                team_salary += signup.monthlycommission
        return team_salary * self.override_rate
    
    def get_down_override(self) -> dict:
        down_override = dict()
        for signup in self.team_signup_list:
            temp = signup.get_down_override(self.frid, self.override_members)
            down_override = dict(Counter(down_override)+Counter(temp))
        return down_override

    def get_final_override(self) -> int:
        total_override = self.get_full_override()
        total_down_override = sum(self.get_down_override().values())
        return total_override - total_down_override

    def get_signup_salary(self) -> int:
        signup_salary = 0
        for signup in self.signup_list:
            if signup.w_status == '출금완료':
                signup_salary += signup.monthlycommission
        
        return signup_salary

    




