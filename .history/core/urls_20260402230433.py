from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from apps.users.urls import bibliothecaire_urlpatterns, etudiant_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),


    path('api/schema/', SpectacularAPIView.as_view(),                        name='schema'),
    path('api/filieres/', include('apps.filiere.urls')),
    path('api/niveaux/', include('apps.niveau.urls')),
    path('api/specialites/', include('apps.specialites.urls')),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'),   name='swagger-ui'),
    path('api/redoc/',  SpectacularRedocView.as_view(url_name='schema'),     name='redoc'),
    path('api/auth/',   include('apps.users.urls')),
    path('api/etudiants/', include((etudiant_urlpatterns, 'users'), namespace='etudiants')),
    path('api/bibliothecaires/', include((bibliothecaire_urlpatterns, 'users'), namespace='bibliothecaires')),
]

# Media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
