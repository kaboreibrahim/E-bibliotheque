"""
apps/filiere/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.filiere.views import FiliereViewSet

router = DefaultRouter()
router.register(r"filieres", FiliereViewSet, basename="filiere")

urlpatterns = router.urls