from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/drivers/', include('apps.drivers.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/delivery-runs/', include('apps.delivery_runs.urls')),
    path('api/delivery-stops/', include('apps.delivery_stops.urls')),
]
