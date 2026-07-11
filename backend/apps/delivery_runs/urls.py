from rest_framework.routers import SimpleRouter

from .views import DeliveryRunViewSet

router = SimpleRouter()
router.register('', DeliveryRunViewSet, basename='delivery-run')

urlpatterns = router.urls
