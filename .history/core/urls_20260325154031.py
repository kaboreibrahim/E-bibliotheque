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
    # API Endpoints for user management
    path('users/',include('apps.users.urls')),  # API Endpoints for user management

    # API Endpoints for UE management
    path('ue/',include('apps.ue.urls')),  # API Endpoints for UE management

    # API Endpoints for Specialite management
    path('specialites/',include('apps.specialites.urls')),  # API Endpoints for Specialite management

    # API Endpoints for Niveau management
    path('niveau/',include('apps.niveau.urls')),  # API Endpoints for Niveau management

    # API Endpoints for History management
    path('history/',include('apps.history.urls')),  # API Endpoints for History management

    # API Endpoints for Filiere management
    path('filiere/',include('apps.filiere.urls')),  # API Endpoints for Filiere management

    # API Endpoints for Favori management
    path('favoris/',include('apps.favoris.urls')),  # API Endpoints for Favori management

    # API Endpoints for Document management
    path('documents/',include('apps.documents.urls')),  # API Endpoints for Document management

    # API Endpoints for Consultation management
    path('consultations/',include('apps.consulations.urls')),  # API Endpoints for Consultation management


    
    
    path('api/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)