from django.contrib import admin

from .models import DeliveryRun


@admin.register(DeliveryRun)
class DeliveryRunAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'driver',
        'status',
        'total_cash_collected',
        'started_at',
        'completed_at',
        'cash_banked_at',
        'created_at',
    ]
    list_filter = ['status', 'driver']
    search_fields = ['driver__name', 'driver__phone_number']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['driver']
    readonly_fields = ['created_at', 'updated_at']
