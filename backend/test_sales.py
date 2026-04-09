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
          <GROUPNAME>Sales Accounts</GROUPNAME>
          <EXPLODEFLAG>Yes</EXPLODEFLAG>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""

res = client._post(payload)
items = client._parse_pnl_group_xml(res)
print(f"Total items: {len(items)}")
total = sum(i['amount'] for i in items)
print(f"Total sum: {total:,.2f}")
for i in items:
    print(f"  {i['name']}: {i['amount']:,.2f}")
