from django.contrib import admin

from .models import Driver


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'phone_number',
        'status',
        'active',
        'max_stops_per_run',
        'created_at',
    ]
    list_filter = ['status', 'active']
    search_fields = ['name', 'phone_number']
    ordering = ['-created_at']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
