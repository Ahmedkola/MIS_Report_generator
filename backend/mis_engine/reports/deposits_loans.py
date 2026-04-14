import re
from .base import BaseReportProcessor


def _norm(s):
    return re.sub(r"\s+", " ", s.strip()).lower()


SECURITY_DEPOSIT_LEDGERS = [
    "CP - Security Deposit",
    "JPN Hotel Security Deposit",
    "Langford Security Deposit",
    "Security Depoosit -Mysore Firenza",   # Tally typo — three o's
    "Security Deposit -Mysore Firenza",    # fallback if typo ever fixed
    "Security deposit - Brigade El-Dorado",
    "Security Deposit-Business Transfer",
    "Security Deposit - CMR",
    "Security Deposit Hebbal",
    "Security Deposit HN",
    "Security Deposit Kora New",
    "SECURITY DEPOSIT LINGRAJPURAM",
    "Security Deposit Mahaveer Celesse 905/601",
    "Security Deposit MN",
    "Security Deposit-Pune Viman Nagar",
    "Security Deposit Waterford",
    "Valley View Assagao",
]

LOAN_LEDGERS = [
    "Adnan Loan A/c",
    "Ameena Loan",
    "Arbaaz Loan A/c",
    "EPIMONEY PRIVATE LIMITED Loan",
    "INDIFI CAPITAL MAS Loan",
    "Parvez Loan",
    "Raiyan Loan A/c",
    "Rumsha Zuha Loan",
    "Ukhail Loan A/c",
]


class DepositsLoansProcessor(BaseReportProcessor):
    def process(self) -> dict:
        tb_norm = {_norm(lb["ledger_name"]): lb for lb in self.raw_data}

        seen: set[str] = set()

        def lookup(name):
            lb = tb_norm.get(_norm(name))
            if not lb:
                return None
            key = _norm(lb["ledger_name"])
            if key in seen:
                return None   # skip duplicate (e.g. typo + corrected name both listed)
            seen.add(key)
            # Use abs — security deposits may be Dr (paid out) or Cr (received), both shown positive
            amount = abs(lb["amount"])
            if amount == 0:
                return None
            return {"name": lb["ledger_name"], "amount": amount}

        deposits = [r for r in (lookup(n) for n in SECURITY_DEPOSIT_LEDGERS) if r]
        loans    = [r for r in (lookup(n) for n in LOAN_LEDGERS) if r]

        return {
            "period":         f"{self.from_date} to {self.to_date}",
            "deposits":       deposits,
            "loans":          loans,
            "total_deposits": sum(d["amount"] for d in deposits),
            "total_loans":    sum(l["amount"] for l in loans),
        }
