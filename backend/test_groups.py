import sys
import xml.etree.ElementTree as ET
from tally_api import TallyAPIClient

client = TallyAPIClient()
payload = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Accounts</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{client.COMPANY_ID}</SVCURRENTCOMPANY>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
        <REQUESTDATA>
          <TALLYMESSAGE xmlns:UDF="TallyUDF">
            <COLLECTION ISMODIFY="No">
              <TYPE>Group</TYPE>
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

res = client._post(payload)

root = ET.fromstring(res)
for group in root.findall(".//GROUP"):
    name = group.get("NAME") or ""
    parent_node = group.find("PARENT")
    parent = parent_node.text if parent_node is not None else ""
    print(f"Group: {name} -> Parent: {parent}")
