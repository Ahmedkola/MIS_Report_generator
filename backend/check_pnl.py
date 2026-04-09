import sys
from tally_api import TallyAPIClient

client = TallyAPIClient()
payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Group Summary</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{client.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVFROMDATE>20250401</SVFROMDATE>
          <SVTODATE>20260131</SVTODATE>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <GROUPNAME>Direct Expenses</GROUPNAME>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

res = client._post(payload)
with open("group_dump.xml", "w", encoding="utf-8") as f:
    f.write(res)
print("Dumped group_dump.xml. Length:", len(res))
