"""
URL configuration for solar_simulator project.
Configuration des URLs principales du projet.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # 🆕 Routes du frontend (à la racine)
    # Donc: localhost:8000/ → home
    #       localhost:8000/simulation/ → formulaire
    #       localhost:8000/simulation/xxx/resultats/ → résultats
    path('', include('frontend.urls', namespace='frontend')),
    
    # 🆕 APIs REST (pour futur)
    path('api/', include('rest_framework.urls')),
    
    # 🆕 Health check (pour monitoring/devops)
    # GET /health/ → {'status': 'ok'}
    path('health/', lambda r: JsonResponse({'status': 'ok'})),
]

# 🆕 En développement, servir les fichiers uploadés
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
