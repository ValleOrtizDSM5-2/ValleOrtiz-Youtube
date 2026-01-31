# videos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Página principal
    path('', views.inicio, name='inicio'),
    
    # Rutas de YouTube OAuth
    path('youtube/login/', views.youtube_login, name='youtube_login'),
    path('oauth/callback/', views.youtube_callback, name='youtube_callback'),
    
    # Dashboard y funcionalidades de YouTube
    path('youtube/dashboard/', views.youtube_dashboard, name='youtube_dashboard'),
    path('youtube/estadisticas/', views.youtube_estadisticas, name='youtube_estadisticas'),
    path('youtube/logout/', views.youtube_logout, name='youtube_logout'),
    path('youtube/refresh/', views.refresh_youtube_token, name='refresh_youtube_token'),
    path('youtube/status/', views.check_auth_status, name='check_auth_status'),
    
    # Funcionalidades de videos
    path('youtube/buscar/', views.buscar_videos, name='buscar_videos'),
    path('youtube/subir/', views.subir_video, name='subir_video'),
    path('youtube/subir/ajax/', views.procesar_subida_ajax, name='procesar_subida_ajax'),
    path('youtube/subir/estado/<int:video_id>/', views.estado_subida_video, name='estado_subida'),
    
    # IMPORTANTE: Cambié el nombre para evitar conflicto
    path('youtube/mis-subidos/', views.mis_videos_subidos, name='mis_videos_subidos'),
    
    # Rutas para la biblioteca personal de videos
    path('videos/mis-videos/', views.mis_videos, name='mis_videos'),
    path('videos/detalle/<int:video_id>/', views.detalle_video, name='detalle_video'),
    path('videos/actualizar/<int:video_id>/', views.actualizar_estadisticas_video, name='actualizar_estadisticas_video'),
    path('videos/favorito/<int:video_id>/', views.toggle_favorito_video, name='toggle_favorito_video'),
    path('videos/guardar-notas/<int:video_id>/', views.guardar_notas_video, name='guardar_notas_video'),
    path('videos/eliminar/<int:video_id>/', views.eliminar_video, name='eliminar_video'),
    # URLs NUEVAS para videos guardados
    path('videos/guardar/', views.guardar_video_busqueda, name='guardar_video'),
    path('mis-videos/', views.mis_videos_guardados, name='mis_videos'),
    path('video/<int:video_id>/', views.detalle_video_guardado, name='detalle_video'),
    path('video/actualizar/<int:video_id>/', views.actualizar_video_guardado, name='actualizar_video'),
    path('video/favorito/<int:video_id>/', views.toggle_favorito_video_guardado, name='toggle_favorito_video'),
    path('video/eliminar/<int:video_id>/', views.eliminar_video_guardado, name='eliminar_video'),
    path('video/notas/<int:video_id>/', views.guardar_notas_video_guardado, name='guardar_notas_video'),
    
    # URLs para el modelo Video original (compatibilidad)
    path('videos/', views.mis_videos, name='mis_videos_original'),
    path('videos/<int:video_id>/', views.detalle_video, name='detalle_video_original'),
    path('videos/actualizar-estadisticas/<int:video_id>/', views.actualizar_estadisticas_video, name='actualizar_estadisticas_video'),
]