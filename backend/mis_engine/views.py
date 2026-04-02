from django.http import JsonResponse
from mis_engine.reports.pnl_bs import StandardReportProcessor
from mis_engine.reports.matrix import MatrixReportProcessor
from mis_engine.reports.unit import UnitReportProcessor

def _get_dates(request):
    from_date = request.GET.get('from', '20250401')
    to_date   = request.GET.get('to',   '20260131')
    if len(from_date) != 8 or not from_date.isdigit():
        raise ValueError("Invalid 'from' date. Expected YYYYMMDD.")
    if len(to_date) != 8 or not to_date.isdigit():
        raise ValueError("Invalid 'to' date. Expected YYYYMMDD.")
    return from_date, to_date

def _handle_error(e):
    import traceback
    return JsonResponse({
        "status": "error", 
        "message": str(e),
        "traceback": traceback.format_exc()
    }, status=500)

def _build_payload(processor, data_key, data):
    return {
        "status": "success",
        "data": {
            "company_id": processor.api.COMPANY_ID,
            "company_name": processor.api.COMPANY_ID,
            "period_start": processor.from_date,
            "period_end": processor.to_date,
            data_key: data,
        }
    }

def get_pnl(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = StandardReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "consolidated_pnl", reports["pnl"]))
    except Exception as e:
        return _handle_error(e)

def get_balance_sheet(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = StandardReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "balance_sheet", reports["balance_sheet"]))
    except Exception as e:
        return _handle_error(e)

def get_matrix(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = MatrixReportProcessor(from_date, to_date)
        reports = processor.process()
        return JsonResponse(_build_payload(processor, "matrix_pnl", reports))
    except Exception as e:
        return _handle_error(e)

def get_unit_wise(request):
    try:
        from_date, to_date = _get_dates(request)
        processor = UnitReportProcessor(from_date, to_date)
        report = processor.process()
        return JsonResponse(_build_payload(processor, "unit_wise", report))
    except Exception as e:
        return _handle_error(e)
