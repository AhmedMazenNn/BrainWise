from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'customer_name',
        'customer_phone',
        'cash_amount',
        'priority',
        'status',
        'assigned_driver',
        'created_at',
        'delivered_at',
    ]
    list_filter = ['status', 'priority', 'assigned_driver']
    search_fields = ['customer_name', 'customer_phone', 'address']
    ordering = ['-created_at']
    raw_id_fields = ['assigned_driver']
    readonly_fields = ['created_at', 'updated_at']
