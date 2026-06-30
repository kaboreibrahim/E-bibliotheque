"""
apps/ue/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.ue.views import UEViewSet, ECUEViewSet

router = DefaultRouter()
router.register(r"ues",   UEViewSet,   basename="ue")
router.register(r"ecues", ECUEViewSet, basename="ecue")

urlpatterns = router.urls