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

    def get_down_override(self, frid: str, override_members: dict) -> dict:
        """
        override_members: {frid: override_rate}
        """
        tree_list = self.treecode.split("-")
        if not frid in tree_list or self.w_status != "출금완료":
            return dict()
        frid_index = tree_list.index(frid)
        submember_list = tree_list[frid_index + 1 :]
        for member in submember_list:
            if member in override_members.keys() and self.m_position != "INTERN":
                return {member: self.monthlycommission * override_members[member]}

        return dict()

    def info_tuple(self) -> tuple:
        return (
            self.signupdate.strftime("%Y-%m-%d"),
            self.pnserial,
            self.site,
            self.applytime.strftime("%H:%M"),
            self.charity,
            self.ahage,
            self.submitstatus,
            self.submitamount,
            self.w_status,
            self.withdrawamount,
            self.monthlycommission,
            self.m_position,
            self.frid,
            self.frname,
            self.treecode,
            self.salarymonth,
            self.rate,
        )


@dataclass
class AttData:
    frid: str
    frname: str
    m_position: str
    flid: str

    def info_tuple(self) -> tuple:
        return (self.flid, self.frid, self.frname, self.m_position)


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
    bonus_salary: int
    workday: int

    def get_settlement_signups(self) -> tuple:
        """
        returns tuple (settlement_signups, amount_by_withdrawal)
        """
        settlement_signups = 0
        amount_by_withdrawal = 0
        for signup in self.signup_list:
            if signup.w_status == "출금완료":
                settlement_signups += 1
                amount_by_withdrawal += signup.withdrawamount
        return settlement_signups, amount_by_withdrawal

    def get_team_salary(self) -> int:
        team_salary = 0
        for signup in self.team_signup_list:
            if signup.w_status == "출금완료" and signup.m_position != "INTERN":
                team_salary += signup.monthlycommission
        return team_salary

    def get_full_override(self) -> int:
        if self.frid not in self.override_members.keys():
            return 0
        team_salary = self.get_team_salary()
        return team_salary * self.override_rate

    def get_team_submit_amount(self, settlement_yearmonth: str) -> int:
        [year, month] = [int(item) for item in settlement_yearmonth.split("-")]
        if month == 1:
            year, month = year - 1, 12
        else:
            year, month = year, month - 1

        last_month_team_submitamount = 0

        for data in self.team_signup_list:
            if (
                data.submitstatus == "정기후원"
                and data.signupdate.year == year
                and data.signupdate.month == month
                and data.m_position != "INTERN"
            ):
                last_month_team_submitamount += data.submitamount
        return last_month_team_submitamount

    def get_down_override(self) -> dict:
        down_override = dict()
        if self.frid not in self.override_members.keys():
            return down_override
        for signup in self.team_signup_list:
            temp = signup.get_down_override(self.frid, self.override_members)
            down_override = dict(Counter(down_override) + Counter(temp))
        return down_override

    def get_distributed_override(self) -> int:
        if self.frid not in self.override_members.keys():
            return 0
        total_override = self.get_full_override()
        total_down_override = sum(self.get_down_override().values())
        return total_override - total_down_override

    def get_attendance_rate(self) -> float:
        attendance_rate = 1 - min(1, (max(20 - self.workday, 0)) / 10)
        return attendance_rate

    def get_final_override(self) -> int:
        if self.frid not in self.override_members.keys():
            return 0
        distributed_override = self.get_distributed_override()
        override_rate = self.get_attendance_rate()
        return distributed_override * override_rate

    def get_signup_salary(self) -> int:
        signup_salary = 0
        for signup in self.signup_list:
            if signup.w_status == "출금완료":
                signup_salary += signup.monthlycommission

        return signup_salary

    def info_tuple(self) -> tuple:
        settlement_amount = (
            self.get_signup_salary()
            + self.get_final_override()
            + self.training_fee
            + self.unsettled_salary
            + self.bonus_salary
        )
        tax = (
            int(int(max(0, settlement_amount) * 0.03) / 10) * 10
            + int(int(max(0, settlement_amount) * 0.003) / 10) * 10
        )
        info = (
            self.frid,
            self.frname,
            self.m_position_settlement,
            self.workday,
            *self.get_settlement_signups(),
            self.get_signup_salary(),
            self.get_final_override(),
            self.training_fee,
            self.unsettled_salary,
            self.bonus_salary,
            settlement_amount,
            max(0, settlement_amount),
            tax,
            max(0, settlement_amount) - tax,
        )
        return info
