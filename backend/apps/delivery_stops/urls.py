from rest_framework.routers import SimpleRouter

from .views import DeliveryStopViewSet

router = SimpleRouter()
router.register('', DeliveryStopViewSet, basename='delivery-stop')

urlpatterns = router.urls
