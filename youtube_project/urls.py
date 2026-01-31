# tu_proyecto/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('videos.urls')),  # ✅ Incluye las URLs de tu app videos
]