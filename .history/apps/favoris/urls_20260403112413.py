"""
apps/favoris/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.favoris.views import FavoriViewSet

router = DefaultRouter()
router.register(r"favoris", FavoriViewSet, basename="favori")

urlpatterns = router.urls