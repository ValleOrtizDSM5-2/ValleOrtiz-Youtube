# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class YouTubeAccount(models.Model):
    """
    Modelo para almacenar cuentas de YouTube vinculadas a usuarios de Django.
    Se crea/actualiza durante el flujo OAuth 2.0.
    """
    
    # Relación uno-a-uno con el usuario de Django
    # Un usuario puede tener solo una cuenta YouTube vinculada
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='youtube_account',
        verbose_name='Usuario Django'
    )
    
    # ID único de YouTube (canal)
    youtube_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='ID de YouTube',
        help_text='ID único del canal de YouTube'
    )
    
    # Información del canal
    nombre_canal = models.CharField(
        max_length=200,
        verbose_name='Nombre del canal',
        help_text='Nombre público del canal de YouTube'
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name='Email asociado',
        help_text='Email de la cuenta de Google (puede estar vacío por privacidad)'
    )
    
    foto_perfil = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Foto de perfil',
        help_text='URL de la imagen de perfil del canal'
    )
    
    # Tokens de autenticación OAuth 2.0
    access_token = models.TextField(
        verbose_name='Token de acceso',
        help_text='Token de acceso OAuth 2.0 para YouTube API'
    )
    
    refresh_token = models.TextField(
        blank=True,
        verbose_name='Token de refresco',
        help_text='Token de refresco para obtener nuevos access tokens'
    )
    
    token_expira = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Token expira',
        help_text='Fecha y hora en que expira el token de acceso'
    )
    
    # Estadísticas del canal (se actualizan periódicamente)
    suscriptores = models.IntegerField(
        default=0,
        verbose_name='Suscriptores',
        help_text='Número de suscriptores del canal'
    )
    
    videos_publicados = models.IntegerField(
        default=0,
        verbose_name='Videos publicados',
        help_text='Número total de videos publicados en el canal'
    )
    
    vistas_totales = models.BigIntegerField(
        default=0,
        verbose_name='Vistas totales',
        help_text='Número total de vistas de todos los videos del canal'
    )
    
    # Metadatos
    fecha_vinculacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de vinculación'
    )
    
    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    # Información adicional (opcional, se puede llenar después)
    descripcion_canal = models.TextField(
        blank=True,
        verbose_name='Descripción del canal',
        help_text='Descripción pública del canal'
    )
    
    url_canal = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='URL del canal',
        help_text='URL completa del canal de YouTube'
    )
    
    # Configuraciones de la cuenta
    monitoreo_activo = models.BooleanField(
        default=True,
        verbose_name='Monitoreo activo',
        help_text='Indica si se deben monitorear las estadísticas automáticamente'
    )
    
    frecuencia_actualizacion = models.IntegerField(
        default=60,
        verbose_name='Frecuencia de actualización (minutos)',
        help_text='Cada cuántos minutos se actualizan las estadísticas'
    )
    
    class Meta:
        verbose_name = 'Cuenta de YouTube'
        verbose_name_plural = 'Cuentas de YouTube'
        ordering = ['-fecha_vinculacion']
        indexes = [
            models.Index(fields=['youtube_id']),
            models.Index(fields=['user']),
            models.Index(fields=['fecha_vinculacion']),
        ]
    
    def __str__(self):
        return f"{self.nombre_canal} ({self.user.username})"
    
    def esta_autenticado(self):
        """
        Verifica si el token de acceso aún es válido.
        
        Returns:
            bool: True si el token es válido, False si ha expirado
        """
        if not self.token_expira:
            return False
        
        # Comparar con la hora actual (usando timezone para consistencia)
        now = timezone.now()
        return now < self.token_expira
    
    def tiempo_restante_token(self):
        """
        Calcula cuánto tiempo queda hasta que el token expire.
        
        Returns:
            str: Tiempo restante en formato legible, o "Expirado"
        """
        if not self.token_expira or not self.esta_autenticado():
            return "Expirado"
        
        from datetime import datetime
        now = timezone.now()
        diferencia = self.token_expira - now
        
        # Convertir a minutos y horas
        minutos = int(diferencia.total_seconds() / 60)
        horas = minutos // 60
        minutos_restantes = minutos % 60
        
        if horas > 0:
            return f"{horas}h {minutos_restantes}m"
        return f"{minutos}m"
    
    def get_channel_url(self):
        """
        Genera la URL del canal de YouTube.
        
        Returns:
            str: URL completa del canal
        """
        if self.url_canal:
            return self.url_canal
        return f"https://www.youtube.com/channel/{self.youtube_id}"
    
    def actualizar_estadisticas(self, suscriptores=None, videos=None, vistas=None):
        """
        Actualiza las estadísticas del canal.
        
        Args:
            suscriptores (int, optional): Nuevo número de suscriptores
            videos (int, optional): Nuevo número de videos
            vistas (int, optional): Nuevo número de vistas totales
        """
        if suscriptores is not None:
            self.suscriptores = suscriptores
        if videos is not None:
            self.videos_publicados = videos
        if vistas is not None:
            self.vistas_totales = vistas
        
        self.save(update_fields=['suscriptores', 'videos_publicados', 'vistas_totales', 'ultima_actualizacion'])
    
    def to_dict(self):
        """
        Convierte la instancia a diccionario para JSON.
        
        Returns:
            dict: Representación en diccionario de la cuenta
        """
        return {
            'id': self.id,
            'youtube_id': self.youtube_id,
            'nombre_canal': self.nombre_canal,
            'email': self.email,
            'suscriptores': self.suscriptores,
            'videos_publicados': self.videos_publicados,
            'vistas_totales': self.vistas_totales,
            'fecha_vinculacion': self.fecha_vinculacion.isoformat() if self.fecha_vinculacion else None,
            'ultima_actualizacion': self.ultima_actualizacion.isoformat() if self.ultima_actualizacion else None,
            'token_valido': self.esta_autenticado(),
            'tiempo_restante': self.tiempo_restante_token(),
            'url_canal': self.get_channel_url(),
        }
    
    def get_channel_url(self):
        """Genera la URL del canal de YouTube."""
        if self.url_canal:
            return self.url_canal
        return f"https://www.youtube.com/channel/{self.youtube_id}"

    def tiempo_restante_token(self):
        """Calcula cuánto tiempo queda hasta que el token expire."""
        if not self.token_expira or not self.esta_autenticado():
            return "Expirado"
        
        from datetime import datetime
        now = timezone.now()
        diferencia = self.token_expira - now
        
        # Convertir a minutos y horas
        minutos = int(diferencia.total_seconds() / 60)
        horas = minutos // 60
        minutos_restantes = minutos % 60
        
        if horas > 0:
            return f"{horas}h {minutos_restantes}m"
        return f"{minutos}m"


class YouTubeVideo(models.Model):
    """
    Modelo para videos de YouTube que están siendo monitoreados o gestionados.
    """
    
    # Relación con la cuenta de YouTube
    youtube_account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='videos',
        verbose_name='Cuenta de YouTube'
    )
    
    # ID único del video en YouTube
    youtube_video_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='ID del video en YouTube',
        help_text='ID único del video (ej: dQw4w9WgXcQ)'
    )
    
    # Información del video
    titulo = models.CharField(
        max_length=300,
        verbose_name='Título del video'
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción del video'
    )
    
    # Thumbnails (podemos guardar múltiples tamaños)
    thumbnail_default = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Thumbnail (default)'
    )
    
    thumbnail_medium = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Thumbnail (medium)'
    )
    
    thumbnail_high = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Thumbnail (high)'
    )
    
    thumbnail_maxres = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Thumbnail (maxres)'
    )
    
    # Duración del video (en segundos)
    duracion_segundos = models.IntegerField(
        default=0,
        verbose_name='Duración (segundos)'
    )
    
    # Estado del video
    ESTADO_CHOICES = [
        ('public', 'Público'),
        ('private', 'Privado'),
        ('unlisted', 'No listado'),
    ]
    
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='public',
        verbose_name='Estado de visibilidad'
    )
    
    # Categoría del video (ID de categoría de YouTube)
    categoria_id = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='ID de categoría'
    )
    
    # Etiquetas (tags)
    etiquetas = models.TextField(
        blank=True,
        verbose_name='Etiquetas',
        help_text='Etiquetas separadas por comas'
    )
    
    # Estadísticas del video
    vistas = models.BigIntegerField(
        default=0,
        verbose_name='Vistas'
    )
    
    likes = models.IntegerField(
        default=0,
        verbose_name='Me gusta'
    )
    
    dislikes = models.IntegerField(
        default=0,
        verbose_name='No me gusta'
    )
    
    comentarios = models.IntegerField(
        default=0,
        verbose_name='Comentarios'
    )
    
    favoritos = models.IntegerField(
        default=0,
        verbose_name='Favoritos'
    )
    
    # Fechas importantes
    fecha_publicacion = models.DateTimeField(
        verbose_name='Fecha de publicación en YouTube'
    )
    
    fecha_subida = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de subida a nuestro sistema'
    )
    
    # Metadatos de monitoreo
    monitoreo_activo = models.BooleanField(
        default=True,
        verbose_name='Monitoreo activo'
    )
    
    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización de estadísticas'
    )
    
    class Meta:
        verbose_name = 'Video de YouTube'
        verbose_name_plural = 'Videos de YouTube'
        ordering = ['-fecha_publicacion']
        indexes = [
            models.Index(fields=['youtube_video_id']),
            models.Index(fields=['youtube_account', 'fecha_publicacion']),
            models.Index(fields=['monitoreo_activo']),
        ]
    
    def __str__(self):
        return f"{self.titulo} ({self.youtube_video_id})"
    
    def get_video_url(self):
        """
        Genera la URL del video en YouTube.
        
        Returns:
            str: URL completa del video
        """
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"
    
    def get_embed_url(self):
        """
        Genera la URL para embed del video.
        
        Returns:
            str: URL para iframe de embed
        """
        return f"https://www.youtube.com/embed/{self.youtube_video_id}"
    
    def get_thumbnail(self, size='medium'):
        """
        Obtiene la URL del thumbnail según el tamaño solicitado.
        
        Args:
            size (str): 'default', 'medium', 'high', o 'maxres'
            
        Returns:
            str: URL del thumbnail, o cadena vacía si no existe
        """
        thumbnails = {
            'default': self.thumbnail_default,
            'medium': self.thumbnail_medium,
            'high': self.thumbnail_high,
            'maxres': self.thumbnail_maxres,
        }
        return thumbnails.get(size, self.thumbnail_medium)
    
    def duracion_formateada(self):
        """
        Formatea la duración del video en formato legible.
        
        Returns:
            str: Duración en formato HH:MM:SS o MM:SS
        """
        horas = self.duracion_segundos // 3600
        minutos = (self.duracion_segundos % 3600) // 60
        segundos = self.duracion_segundos % 60
        
        if horas > 0:
            return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        return f"{minutos:02d}:{segundos:02d}"
    
    def actualizar_estadisticas(self, vistas=None, likes=None, dislikes=None, 
                                comentarios=None, favoritos=None):
        """
        Actualiza las estadísticas del video.
        """
        update_fields = ['ultima_actualizacion']
        
        if vistas is not None:
            self.vistas = vistas
            update_fields.append('vistas')
        
        if likes is not None:
            self.likes = likes
            update_fields.append('likes')
        
        if dislikes is not None:
            self.dislikes = dislikes
            update_fields.append('dislikes')
        
        if comentarios is not None:
            self.comentarios = comentarios
            update_fields.append('comentarios')
        
        if favoritos is not None:
            self.favoritos = favoritos
            update_fields.append('favoritos')
        
        self.save(update_fields=update_fields)
    
    def to_dict(self):
        """
        Convierte la instancia a diccionario para JSON.
        """
        return {
            'id': self.id,
            'youtube_video_id': self.youtube_video_id,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'url_video': self.get_video_url(),
            'url_embed': self.get_embed_url(),
            'thumbnail': self.get_thumbnail(),
            'duracion': self.duracion_formateada(),
            'estado': self.get_estado_display(),
            'vistas': self.vistas,
            'likes': self.likes,
            'comentarios': self.comentarios,
            'fecha_publicacion': self.fecha_publicacion.isoformat() if self.fecha_publicacion else None,
            'fecha_subida': self.fecha_subida.isoformat() if self.fecha_subida else None,
        }


class YouTubeAnalytics(models.Model):
    """
    Modelo para almacenar análisis histórico de estadísticas.
    Permite hacer gráficos de crecimiento a lo largo del tiempo.
    """
    
    youtube_account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name='Cuenta de YouTube'
    )
    
    # Fecha del registro (normalmente diario)
    fecha_registro = models.DateField(
        verbose_name='Fecha del registro'
    )
    
    # Estadísticas capturadas
    suscriptores = models.IntegerField(
        default=0,
        verbose_name='Suscriptores'
    )
    
    vistas_totales = models.BigIntegerField(
        default=0,
        verbose_name='Vistas totales'
    )
    
    videos_publicados = models.IntegerField(
        default=0,
        verbose_name='Videos publicados'
    )
    
    # Métricas calculadas
    crecimiento_suscriptores = models.IntegerField(
        default=0,
        verbose_name='Crecimiento de suscriptores'
    )
    
    crecimiento_vistas = models.BigIntegerField(
        default=0,
        verbose_name='Crecimiento de vistas'
    )
    
    class Meta:
        verbose_name = 'Análisis de YouTube'
        verbose_name_plural = 'Análisis de YouTube'
        ordering = ['-fecha_registro']
        unique_together = ['youtube_account', 'fecha_registro']
        indexes = [
            models.Index(fields=['youtube_account', 'fecha_registro']),
        ]
    
    def __str__(self):
        return f"Análisis {self.youtube_account.nombre_canal} - {self.fecha_registro}"
    
    def calcular_crecimiento(self, registro_anterior):
        """
        Calcula el crecimiento comparado con un registro anterior.
        
        Args:
            registro_anterior (YouTubeAnalytics): Registro del día anterior
        """
        if registro_anterior:
            self.crecimiento_suscriptores = self.suscriptores - registro_anterior.suscriptores
            self.crecimiento_vistas = self.vistas_totales - registro_anterior.vistas_totales
            self.save()


class OAuthErrorLog(models.Model):
    """
    Modelo para registrar errores de OAuth para debugging.
    """
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuario relacionado'
    )
    
    tipo_error = models.CharField(
        max_length=100,
        verbose_name='Tipo de error'
    )
    
    descripcion = models.TextField(
        verbose_name='Descripción del error'
    )
    
    url_solicitud = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='URL de la solicitud'
    )
    
    respuesta_api = models.TextField(
        blank=True,
        verbose_name='Respuesta de la API'
    )
    
    fecha_error = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del error'
    )
    
    resuelto = models.BooleanField(
        default=False,
        verbose_name='¿Resuelto?'
    )
    
    class Meta:
        verbose_name = 'Log de error OAuth'
        verbose_name_plural = 'Logs de errores OAuth'
        ordering = ['-fecha_error']
    
    def __str__(self):
        return f"{self.tipo_error} - {self.fecha_error}"


# ============================================
# MODELOS EXISTENTES (que ya tenías en tu archivo)
# ============================================

class Video(models.Model):
    """Modelo para almacenar información de videos de YouTube"""
    
    # Información de YouTube
    youtube_id = models.CharField(max_length=20, unique=True)  # ID único de YouTube (11 chars)
    titulo = models.CharField(max_length=300)  # Título del video
    descripcion = models.TextField()  # Descripción completa
    
    # URLs
    url_video = models.URLField()  # https://youtube.com/watch?v=xxxxx
    url_thumbnail = models.URLField()  # URL de la miniatura (imagen)
    
    # Información del canal
    canal_id = models.CharField(max_length=50)  # ID del canal de YouTube
    canal_nombre = models.CharField(max_length=200)  # Nombre del canal
    
    # Detalles
    duracion = models.CharField(max_length=20, blank=True)  # Formato ISO 8601 (PT15M30S)
    fecha_publicacion = models.DateTimeField()  # Cuándo se publicó en YouTube
    
    # Estadísticas (se actualizan periódicamente)
    vistas = models.BigIntegerField(default=0)  # Visualizaciones en YouTube
    likes = models.IntegerField(default=0)  # Me gusta
    comentarios = models.IntegerField(default=0)  # Cantidad de comentarios
    
    # Categorización local
    categoria = models.CharField(max_length=50, choices=[  # Categorías personalizadas
        ('programacion', 'Programación'),
        ('bases_datos', 'Bases de Datos'),
        ('redes', 'Redes'),
        ('seguridad', 'Seguridad'),
        ('otro', 'Otro'),
    ])
    etiquetas = models.CharField(max_length=500, blank=True)  # Tags separados por comas
    
    # Relaciones
    agregado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # Usuario que agregó
    
    # Metadatos
    creado = models.DateTimeField(auto_now_add=True)  # Fecha de creación en BD local
    actualizado = models.DateTimeField(auto_now=True)  # Última actualización
    
    class Meta:
        ordering = ['-fecha_publicacion']  # Más recientes primero
        verbose_name_plural = 'Videos'
    
    def __str__(self):
        return self.titulo
    
    def get_embed_url(self):
        """Retorna URL para embed iframe"""
        return f"https://www.youtube.com/embed/{self.youtube_id}?rel=0"  # Para <iframe>


class Playlist(models.Model):
    """Playlist personalizada de videos"""
    
    nombre = models.CharField(max_length=200)  # Nombre de la playlist
    descripcion = models.TextField(blank=True)  # Descripción
    videos = models.ManyToManyField(Video, related_name='playlists')  # Videos incluidos
    creador = models.ForeignKey(User, on_delete=models.CASCADE)  # Dueño de la playlist
    publica = models.BooleanField(default=False)  # Si es visible para todos
    
    creado = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre


# ============================================
# SEÑALES (SIGNALS) PARA AUTOMATIZACIÓN
# ============================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=YouTubeAccount)
def crear_url_canal(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una YouTubeAccount.
    Si no tiene URL de canal, la crea automáticamente.
    """
    if created and not instance.url_canal:
        instance.url_canal = f"https://www.youtube.com/channel/{instance.youtube_id}"
        instance.save(update_fields=['url_canal'])


@receiver(post_save, sender=YouTubeVideo)
def sincronizar_con_video_existente(sender, instance, created, **kwargs):
    """
    Señal para sincronizar YouTubeVideo con el modelo Video existente.
    Si el video no existe en el modelo Video, lo crea automáticamente.
    """
    if created:
        try:
            # Verificar si ya existe en el modelo Video
            Video.objects.get(youtube_id=instance.youtube_video_id)
        except Video.DoesNotExist:
            # Crear un nuevo registro en Video
            Video.objects.create(
                youtube_id=instance.youtube_video_id,
                titulo=instance.titulo,
                descripcion=instance.descripcion,
                url_video=instance.get_video_url(),
                url_thumbnail=instance.get_thumbnail(),
                canal_id=instance.youtube_account.youtube_id,
                canal_nombre=instance.youtube_account.nombre_canal,
                duracion=f"PT{instance.duracion_segundos}S",
                fecha_publicacion=instance.fecha_publicacion,
                vistas=instance.vistas,
                likes=instance.likes,
                comentarios=instance.comentarios,
                categoria='otro',  # Categoría por defecto
                agregado_por=instance.youtube_account.user,
            )

class BusquedaVideo(models.Model):
    """
    Modelo para guardar el historial de búsquedas de videos.
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='busquedas_videos',
        verbose_name='Usuario'
    )
    
    query = models.CharField(
        max_length=300,
        verbose_name='Término de búsqueda'
    )
    
    resultado_count = models.IntegerField(
        default=0,
        verbose_name='Número de resultados'
    )
    
    parametros_busqueda = models.JSONField(
        default=dict,
        verbose_name='Parámetros de búsqueda',
        help_text='Parámetros adicionales de búsqueda en formato JSON'
    )
    
    fecha_busqueda = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de búsqueda'
    )
    
    class Meta:
        verbose_name = 'Búsqueda de video'
        verbose_name_plural = 'Búsquedas de videos'
        ordering = ['-fecha_busqueda']
        indexes = [
            models.Index(fields=['usuario', 'fecha_busqueda']),
            models.Index(fields=['query']),
        ]
    
    def __str__(self):
        return f"{self.query} ({self.usuario.username})"


class VideoSubido(models.Model):
    """
    Modelo para registrar videos subidos a través de nuestra aplicación.
    """
    youtube_account = models.ForeignKey(
        YouTubeAccount,
        on_delete=models.CASCADE,
        related_name='videos_subidos',
        verbose_name='Cuenta de YouTube'
    )
    
    youtube_video_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='ID del video en YouTube'
    )
    
    titulo = models.CharField(
        max_length=300,
        verbose_name='Título del video'
    )
    
    ESTADO_UPLOAD = [
        ('pending', 'Pendiente'),
        ('uploading', 'Subiendo'),
        ('processing', 'Procesando'),
        ('published', 'Publicado'),
        ('failed', 'Fallido'),
    ]
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_UPLOAD,
        default='pending',
        verbose_name='Estado de subida'
    )
    
    archivo_path = models.CharField(
        max_length=500,
        verbose_name='Ruta del archivo',
        help_text='Ruta local del archivo de video'
    )
    
    archivo_size = models.BigIntegerField(
        default=0,
        verbose_name='Tamaño del archivo (bytes)'
    )
    
    duracion = models.IntegerField(
        default=0,
        verbose_name='Duración (segundos)'
    )
    
    # Metadatos del video
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    etiquetas = models.TextField(
        blank=True,
        verbose_name='Etiquetas',
        help_text='Separadas por comas'
    )
    
    categoria_id = models.CharField(
        max_length=20,
        default='22',
        verbose_name='ID de categoría YouTube',
        help_text='22 por defecto (People & Blogs)'
    )
    
    privacidad = models.CharField(
        max_length=10,
        choices=[
            ('public', 'Público'),
            ('private', 'Privado'),
            ('unlisted', 'No listado'),
        ],
        default='private',
        verbose_name='Configuración de privacidad'
    )
    
    # Estadísticas de subida
    inicio_subida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Inicio de subida'
    )
    
    fin_subida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fin de subida'
    )
    
    mensaje_error = models.TextField(
        blank=True,
        verbose_name='Mensaje de error'
    )
    
    # Metadatos
    creado = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado'
    )
    
    actualizado = models.DateTimeField(
        auto_now=True,
        verbose_name='Actualizado'
    )
    
    class Meta:
        verbose_name = 'Video subido'
        verbose_name_plural = 'Videos subidos'
        ordering = ['-creado']
        indexes = [
            models.Index(fields=['youtube_account', 'estado']),
            models.Index(fields=['estado']),
            models.Index(fields=['creado']),
        ]
    
    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()})"
    
    def get_video_url(self):
        if self.youtube_video_id:
            return f"https://www.youtube.com/watch?v={self.youtube_video_id}"
        return None
    
    def tiempo_subida(self):
        if self.inicio_subida and self.fin_subida:
            diferencia = self.fin_subida - self.inicio_subida
            return diferencia.total_seconds()
        return None

class VideoManager(models.Model):
    """
    Modelo para gestionar videos del usuario.
    Extiende la funcionalidad del modelo Video existente.
    """
    video = models.OneToOneField(
        Video,
        on_delete=models.CASCADE,
        related_name='manager',
        verbose_name='Video'
    )
    
    usuario_propietario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos_gestionados',
        verbose_name='Propietario'
    )
    
    fecha_agregado = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de agregado'
    )
    
    visible = models.BooleanField(
        default=True,
        verbose_name='Visible'
    )
    
    favorito = models.BooleanField(
        default=False,
        verbose_name='Favorito'
    )
    
    notas = models.TextField(
        blank=True,
        verbose_name='Notas personales'
    )
    
    class Meta:
        verbose_name = 'Gestor de Video'
        verbose_name_plural = 'Gestores de Video'
        ordering = ['-fecha_agregado']
        indexes = [
            models.Index(fields=['usuario_propietario', 'favorito']),
        ]
    
    def __str__(self):
        return f"{self.video.titulo} - {self.usuario_propietario.username}"


class EstadisticasVideo(models.Model):
    """
    Modelo para registrar estadísticas diarias de videos.
    """
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='estadisticas_diarias',
        verbose_name='Video'
    )
    
    fecha = models.DateField(
        verbose_name='Fecha del registro'
    )
    
    vistas = models.IntegerField(
        default=0,
        verbose_name='Vistas del día'
    )
    
    likes = models.IntegerField(
        default=0,
        verbose_name='Likes del día'
    )
    
    comentarios = models.IntegerField(
        default=0,
        verbose_name='Comentarios del día'
    )
    
    crecimiento_vistas = models.IntegerField(
        default=0,
        verbose_name='Crecimiento de vistas'
    )
    
    class Meta:
        verbose_name = 'Estadística Diaria de Video'
        verbose_name_plural = 'Estadísticas Diarias de Video'
        unique_together = ['video', 'fecha']
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Estadísticas {self.video.youtube_id} - {self.fecha}"
    
# Agrega estos modelos al final de models.py

class VideoGuardado(models.Model):
    """
    Modelo para videos guardados desde búsquedas de YouTube.
    Estos son videos NO subidos por el usuario, sino videos de YouTube que el usuario quiere guardar.
    """
    video_id = models.CharField(
        max_length=100,
        verbose_name='ID del video en YouTube',
        help_text='Ej: dQw4w9WgXcQ'
    )
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='videos_guardados',
        verbose_name='Usuario'
    )
    
    titulo = models.CharField(
        max_length=300,
        verbose_name='Título del video'
    )
    
    descripcion = models.TextField(
        blank=True,
        null=True,
        verbose_name='Descripción'
    )
    
    canal_nombre = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Nombre del canal'
    )
    
    canal_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID del canal'
    )
    
    url_thumbnail = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL del thumbnail'
    )
    
    fecha_publicacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de publicación en YouTube'
    )
    
    # Estadísticas (se actualizan cuando se consulta)
    vistas = models.BigIntegerField(
        default=0,
        verbose_name='Vistas'
    )
    
    likes = models.IntegerField(
        default=0,
        verbose_name='Likes'
    )
    
    comentarios = models.IntegerField(
        default=0,
        verbose_name='Comentarios'
    )
    
    duracion = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Duración'
    )
    
    categoria = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Categoría'
    )
    
    etiquetas = models.TextField(
        blank=True,
        null=True,
        verbose_name='Etiquetas (separadas por comas)'
    )
    
    # Metadatos
    fecha_guardado = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de guardado'
    )
    
    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    # Gestión
    favorito = models.BooleanField(
        default=False,
        verbose_name='Favorito'
    )
    
    notas = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas personales'
    )
    
    visto = models.BooleanField(
        default=False,
        verbose_name='¿Visto?'
    )
    
    class Meta:
        verbose_name = 'Video Guardado'
        verbose_name_plural = 'Videos Guardados'
        unique_together = ['video_id', 'usuario']
        ordering = ['-fecha_guardado']
        indexes = [
            models.Index(fields=['usuario', 'fecha_guardado']),
            models.Index(fields=['video_id']),
            models.Index(fields=['favorito']),
        ]
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"
    
    def get_video_url(self):
        """Genera URL del video en YouTube"""
        return f"https://www.youtube.com/watch?v={self.video_id}"
    
    def get_embed_url(self):
        """Genera URL para embed iframe"""
        return f"https://www.youtube.com/embed/{self.video_id}"
    
    def get_qr_code_url(self):
        """Genera URL para código QR"""
        video_url = self.get_video_url()
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={video_url}"


class HistorialBusqueda(models.Model):
    """
    Historial de búsquedas de videos en YouTube.
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='historial_busquedas',
        verbose_name='Usuario'
    )
    
    query = models.CharField(
        max_length=300,
        verbose_name='Término de búsqueda'
    )
    
    parametros = models.JSONField(
        default=dict,
        verbose_name='Parámetros de búsqueda',
        help_text='Filtros, orden, etc.'
    )
    
    resultados_encontrados = models.IntegerField(
        default=0,
        verbose_name='Resultados encontrados'
    )
    
    fecha_busqueda = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de búsqueda'
    )
    
    class Meta:
        verbose_name = 'Historial de Búsqueda'
        verbose_name_plural = 'Historial de Búsquedas'
        ordering = ['-fecha_busqueda']
    
    def __str__(self):
        return f"{self.query} - {self.usuario.username}"