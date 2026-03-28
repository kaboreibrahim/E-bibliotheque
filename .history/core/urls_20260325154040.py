from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

import specialites

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

    # API Endpoints
    path('users/',include('apps.users.urls')),
    path('ue/',include('apps.ue.urls')),
    path('specialites/',include('apps.specialites.urls')),
    path('niveau/',include('apps.niveau.urls')),
    path('history/',include('apps.history.urls')),
    path('filiere/',include('apps.filiere.urls')),
    path('favoris/',include('apps.favoris.urls')),
    path('documents/',include('apps.documents.urls')),
    path('consultations/',include('apps.consulations.urls')),


    
    
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)