"""
apps/niveau/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.niveau.views import NiveauViewSet

router = DefaultRouter()
router.register(r"niveaux", NiveauViewSet, basename="niveau")

urlpatterns = router.urls