from rest_framework.routers import DefaultRouter

from apps.documents.views import DocumentViewSet, TypeDocumentViewSet

router = DefaultRouter()
router.register(r"types", TypeDocumentViewSet, basename="document-type")
router.register(r"", DocumentViewSet, basename="document")

urlpatterns = router.urls
