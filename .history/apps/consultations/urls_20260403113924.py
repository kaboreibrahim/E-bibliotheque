"""
apps/consultations/urls.py
"""
from rest_framework.routers import DefaultRouter
from apps.consultations.views import ConsultationViewSet

router = DefaultRouter()
router.register(r"consultations", ConsultationViewSet, basename="consultation")

urlpatterns = router.urls