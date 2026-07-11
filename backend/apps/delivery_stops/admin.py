from django.contrib import admin

from .models import DeliveryStop


@admin.register(DeliveryStop)
class DeliveryStopAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'delivery_run',
        'order',
        'stop_sequence',
        'customer_name',
        'status',
        'cash_amount',
        'delivered_at',
        'created_at',
    ]
    list_filter = ['status', 'delivery_run']
    search_fields = ['customer_name', 'address', 'delivery_run__driver__name']
    ordering = ['stop_sequence']
    date_hierarchy = 'created_at'
    raw_id_fields = ['delivery_run', 'order']
    readonly_fields = ['customer_name', 'address', 'cash_amount', 'created_at', 'updated_at']
