"""
apps/annee_academique/urls.py
"""
from rest_framework.routers import DefaultRouter

from apps.annee_academique.views import AnneeAcademiqueViewSet

router = DefaultRouter()
router.register(r"annees-academiques", AnneeAcademiqueViewSet, basename="annee-academique")

urlpatterns = router.urls
