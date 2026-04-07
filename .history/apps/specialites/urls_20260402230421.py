"""
apps/specialites/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.specialites.views import SpecialiteViewSet

router = DefaultRouter()
router.register(r"specialites", SpecialiteViewSet, basename="specialite")

urlpatterns = router.urls