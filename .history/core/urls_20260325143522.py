from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger configuration
schema_view = get_schema_view(
    openapi.Info(
        title="E-BIBLIO API",
        default_version='v1',
        description="API documentation for E-BIBLIO application",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@ebiblio.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
  
urlpatterns = [
    path('admin/', admin.site.urls),

    # API Documentation
    path('docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
