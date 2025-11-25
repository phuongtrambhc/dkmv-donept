from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
import xlwt
from django.shortcuts import render

# Import Models
from orders.models import Order

# Import các hàm xử lý dữ liệu từ file utils.py
from .utils import (
    get_kpi_data,
    get_chart_data,
    get_inventory_data,
    get_recent_orders_json,
    get_notifications,
    get_recent_customers_json,
)

# --- SỬA LỖI ATTRIBUTE ERROR TẠI ĐÂY ---
def is_admin(user):
    # Model của bạn dùng 'is_superadmin', không phải 'is_superuser'
    return user.is_superadmin or user.is_staff


@login_required(login_url='login')
@user_passes_test(is_admin)
def statistical_reports(request):
    # --- 1. LẤY THAM SỐ TỪ URL (SỬA LỖI FILTER) ---
    # Mặc định là '7days' nếu không có tham số
    period = request.GET.get('period', '7days')

    # --- 2. TRUYỀN PERIOD VÀO CÁC HÀM UTILS ---
    kpi_data = get_kpi_data(period)  # Truyền period vào đây
    chart_data = get_chart_data(period)  # Truyền period vào đây

    inventory_data = get_inventory_data()
    recent_orders = get_recent_orders_json()
    notifications = get_notifications()
    recent_customers = get_recent_customers_json()

    # Tạo label hiển thị trên nút bấm cho đẹp (Optional)
    period_label = {
        '7days': 'Last 7 Days',
        'this_month': 'This Month',
        'this_year': 'This Year',
        'last_30_days': 'Last 30 Days'
    }.get(period, 'Last 7 Days')

    context = {
        **kpi_data,
        **chart_data,
        'inventory_data': inventory_data,
        'latest_orders_json': recent_orders,
        'latest_customers_json': recent_customers,
        'notifications': notifications,
        'notif_count': len(notifications),

        # --- 3. TRUYỀN BIẾN NÀY ĐỂ HIỂN THỊ LABEL TRÊN GIAO DIỆN ---
        'current_period': period_label,
    }

    return render(request, 'reports/statistical_reports.html', context)


# Hàm xuất Excel (Giữ nguyên)
@login_required(login_url='login')
@user_passes_test(is_admin)
def export_orders_xls(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="orders_report.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Orders Report')

    font_style = xlwt.XFStyle()
    font_style.font.bold = True

    columns = ['Order Number', 'Customer', 'Phone', 'Email', 'City', 'Total ($)', 'Status', 'Date']
    for col_num in range(len(columns)):
        ws.write(0, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()

    rows = Order.objects.filter(is_ordered=True).order_by('-created_at').values_list(
        'order_number', 'first_name', 'phone', 'email', 'city', 'order_total', 'status', 'created_at'
    )

    for row_num, row in enumerate(rows):
        for col_num, val in enumerate(row):
            if col_num == 7:
                val = val.strftime('%d/%m/%Y %H:%M')
            ws.write(row_num + 1, col_num, str(val), font_style)

    wb.save(response)
    return response

