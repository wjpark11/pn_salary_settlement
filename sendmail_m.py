from time import sleep
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from pathlib import Path
import smtplib
import pandas as pd

YEAR = int(input("Enter settlement year (yyyy): "))
MONTH = int(input("Enter settlement month : "))
PREV_MONTH = MONTH - 1 if MONTH != 1 else 12
BASE_DIR = Path("./paystubs")
df = pd.read_excel(BASE_DIR / f"급여정산({YEAR}-{MONTH:02}).xlsm", sheet_name="mailsend", header=0)


s = smtplib.SMTP("smtp.worksmobile.com", 587)
s.starttls()

s.login("wjpark@project-n.or.kr", "NIRn8wX5MmyZ")

for i in range(len(df)):
    try:
        mail = MIMEMultipart()
        mail["From"] = "wjpark@project-n.or.kr"
        mail["To"] = f"{df.iloc[i][2]}"
        mail["Subject"] = f"{YEAR}년 {MONTH}월 PROJECT-N 급여명세서입니다."
        mail["Cc"] = "wjpark@project-n.or.kr"

        msg = MIMEText(
            f"""{YEAR}년 {MONTH}월 PROJECT-N 급여명세서입니다.

명세에 포함된 항목은 {PREV_MONTH}월 등록건 전체와 {PREV_MONTH}월 이전 등록건 중 출금결과가 나온 건들입니다.

지난 달 명세에 진행중으로 나온 항목이라도 출금결과가 나오지 않은 경우 명세에 포함되지 않습니다. 그러한 건들은 출금결과가 나오는 달의 급여명세에 포함되어 나가게 되므로 이점 혼동 없으시기 바랍니다.

그 외 급여명세에 대한 문의는 박원진 책임에게 해 주시기 바랍니다.

감사합니다."""
        )

        mail.attach(msg)

        path = BASE_DIR / f"{df.iloc[i][3]}"
        file = MIMEBase("application", "octet-stream")
        file.set_payload(open(path, "rb").read())
        encoders.encode_base64(file)
        file.add_header("Content-Disposition", "attachment", filename=f"{df.iloc[i][3]}")
        mail.attach(file)

        s.sendmail("wjpark@project-n.or.kr", df.iloc[i][2], mail.as_string())
        print(f"{df.iloc[i][3]} 발송 성공!")

    except:
        print(f"{df.iloc[i][3]} 메일 에러")
    sleep(1)

s.quit()
