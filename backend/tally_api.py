"""
tally_api.py – TallyPrime XML API Client
Company: Unreal Estate Habitat Pvt. Ltd. (ID: 110011)

Three-tier extraction strategy (tried in order until one returns data):

  STRATEGY 1 → Inline TDL Custom Collection  ← PRIMARY (gold standard)
    Sends a self-contained TDL script that forces Tally to loop its internal
    Ledger objects and emit OUR custom XML tags (LEDGER_NAME, CLOSING_BALANCE).
    Immune to Tally UI / F12 config changes. Company-locked.

  STRATEGY 2 → Raw Ledger Collection API  ← FALLBACK
    Fetches the built-in Ledger collection via FETCHLIST. Works on most builds
    but tag names are Tally-defined, not ours.

  STRATEGY 3 → Trial Balance Report API  ← LAST RESORT
    Parses Tally's rendered report XML. Fragile (display-tag dependent).
    Kept only for edge-case Tally configurations.

Prerequisites:
  - TallyPrime open, Company 110011 loaded and active
  - HTTP XML Server enabled on port 9000:
      Gateway of Tally → F12 Configure → Advanced Configuration →
      Enable ODBC / HTTP Server → Port: 9000

Usage:
  python tally_api.py
  python tally_api.py --from 20250401 --to 20260131
  python tally_api.py --debug
"""

from __future__ import annotations

import argparse
import logging
import re
import xml.etree.ElementTree as ET
from typing import TypedDict

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("tally_api")


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

class LedgerBalance(TypedDict):
    ledger_name: str   # Exact Tally ledger name — used for LedgerMapping lookup
    amount: float      # Signed; negative = Debit (expense/outflow), positive = Credit
    dr_cr: str         # "Dr" or "Cr" — retained for audit purposes


# ---------------------------------------------------------------------------
# Amount parser (shared by all three strategies)
# ---------------------------------------------------------------------------

def _parse_tally_amount(raw: str | None) -> tuple[float, str]:
    """
    Handles all Tally amount string formats:
      "34085700.00 Dr"   → (-34085700.0,  "Dr")
      "250.50 Cr"        → (250.5,         "Cr")
      "-34085700.00"     → (-34085700.0,   "Dr")  ← pure-negative fallback
      ""  / None         → (0.0,           "Cr")

    Convention: Dr = negative, Cr = positive.
    """
    if not raw:
        return 0.0, "Cr"

    raw = raw.strip()
    dr_cr = "Cr"  # default

    suffix = re.search(r"\b(Dr|Cr)\b", raw, re.IGNORECASE)
    if suffix:
        dr_cr = suffix.group(1).capitalize()
        raw = raw[: suffix.start()].strip()

    # Strip everything except digits, dot, minus
    clean = re.sub(r"[^\d.\-]", "", raw)
    try:
        value = float(clean)
    except ValueError:
        return 0.0, dr_cr

    # If no Dr/Cr suffix, infer from sign of raw number
    if not suffix and value < 0:
        dr_cr = "Dr"

    value = -abs(value) if dr_cr == "Dr" else abs(value)
    return value, dr_cr


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class TallyAPIClient:
    """
    Service to communicate with the local TallyPrime XML API.
    """

    # We no longer hardcode 110011, we pass the exact active company name.
    COMPANY_ID = "Unreal Estate Habitat Private Limited"

    def __init__(self, host: str = "127.0.0.1", port: int = 9000, timeout: int = 30):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/xml"})
        self._cc_alloc_cache: dict[str, dict[str, float]] | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch_trial_balance(self, from_date: str, to_date: str) -> list[LedgerBalance]:
        """
        Returns closing balances for every non-zero ledger in the period.

        Args:
            from_date / to_date: "YYYYMMDD"  e.g. "20250401"
        """
        logger.info("Fetching trial balance for [%s] %s → %s", self.COMPANY_ID, from_date, to_date)

        # 🚨 STRATEGY 1 DISABLED: Caused Memory Access Violation on execution 🚨
        # results = self._fetch_via_tdl(from_date, to_date)
        # if results:
        #     logger.info("Strategy 1 (TDL): %d ledgers.", len(results))
        #     return results

        # Strategy 1 – Trial Balance Report API (primary; fast on 127.0.0.1)
        try:
            logger.info("Using Strategy 1 (Trial Balance Report API)...")
            results = self._fetch_via_report(from_date, to_date)
            if results:
                logger.info("Strategy 1 (Report): %d ledgers.", len(results))
                return results
            logger.warning("Strategy 1 returned empty results.")
        except (TimeoutError, ConnectionError, requests.Timeout, requests.ConnectionError) as e:
            logger.warning("Strategy 1 failed (%s). Falling back to Strategy 2 (Collection API)...", type(e).__name__)

        # Strategy 2 – Raw Collection API (fallback; returns masters without period amounts)
        results = self._fetch_via_collection(from_date, to_date)
        logger.info("Strategy 2 (Collection): %d ledgers.", len(results))
        return results

    def ping(self) -> bool:
        """True if Tally is reachable."""
        try:
            payload = (
                "<ENVELOPE><HEADER>"
                "<TALLYREQUEST>List of Companies</TALLYREQUEST>"
                "</HEADER></ENVELOPE>"
            )
            r = self._session.post(self.base_url, data=payload, timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # Strategy 1: Inline TDL Custom Collection  (PRIMARY)
    #
    # Sends a fully self-contained TDL program. Tally compiles it at
    # runtime and emits clean LEDGERLINE nodes with our custom tags.
    #
    # Critical TDL syntax note:
    #   <XMLTAG> must NOT have quotes around the value.
    #   ✓  <XMLTAG>LEDGER_NAME</XMLTAG>
    #   ✗  <XMLTAG>"LEDGER_NAME"</XMLTAG>  ← would produce literal " in tag
    # ------------------------------------------------------------------

    def _fetch_via_tdl(self, from_date: str, to_date: str) -> list[LedgerBalance]:
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>MIS_LedgerExport</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <TDL>
          <TDLMESSAGE>
            <REPORT NAME="MIS_LedgerExport">
              <FORMS>MIS_LedgerForm</FORMS>
            </REPORT>
            <FORM NAME="MIS_LedgerForm">
              <PARTS>MIS_LedgerPart</PARTS>
            </FORM>
            <PART NAME="MIS_LedgerPart">
              <LINES>MIS_LedgerLine</LINES>
              <REPEAT>MIS_LedgerLine : MIS_LedgerColl</REPEAT>
              <SCROLLED>Vertical</SCROLLED>
            </PART>
            <LINE NAME="MIS_LedgerLine">
              <FIELDS>MIS_FldName, MIS_FldBalance</FIELDS>
            </LINE>
            <FIELD NAME="MIS_FldName">
              <SET>$Name</SET>
              <XMLTAG>LEDGER_NAME</XMLTAG>
            </FIELD>
            <FIELD NAME="MIS_FldBalance">
              <SET>$ClosingBalance</SET>
              <XMLTAG>CLOSING_BALANCE</XMLTAG>
            </FIELD>
            <COLLECTION NAME="MIS_LedgerColl">
              <TYPE>Ledger</TYPE>
            </COLLECTION>
          </TDLMESSAGE>
        </TDL>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        if not raw_xml:
            return []
        return self._parse_tdl_xml(raw_xml)

    def _parse_tdl_xml(self, raw_xml: str) -> list[LedgerBalance]:
        """
        Parses our custom TDL output.

        Tally uppercases LINE names and strips spaces, so <LINE NAME="MIS_LedgerLine">
        produces <MIS_LEDGERLINE> wrapper nodes.
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("TDL XML parse error: %s", exc)
            return []

        results: list[LedgerBalance] = []

        # Tally emits the line name uppercased with underscores collapsed
        for line in root.findall(".//MIS_LEDGERLINE"):
            name_node = line.find("LEDGER_NAME")
            bal_node = line.find("CLOSING_BALANCE")

            if name_node is None or not name_node.text:
                continue

            amount, dr_cr = _parse_tally_amount(
                bal_node.text if bal_node is not None else None
            )
            if amount == 0.0:
                continue  # skip inactive ledgers

            results.append(
                LedgerBalance(
                    ledger_name=name_node.text.strip(),
                    amount=amount,
                    dr_cr=dr_cr,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Strategy 2: Raw Ledger Collection API  (FALLBACK)
    # ------------------------------------------------------------------

    def _fetch_via_collection(self, from_date: str, to_date: str) -> list[LedgerBalance]:
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <REQUESTDATA>
          <TALLYMESSAGE xmlns:UDF="TallyUDF">
            <COLLECTION ISMODIFY="No">
              <TYPE>Ledger</TYPE>
              <FETCHLIST>
                <FETCH>NAME</FETCH>
                <FETCH>CLOSINGBALANCE</FETCH>
              </FETCHLIST>
            </COLLECTION>
          </TALLYMESSAGE>
        </REQUESTDATA>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        if not raw_xml:
            return []

        # --- ADD THESE 3 LINES ---
        with open("tally_dump.xml", "w", encoding="utf-8") as f:
            f.write(_sanitize_xml(raw_xml))
        print("\n[SUCCESS] Dumped raw Tally data to tally_dump.xml!")
        # -------------------------

        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("Collection XML parse error: %s", exc)
            return []

        results: list[LedgerBalance] = []
        for ledger in root.findall(".//LEDGER"):
            name = ledger.get("NAME") or _text(ledger, "NAME")
            if not name:
                continue
            closing = ledger.find("CLOSINGBALANCE")
            amount, dr_cr = _parse_tally_amount(
                closing.text if closing is not None else None
            )
            if amount == 0.0:
                continue
            results.append(
                LedgerBalance(ledger_name=name.strip(), amount=amount, dr_cr=dr_cr)
            )
        return results

    # ------------------------------------------------------------------
    # Strategy 3: Trial Balance Report API  (LAST RESORT)
    # ------------------------------------------------------------------

    def _fetch_via_report(self, from_date: str, to_date: str) -> list[LedgerBalance]:
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Trial Balance</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <EXPLODEALLLEVELS>Yes</EXPLODEALLLEVELS>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        if not raw_xml:
            return []
        return self._parse_report_sibling_nodes(raw_xml)

    # ------------------------------------------------------------------
    # Phase 5: Cost Centre Breakup API
    # ------------------------------------------------------------------

    def fetch_balance_sheet(self, to_date: str) -> dict:
        """
        Fetches the Balance Sheet with full ledger-level detail (EXPLODEFLAG=Yes).

        Returns a dict keyed by top-level group name, e.g.:
          {
            "Capital Account":    {"total": 100000.0,   "items": [LedgerBalance, ...]},
            "Loans (Liability)":  {"total": 27813510.18,"items": [...]},
            "Fixed Assets":       {"total": -16795524.41,"items": [...]},
            ...
          }
        Group totals are signed (positive=Cr/liability, negative=Dr/asset).
        Item amounts are also signed the same way.
        """
        logger.info("Fetching Balance Sheet (detailed) as at %s", to_date)
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Balance Sheet</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <EXPLODEALLLEVELS>Yes</EXPLODEALLLEVELS>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""
        raw_xml = self._post(payload)
        if not raw_xml:
            return {}
        return self._parse_bs_xml(raw_xml)

    def _parse_bs_xml(self, raw_xml: str) -> dict:
        """
        Parses the full exploded Tally Balance Sheet XML.

        All rows use the same BSNAME/BSAMT sibling pattern.
        Distinguishing group headers from sub-items:
          Group header  → BSMAINAMT is filled, BSSUBAMT is empty
          Sub-item      → BSSUBAMT is filled, BSMAINAMT is empty

        Structure:
          <BSNAME><DSPACCNAME><DSPDISPNAME>Capital Account</DSPDISPNAME></DSPACCNAME></BSNAME>
          <BSAMT><BSSUBAMT></BSSUBAMT><BSMAINAMT>100000.00</BSMAINAMT></BSAMT>

          <BSNAME><DSPACCNAME><DSPDISPNAME>Arbaz Capital</DSPDISPNAME></DSPACCNAME></BSNAME>
          <BSAMT><BSSUBAMT>25000.00</BSSUBAMT><BSMAINAMT></BSMAINAMT></BSAMT>

        Returns dict keyed by group name: {"total": float, "items": list[LedgerBalance]}.
        Positive = Cr (liabilities), Negative = Dr (assets).
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("BS XML parse error: %s", exc)
            return {}

        # Dump raw XML for debugging
        try:
            with open("bs_dump.xml", "w", encoding="utf-8") as _f:
                _f.write(raw_xml)
        except OSError:
            pass

        groups: dict = {}          # group_name → {"total": float, "items": list}
        current_group: str | None = None
        pending_name: str | None = None

        for elem in root:
            tag = elem.tag

            if tag == "BSNAME":
                disp = elem.find(".//DSPDISPNAME")
                pending_name = disp.text.strip() if disp is not None and disp.text else None

            elif tag == "BSAMT" and pending_name:
                main_node = elem.find("BSMAINAMT")
                sub_node  = elem.find("BSSUBAMT")
                raw_main  = main_node.text.strip() if main_node is not None and main_node.text else ""
                raw_sub   = sub_node.text.strip()  if sub_node  is not None and sub_node.text  else ""

                if raw_main:
                    # Group header — create a new bucket
                    try:
                        total = float(raw_main)
                    except ValueError:
                        total = 0.0
                    groups[pending_name] = {"total": total, "items": []}
                    current_group = pending_name

                elif raw_sub and current_group:
                    # Sub-item under current group
                    try:
                        value = float(raw_sub)
                    except ValueError:
                        value = 0.0
                    if value != 0.0:
                        dr_cr = "Dr" if value < 0 else "Cr"
                        groups[current_group]["items"].append(LedgerBalance(
                            ledger_name=pending_name,
                            amount=value,
                            dr_cr=dr_cr,
                        ))

                pending_name = None

        logger.info("BS parse: %d groups, %d total items",
                    len(groups),
                    sum(len(v["items"]) for v in groups.values()))
        return groups

    def fetch_balance_sheet_group(self, group_name: str, to_date: str) -> list[LedgerBalance]:
        """
        Fetches individual ledgers within a BS top-level group.
        Uses EXPLODEFLAG=Yes and PARENTGROUP to drill into one group.
        Returns LedgerBalance list: Cr amounts positive, Dr amounts negative.
        """
        logger.info("Fetching BS group detail: %s as at %s", group_name, to_date)
        group_escaped = group_name.replace("&", "&amp;")
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Balance Sheet</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <PARENTGROUP>{group_escaped}</PARENTGROUP>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""
        raw_xml = self._post(payload)
        if not raw_xml:
            return []
        return self._parse_bs_group_xml(raw_xml)

    def _parse_bs_group_xml(self, raw_xml: str) -> list[LedgerBalance]:
        """
        Parses the sub-ledger drill-down XML for a BS group.
        Sibling pattern: DSPACCNAME then DSPACCINFO.

        Structure:
          <DSPACCNAME><DSPDISPNAME>Arbaz Capital</DSPDISPNAME></DSPACCNAME>
          <DSPACCINFO>
            <DSPCLDRAMTA></DSPCLDRAMTA>
            <DSPCLCRAMTA>25000.00</DSPCLCRAMTA>
          </DSPACCINFO>

        Cr amounts → positive; Dr amounts → negative (assets).
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("BS group XML parse error: %s", exc)
            return []

        results: list[LedgerBalance] = []
        pending_name: str | None = None
        for elem in root:
            if elem.tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                pending_name = disp.text.strip() if disp is not None and disp.text else None
            elif elem.tag == "DSPACCINFO" and pending_name:
                dr_node = elem.find("DSPCLDRAMTA")
                cr_node = elem.find("DSPCLCRAMTA")
                dr_raw = dr_node.text.strip() if dr_node is not None and dr_node.text else ""
                cr_raw = cr_node.text.strip() if cr_node is not None and cr_node.text else ""
                value = 0.0
                dr_cr = "Cr"
                if cr_raw:
                    try:
                        value = float(cr_raw)
                        dr_cr = "Cr"
                    except ValueError:
                        pass
                elif dr_raw:
                    try:
                        value = -float(dr_raw)   # Dr = negative (asset)
                        dr_cr = "Dr"
                    except ValueError:
                        pass
                if value != 0.0:
                    results.append(LedgerBalance(
                        ledger_name=pending_name,
                        amount=value,
                        dr_cr=dr_cr,
                    ))
                pending_name = None
        return results

    def fetch_ledger_vouchers(self, ledger_name: str, from_date: str, to_date: str) -> list[dict]:
        """
        Fetches the line-by-line voucher details for a specific ledger.
        Returns a list of vouchers. Each voucher dict contains:
           - 'amount': the amount for THIS ledger in the voucher
           - 'dr_cr': Dr or Cr
           - 'lines': list of ledger names for the *other* legs of the voucher
        This is critical for mapping GST/Host Fees to specific Unit Sales accounts.
        """
        logger.info("Fetching Ledger Vouchers for %s (%s → %s)", ledger_name, from_date, to_date)
        
        ledger_escaped = ledger_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Ledger Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <LEDGERNAME>{ledger_escaped}</LEDGERNAME>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <EXPLODEALLLEVELS>Yes</EXPLODEALLLEVELS>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        if not raw_xml:
            return []
        return self._parse_ledger_vouchers_xml(raw_xml)

    def _parse_ledger_vouchers_xml(self, raw_xml: str) -> list[dict]:
        """
        Parses the Tally 'Ledger Vouchers' report.
        Tally returns flat nodes.
        <DSPVCHDATE> begins a new voucher.
        The main ledger's amount is in <DSPVCHDRAMT> or <DSPVCHCRAMT>.
        The other legs are in <DSPVCHEXPLACCOUNT>.
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("Ledger Vouchers XML parse error: %s", exc)
            return []

        vouchers = []
        current_voucher = None

        for elem in root:
            if elem.tag == "DSPVCHDATE":
                if current_voucher and current_voucher["amount"] != 0:
                    vouchers.append(current_voucher)
                current_voucher = {
                    "amount": 0.0,
                    "dr_cr": "Cr",
                    "lines": set()  # Using set to avoid duplicates
                }
            elif elem.tag == "DSPVCHDRAMT" and current_voucher is not None:
                if elem.text and elem.text.strip():
                    try:
                        current_voucher["amount"] = abs(float(elem.text.strip()))
                        current_voucher["dr_cr"] = "Dr"
                    except ValueError:
                        pass
            elif elem.tag == "DSPVCHCRAMT" and current_voucher is not None:
                if elem.text and elem.text.strip():
                    try:
                        current_voucher["amount"] = abs(float(elem.text.strip()))
                        current_voucher["dr_cr"] = "Cr"
                    except ValueError:
                        pass
            elif elem.tag == "DSPVCHEXPLACCOUNT" and current_voucher is not None:
                if elem.text and elem.text.strip():
                    current_voucher["lines"].add(elem.text.strip())

        if current_voucher and current_voucher["amount"] != 0:
            vouchers.append(current_voucher)

        return vouchers

    # ------------------------------------------------------------------
    # Strategy: P&L via Group Summary  ← AUTHORITATIVE
    #
    # The monolithic "Profit & Loss" report API can't be called by name via
    # Tally's HTTP XML server. Instead, we call Group Summary once per P&L
    # group — exactly the same proven approach used by fetch_balance_sheet_group.
    # The XML format is identical: DSPACCNAME → DSPACCINFO (DSPCLDRAMTA/DSPCLCRAMTA).
    # ------------------------------------------------------------------

    def fetch_pnl_report(self, from_date: str, to_date: str) -> dict:
        """
        Fetches P&L by calling Group Summary once per P&L group.

        This mirrors exactly how fetch_balance_sheet_group works for the Balance Sheet.
        The monolithic "Profit & Loss A/c" report cannot be fetched by name via Tally API,
        but Group Summary is proven to work (confirmed by group_dump.xml).

        Returns a dict keyed by Tally's own section names:
          {
            "Sales Accounts":   {"total": 75414283.37, "items": [{"name": "Koramangala", "amount": 8265642.68}, ...]},
            "Direct Incomes":   {"total": 7205.65,     "items": [...]},
            "Direct Expenses":  {"total": -44615529.20,"items": [...]},
            "Indirect Incomes": {"total": 237060.06,   "items": [...]},
            "Indirect Expenses":{"total": -12642983.93,"items": [...]},
          }
        """
        logger.info("Fetching P&L via Group Summary for [%s] %s → %s", self.COMPANY_ID, from_date, to_date)

        PNL_GROUPS = [
            "Sales Accounts",
            "Direct Incomes",
            "Direct Expenses",
            "Indirect Incomes",
            "Indirect Expenses",
        ]

        result: dict = {}

        for group_name in PNL_GROUPS:
            group_escaped = group_name.replace("&", "&amp;")

            payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Group Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <GROUPNAME>{group_escaped}</GROUPNAME>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

            raw_xml = self._post(payload)
            if not raw_xml:
                logger.warning("P&L Group Summary returned no data for: %s", group_name)
                result[group_name] = {"total": 0.0, "items": []}
                continue

            items = self._parse_pnl_group_xml(raw_xml)
            total = sum(item["amount"] for item in items)
            result[group_name] = {"total": total, "items": items}
            logger.info("P&L group [%s]: %d ledgers, total=%.2f", group_name, len(items), total)

        return result

    def _parse_pnl_group_xml(self, raw_xml: str) -> list[dict]:
        """
        Parses a single Group Summary response for a P&L group.

        Proven XML structure (from user's directExp.xml, SalesAccount.xml, etc.):

          <DSPACCNAME><DSPDISPNAME>Electricity</DSPDISPNAME></DSPACCNAME>
          <DSPACCINFO>
            <DSPCLDRAMT><DSPCLDRAMTA>-2462696.62</DSPCLDRAMTA></DSPCLDRAMT>  ← expense
            <DSPCLCRAMT><DSPCLCRAMTA></DSPCLCRAMTA></DSPCLCRAMT>
          </DSPACCINFO>

          <DSPACCNAME><DSPDISPNAME>Koramangala</DSPDISPNAME></DSPACCNAME>
          <DSPACCINFO>
            <DSPCLDRAMT><DSPCLDRAMTA></DSPCLDRAMTA></DSPCLDRAMT>
            <DSPCLCRAMT><DSPCLCRAMTA>8265642.68</DSPCLCRAMTA></DSPCLCRAMT>   ← revenue
          </DSPACCINFO>

        Uses .// to handle any nesting depth of DSPCLDRAMT/DSPCLCRAMTA wrapper.
        Returns list of {"name": str, "amount": float}.
          - Expenses: negative (Dr)
          - Income: positive (Cr)
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("P&L group XML parse error: %s", exc)
            return []

        items: list[dict] = []
        pending_name: str | None = None

        for elem in root:
            if elem.tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                pending_name = disp.text.strip() if disp is not None and disp.text else None

            elif elem.tag == "DSPACCINFO" and pending_name:
                dr_node = elem.find(".//DSPCLDRAMTA")
                cr_node = elem.find(".//DSPCLCRAMTA")

                dr_raw = dr_node.text.strip() if dr_node is not None and dr_node.text else ""
                cr_raw = cr_node.text.strip() if cr_node is not None and cr_node.text else ""

                amount = 0.0
                if dr_raw:
                    try:
                        amount = float(dr_raw)   # Tally gives Dr as negative already
                    except ValueError:
                        pass
                elif cr_raw:
                    try:
                        amount = float(cr_raw)   # Cr = positive
                    except ValueError:
                        pass

                if amount != 0.0:
                    items.append({"name": pending_name, "amount": amount})

                pending_name = None

        return items



    def _parse_pnl_xml(self, raw_xml: str) -> dict:
        """
        Parses Tally's Profit & Loss report XML.

        Structure (sibling nodes under root ENVELOPE):
          <DSPACCNAME><DSPDISPNAME>Sales Accounts</DSPDISPNAME></DSPACCNAME>
          <PLAMT><PLSUBAMT></PLSUBAMT><BSMAINAMT>75414283.37</BSMAINAMT></PLAMT>

          <!-- sub-section: PLSUBAMT filled, BSMAINAMT empty -->
          <DSPACCNAME><DSPDISPNAME>Direct Expenses</DSPDISPNAME></DSPACCNAME>
          <PLAMT><PLSUBAMT>-44615529.20</PLSUBAMT><BSMAINAMT></BSMAINAMT></PLAMT>

          <!-- individual item: BSNAME + BSAMT -->
          <BSNAME><DSPACCNAME><DSPDISPNAME>Electricity</DSPDISPNAME></DSPACCNAME></BSNAME>
          <BSAMT><BSSUBAMT>-2462696.62</BSSUBAMT><BSMAINAMT></BSMAINAMT></BSAMT>

        Rules:
          • DSPACCNAME (top-level) + PLAMT/BSMAINAMT filled  → top-level section header
          • DSPACCNAME (top-level) + PLAMT/PLSUBAMT filled   → sub-section (becomes active bucket for items)
          • BSNAME + BSAMT/BSSUBAMT                          → individual line item; stored under current active section
        """
        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("P&L XML parse error: %s", exc)
            return {}

        sections: dict = {}          # keyed by section name
        current_section: str | None = None   # most recently seen active section
        pending_item: str | None = None

        for elem in root:
            tag = elem.tag

            if tag == "DSPACCNAME":
                disp = elem.find("DSPDISPNAME")
                if disp is not None and disp.text:
                    current_section = disp.text.strip()
                    if current_section and current_section not in sections:
                        sections[current_section] = {"total": 0.0, "items": []}
                pending_item = None

            elif tag == "PLAMT" and current_section:
                # BSMAINAMT = top-level section total (may be positive or negative)
                main_node = elem.find("BSMAINAMT")
                sub_node  = elem.find("PLSUBAMT")
                raw_main  = main_node.text.strip() if (main_node is not None and main_node.text) else ""
                raw_sub   = sub_node.text.strip()  if (sub_node  is not None and sub_node.text)  else ""
                amount_str = raw_main if raw_main else raw_sub
                if amount_str:
                    try:
                        sections[current_section]["total"] = float(amount_str)
                    except ValueError:
                        pass

            elif tag == "BSNAME":
                disp = elem.find(".//DSPDISPNAME")
                pending_item = disp.text.strip() if (disp is not None and disp.text) else None

            elif tag == "BSAMT" and pending_item and current_section:
                sub_node = elem.find("BSSUBAMT")
                raw_val  = sub_node.text.strip() if (sub_node is not None and sub_node.text) else ""
                if raw_val:
                    try:
                        amount = float(raw_val)
                        if amount != 0.0:
                            sections[current_section]["items"].append(
                                {"name": pending_item, "amount": amount}
                            )
                    except ValueError:
                        pass
                pending_item = None

        logger.info(
            "P&L parse: %d sections, %d total items",
            len(sections),
            sum(len(v["items"]) for v in sections.values()),
        )
        return sections

    def fetch_account_hierarchy(self) -> tuple[dict[str, str], set[str]]:
        """
        Fetches the complete Chart of Accounts tree from Tally (both Groups and Ledgers).
        Returns a tuple: (hierarchy_dict, ledger_names_set)
          - hierarchy_dict: mapping each node to its parent: {"Salary A/c": "Operating Costs"}
          - ledger_names_set: a set of names that are specifically Ledgers (not Groups)
        """
        logger.info("Fetching complete Account Hierarchy from Tally")
        
        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <REQUESTDATA>
          <TALLYMESSAGE xmlns:UDF="TallyUDF">
            <COLLECTION ISMODIFY="No">
              <TYPE>Group</TYPE>
              <TYPE>Ledger</TYPE>
              <FETCHLIST>
                <FETCH>NAME</FETCH>
                <FETCH>PARENT</FETCH>
              </FETCHLIST>
            </COLLECTION>
          </TALLYMESSAGE>
        </REQUESTDATA>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        hierarchy = {}
        ledgers = set()
        
        if not raw_xml:
            logger.warning("Empty response for Account Hierarchy")
            return hierarchy, ledgers

        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
            for item in root.findall(".//*"):
                if item.tag in ("GROUP", "LEDGER"):
                    name = item.get("NAME") or _text(item, "NAME")
                    parent = _text(item, "PARENT")
                    if name:
                        clean_name = name.strip()
                        if parent:
                            hierarchy[clean_name] = parent.strip()
                        if item.tag == "LEDGER":
                            ledgers.add(clean_name)
            
            logger.info("Account Hierarchy: %d nodes, %d ledgers", len(hierarchy), len(ledgers))
        except ET.ParseError as exc:
            logger.error("Hierarchy XML parse error: %s", exc)

        return hierarchy, ledgers

    def fetch_cost_center_breakup(self, from_date: str, to_date: str, cost_center_name: str) -> list[LedgerBalance]:
        """
        Queries Tally's Cost Centre Breakup report DIRECTLY for a specific cost center.

        Uses COSTCENTRENAME + EXPLODEFLAG=Yes + ISDETAILED=Yes to get the proven
        accurate per-room ledger breakdown (matching the user's standalone scripts).

        Results are cached per CC name to avoid duplicate API calls within one report run.
        Only leaf-level Direct Expense / Indirect Expense ledgers are returned;
        parent group subtotal rows (e.g. 'Direct Expenses', 'Fixed Assets') are skipped.
        """
        # Initialise cache on first call
        if self._cc_alloc_cache is None:
            self._cc_alloc_cache = {}

        # Return cached result on subsequent calls for the same CC
        if cost_center_name in self._cc_alloc_cache:
            allocs = self._cc_alloc_cache[cost_center_name]
            results: list[LedgerBalance] = []
            for lname, amt in allocs.items():
                if amt != 0.0:
                    dr_cr = "Dr" if amt < 0 else "Cr"
                    results.append(LedgerBalance(ledger_name=lname, amount=abs(amt), dr_cr=dr_cr))
            return results

        logger.info("Fetching CC Breakup for: %s (%s->%s)", cost_center_name, from_date, to_date)

        payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Cost Centre Breakup</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVCURRENTCOMPANY>{self.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>{from_date}</SVFROMDATE>
          <SVTODATE>{to_date}</SVTODATE>
          <COSTCENTRENAME>{cost_center_name}</COSTCENTRENAME>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
          <ISDETAILED>Yes</ISDETAILED>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

        raw_xml = self._post(payload)
        allocs: dict[str, float] = {}

        if raw_xml:
            allocs = self._parse_cc_breakup_xml(raw_xml)

        self._cc_alloc_cache[cost_center_name] = allocs

        results = []
        for lname, amt in allocs.items():
            if amt != 0.0:
                dr_cr = "Dr" if amt < 0 else "Cr"
                results.append(LedgerBalance(ledger_name=lname, amount=abs(amt), dr_cr=dr_cr))
        return results

    # Parent group names returned by Tally as section-header rows — NOT leaf ledgers.
    # These are subtotals and must be skipped to avoid double-counting.
    _CC_PARENT_GROUPS = frozenset([
        # Top-level Tally section groups
        "Direct Expenses", "Indirect Expenses", "Fixed Assets", "Current Assets",
        "Loans & Advances (Asset)", "Capital Account", "Investments",
        "Current Liabilities", "Suspense A/c", "Profit & Loss A/c",
        "Misc. Expenses (Asset)", "Sales Accounts", "Indirect Incomes",
        # Intermediate sub-groups within Direct Expenses that appear as parent rows
        # when EXPLODEFLAG=Yes + ISDETAILED=Yes — their leaf ledgers carry the same
        # amount so including both would double-count.
        "RENT", "Salary", "Electricity",
    ])

    def _parse_cc_breakup_xml(self, raw_xml: str) -> dict[str, float]:
        """
        Parses the Cost Centre Breakup XML response.

        XML structure (one name node followed by one info node, repeating):
          <DSPACCNAME><DSPDISPNAME>Electiricty</DSPDISPNAME></DSPACCNAME>
          <DSPACCINFO>
            <DSPCLAMTA>-1374.66</DSPCLAMTA>   ← negative = Dr (expense)
          </DSPACCINFO>

        Rule:
          • Skip rows whose name is a known parent group (these are subtotals)
          • The DSPCLAMTA value is the signed closing balance:
              negative → Debit (expense) → stored as-is (negative)
              positive → Credit (income) → stored as-is (positive)
          • Empty DSPCLAMTA → skip
        """
        # Strip invalid XML chars the same way _sanitize_xml does
        clean = re.sub(
            r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]",
            "",
            raw_xml.lstrip("\ufeff"),
        )
        clean = re.sub(r"&#[xX]0*([0-8b-cB-Ce-fE-F]|1[0-9a-fA-F]);", "", clean)
        clean = re.sub(r"&#0*([0-8]|1[1-2]|1[4-9]|2[0-9]|3[0-1]);", "", clean)
        # Note: &amp; is left as-is — ET.fromstring() handles it correctly.

        allocs: dict[str, float] = {}
        current_name: str | None = None

        try:
            root = ET.fromstring(clean)
        except ET.ParseError as exc:
            logger.error("CC Breakup XML parse error: %s", exc)
            return allocs

        for elem in root:
            if elem.tag == "DSPACCNAME":
                name_node = elem.find("DSPDISPNAME")
                current_name = name_node.text.strip() if (name_node is not None and name_node.text) else None

            elif elem.tag == "DSPACCINFO" and current_name:
                # Skip parent group header rows (subtotals)
                if current_name in self._CC_PARENT_GROUPS:
                    current_name = None
                    continue

                cl_node = elem.find(".//DSPCLAMTA")
                if cl_node is not None and cl_node.text and cl_node.text.strip():
                    try:
                        val = float(cl_node.text.strip())
                        if val != 0.0:
                            # Accumulate in case the same ledger appears under multiple sub-sections
                            allocs[current_name] = allocs.get(current_name, 0.0) + val
                    except ValueError:
                        pass
                current_name = None

        return allocs

    # ------------------------------------------------------------------
    # Shared Sibling-Node Parser (Used by Trial Balance and CC Breakup)
    # ------------------------------------------------------------------

    def _parse_report_sibling_nodes(self, raw_xml: str) -> list[LedgerBalance]:
        results: list[LedgerBalance] = []
        current_name = None

        try:
            root = ET.fromstring(_sanitize_xml(raw_xml))
        except ET.ParseError as exc:
            logger.error("Report XML parse error: %s", exc)
            return []

        for elem in root.findall(".//*"):
            if elem.tag == "DSPACCNAME":
                current_name = _text(elem, "DSPDISPNAME")
            elif elem.tag == "DSPACCINFO" and current_name:
                dr_node = elem.find(".//DSPCLDRAMTA")
                cr_node = elem.find(".//DSPCLCRAMTA")
                
                # In standard Trial Balance
                dr_amt = dr_node.text.strip() if dr_node is not None and dr_node.text else ""
                cr_amt = cr_node.text.strip() if cr_node is not None and cr_node.text else ""
                
                # In Cost Centre Breakup, the tag is often just DSPCLAMTA 
                if not dr_amt and not cr_amt:
                    cl_node = elem.find(".//DSPCLAMTA")
                    cl_amt = cl_node.text.strip() if cl_node is not None and cl_node.text else ""
                    amt_str = cl_amt
                else:
                    amt_str = dr_amt if dr_amt else cr_amt
                    
                if amt_str:
                    amount, dr_cr = _parse_tally_amount(amt_str)
                    if amount != 0.0:
                        results.append(
                            LedgerBalance(ledger_name=current_name.strip(), amount=amount, dr_cr=dr_cr)
                        )
                current_name = None

        return results

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _post(self, xml_payload: str) -> str | None:
        try:
            r = self._session.post(
                self.base_url,
                data=xml_payload.encode("utf-8"),
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.text
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach Tally at {self.base_url}.\n"
                "Ensure TallyPrime is open and HTTP XML Server is enabled on port 9000."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Tally did not respond within {self.timeout}s. "
                "Check that Company 110011 is fully loaded."
            )
        except requests.HTTPError as exc:
            logger.error("Tally HTTP error: %s", exc)
            return None

    def _post_raw(self, xml_payload: str) -> bytes | None:
        """Same as _post() but returns raw bytes so callers can handle encoding themselves."""
        try:
            r = self._session.post(
                self.base_url,
                data=xml_payload.encode("utf-8"),
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.content
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot reach Tally at {self.base_url}.\n"
                "Ensure TallyPrime is open and HTTP XML Server is enabled on port 9000."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                f"Tally did not respond within {self.timeout}s. "
                "Check that Company 110011 is fully loaded."
            )
        except requests.HTTPError as exc:
            logger.error("Tally HTTP error (raw): %s", exc)
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _text(node: ET.Element, tag: str) -> str | None:
    child = node.find(tag)
    if child is not None and child.text:
        return child.text.strip() or None
    return None


def _sanitize_xml(raw: str) -> str:
    """
    Strips characters that are invalid in XML 1.0. Tally sometimes includes
    unescaped control characters in ledger names which crash strict XML parsers.
    """
    raw = raw.lstrip("\ufeff")  # strip BOM
    # XML 1.0 valid character ranges:
    # #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # We strip anything NOT in those ranges.
    clean = re.sub(
        r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]",
        "",
        raw,
    )
    # Tally sometimes escapes invalid control chars as entities (e.g. &#x04; or &#27;)
    # We must strip these or the XML parser throws "reference to invalid character number"
    # Hex: 0-8, B-C, E-1F
    clean = re.sub(r"&#[xX]0*([0-8b-cB-Ce-fE-F]|1[0-9a-fA-F]);", "", clean)
    # Decimal: 0-8, 11-12, 14-31
    clean = re.sub(r"&#0*([0-8]|1[1-2]|1[4-9]|2[0-9]|3[0-1]);", "", clean)
    return clean


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tally API smoke-test")
    p.add_argument("--host",  default="localhost")
    p.add_argument("--port",  type=int, default=9000)
    p.add_argument("--from",  dest="from_date", default="20250401")
    p.add_argument("--to",    dest="to_date",   default="20260131")
    p.add_argument("--limit", type=int, default=15)
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = _cli()
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    client = TallyAPIClient(host=args.host, port=args.port)

    print(f"\nPinging Tally at {client.base_url} …", end=" ", flush=True)
    print("✓ Connected\n" if client.ping() else "✗ No response\n")

    try:
        data = client.fetch_trial_balance(
            from_date=args.from_date, to_date=args.to_date
        )
    except (ConnectionError, TimeoutError) as exc:
        print(f"\n[ERROR] {exc}")
        raise SystemExit(1)

    if not data:
        print("[WARN] 0 ledgers returned. Check company selection and date range.")
        raise SystemExit(1)

    print(f"✓  {len(data)} active ledgers extracted from Company [{TallyAPIClient.COMPANY_ID}]\n")
    print(f"{'Ledger Name':<50} {'Dr/Cr':<5} {'Amount':>20}")
    print("─" * 78)
    for row in data[: args.limit]:
        print(f"{row['ledger_name']:<50} {row['dr_cr']:<5} {row['amount']:>20,.2f}")
    if len(data) > args.limit:
        print(f"  … and {len(data) - args.limit} more ledgers not shown.")
    print()
