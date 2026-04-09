from mis_engine.reports.pnl_bs import StandardReportProcessor

proc = StandardReportProcessor('20250401', '20260131')
r = proc.process()

print("\n=== P&L SECTIONS ===")
for sec, groups in r['pnl']['sections'].items():
    for grp, gdata in groups.items():
        print(f"  [{sec}] {grp}: subtotal={gdata['subtotal']:,.2f}")
        for name, item in list(gdata['items'].items())[:4]:
            print(f"    {name}: {item['amount']:,.2f}")

print("\n=== P&L SUMMARY ===")
for k, v in r['pnl']['summary'].items():
    print(f"  {k}: {v:,.2f}")
