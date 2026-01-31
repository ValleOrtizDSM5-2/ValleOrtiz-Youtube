# videos/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    YouTubeAccount, YouTubeVideo, YouTubeAnalytics, 
    OAuthErrorLog, Video, Playlist
)

# ============================================
# ADMIN PARA YouTubeAccount
# ============================================
@admin.register(YouTubeAccount)
class YouTubeAccountAdmin(admin.ModelAdmin):
    list_display = ('nombre_canal', 'user', 'suscriptores', 'videos_publicados', 
                   'token_valido', 'fecha_vinculacion', 'acciones')
    list_filter = ('monitoreo_activo', 'fecha_vinculacion')
    search_fields = ('nombre_canal', 'youtube_id', 'user__username', 'email')
    readonly_fields = ('youtube_id', 'fecha_vinculacion', 'ultima_actualizacion', 
                      'token_info', 'channel_link')
    fieldsets = (
        ('Información del Canal', {
            'fields': ('user', 'youtube_id', 'nombre_canal', 'email', 
                      'foto_perfil', 'descripcion_canal', 'channel_link')
        }),
        ('Tokens OAuth', {
            'fields': ('token_info', 'access_token_preview', 'refresh_token_preview',
                      'token_expira'),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': ('suscriptores', 'videos_publicados', 'vistas_totales')
        }),
        ('Configuración', {
            'fields': ('monitoreo_activo', 'frecuencia_actualizacion', 
                      'url_canal'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('fecha_vinculacion', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def token_valido(self, obj):
        if obj.esta_autenticado():
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Válido</span><br>'
                '<small>{}</small>', 
                obj.tiempo_restante_token()
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Expirado</span>'
        )
    token_valido.short_description = 'Token'
    
    def token_info(self, obj):
        if obj.token_expira:
            return f"Expira: {obj.token_expira.strftime('%d/%m/%Y %H:%M')}"
        return "Sin fecha de expiración"
    token_info.short_description = 'Información del Token'
    
    def access_token_preview(self, obj):
        if obj.access_token:
            return f"{obj.access_token[:30]}..."
        return "No disponible"
    access_token_preview.short_description = 'Access Token (preview)'
    
    def refresh_token_preview(self, obj):
        if obj.refresh_token:
            return f"{obj.refresh_token[:30]}..."
        return "No disponible"
    refresh_token_preview.short_description = 'Refresh Token (preview)'
    
    def channel_link(self, obj):
        if obj.youtube_id:
            url = f"https://www.youtube.com/channel/{obj.youtube_id}"
            return format_html(
                '<a href="{}" target="_blank" style="background: #FF0000; color: white; '
                'padding: 5px 10px; border-radius: 4px; text-decoration: none;">'
                '▶️ Ver Canal en YouTube</a>',
                url
            )
        return "No disponible"
    channel_link.short_description = 'Enlace al Canal'
    
    def acciones(self, obj):
        links = []
        if obj.youtube_id:
            # Link para ver videos del canal
            videos_url = reverse('admin:videos_youtubevideo_changelist') + f'?q={obj.youtube_id}'
            links.append(f'<a href="{videos_url}">📹 Videos</a>')
            
            # Link para ver analytics
            analytics_url = reverse('admin:videos_youtubeanalytics_changelist') + f'?q={obj.youtube_id}'
            links.append(f'<a href="{analytics_url}">📊 Analytics</a>')
        
        return format_html(' | '.join(links))
    acciones.short_description = 'Acciones'

# ============================================
# ADMIN PARA YouTubeVideo
# ============================================
@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'youtube_account', 'vistas', 'likes', 
                   'fecha_publicacion', 'video_link', 'estado')
    list_filter = ('estado', 'monitoreo_activo', 'fecha_publicacion')
    search_fields = ('titulo', 'youtube_video_id', 'youtube_account__nombre_canal')
    readonly_fields = ('youtube_video_id', 'fecha_publicacion', 'fecha_subida', 
                      'video_links', 'thumbnail_preview', 'duracion_formateada_display')
    fieldsets = (
        ('Información Básica', {
            'fields': ('youtube_account', 'titulo', 'descripcion', 'etiquetas')
        }),
        ('Identificación YouTube', {
            'fields': ('youtube_video_id', 'video_links', 'thumbnail_preview'),
            'classes': ('collapse',)
        }),
        ('Medios', {
            'fields': ('thumbnail_default', 'thumbnail_medium', 
                      'thumbnail_high', 'thumbnail_maxres')
        }),
        ('Detalles Técnicos', {
            'fields': ('duracion_segundos', 'duracion_formateada_display', 
                      'categoria_id', 'estado'),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': ('vistas', 'likes', 'dislikes', 'comentarios', 'favoritos')
        }),
        ('Metadatos', {
            'fields': ('fecha_publicacion', 'fecha_subida', 
                      'ultima_actualizacion', 'monitoreo_activo'),
            'classes': ('collapse',)
        }),
    )
    
    def video_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" style="background: #FF0000; color: white; '
            'padding: 3px 8px; border-radius: 3px; text-decoration: none; font-size: 12px;">'
            '▶️ Ver</a>',
            obj.get_video_url()
        )
    video_link.short_description = 'Video'
    
    def video_links(self, obj):
        return format_html('''
            <div style="margin-bottom: 10px;">
                <a href="{}" target="_blank" style="background: #FF0000; color: white; 
                   padding: 8px 15px; border-radius: 4px; text-decoration: none; 
                   margin-right: 10px; display: inline-block;">
                    ▶️ Ver en YouTube
                </a>
                <a href="{}" target="_blank" style="background: #333; color: white; 
                   padding: 8px 15px; border-radius: 4px; text-decoration: none; 
                   display: inline-block;">
                    📺 Embed
                </a>
            </div>
            <div><strong>ID:</strong> {}</div>
        ''', obj.get_video_url(), obj.get_embed_url(), obj.youtube_video_id)
    video_links.short_description = 'Enlaces del Video'
    
    def thumbnail_preview(self, obj):
        if obj.thumbnail_medium:
            return format_html(
                '<img src="{}" style="max-width: 200px; border-radius: 8px; border: 2px solid #ddd;">',
                obj.thumbnail_medium
            )
        return "Sin thumbnail"
    thumbnail_preview.short_description = 'Vista previa'
    
    def duracion_formateada_display(self, obj):
        return obj.duracion_formateada()
    duracion_formateada_display.short_description = 'Duración'

# ============================================
# ADMIN PARA YouTubeAnalytics
# ============================================
@admin.register(YouTubeAnalytics)
class YouTubeAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('youtube_account', 'fecha_registro', 'suscriptores', 
                   'vistas_totales', 'crecimiento_suscriptores', 'crecimiento_vistas')
    list_filter = ('fecha_registro', 'youtube_account')
    search_fields = ('youtube_account__nombre_canal',)
    readonly_fields = ('fecha_registro',)
    date_hierarchy = 'fecha_registro'
    
    def crecimiento_suscriptores_display(self, obj):
        if obj.crecimiento_suscriptores > 0:
            return format_html(
                '<span style="color: green;">+{}</span>',
                obj.crecimiento_suscriptores
            )
        elif obj.crecimiento_suscriptores < 0:
            return format_html(
                '<span style="color: red;">{}</span>',
                obj.crecimiento_suscriptores
            )
        return "0"
    crecimiento_suscriptores_display.short_description = 'Crecimiento'

# ============================================
# ADMIN PARA OAuthErrorLog
# ============================================
@admin.register(OAuthErrorLog)
class OAuthErrorLogAdmin(admin.ModelAdmin):
    list_display = ('tipo_error', 'usuario', 'fecha_error', 'resuelto', 'acciones')
    list_filter = ('tipo_error', 'resuelto', 'fecha_error')
    search_fields = ('tipo_error', 'descripcion', 'usuario__username')
    readonly_fields = ('fecha_error', 'error_details')
    list_per_page = 20
    
    fieldsets = (
        ('Información del Error', {
            'fields': ('tipo_error', 'descripcion', 'usuario', 'resuelto')
        }),
        ('Detalles Técnicos', {
            'fields': ('url_solicitud', 'respuesta_api', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('fecha_error',),
            'classes': ('collapse',)
        }),
    )
    
    def error_details(self, obj):
        return format_html('''
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>URL:</strong> {url}<br><br>
                <strong>Respuesta API:</strong><br>
                <pre style="background: white; padding: 10px; border-radius: 3px; 
                      max-height: 200px; overflow: auto;">{respuesta}</pre>
            </div>
        ''', url=obj.url_solicitud or "No disponible", 
           respuesta=obj.respuesta_api or "No disponible")
    error_details.short_description = 'Detalles Completos'
    
    def acciones(self, obj):
        if not obj.resuelto:
            url = reverse('admin:videos_oautherrorlog_change', args=[obj.id])
            return format_html(
                '<a href="{}" style="background: #28a745; color: white; '
                'padding: 5px 10px; border-radius: 3px; text-decoration: none;">'
                'Marcar como Resuelto</a>',
                url
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">✓ Resuelto</span>'
        )
    acciones.short_description = 'Acciones'
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(resuelto=True)
        self.message_user(request, f"{queryset.count()} errores marcados como resueltos.")
    mark_as_resolved.short_description = "Marcar como resuelto"
    
    actions = [mark_as_resolved]

# ============================================
# ADMIN PARA Video (modelo existente)
# ============================================
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'canal_nombre', 'vistas', 'likes', 
                   'fecha_publicacion', 'categoria', 'video_link')
    list_filter = ('categoria', 'fecha_publicacion')
    search_fields = ('titulo', 'descripcion', 'canal_nombre', 'youtube_id')
    readonly_fields = ('youtube_id', 'fecha_publicacion', 'creado', 
                      'actualizado', 'embed_preview')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('titulo', 'descripcion', 'categoria', 'etiquetas')
        }),
        ('YouTube', {
            'fields': ('youtube_id', 'url_video', 'url_thumbnail', 'embed_preview')
        }),
        ('Canal', {
            'fields': ('canal_id', 'canal_nombre')
        }),
        ('Detalles', {
            'fields': ('duracion', 'fecha_publicacion')
        }),
        ('Estadísticas', {
            'fields': ('vistas', 'likes', 'comentarios')
        }),
        ('Relaciones', {
            'fields': ('agregado_por',)
        }),
        ('Metadatos', {
            'fields': ('creado', 'actualizado'),
            'classes': ('collapse',)
        }),
    )
    
    def video_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" style="background: #FF0000; color: white; '
            'padding: 3px 8px; border-radius: 3px; text-decoration: none; font-size: 12px;">'
            '▶️ YouTube</a>',
            obj.url_video
        )
    video_link.short_description = 'Enlace'
    
    def embed_preview(self, obj):
        return format_html('''
            <div style="margin: 10px 0;">
                <a href="{}" target="_blank" style="background: #FF0000; color: white; 
                   padding: 8px 15px; border-radius: 4px; text-decoration: none; 
                   margin-right: 10px; display: inline-block;">
                    ▶️ Ver en YouTube
                </a>
                <a href="{}" target="_blank" style="background: #333; color: white; 
                   padding: 8px 15px; border-radius: 4px; text-decoration: none; 
                   display: inline-block;">
                    📺 Embed
                </a>
            </div>
            <div style="margin-top: 10px;">
                <strong>ID:</strong> {}<br>
                <strong>Embed URL:</strong> {}
            </div>
        ''', obj.url_video, obj.get_embed_url(), obj.youtube_id, obj.get_embed_url())
    embed_preview.short_description = 'Enlaces y Embed'

# ============================================
# ADMIN PARA Playlist (modelo existente)
# ============================================
@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'creador', 'publica', 'cantidad_videos', 'creado')
    list_filter = ('publica', 'creador', 'creado')
    search_fields = ('nombre', 'descripcion', 'creador__username')
    filter_horizontal = ('videos',)
    readonly_fields = ('creado',)
    
    def cantidad_videos(self, obj):
        return obj.videos.count()
    cantidad_videos.short_description = 'Videos'

# ============================================
# Personalización del sitio admin
# ============================================
admin.site.site_header = 'Administración de Videos YouTube'
admin.site.site_title = 'YouTube Manager'
admin.site.index_title = 'Panel de Administración'