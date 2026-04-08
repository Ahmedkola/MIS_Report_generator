// Cost centers in exact order matching schemas.py COST_CENTERS
const CC = [
  'JPN 202', 'Koramangala', 'EEE', 'E-City', 'Kalyan Nagar', 'Mysore',
  'Coles Park', 'Mahaveer Celese', 'Hebbal', 'CMR', 'Prestige', 'Manyata',
  'Hennur', 'Mysore Frenza', 'Kora-2', 'JPN-Hotel', 'Brigade', 'Lang Ford',
  'Viman Nagar', 'LRP', 'General', 'Total',
]

function ccRow(vals) {
  const row = {}
  CC.forEach((c, i) => { row[c] = vals[i] ?? 0 })
  return row
}

// ─── Jan-26 (current month) — values from Excel "Building Wise Data" Jan-26 block ───
const JAN26 = {
  period: '2026-01',
  rows: [
    {
      row_name: 'Gross Sales',
      cost_centers: ccRow([0, 346643, 670344, 0, 788926, 262619, 542986, 272516, 961347, 932351, 0, 680000, 318000, 142000, 198000, 254000, 286000, 124000, 164000, 136000, 215000, 6295632]),
      total: 6295632,
    },
    {
      row_name: 'Net Sales',
      cost_centers: ccRow([0, 320636, 621889, 0, 731561, 236836, 474869, 253327, 904792, 869287, 0, 629800, 294480, 131380, 183480, 235180, 264980, 114920, 151880, 125960, 199100, 5763930]),
      total: 5763930,
    },
    {
      row_name: 'Other Income',
      cost_centers: ccRow([0, 2800, 5400, 0, 6200, 2100, 4300, 2200, 7600, 7400, 0, 5400, 2500, 1100, 1600, 2000, 2300, 1000, 1300, 1100, 1700, 58000]),
      total: 58000,
    },
    {
      row_name: 'Direct Expenses',
      cost_centers: ccRow([0, -177026, -311468, -20020, -390967, -104396, -248448, -169578, -601541, -468051, 0, -312000, -145200, -64800, -90000, -116000, -131000, -56600, -74800, -62000, -98000, -3241895]),
      total: -3241895,
    },
    {
      row_name: 'Gross Profit',
      cost_centers: ccRow([0, 143610, 310420, -20020, 340593, 132440, 226421, 83749, 303251, 401236, 0, 317800, 149280, 66580, 93480, 119180, 133980, 58320, 77080, 64960, 101100, 2562035]),
      total: 2562035,
    },
    {
      row_name: 'Indirect Expenses',
      cost_centers: ccRow([0, -22137, -59018, -102842, -66481, -51421, -36879, -29383, -75285, -136223, 0, -62000, -29000, -13000, -17400, -23000, -26000, -11300, -14900, -12400, -19500, -807169]),
      total: -807169,
    },
    {
      row_name: 'EBIDTA',
      cost_centers: ccRow([0, 121473, 251403, -122862, 274112, 81019, 189542, 54366, 227966, 265013, 0, 255800, 120280, 53580, 76080, 96180, 107980, 47020, 62180, 52560, 81600, 1754866]),
      total: 1754866,
    },
    {
      row_name: 'EBIDTA %',
      cost_centers: ccRow([null, 37.9, 40.4, null, 37.5, 34.2, 39.9, 21.5, 25.2, 30.5, null, 40.6, 40.8, 40.8, 41.5, 40.9, 40.8, 40.9, 40.9, 41.7, null, 30.4]),
      total: 30.4,
    },
    {
      row_name: 'Occupancy %',
      cost_centers: ccRow([null, 82, 88, null, 79, 72, 85, 68, 91, 87, null, 84, 78, 71, 76, 80, 82, 70, 75, 73, null, 80.1]),
      total: 80.1,
    },
  ],
}

// ─── Dec-25 (previous month) — values from Excel "Building Wise Data" Dec-25 block ───
const DEC25 = {
  period: '2025-12',
  rows: [
    {
      row_name: 'Gross Sales',
      cost_centers: ccRow([0, 430627, 918362, 0, 922730, 273456, 737138, 354478, 1146642, 1140632, 0, 840000, 392000, 175000, 244000, 314000, 352000, 153000, 202000, 168000, 265000, 7829065]),
      total: 7829065,
    },
    {
      row_name: 'Net Sales',
      cost_centers: ccRow([0, 397562, 848508, 0, 858667, 244706, 649771, 327858, 1056933, 1048042, 0, 777600, 363040, 161875, 225920, 290680, 325840, 141525, 186940, 155520, 245250, 7239838]),
      total: 7239838,
    },
    {
      row_name: 'Other Income',
      cost_centers: ccRow([0, 3400, 6800, 0, 7600, 2600, 5300, 2700, 9400, 9100, 0, 6600, 3100, 1400, 1900, 2500, 2800, 1200, 1600, 1300, 2100, 71200]),
      total: 71200,
    },
    {
      row_name: 'Direct Expenses',
      cost_centers: ccRow([-1783, -190137, -320094, -14832, -486497, -64797, -227939, -161955, -500961, -420832, 0, -385000, -179200, -79900, -111800, -143800, -161600, -70300, -92800, -77200, -121700, -3832327]),
      total: -3832327,
    },
    {
      row_name: 'Gross Profit',
      cost_centers: ccRow([-1783, 207426, 528414, -14832, 372170, 179909, 421832, 165903, 555972, 627209, 0, 392600, 183840, 81975, 114120, 146880, 164240, 71225, 94140, 78320, 123550, 3478711]),
      total: 3478711,
    },
    {
      row_name: 'Indirect Expenses',
      cost_centers: ccRow([0, -13474, -35958, -62877, -40483, -31839, -22550, -17965, -44912, -81539, 0, -76400, -35700, -16000, -21400, -28300, -32000, -13900, -18400, -15300, -24000, -633627]),
      total: -633627,
    },
    {
      row_name: 'EBIDTA',
      cost_centers: ccRow([-1783, 193952, 492456, -77710, 331687, 148070, 399282, 147938, 511059, 545670, 0, 316200, 148140, 65975, 92720, 118580, 132240, 57325, 75740, 63020, 99550, 3261911]),
      total: 3261911,
    },
    {
      row_name: 'EBIDTA %',
      cost_centers: ccRow([null, 48.8, 58.0, null, 38.6, 60.5, 61.5, 45.1, 48.4, 52.1, null, 40.7, 40.8, 40.8, 41.0, 40.8, 40.6, 40.5, 40.5, 40.5, null, 45.1]),
      total: 45.1,
    },
    {
      row_name: 'Occupancy %',
      cost_centers: ccRow([null, 91, 96, null, 88, 80, 94, 76, 98, 95, null, 93, 86, 78, 83, 88, 91, 77, 83, 80, null, 88.4]),
      total: 88.4,
    },
  ],
}

// ─── YTD Apr-25 to Jan-26 ───
const YTD_APR_JAN = {
  period: '2025-04_2026-01',   // special token for YTD
  label: 'YTD: Apr-25 to Jan-26',
  rows: [
    {
      row_name: 'Gross Sales',
      cost_centers: ccRow([18400, 3214820, 6182340, 34852, 7329800, 2418974, 5084716, 2546544, 8972034, 8712288, 0, 6348000, 2964000, 1323000, 1844000, 2373000, 2659000, 1157000, 1528000, 1267000, 2002000, 67782768]),
      total: 67782768,
    },
    {
      row_name: 'Net Sales',
      cost_centers: ccRow([17020, 2973608, 5718764, 32238, 6780065, 2237450, 4703562, 2355054, 8298751, 8059467, 0, 5871840, 2742240, 1223775, 1704960, 2194905, 2459580, 1070225, 1413560, 1171975, 1851850, 62680889]),
      total: 62680889,
    },
    {
      row_name: 'Other Income',
      cost_centers: ccRow([0, 28420, 54700, 0, 62800, 21300, 43500, 22300, 76900, 74900, 0, 54600, 25300, 11100, 16100, 20200, 23200, 10100, 13100, 11100, 17200, 587820]),
      total: 587820,
    },
    {
      row_name: 'Direct Expenses',
      cost_centers: ccRow([-1783, -1688326, -2904982, -141748, -4317717, -970344, -2317862, -1582874, -5627018, -4372574, 0, -2914000, -1355200, -604200, -846800, -1089000, -1219400, -530600, -700800, -583400, -923700, -34591328]),
      total: -34591328,
    },
    {
      row_name: 'Gross Profit',
      cost_centers: ccRow([15237, 1285282, 2813782, -109510, 2462348, 1267106, 2386700, 772480, 2672733, 3687793, 0, 2957840, 1387340, 619675, 857260, 1106105, 1240180, 539725, 712760, 588575, 927350, 28691381]),
      total: 28691381,
    },
    {
      row_name: 'Indirect Expenses',
      cost_centers: ccRow([0, -205640, -553898, -950762, -633018, -489762, -350802, -279668, -717010, -1296642, 0, -590800, -275700, -123600, -165600, -219200, -247500, -107700, -141900, -118100, -185900, -7653502]),
      total: -7653502,
    },
    {
      row_name: 'EBIDTA',
      cost_centers: ccRow([15237, 1079642, 2259884, -1060272, 1829330, 777344, 2035898, 492812, 1955723, 2391151, 0, 2367040, 1111640, 496075, 691660, 886905, 992680, 432025, 570860, 470475, 741450, 21037879]),
      total: 21037879,
    },
    {
      row_name: 'EBIDTA %',
      cost_centers: ccRow([null, 36.3, 39.5, null, 27.0, 34.7, 43.3, 20.9, 23.6, 29.7, null, 40.3, 40.6, 40.5, 40.6, 40.4, 40.4, 40.4, 40.4, 40.1, null, 33.6]),
      total: 33.6,
    },
    {
      row_name: 'Occupancy %',
      cost_centers: ccRow([null, 85, 91, null, 83, 74, 88, 70, 94, 90, null, 87, 81, 74, 79, 83, 85, 73, 78, 76, null, 83.2]),
      total: 83.2,
    },
  ],
}

export function getMockData(from = '20250401', to = '20260131') {
  return {
  status: 'success',
  data: {
    company_id: '110011',
    company_name: 'Unreal Estate Habitat Private Limited',
    period_start: from,
    period_end: to,

    consolidated_pnl: {
      report_type: 'pnl',
      period: '20250401 to 20260131',
      company: 'Unreal Estate Habitat Private Limited',
      sections: {
        Income: {
          'Sales Accounts': {
            group_name: 'Sales Accounts',
            items: {
              Koramangala: { name: 'Koramangala', amount: 3214820, breakdown: null },
              EEE: { name: 'EEE', amount: 6182340, breakdown: null },
              'Kalyan Nagar': { name: 'Kalyan Nagar', amount: 7329800, breakdown: null },
              Mysore: { name: 'Mysore', amount: 2418974, breakdown: null },
              'Coles Park': { name: 'Coles Park', amount: 5084716, breakdown: null },
              'Mahaveer Celese': { name: 'Mahaveer Celese', amount: 2546544, breakdown: null },
              Hebbal: { name: 'Hebbal', amount: 8972034, breakdown: null },
              CMR: { name: 'CMR', amount: 8712288, breakdown: null },
              Manyata: { name: 'Manyata', amount: 6348000, breakdown: null },
              Hennur: { name: 'Hennur', amount: 2964000, breakdown: null },
              Others: { name: 'Others', amount: 14009252, breakdown: null },
            },
            subtotal: 67782768,
          },
          'Indirect Incomes': {
            group_name: 'Indirect Incomes',
            items: {
              'Interest Income': { name: 'Interest Income', amount: 310000, breakdown: null },
              'Miscellaneous Income': { name: 'Miscellaneous Income', amount: 195000, breakdown: null },
              'Late Fee / Penalty': { name: 'Late Fee / Penalty', amount: 82820, breakdown: null },
            },
            subtotal: 587820,
          },
        },
        Expenses: {
          'Direct Expenses': {
            group_name: 'Direct Expenses',
            items: {
              Consumables: { name: 'Consumables', amount: -3480000, breakdown: null },
              Laundry: { name: 'Laundry', amount: -2105432, breakdown: null },
              'Housekeeping Charges': { name: 'Housekeeping Charges', amount: -4820000, breakdown: null },
              Maintenance: { name: 'Maintenance', amount: -3950000, breakdown: null },
              'Electricity Charges': { name: 'Electricity Charges', amount: -5480000, breakdown: null },
              'Rent Paid': { name: 'Rent Paid', amount: -8120000, breakdown: null },
              'OTA Commission': { name: 'OTA Commission', amount: -2340000, breakdown: null },
              'Pillow/Cover': { name: 'Pillow/Cover', amount: -839365, breakdown: null },
              'Other Direct': { name: 'Other Direct', amount: -3456531, breakdown: null },
            },
            subtotal: -34591328,
          },
          'Indirect Expenses': {
            group_name: 'Indirect Expenses',
            items: {
              'Salary & Wages': { name: 'Salary & Wages', amount: -3840000, breakdown: null },
              'Office Expenses': { name: 'Office Expenses', amount: -620000, breakdown: null },
              'Professional Fees': { name: 'Professional Fees', amount: -480000, breakdown: null },
              'Travel & Conveyance': { name: 'Travel & Conveyance', amount: -310000, breakdown: null },
              'Bank Charges': { name: 'Bank Charges', amount: -145000, breakdown: null },
              Advertisement: { name: 'Advertisement', amount: -540000, breakdown: null },
              Depreciation: { name: 'Depreciation', amount: -720000, breakdown: null },
              'Other Indirect': { name: 'Other Indirect', amount: -998502, breakdown: null },
            },
            subtotal: -7653502,
          },
        },
      },
      summary: {
        total_income: 68370588,
        total_expenses: -42244830,
        net_profit: 26125758,
      },
    },

    balance_sheet: {
      report_type: 'balance_sheet',
      period: '20250401 to 20260131',
      company: 'Unreal Estate Habitat Private Limited',
      sections: {
        Assets: {
          'Fixed Assets': {
            group_name: 'Fixed Assets',
            items: {
              'Furniture & Fixtures': { name: 'Furniture & Fixtures', amount: 8420000 },
              'Computer & Peripherals': { name: 'Computer & Peripherals', amount: 1850000 },
              'Air Conditioners': { name: 'Air Conditioners', amount: 3200000 },
              'Kitchen Equipment': { name: 'Kitchen Equipment', amount: 980000 },
            },
            subtotal: 14450000,
          },
          'Current Assets': {
            group_name: 'Current Assets',
            items: {
              'Cash in Hand': { name: 'Cash in Hand', amount: 325000 },
              'Bank Accounts': { name: 'Bank Accounts', amount: 12480000 },
              'Sundry Debtors': { name: 'Sundry Debtors', amount: 4820000 },
              'Security Deposits': { name: 'Security Deposits', amount: 6750000 },
              'Prepaid Expenses': { name: 'Prepaid Expenses', amount: 840000 },
            },
            subtotal: 25215000,
          },
        },
        'Equity & Liabilities': {
          'Capital Account': {
            group_name: 'Capital Account',
            items: {
              'Share Capital': { name: 'Share Capital', amount: 10000000 },
              'Retained Earnings': { name: 'Retained Earnings', amount: 8210000 },
              'Current Year Profit': { name: 'Current Year Profit', amount: 26125758 },
            },
            subtotal: 44335758,
          },
          'Loans & Borrowings': {
            group_name: 'Loans & Borrowings',
            items: {
              'Term Loans': { name: 'Term Loans', amount: -12500000 },
              'Directors Loans': { name: 'Directors Loans', amount: -4800000 },
            },
            subtotal: -17300000,
          },
          'Current Liabilities': {
            group_name: 'Current Liabilities',
            items: {
              'Sundry Creditors': { name: 'Sundry Creditors', amount: -6820000 },
              'TDS Payable': { name: 'TDS Payable', amount: -480000 },
              'GST Payable': { name: 'GST Payable', amount: -1240000 },
              'Salary Payable': { name: 'Salary Payable', amount: -620000 },
            },
            subtotal: -9160000,
          },
        },
      },
      summary: {
        total_assets: 39665000,
        total_liabilities: 26460000,
        net_worth: 13205000,
      },
    },

    // matrix_pnl: one entry for the selected period
    matrix_pnl: [{ ...YTD_APR_JAN, period: `${from}_${to}`, label: null }],

    // unit_wise: not included in mock — page will show EmptyState
    unit_wise: null,

    cash_flow_statement: {},
  },
 }
}
