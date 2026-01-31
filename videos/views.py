# views.py
import requests
import json
import re
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from urllib.parse import urlencode
from .models import YouTubeAccount, Video, BusquedaVideo, VideoSubido, VideoManager, EstadisticasVideo, VideoGuardado
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError


# ============================================
# VISTA 0: Página de Inicio
# ============================================
def inicio(request):
    """
    Página principal para conectar con YouTube.
    Si el usuario ya está autenticado y tiene cuenta YouTube, redirige al dashboard.
    """
    # Si el usuario ya está autenticado
    if request.user.is_authenticated:
        try:
            # Verificar si ya tiene cuenta YouTube vinculada
            youtube_account = YouTubeAccount.objects.get(user=request.user)
            return redirect('youtube_dashboard')
        except YouTubeAccount.DoesNotExist:
            # Autenticado pero sin cuenta YouTube, mostrar opción para conectar
            pass
    
    # Mostrar página de login
    return render(request, 'login.html')

# ============================================
# VISTA 1: Iniciar Login con YouTube
# ============================================
def youtube_login(request):
    """
    Redirige al usuario a YouTube para autorizar nuestra aplicación.
    Flujo OAuth 2.0 - Paso 1: Authorization Request
    """
    # Para debugging: mostrar la URI configurada
    print(f"[DEBUG] YouTube Login iniciado")
    print(f"[DEBUG] Redirect URI configurada: {settings.YOUTUBE_REDIRECT_URI}")
    print(f"[DEBUG] Client ID: {settings.YOUTUBE_CLIENT_ID[:10]}...")
    
    # Construir URL de autorización de Google OAuth 2.0
    auth_url = "https://accounts.google.com/o/oauth2/auth"
    
    # Parámetros REQUERIDOS para OAuth 2.0
    params = {
        'client_id': settings.YOUTUBE_CLIENT_ID,
        'redirect_uri': settings.YOUTUBE_REDIRECT_URI,  # ¡DEBE coincidir con Google Cloud Console!
        'response_type': 'code',
        'access_type': 'offline',      # Importante: obtener refresh_token
        'prompt': 'consent',           # Fuerza a pedir permisos cada vez
        'scope': ' '.join(settings.YOUTUBE_SCOPES),  # Scopes separados por espacios
    }
    
    # Construir URL completa
    full_auth_url = f"{auth_url}?{urlencode(params)}"
    
    print(f"[DEBUG] URL de autorización generada: {full_auth_url[:100]}...")
    
    # Redirigir al usuario a YouTube/Google para autorización
    return redirect(full_auth_url)

# ============================================
# VISTA 2: Callback de YouTube
# ============================================
def youtube_callback(request):
    """
    Maneja la respuesta de YouTube OAuth.
    Esta vista se ejecuta cuando Google redirige al usuario de vuelta a nuestra app.
    Flujo OAuth 2.0 - Pasos 2 y 3: Intercambiar código por tokens
    """
    print(f"[DEBUG] Callback recibido")
    print(f"[DEBUG] URL completa: {request.build_absolute_uri()}")
    print(f"[DEBUG] Parámetros GET: {dict(request.GET)}")
    
    # PASO 1: Obtener el código de autorización de la URL
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    # Si hay un error o no hay código
    if error:
        error_description = request.GET.get('error_description', 'Error desconocido')
        print(f"[ERROR] Error de autorización: {error} - {error_description}")
        
        return render(request, 'error.html', {
            'error': f'Error de autorización: {error}',
            'detalle': error_description
        })
    
    if not code:
        print("[ERROR] No se recibió código de autorización")
        return render(request, 'error.html', {
            'error': 'No se recibió código de autorización',
            'detalle': 'El usuario canceló la autorización o hubo un error en el proceso.'
        })
    
    print(f"[DEBUG] Código recibido: {code[:20]}...")
    
    # PASO 2: Intercambiar código por access_token
    token_url = "https://oauth2.googleapis.com/token"
    
    # Datos para la petición POST (application/x-www-form-urlencoded)
    token_data = {
        'client_id': settings.YOUTUBE_CLIENT_ID,
        'client_secret': settings.YOUTUBE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.YOUTUBE_REDIRECT_URI,  # ¡DEBE ser la misma del paso 1!
    }
    
    print(f"[DEBUG] Intercambiando código por token...")
    print(f"[DEBUG] Token URL: {token_url}")
    print(f"[DEBUG] Redirect URI usada: {settings.YOUTUBE_REDIRECT_URI}")
    
    try:
        # Hacer petición POST para obtener tokens
        response = requests.post(token_url, data=token_data, timeout=30)
        token_response = response.json()
        
        print(f"[DEBUG] Respuesta de token: {json.dumps(token_response, indent=2)}")
        
        # Verificar si hubo error en la respuesta
        if 'error' in token_response:
            error_msg = token_response.get('error_description', 'Error desconocido al obtener tokens')
            print(f"[ERROR] Error al obtener tokens: {error_msg}")
            
            return render(request, 'error.html', {
                'error': 'Error al obtener tokens de acceso',
                'detalle': error_msg
            })
        
        # Extraer tokens de la respuesta
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token', '')  # Puede no venir si ya se tenía
        expires_in = token_response.get('expires_in', 3600)      # Default 1 hora
        
        if not access_token:
            print("[ERROR] No se recibió access_token en la respuesta")
            return render(request, 'error.html', {
                'error': 'Error en la respuesta de Google',
                'detalle': 'No se recibió token de acceso válido.'
            })
        
        print(f"[DEBUG] Access token obtenido: {access_token[:20]}...")
        if refresh_token:
            print(f"[DEBUG] Refresh token obtenido: {refresh_token[:20]}...")
        
        # Calcular fecha de expiración
        token_expira = datetime.now() + timedelta(seconds=expires_in)
        print(f"[DEBUG] Token expira: {token_expira}")
        
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout al obtener token")
        return render(request, 'error.html', {
            'error': 'Timeout de conexión',
            'detalle': 'Google no respondió a tiempo. Intenta nuevamente.'
        })
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de conexión: {e}")
        return render(request, 'error.html', {
            'error': 'Error de conexión',
            'detalle': f'No se pudo conectar con Google: {str(e)}'
        })
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return render(request, 'error.html', {
            'error': 'Error inesperado',
            'detalle': f'Ocurrió un error: {str(e)}'
        })
    
    # PASO 3: Obtener información del usuario con el access_token
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # 3.1 Obtener información básica del usuario (email)
    user_email = ''
    try:
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        user_response = requests.get(userinfo_url, headers=headers, timeout=10)
        user_data = user_response.json()
        
        if 'error' not in user_data:
            user_email = user_data.get('email', '')
            print(f"[DEBUG] Email del usuario: {user_email}")
        else:
            print(f"[WARNING] No se pudo obtener email: {user_data.get('error', {})}")
    except Exception as e:
        print(f"[WARNING] Error al obtener userinfo: {e}")
    
    # 3.2 Obtener información del canal de YouTube
    try:
        channels_url = "https://www.googleapis.com/youtube/v3/channels"
        channels_params = {
            'part': 'snippet,statistics,brandingSettings',
            'mine': 'true',  # Obtener el canal del usuario autenticado
        }
        
        print(f"[DEBUG] Obteniendo información del canal...")
        channels_response = requests.get(channels_url, params=channels_params, headers=headers, timeout=10)
        channels_data = channels_response.json()
        
        print(f"[DEBUG] Respuesta del canal: {json.dumps(channels_data, indent=2)[:500]}...")
        
        # Verificar errores en la respuesta del canal
        if 'error' in channels_data:
            error_msg = channels_data.get('error', {}).get('message', 'Error desconocido al obtener canal')
            print(f"[ERROR] Error al obtener canal: {error_msg}")
            
            return render(request, 'error.html', {
                'error': 'Error al obtener datos del canal de YouTube',
                'detalle': error_msg
            })
        
        # Verificar que haya al menos un canal
        if not channels_data.get('items'):
            print("[ERROR] No se encontraron canales para este usuario")
            return render(request, 'error.html', {
                'error': 'No se encontró canal de YouTube',
                'detalle': 'Esta cuenta de Google no tiene un canal de YouTube asociado.'
            })
        
        # Procesar el primer canal (usuario puede tener solo uno con "mine": true)
        channel = channels_data['items'][0]
        channel_id = channel['id']
        snippet = channel.get('snippet', {})
        stats = channel.get('statistics', {})
        
        # Extraer datos del canal
        channel_name = snippet.get('title', 'Mi Canal de YouTube')
        channel_thumbnail = snippet.get('thumbnails', {}).get('high', {}).get('url', 
                            snippet.get('thumbnails', {}).get('medium', {}).get('url',
                            snippet.get('thumbnails', {}).get('default', {}).get('url', '')))
        channel_description = snippet.get('description', '')
        
        # Convertir estadísticas a enteros (pueden venir como strings)
        try:
            subscribers = int(stats.get('subscriberCount', 0))
        except (ValueError, TypeError):
            subscribers = 0
            
        try:
            video_count = int(stats.get('videoCount', 0))
        except (ValueError, TypeError):
            video_count = 0
            
        try:
            view_count = int(stats.get('viewCount', 0))
        except (ValueError, TypeError):
            view_count = 0
        
        print(f"[DEBUG] Canal encontrado: {channel_name} (ID: {channel_id})")
        print(f"[DEBUG] Suscriptores: {subscribers}, Videos: {video_count}, Vistas: {view_count}")
        
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout al obtener información del canal")
        return render(request, 'error.html', {
            'error': 'Timeout de conexión',
            'detalle': 'YouTube no respondió a tiempo al solicitar información del canal.'
        })
    except Exception as e:
        print(f"[ERROR] Error al procesar canal: {e}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'error.html', {
            'error': 'Error al procesar información del canal',
            'detalle': f'Ocurrió un error inesperado: {str(e)}'
        })
    
    # PASO 4: Crear o actualizar usuario y cuenta YouTube en nuestra base de datos
    try:
        # Buscar si ya existe una cuenta YouTube con este ID
        try:
            youtube_account = YouTubeAccount.objects.get(youtube_id=channel_id)
            print(f"[DEBUG] Cuenta YouTube existente encontrada: {youtube_account.nombre_canal}")
            
            # ACTUALIZAR cuenta existente
            youtube_account.access_token = access_token
            
            # Solo actualizar refresh_token si recibimos uno nuevo
            if refresh_token:
                youtube_account.refresh_token = refresh_token
                print("[DEBUG] Refresh token actualizado")
            
            youtube_account.token_expira = token_expira
            youtube_account.nombre_canal = channel_name
            youtube_account.email = user_email or youtube_account.email  # Mantener email anterior si no hay nuevo
            youtube_account.foto_perfil = channel_thumbnail
            youtube_account.suscriptores = subscribers
            youtube_account.videos_publicados = video_count
            youtube_account.vistas_totales = view_count
            youtube_account.save()
            
            print(f"[DEBUG] Cuenta YouTube actualizada: {youtube_account.id}")
            django_user = youtube_account.user
            
        except YouTubeAccount.DoesNotExist:
            print(f"[DEBUG] Creando nueva cuenta YouTube para ID: {channel_id}")
            
            # CREAR NUEVA cuenta YouTube
            
            # Verificar si hay un usuario Django autenticado actualmente
            if request.user.is_authenticated:
                # Usar el usuario actualmente autenticado
                django_user = request.user
                print(f"[DEBUG] Usando usuario autenticado existente: {django_user.username}")
            else:
                # Crear nuevo usuario Django
                # Generar username único basado en el ID de YouTube
                base_username = f"youtube_{channel_id}"
                username = base_username[:30]  # Django limita usernames a 30 caracteres
                
                # Verificar si el username ya existe
                counter = 1
                original_username = username
                while User.objects.filter(username=username).exists():
                    username = f"{original_username}_{counter}"
                    counter += 1
                    if counter > 100:  # Límite de seguridad
                        username = f"youtube_user_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        break
                
                # Crear el usuario
                django_user = User.objects.create_user(
                    username=username,
                    email=user_email,
                    first_name=channel_name.split()[0] if channel_name else '',
                    password=None  # Sin contraseña, se autentica via OAuth
                )
                print(f"[DEBUG] Nuevo usuario Django creado: {django_user.username}")
            
            # Crear la cuenta YouTube vinculada
            youtube_account = YouTubeAccount.objects.create(
                user=django_user,
                youtube_id=channel_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expira=token_expira,
                nombre_canal=channel_name,
                email=user_email,
                foto_perfil=channel_thumbnail,
                suscriptores=subscribers,
                videos_publicados=video_count,
                vistas_totales=view_count,
            )
            print(f"[DEBUG] Nueva cuenta YouTube creada con ID: {youtube_account.id}")
        
        # PASO 5: Iniciar sesión en Django (si no está autenticado)
        if not request.user.is_authenticated:
            print(f"[DEBUG] Iniciando sesión para usuario: {django_user.username}")
            login(request, django_user, backend='django.contrib.auth.backends.ModelBackend')
        
        # PASO 6: Guardar ID de cuenta en sesión para uso posterior
        request.session['youtube_account_id'] = youtube_account.id
        print(f"[DEBUG] Cuenta ID guardada en sesión: {youtube_account.id}")
        
        # PASO 7: Redirigir al dashboard
        print(f"[DEBUG] Autenticación completada exitosamente. Redirigiendo a dashboard...")
        return redirect('youtube_dashboard')
        
    except Exception as e:
        print(f"[ERROR] Error al guardar en base de datos: {e}")
        import traceback
        traceback.print_exc()
        
        return render(request, 'error.html', {
            'error': 'Error al guardar información',
            'detalle': f'Ocurrió un error al guardar los datos: {str(e)}'
        })

# ============================================
# VISTA 3: Dashboard de YouTube
# ============================================
@login_required
def youtube_dashboard(request):
    """
    Dashboard principal después de conectar con YouTube.
    Muestra información del canal y videos recientes.
    """
    print(f"[DEBUG] Accediendo al dashboard para usuario: {request.user.username}")
    
    try:
        # Obtener la cuenta YouTube del usuario actual
        youtube_account = YouTubeAccount.objects.get(user=request.user)
        print(f"[DEBUG] Cuenta YouTube encontrada: {youtube_account.nombre_canal}")
        
    except YouTubeAccount.DoesNotExist:
        print(f"[DEBUG] Usuario {request.user.username} no tiene cuenta YouTube vinculada")
        # Si no tiene cuenta YouTube, redirigir a conectar
        return redirect('youtube_login')
    
    # Verificar si el token de acceso aún es válido
    if not youtube_account.esta_autenticado():
        print(f"[WARNING] Token expirado para cuenta: {youtube_account.nombre_canal}")
        # Podrías redirigir a renovar token o mostrar advertencia
    
    # Intentar obtener videos recientes del canal usando la API
    videos = []
    api_error = None
    
    if youtube_account.esta_autenticado():
        try:
            headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
            
            # Llamar a YouTube API para obtener videos del canal
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                'part': 'snippet',
                'channelId': youtube_account.youtube_id,
                'maxResults': 10,
                'order': 'date',
                'type': 'video',
            }
            
            print(f"[DEBUG] Obteniendo videos para canal: {youtube_account.youtube_id}")
            search_response = requests.get(search_url, params=search_params, headers=headers, timeout=10)
            search_data = search_response.json()
            
            if 'error' in search_data:
                api_error = search_data.get('error', {}).get('message', 'Error desconocido')
                print(f"[ERROR] Error al obtener videos: {api_error}")
            elif 'items' in search_data:
                videos = search_data['items']
                print(f"[DEBUG] {len(videos)} videos obtenidos del canal")
            else:
                print(f"[DEBUG] No se encontraron videos para el canal")
                
        except requests.exceptions.Timeout:
            api_error = "Timeout al obtener videos"
            print(f"[ERROR] {api_error}")
        except Exception as e:
            api_error = f"Error: {str(e)}"
            print(f"[ERROR] Error al obtener videos: {e}")
    else:
        api_error = "Token expirado. Reconecta con YouTube."
        print(f"[WARNING] {api_error}")
    
    # Preparar contexto para el template
    context = {
        'youtube_account': youtube_account,
        'videos': videos[:5],  # Mostrar solo 5 videos máximo
        'total_videos': len(videos),
        'api_error': api_error,
        'token_valido': youtube_account.esta_autenticado(),
    }
    
    print(f"[DEBUG] Renderizando dashboard con {len(videos)} videos")
    return render(request, 'youtube_dashboard.html', context)

# ============================================
# VISTA 4: Obtener estadísticas actualizadas
# ============================================
@login_required
def youtube_estadisticas(request):
    """
    Endpoint API para obtener estadísticas actualizadas del canal.
    Retorna JSON con datos actualizados.
    """
    print(f"[DEBUG] Solicitando estadísticas actualizadas")
    
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
    except YouTubeAccount.DoesNotExist:
        print(f"[ERROR] Usuario {request.user.username} no tiene cuenta YouTube")
        return JsonResponse({
            'error': 'No hay cuenta de YouTube vinculada',
            'success': False
        }, status=400)
    
    # Verificar si el token es válido
    if not youtube_account.esta_autenticado():
        print(f"[ERROR] Token expirado para {youtube_account.nombre_canal}")
        return JsonResponse({
            'error': 'La sesión ha expirado. Por favor, reconecta con YouTube.',
            'success': False,
            'token_expirado': True
        }, status=401)
    
    # Llamar a YouTube API para obtener estadísticas actualizadas
    headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
    
    try:
        channels_url = "https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'statistics,snippet',
            'id': youtube_account.youtube_id,
        }
        
        print(f"[DEBUG] Obteniendo estadísticas actualizadas para {youtube_account.youtube_id}")
        response = requests.get(channels_url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if 'error' in data:
            error_msg = data.get('error', {}).get('message', 'Error desconocido')
            print(f"[ERROR] Error de API: {error_msg}")
            
            return JsonResponse({
                'error': f'Error de YouTube API: {error_msg}',
                'success': False
            }, status=500)
        
        if 'items' in data and data['items']:
            channel_data = data['items'][0]
            stats = channel_data.get('statistics', {})
            snippet = channel_data.get('snippet', {})
            
            # Actualizar datos en nuestra base de datos
            try:
                youtube_account.suscriptores = int(stats.get('subscriberCount', 0))
                youtube_account.videos_publicados = int(stats.get('videoCount', 0))
                youtube_account.vistas_totales = int(stats.get('viewCount', 0))
                
                # Actualizar también nombre y thumbnail si cambiaron
                youtube_account.nombre_canal = snippet.get('title', youtube_account.nombre_canal)
                youtube_account.foto_perfil = snippet.get('thumbnails', {}).get('high', {}).get('url', 
                                    snippet.get('thumbnails', {}).get('medium', {}).get('url',
                                    snippet.get('thumbnails', {}).get('default', {}).get('url', 
                                    youtube_account.foto_perfil)))
                
                youtube_account.save()
                print(f"[DEBUG] Estadísticas actualizadas para {youtube_account.nombre_canal}")
                
                # Preparar respuesta
                ahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                return JsonResponse({
                    'success': True,
                    'suscriptores': youtube_account.suscriptores,
                    'videos': youtube_account.videos_publicados,
                    'vistas': youtube_account.vistas_totales,
                    'nombre_canal': youtube_account.nombre_canal,
                    'actualizado': ahora,
                    'token_expirado': False
                })
                
            except (ValueError, TypeError) as e:
                print(f"[ERROR] Error al convertir estadísticas: {e}")
                return JsonResponse({
                    'error': 'Error en el formato de datos recibidos',
                    'success': False
                }, status=500)
        
        return JsonResponse({
            'error': 'No se encontraron datos del canal',
            'success': False
        }, status=404)
        
    except requests.exceptions.Timeout:
        print("[ERROR] Timeout al obtener estadísticas")
        return JsonResponse({
            'error': 'Timeout de conexión con YouTube',
            'success': False
        }, status=504)
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return JsonResponse({
            'error': f'Error inesperado: {str(e)}',
            'success': False
        }, status=500)

# ============================================
# VISTA 5: Cerrar sesión/desvincular YouTube
# ============================================
@login_required
def youtube_logout(request):
    """
    Desvincular cuenta de YouTube y cerrar sesión en Django.
    """
    print(f"[DEBUG] Solicitud de logout para usuario: {request.user.username}")
    
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
        account_name = youtube_account.nombre_canal
        
        # Intentar revocar el token en Google (opcional pero recomendado)
        try:
            revoke_url = "https://oauth2.googleapis.com/revoke"
            revoke_params = {'token': youtube_account.access_token}
            requests.post(revoke_url, params=revoke_params, timeout=5)
            print(f"[DEBUG] Token revocado en Google para {account_name}")
        except Exception as e:
            print(f"[WARNING] No se pudo revocar token en Google: {e}")
            # Continuar de todas formas
        
        # Eliminar la cuenta YouTube de nuestra base de datos
        youtube_account.delete()
        print(f"[DEBUG] Cuenta YouTube eliminada: {account_name}")
        
        # Limpiar sesión
        if 'youtube_account_id' in request.session:
            del request.session['youtube_account_id']
        
    except YouTubeAccount.DoesNotExist:
        print(f"[DEBUG] Usuario {request.user.username} no tenía cuenta YouTube vinculada")
    
    # Cerrar sesión en Django
    logout(request)
    print(f"[DEBUG] Sesión de Django cerrada")
    
    # Redirigir a la página de inicio
    return redirect('inicio')

# ============================================
# VISTA 6: Refrescar token de acceso (si expira)
# ============================================
@login_required
def refresh_youtube_token(request):
    """
    Refrescar el token de acceso usando el refresh_token.
    Esta función se llama automáticamente cuando el token expira.
    """
    print(f"[DEBUG] Intentando refrescar token para usuario: {request.user.username}")
    
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
        
        # Verificar que tenemos refresh_token
        if not youtube_account.refresh_token:
            print(f"[ERROR] No hay refresh_token para {youtube_account.nombre_canal}")
            return JsonResponse({
                'error': 'No se puede refrescar el token. Reautentica con YouTube.',
                'success': False,
                'needs_reauth': True
            }, status=401)
        
        # Solicitar nuevo token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': settings.YOUTUBE_CLIENT_ID,
            'client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'refresh_token': youtube_account.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(token_url, data=token_data, timeout=10)
        token_response = response.json()
        
        if 'error' in token_response:
            print(f"[ERROR] Error al refrescar token: {token_response.get('error_description')}")
            return JsonResponse({
                'error': 'Error al refrescar token. Reautentica con YouTube.',
                'success': False,
                'needs_reauth': True
            }, status=401)
        
        # Actualizar tokens
        youtube_account.access_token = token_response.get('access_token')
        expires_in = token_response.get('expires_in', 3600)
        youtube_account.token_expira = datetime.now() + timedelta(seconds=expires_in)
        youtube_account.save()
        
        print(f"[DEBUG] Token refrescado exitosamente para {youtube_account.nombre_canal}")
        
        return JsonResponse({
            'success': True,
            'message': 'Token refrescado exitosamente',
            'expira_en': youtube_account.token_expira.strftime('%d/%m/%Y %H:%M:%S')
        })
        
    except YouTubeAccount.DoesNotExist:
        return JsonResponse({
            'error': 'No hay cuenta YouTube vinculada',
            'success': False
        }, status=400)
    except Exception as e:
        print(f"[ERROR] Error al refrescar token: {e}")
        return JsonResponse({
            'error': f'Error inesperado: {str(e)}',
            'success': False
        }, status=500)

# ============================================
# VISTA 7: Verificar estado de autenticación
# ============================================
@login_required
def check_auth_status(request):
    """
    Verificar el estado de autenticación con YouTube.
    Útil para el frontend para saber si necesita reautenticar.
    """
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
        
        status = {
            'autenticado': True,
            'nombre_canal': youtube_account.nombre_canal,
            'token_valido': youtube_account.esta_autenticado(),
            'token_expira': youtube_account.token_expira.strftime('%d/%m/%Y %H:%M:%S') if youtube_account.token_expira else None,
            'tiene_refresh_token': bool(youtube_account.refresh_token),
            'suscriptores': youtube_account.suscriptores,
            'videos': youtube_account.videos_publicados,
        }
        
        return JsonResponse(status)
        
    except YouTubeAccount.DoesNotExist:
        return JsonResponse({
            'autenticado': False,
            'message': 'No hay cuenta YouTube vinculada'
        })

# ============================================
# VISTA 8: Buscar videos en YouTube
# ============================================
@login_required
def buscar_videos(request):
    """
    Buscar videos en YouTube usando la API.
    Se puede buscar por término y aplicar filtros.
    """
    print(f"[DEBUG] Buscando videos para usuario: {request.user.username}")
    
    # Obtener cuenta YouTube del usuario
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
    except YouTubeAccount.DoesNotExist:
        print(f"[ERROR] Usuario no tiene cuenta YouTube")
        return render(request, 'error.html', {
            'error': 'Cuenta no vinculada',
            'detalle': 'Debes conectar tu cuenta de YouTube primero.',
            'next_action': 'Conectar a YouTube',
            'next_url': 'youtube_login'
        })
    
    # Verificar token
    if not youtube_account.esta_autenticado():
        print(f"[WARNING] Token expirado, refrescando...")
        # Intentar refrescar token
        refresh_result = _refresh_youtube_token_internal(youtube_account)
        if not refresh_result['success']:
            return render(request, 'error.html', {
                'error': 'Sesión expirada',
                'detalle': 'Tu sesión con YouTube ha expirado. Debes reconectar.',
                'next_action': 'Reconectar',
                'next_url': 'youtube_login'
            })
    
    # Obtener parámetros de búsqueda
    query = request.GET.get('q', '')
    max_results = int(request.GET.get('max', 12))
    order = request.GET.get('order', 'relevance')
    type_filter = request.GET.get('type', 'video')
    
    videos = []
    error = None
    
    if query:
        try:
            headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
            
            # Parámetros de búsqueda
            params = {
                'part': 'snippet',
                'q': query,
                'maxResults': max_results,
                'order': order,
                'type': type_filter,
                'safeSearch': 'moderate',
            }
            
            # Añadir filtros opcionales
            if request.GET.get('publishedAfter'):
                params['publishedAfter'] = request.GET.get('publishedAfter')
            
            if request.GET.get('duration'):
                params['videoDuration'] = request.GET.get('duration')
            
            # Realizar búsqueda
            search_url = "https://www.googleapis.com/youtube/v3/search"
            print(f"[DEBUG] Buscando: {query}, max: {max_results}")
            
            response = requests.get(search_url, params=params, headers=headers, timeout=15)
            data = response.json()
            
            if 'error' in data:
                error = data.get('error', {}).get('message', 'Error desconocido')
                print(f"[ERROR] Error en búsqueda: {error}")
            else:
                videos = data.get('items', [])
                print(f"[DEBUG] Encontrados {len(videos)} videos")
                
                # Guardar en historial de búsquedas
                BusquedaVideo.objects.create(
                    usuario=request.user,
                    query=query,
                    resultado_count=len(videos),
                    parametros_busqueda=params
                )
                
        except Exception as e:
            error = f"Error al buscar videos: {str(e)}"
            print(f"[ERROR] {error}")
    
    # Obtener búsquedas recientes
    busquedas_recientes = BusquedaVideo.objects.filter(
        usuario=request.user
    ).order_by('-fecha_busqueda')[:10]
    
    context = {
        'youtube_account': youtube_account,
        'videos': videos,
        'query': query,
        'error': error,
        'max_results': max_results,
        'order': order,
        'busquedas_recientes': busquedas_recientes,
        'ordenes': [
            ('relevance', 'Relevancia'),
            ('date', 'Fecha'),
            ('rating', 'Calificación'),
            ('title', 'Título'),
            ('viewCount', 'Vistas'),
        ],
        'duraciones': [
            ('any', 'Cualquier duración'),
            ('short', 'Corta (< 4 min)'),
            ('medium', 'Media (4-20 min)'),
            ('long', 'Larga (> 20 min)'),
        ],
    }
    
    return render(request, 'buscar_videos.html', context)

# ============================================
# VISTA 9: Subir video a YouTube
# ============================================
@login_required
def subir_video(request):
    """
    Página para subir un video a YouTube.
    """
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
    except YouTubeAccount.DoesNotExist:
        return redirect('youtube_login')
    
    # Verificar token
    if not youtube_account.esta_autenticado():
        refresh_result = _refresh_youtube_token_internal(youtube_account)
        if not refresh_result['success']:
            return render(request, 'error.html', {
                'error': 'Sesión expirada',
                'detalle': 'Debes reconectar tu cuenta de YouTube.',
                'next_action': 'Reconectar',
                'next_url': 'youtube_login'
            })
    
    # Procesar formulario de subida
    if request.method == 'POST':
        return _procesar_subida_video(request, youtube_account)
    
    # Obtener categorías de YouTube para el formulario
    categorias = _obtener_categorias_youtube(youtube_account.access_token)
    
    # Obtener videos subidos recientemente
    videos_subidos = VideoSubido.objects.filter(
        youtube_account=youtube_account
    ).order_by('-creado')[:5]
    
    context = {
        'youtube_account': youtube_account,
        'categorias': categorias,
        'videos_subidos': videos_subidos,
        'max_size_mb': 128,  # Límite de YouTube
        'formatos_permitidos': ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm'],
    }
    
    return render(request, 'subir_video.html', context)

# ============================================
# VISTA 10: Procesar subida de video (AJAX)
# ============================================
@login_required
def procesar_subida_ajax(request):
    """
    Endpoint AJAX para procesar la subida de videos.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
    except YouTubeAccount.DoesNotExist:
        return JsonResponse({'error': 'Cuenta no vinculada'}, status=400)
    
    # Verificar token
    if not youtube_account.esta_autenticado():
        return JsonResponse({
            'error': 'Token expirado',
            'needs_reauth': True
        }, status=401)
    
    # Procesar archivo
    if 'video_file' not in request.FILES:
        return JsonResponse({'error': 'No se envió archivo'}, status=400)
    
    video_file = request.FILES['video_file']
    
    # Validar archivo
    if not _validar_archivo_video(video_file):
        return JsonResponse({'error': 'Archivo no válido'}, status=400)
    
    # Crear registro de video subido
    video_subido = VideoSubido.objects.create(
        youtube_account=youtube_account,
        titulo=request.POST.get('titulo', video_file.name),
        descripcion=request.POST.get('descripcion', ''),
        etiquetas=request.POST.get('etiquetas', ''),
        categoria_id=request.POST.get('categoria', '22'),
        privacidad=request.POST.get('privacidad', 'private'),
        archivo_path=video_file.name,
        archivo_size=video_file.size,
        estado='pending'
    )
    
    # Guardar archivo temporalmente
    import os
    from django.conf import settings
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(request.user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{video_subido.id}_{video_file.name}")
    
    with open(file_path, 'wb+') as destination:
        for chunk in video_file.chunks():
            destination.write(chunk)
    
    video_subido.archivo_path = file_path
    video_subido.save()
    
    # Iniciar subida asíncrona (en background)
    import threading
    thread = threading.Thread(
        target=_subir_video_youtube,
        args=(video_subido, youtube_account.access_token)
    )
    thread.daemon = True
    thread.start()
    
    return JsonResponse({
        'success': True,
        'video_id': video_subido.id,
        'message': 'Video en cola para subida',
        'estado': video_subido.get_estado_display()
    })

# ============================================
# VISTA 11: Estado de subida de video
# ============================================
@login_required
def estado_subida_video(request, video_id):
    """
    Obtener estado de un video que se está subiendo.
    """
    try:
        video_subido = VideoSubido.objects.get(
            id=video_id,
            youtube_account__user=request.user
        )
        
        return JsonResponse({
            'id': video_subido.id,
            'titulo': video_subido.titulo,
            'estado': video_subido.estado,
            'estado_display': video_subido.get_estado_display(),
            'mensaje_error': video_subido.mensaje_error,
            'youtube_video_id': video_subido.youtube_video_id,
            'youtube_url': video_subido.get_video_url(),
            'creado': video_subido.creado.strftime('%d/%m/%Y %H:%M:%S'),
            'actualizado': video_subido.actualizado.strftime('%d/%m/%Y %H:%M:%S'),
        })
        
    except VideoSubido.DoesNotExist:
        return JsonResponse({'error': 'Video no encontrado'}, status=404)

# ============================================
# VISTA 12: Listar videos subidos
# ============================================
@login_required
def mis_videos_subidos(request):
    """
    Listar todos los videos subidos por el usuario.
    """
    try:
        youtube_account = YouTubeAccount.objects.get(user=request.user)
    except YouTubeAccount.DoesNotExist:
        return redirect('youtube_login')
    
    # Obtener parámetros de filtro
    buscar = request.GET.get('buscar', '')
    estado = request.GET.get('estado', '')
    
    # Filtrar videos subidos
    videos_query = VideoSubido.objects.filter(
        youtube_account=youtube_account
    ).order_by('-creado')
    
    # Aplicar filtros
    if buscar:
        videos_query = videos_query.filter(
            Q(titulo__icontains=buscar) |
            Q(descripcion__icontains=buscar)
        )
    
    if estado:
        videos_query = videos_query.filter(estado=estado)
    
    # Calcular estadísticas
    total_videos = videos_query.count()
    publicados_count = videos_query.filter(estado='published').count()
    proceso_count = videos_query.filter(
        estado__in=['uploading', 'processing', 'pending']
    ).count()
    
    total_size = videos_query.aggregate(
        total=Sum('archivo_size')
    )['total'] or 0
    
    # Paginación
    paginator = Paginator(videos_query, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'youtube_account': youtube_account,
        'videos': page_obj,
        'total_videos': total_videos,
        'publicados_count': publicados_count,
        'proceso_count': proceso_count,
        'total_size': total_size,
        'search_term': buscar,
        'selected_estado': estado,
    }
    
    # IMPORTANTE: Cambiar el template a usar
    return render(request, 'mis_videos_subidos.html', context)

# ============================================
# FUNCIONES AUXILIARES (privadas)
# ============================================

def _refresh_youtube_token_internal(youtube_account):
    """
    Función interna para refrescar token.
    """
    try:
        if not youtube_account.refresh_token:
            return {'success': False, 'error': 'No hay refresh token'}
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': settings.YOUTUBE_CLIENT_ID,
            'client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'refresh_token': youtube_account.refresh_token,
            'grant_type': 'refresh_token',
        }
        
        response = requests.post(token_url, data=token_data, timeout=10)
        token_response = response.json()
        
        if 'error' in token_response:
            return {'success': False, 'error': token_response.get('error_description')}
        
        # Actualizar token
        youtube_account.access_token = token_response.get('access_token')
        expires_in = token_response.get('expires_in', 3600)
        youtube_account.token_expira = datetime.now() + timedelta(seconds=expires_in)
        youtube_account.save()
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _obtener_categorias_youtube(access_token):
    """
    Obtener lista de categorías de videos de YouTube.
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        url = "https://www.googleapis.com/youtube/v3/videoCategories"
        params = {
            'part': 'snippet',
            'regionCode': 'US',  # Puedes cambiar según región
            'hl': 'es'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        categorias = []
        if 'items' in data:
            for item in data['items']:
                categorias.append({
                    'id': item['id'],
                    'title': item['snippet'].get('title', f'Categoría {item["id"]}')
                })
        
        return categorias
        
    except Exception as e:
        print(f"[WARNING] Error al obtener categorías: {e}")
        # Categorías por defecto
        return [
            {'id': '22', 'title': 'Personas y blogs'},
            {'id': '20', 'title': 'Gaming'},
            {'id': '10', 'title': 'Música'},
            {'id': '1', 'title': 'Películas y animación'},
        ]

def _validar_archivo_video(video_file):
    """
    Validar archivo de video antes de subir.
    """
    # Verificar tamaño (máximo 128MB para API simple)
    max_size = 128 * 1024 * 1024  # 128MB
    if video_file.size > max_size:
        return False
    
    # Verificar extensión
    allowed_extensions = ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.webm']
    import os
    ext = os.path.splitext(video_file.name)[1].lower()
    
    if ext not in allowed_extensions:
        return False
    
    # Verificar tipo MIME (opcional)
    allowed_mimes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 
                     'video/x-ms-wmv', 'video/x-flv', 'video/webm']
    
    # Django no siempre detecta bien MIME de videos
    # Podrías usar python-magic si es necesario
    
    return True

def _subir_video_youtube(video_subido, access_token):
    """
    Función para subir video a YouTube en background.
    """
    import os
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    
    try:
        # Actualizar estado
        video_subido.estado = 'uploading'
        video_subido.inicio_subida = datetime.now()
        video_subido.save()
        
        # Configurar credenciales
        credentials = Credentials(token=access_token)
        
        # Crear servicio de YouTube
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Preparar metadatos del video
        body = {
            'snippet': {
                'title': video_subido.titulo,
                'description': video_subido.descripcion,
                'tags': video_subido.etiquetas.split(',') if video_subido.etiquetas else [],
                'categoryId': video_subido.categoria_id,
            },
            'status': {
                'privacyStatus': video_subido.privacidad,
                'selfDeclaredMadeForKids': False,
            }
        }
        
        # Subir video
        media = MediaFileUpload(
            video_subido.archivo_path,
            chunksize=1024*1024,
            resumable=True
        )
        
        # Llamada a la API
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = request.execute()
        
        # Actualizar con ID de YouTube
        video_subido.youtube_video_id = response['id']
        video_subido.estado = 'processing'
        video_subido.save()
        
        # Esperar a que termine de procesar (opcional)
        import time
        for i in range(30):  # Esperar máximo 5 minutos
            time.sleep(10)
            
            # Verificar estado
            video_response = youtube.videos().list(
                part='status',
                id=video_subido.youtube_video_id
            ).execute()
            
            status = video_response['items'][0]['status']['uploadStatus']
            
            if status == 'processed':
                video_subido.estado = 'published'
                break
            elif status == 'failed':
                video_subido.estado = 'failed'
                video_subido.mensaje_error = 'Falló el procesamiento en YouTube'
                break
        
        video_subido.fin_subida = datetime.now()
        video_subido.save()
        
        print(f"[INFO] Video subido exitosamente: {video_subido.youtube_video_id}")
        
    except Exception as e:
        print(f"[ERROR] Error al subir video: {e}")
        video_subido.estado = 'failed'
        video_subido.mensaje_error = str(e)
        video_subido.fin_subida = datetime.now()
        video_subido.save()

def _procesar_subida_video(request, youtube_account):
    """
    Procesar formulario de subida (para formularios normales, no AJAX).
    """
    # Esta función maneja el formulario tradicional
    # La versión AJAX es preferida para archivos grandes
    
    if 'video_file' not in request.FILES:
        return render(request, 'subir_video.html', {
            'youtube_account': youtube_account,
            'error': 'Debes seleccionar un archivo de video'
        })
    
    video_file = request.FILES['video_file']
    
    # Validar archivo
    if not _validar_archivo_video(video_file):
        return render(request, 'subir_video.html', {
            'youtube_account': youtube_account,
            'error': 'Archivo no válido. Verifica formato y tamaño (<128MB)'
        })
    
    # Crear registro
    video_subido = VideoSubido.objects.create(
        youtube_account=youtube_account,
        titulo=request.POST.get('titulo', video_file.name),
        descripcion=request.POST.get('descripcion', ''),
        etiquetas=request.POST.get('etiquetas', ''),
        categoria_id=request.POST.get('categoria', '22'),
        privacidad=request.POST.get('privacidad', 'private'),
        archivo_path=video_file.name,
        archivo_size=video_file.size,
        estado='pending'
    )
    
    # Guardar archivo
    import os
    from django.conf import settings
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(request.user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{video_subido.id}_{video_file.name}")
    
    with open(file_path, 'wb+') as destination:
        for chunk in video_file.chunks():
            destination.write(chunk)
    
    video_subido.archivo_path = file_path
    video_subido.save()
    
    # Iniciar subida en background
    import threading
    thread = threading.Thread(
        target=_subir_video_youtube,
        args=(video_subido, youtube_account.access_token)
    )
    thread.daemon = True
    thread.start()
    
    return redirect('estado_subida', video_id=video_subido.id)

# ============================================
# VISTA 13: Listar mis videos
# ============================================
@login_required
def mis_videos(request):
    """
    Vista para listar los videos del usuario.
    """
    # Obtener parámetros de filtro
    buscar = request.GET.get('buscar', '')
    categoria = request.GET.get('categoria', '')
    page_number = request.GET.get('page', 1)
    
    # Filtrar videos del usuario
    videos_query = Video.objects.filter(
        agregado_por=request.user
    ).order_by('-fecha_publicacion')
    
    # Aplicar filtros
    if buscar:
        videos_query = videos_query.filter(
            Q(titulo__icontains=buscar) |
            Q(descripcion__icontains=buscar)
        )
    
    if categoria:
        videos_query = videos_query.filter(categoria=categoria)
    
    # Calcular estadísticas totales
    total_views = videos_query.aggregate(total=Sum('vistas'))['total'] or 0
    total_likes = videos_query.aggregate(total=Sum('likes'))['total'] or 0
    total_comments = videos_query.aggregate(total=Sum('comentarios'))['total'] or 0
    
    # Paginación
    paginator = Paginator(videos_query, 10)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'videos': page_obj,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'search_term': buscar,
        'selected_category': categoria,
        'categories': [
            ('programacion', 'Programación'),
            ('bases_datos', 'Bases de Datos'),
            ('redes', 'Redes'),
            ('seguridad', 'Seguridad'),
            ('otro', 'Otro'),
        ]
    }
    
    return render(request, 'mis_videos.html', context)

# ============================================
# VISTA 14: Detalle de video
# ============================================
@login_required
def detalle_video(request, video_id):
    """
    Vista para mostrar detalles de un video específico.
    Incluye player embebido, estadísticas y controles.
    """
    print(f"[DEBUG] Mostrando detalle del video ID: {video_id}")
    
    try:
        # Obtener video
        video = Video.objects.get(id=video_id, agregado_por=request.user)
        
        # Obtener o crear gestor de video
        try:
            video_manager = VideoManager.objects.get(
                video=video,
                usuario_propietario=request.user
            )
        except VideoManager.DoesNotExist:
            video_manager = VideoManager.objects.create(
                video=video,
                usuario_propietario=request.user
            )
        
        # Obtener estadísticas recientes
        estadisticas_recientes = EstadisticasVideo.objects.filter(
            video=video
        ).order_by('-fecha')[:7]  # Últimos 7 días
        
        # Preparar datos para gráficos
        fechas = []
        vistas_diarias = []
        likes_diarios = []
        
        for estadistica in estadisticas_recientes:
            fechas.append(estadistica.fecha.strftime('%d/%m'))
            vistas_diarias.append(estadistica.vistas)
            likes_diarios.append(estadistica.likes)
        
        # Video relacionado (misma categoría)
        videos_relacionados = Video.objects.filter(
            categoria=video.categoria,
            agregado_por=request.user
        ).exclude(id=video.id)[:4]
        
        context = {
            'video': video,
            'video_manager': video_manager,
            'videos_relacionados': videos_relacionados,
            'estadisticas_recientes': estadisticas_recientes,
            'fechas_json': json.dumps(fechas),
            'vistas_diarias_json': json.dumps(vistas_diarias),
            'likes_diarios_json': json.dumps(likes_diarios),
        }
        
        print(f"[DEBUG] Video encontrado: {video.titulo}")
        return render(request, 'detalle_video.html', context)
        
    except Video.DoesNotExist:
        print(f"[ERROR] Video no encontrado o no autorizado: {video_id}")
        return render(request, 'error.html', {
            'error': 'Video no encontrado',
            'detalle': 'El video que buscas no existe o no tienes permisos para verlo.',
            'next_action': 'Volver a mis videos',
            'next_url': 'mis_videos'
        })

# ============================================
# VISTA 15: Actualizar estadísticas de video
# ============================================
@login_required
def actualizar_estadisticas_video(request, video_id):
    """
    Endpoint para actualizar estadísticas de un video desde YouTube.
    """
    print(f"[DEBUG] Actualizando estadísticas para video ID: {video_id}")
    
    try:
        video = Video.objects.get(id=video_id, agregado_por=request.user)
        
        # Intentar obtener cuenta YouTube del usuario
        try:
            youtube_account = YouTubeAccount.objects.get(user=request.user)
            
            if youtube_account.esta_autenticado():
                # Usar YouTube API para obtener estadísticas actualizadas
                headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
                
                videos_url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    'part': 'statistics,snippet,contentDetails',
                    'id': video.youtube_id,
                }
                
                response = requests.get(videos_url, params=params, headers=headers, timeout=10)
                data = response.json()
                
                if 'items' in data and data['items']:
                    video_data = data['items'][0]
                    stats = video_data.get('statistics', {})
                    snippet = video_data.get('snippet', {})
                    content_details = video_data.get('contentDetails', {})
                    
                    # Actualizar estadísticas
                    video.vistas = int(stats.get('viewCount', 0))
                    video.likes = int(stats.get('likeCount', 0))
                    video.comentarios = int(stats.get('commentCount', 0))
                    
                    # Actualizar título y descripción si cambiaron
                    video.titulo = snippet.get('title', video.titulo)
                    video.descripcion = snippet.get('description', video.descripcion)
                    
                    # Actualizar duración si está disponible
                    if 'duration' in content_details:
                        # Convertir duración ISO 8601 a formato legible
                        video.duracion = content_details['duration']
                    
                    video.save()
                    
                    # Registrar estadística diaria
                    hoy = datetime.now().date()
                    try:
                        estadistica = EstadisticasVideo.objects.get(video=video, fecha=hoy)
                        # Calcular crecimiento
                        estadistica.crecimiento_vistas = video.vistas - estadistica.vistas
                        estadistica.vistas = video.vistas
                        estadistica.likes = video.likes
                        estadistica.comentarios = video.comentarios
                        estadistica.save()
                    except EstadisticasVideo.DoesNotExist:
                        EstadisticasVideo.objects.create(
                            video=video,
                            fecha=hoy,
                            vistas=video.vistas,
                            likes=video.likes,
                            comentarios=video.comentarios,
                            crecimiento_vistas=0
                        )
                    
                    print(f"[DEBUG] Estadísticas actualizadas para video: {video.youtube_id}")
                    
                    return JsonResponse({
                        'success': True,
                        'vistas': video.vistas,
                        'likes': video.likes,
                        'comentarios': video.comentarios,
                        'titulo': video.titulo,
                        'actualizado': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                    })
            
            else:
                return JsonResponse({
                    'error': 'Token de YouTube expirado',
                    'needs_reauth': True
                }, status=401)
                
        except YouTubeAccount.DoesNotExist:
            # Si no hay cuenta YouTube, solo retornar datos actuales
            return JsonResponse({
                'success': True,
                'vistas': video.vistas,
                'likes': video.likes,
                'comentarios': video.comentarios,
                'titulo': video.titulo,
                'message': 'No se pudo actualizar desde YouTube (cuenta no vinculada)'
            })
            
    except Video.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)
    except Exception as e:
        print(f"[ERROR] Error al actualizar estadísticas: {e}")
        return JsonResponse({
            'error': f'Error inesperado: {str(e)}',
            'success': False
        }, status=500)

# ============================================
# VISTA 16: Toggle favorito de video
# ============================================
@login_required
def toggle_favorito_video(request, video_id):
    """
    Marcar/desmarcar un video como favorito.
    """
    try:
        video = Video.objects.get(id=video_id, agregado_por=request.user)
        
        try:
            video_manager = VideoManager.objects.get(
                video=video,
                usuario_propietario=request.user
            )
        except VideoManager.DoesNotExist:
            video_manager = VideoManager.objects.create(
                video=video,
                usuario_propietario=request.user
            )
        
        # Cambiar estado de favorito
        video_manager.favorito = not video_manager.favorito
        video_manager.save()
        
        return JsonResponse({
            'success': True,
            'favorito': video_manager.favorito,
            'message': 'Video marcado como favorito' if video_manager.favorito else 'Video eliminado de favoritos'
        })
        
    except Video.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)

# ============================================
# VISTA 17: Guardar notas del video
# ============================================
@login_required
def guardar_notas_video(request, video_id):
    """
    Guardar notas personales para un video.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        video = Video.objects.get(id=video_id, agregado_por=request.user)
        
        try:
            video_manager = VideoManager.objects.get(
                video=video,
                usuario_propietario=request.user
            )
        except VideoManager.DoesNotExist:
            video_manager = VideoManager.objects.create(
                video=video,
                usuario_propietario=request.user
            )
        
        notas = request.POST.get('notas', '')
        video_manager.notas = notas
        video_manager.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notas guardadas exitosamente'
        })
        
    except Video.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)

# ============================================
# VISTA 18: Eliminar video
# ============================================
@login_required
def eliminar_video(request, video_id):
    """
    Eliminar un video de la biblioteca del usuario.
    """
    try:
        video = Video.objects.get(id=video_id, agregado_por=request.user)
        
        # Eliminar gestor de video si existe
        VideoManager.objects.filter(video=video, usuario_propietario=request.user).delete()
        
        # Si el video no está siendo usado por otros usuarios, eliminarlo completamente
        if not Video.objects.filter(youtube_id=video.youtube_id).exclude(id=video_id).exists():
            video.delete()
        else:
            # Solo desvincular del usuario actual
            video.agregado_por = None
            video.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Video eliminado exitosamente'
        })
        
    except Video.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _formatear_duracion(duracion_iso):
    """
    Convertir duración ISO 8601 a formato legible.
    Ej: PT15M30S -> 15:30
    """
    if not duracion_iso:
        return "N/A"
    
    import re
    
    # Extraer horas, minutos y segundos
    horas = re.search(r'(\d+)H', duracion_iso)
    minutos = re.search(r'(\d+)M', duracion_iso)
    segundos = re.search(r'(\d+)S', duracion_iso)
    
    h = int(horas.group(1)) if horas else 0
    m = int(minutos.group(1)) if minutos else 0
    s = int(segundos.group(1)) if segundos else 0
    
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def _obtener_estadisticas_grafico(video):
    """
    Obtener datos para gráficos de estadísticas.
    """
    estadisticas = EstadisticasVideo.objects.filter(video=video).order_by('fecha')[:30]
    
    fechas = []
    vistas = []
    likes = []
    
    for estadistica in estadisticas:
        fechas.append(estadistica.fecha.strftime('%d/%m'))
        vistas.append(estadistica.vistas)
        likes.append(estadistica.likes)
    
    return {
        'fechas': fechas,
        'vistas': vistas,
        'likes': likes
    }

# ============================================
# VISTA 19: Guardar video desde búsqueda (AJAX)
# ============================================
@csrf_exempt
@login_required
def guardar_video_busqueda(request):
    """
    Endpoint AJAX para guardar un video desde los resultados de búsqueda.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        titulo = data.get('titulo', '')
        
        if not video_id:
            return JsonResponse({'success': False, 'error': 'ID de video requerido'})
        
        # Verificar si ya existe
        if VideoGuardado.objects.filter(video_id=video_id, usuario=request.user).exists():
            return JsonResponse({
                'success': False, 
                'error': 'Ya tienes este video guardado',
                'video_id': video_id
            })
        
        # Obtener información completa del video de YouTube API
        video_info = _obtener_info_video_youtube(video_id, request.user)
        
        # Crear video guardado
        video_guardado = VideoGuardado.objects.create(
            video_id=video_id,
            usuario=request.user,
            titulo=video_info.get('titulo', titulo),
            descripcion=video_info.get('descripcion', ''),
            canal_nombre=video_info.get('canal_nombre', ''),
            canal_id=video_info.get('canal_id', ''),
            url_thumbnail=video_info.get('url_thumbnail', ''),
            fecha_publicacion=video_info.get('fecha_publicacion'),
            vistas=video_info.get('vistas', 0),
            likes=video_info.get('likes', 0),
            comentarios=video_info.get('comentarios', 0),
            duracion=video_info.get('duracion', ''),
            categoria=video_info.get('categoria', ''),
            etiquetas=video_info.get('etiquetas', ''),
        )
        
        return JsonResponse({
            'success': True, 
            'id': video_guardado.id,
            'titulo': video_guardado.titulo,
            'message': 'Video guardado exitosamente'
        })
        
    except Exception as e:
        print(f"[ERROR] Error al guardar video: {e}")
        return JsonResponse({
            'success': False, 
            'error': f'Error al guardar video: {str(e)}'
        }, status=500)


# ============================================
# VISTA 20: Mis videos guardados
# ============================================
# En views.py, modifica la vista mis_videos_guardados:
@login_required
def mis_videos_guardados(request):
    """
    Lista de videos guardados por el usuario desde búsquedas.
    """
    print(f"[DEBUG] Mostrando videos guardados para usuario: {request.user.username}")
    
    # Obtener parámetros de filtro
    buscar = request.GET.get('buscar', '')
    categoria = request.GET.get('categoria', '')
    favorito = request.GET.get('favorito', '')
    page_number = request.GET.get('page', 1)
    
    # Filtrar videos guardados del usuario
    videos_query = VideoGuardado.objects.filter(
        usuario=request.user
    ).order_by('-fecha_guardado')
    
    # Aplicar filtros
    if buscar:
        videos_query = videos_query.filter(
            Q(titulo__icontains=buscar) |
            Q(descripcion__icontains=buscar) |
            Q(canal_nombre__icontains=buscar)
        )
    
    if categoria:
        videos_query = videos_query.filter(categoria=categoria)
    
    if favorito == 'true':
        videos_query = videos_query.filter(favorito=True)
    
    # Calcular estadísticas totales
    total_videos = videos_query.count()
    total_views = videos_query.aggregate(total=Sum('vistas'))['total'] or 0
    total_likes = videos_query.aggregate(total=Sum('likes'))['total'] or 0
    total_comments = videos_query.aggregate(total=Sum('comentarios'))['total'] or 0
    
    # Obtener categorías únicas para el filtro
    categorias_disponibles = VideoGuardado.objects.filter(
        usuario=request.user
    ).exclude(categoria__isnull=True).exclude(categoria='').values_list(
        'categoria', flat=True
    ).distinct()
    
    # Paginación
    paginator = Paginator(videos_query, 12)
    page_obj = paginator.get_page(page_number)
    
    # NO necesitamos video_managers como diccionario separado
    # porque cada VideoGuardado ya tiene su campo 'favorito'
    
    context = {
        'videos': page_obj,
        'total_videos': total_videos,
        'total_views': total_views,
        'total_likes': total_likes,
        'total_comments': total_comments,
        'search_term': buscar,
        'selected_category': categoria,
        'selected_favorito': favorito,
        'categories': [(cat, cat) for cat in categorias_disponibles if cat],
        # 'video_managers': {} ya no es necesario
    }
    
    return render(request, 'mis_videos.html', context)


# ============================================
# VISTA 21: Detalle de video guardado
# ============================================
@login_required
def detalle_video_guardado(request, video_id):
    """
    Detalle completo de un video guardado, con player embebido.
    """
    print(f"[DEBUG] Mostrando detalle de video guardado ID: {video_id}")
    
    try:
        # Obtener video guardado
        video = VideoGuardado.objects.get(id=video_id, usuario=request.user)
        
        # Intentar actualizar información desde YouTube
        try:
            _actualizar_info_video_youtube(video, request.user)
        except Exception as e:
            print(f"[WARNING] No se pudo actualizar info de YouTube: {e}")
        
        # Obtener videos relacionados (misma categoría)
        videos_relacionados = []
        if video.categoria:
            videos_relacionados = VideoGuardado.objects.filter(
                usuario=request.user,
                categoria=video.categoria
            ).exclude(id=video_id)[:4]
        
        context = {
            'video': {
                'titulo': video.titulo,
                'descripcion': video.descripcion or '',
                'youtube_id': video.video_id,
                'vistas': video.vistas,
                'likes': video.likes,
                'comentarios': video.comentarios,
                'duracion': video.duracion or 'N/A',
                'canal_nombre': video.canal_nombre or '',
                'canal_id': video.canal_id or '',
                'fecha_publicacion': video.fecha_publicacion,
                'categoria': video.categoria or '',
                'etiquetas': video.etiquetas or '',
                'url_video': video.get_video_url(),
                'url_thumbnail': video.url_thumbnail or '',
                'actualizado': video.ultima_actualizacion,
                'agregado_por': request.user.username,
            },
            'videos_relacionados': videos_relacionados,
        }
        
        # Añadir métodos necesarios para el template
        class VideoProxy:
            def __init__(self, data):
                self.__dict__.update(data)
            
            def get_embed_url(self):
                return f"https://www.youtube.com/embed/{self.youtube_id}"
            
            def get_video_url(self):
                return self.url_video
        
        context['video'] = VideoProxy(context['video'])
        
        return render(request, 'detalle_video.html', context)
        
    except VideoGuardado.DoesNotExist:
        print(f"[ERROR] Video guardado no encontrado: {video_id}")
        return render(request, 'error.html', {
            'error': 'Video no encontrado',
            'detalle': 'El video que buscas no existe o no tienes permisos para verlo.',
            'next_action': 'Volver a mis videos',
            'next_url': 'mis_videos_guardados'
        })


# ============================================
# VISTA 22: Toggle favorito video guardado
# ============================================
@login_required
def toggle_favorito_video_guardado(request, video_id):
    """
    Marcar/desmarcar un video guardado como favorito.
    """
    try:
        video = VideoGuardado.objects.get(id=video_id, usuario=request.user)
        
        # Cambiar estado de favorito
        video.favorito = not video.favorito
        video.save()
        
        return JsonResponse({
            'success': True,
            'favorito': video.favorito,
            'message': 'Video marcado como favorito' if video.favorito else 'Video eliminado de favoritos'
        })
        
    except VideoGuardado.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)


# ============================================
# VISTA 23: Actualizar video guardado desde YouTube
# ============================================
@login_required
def actualizar_video_guardado(request, video_id):
    """
    Actualizar información de un video guardado desde YouTube API.
    """
    try:
        video = VideoGuardado.objects.get(id=video_id, usuario=request.user)
        
        try:
            # Obtener cuenta YouTube del usuario para usar API
            youtube_account = YouTubeAccount.objects.get(user=request.user)
            
            if youtube_account.esta_autenticado():
                # Actualizar información desde YouTube
                _actualizar_info_video_youtube(video, request.user)
                
                return JsonResponse({
                    'success': True,
                    'vistas': video.vistas,
                    'likes': video.likes,
                    'comentarios': video.comentarios,
                    'titulo': video.titulo,
                    'actualizado': video.ultima_actualizacion.strftime('%d/%m/%Y %H:%M:%S'),
                    'message': 'Información actualizada desde YouTube'
                })
            else:
                return JsonResponse({
                    'error': 'Token de YouTube expirado',
                    'needs_reauth': True
                }, status=401)
                
        except YouTubeAccount.DoesNotExist:
            # Si no hay cuenta YouTube, intentar usar API pública
            try:
                _actualizar_info_video_public_api(video)
                
                return JsonResponse({
                    'success': True,
                    'vistas': video.vistas,
                    'likes': video.likes,
                    'comentarios': video.comentarios,
                    'actualizado': video.ultima_actualizacion.strftime('%d/%m/%Y %H:%M:%S'),
                    'message': 'Información actualizada (API pública)'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'No se pudo actualizar: {str(e)}'
                })
            
    except VideoGuardado.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)
    except Exception as e:
        print(f"[ERROR] Error al actualizar video: {e}")
        return JsonResponse({
            'error': f'Error inesperado: {str(e)}',
            'success': False
        }, status=500)


# ============================================
# VISTA 24: Eliminar video guardado
# ============================================
@login_required
def eliminar_video_guardado(request, video_id):
    """
    Eliminar un video de la lista de videos guardados.
    """
    try:
        video = VideoGuardado.objects.get(id=video_id, usuario=request.user)
        video.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Video eliminado exitosamente'
        })
        
    except VideoGuardado.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)


# ============================================
# VISTA 25: Guardar notas de video guardado
# ============================================
@login_required
def guardar_notas_video_guardado(request, video_id):
    """
    Guardar notas personales para un video guardado.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        video = VideoGuardado.objects.get(id=video_id, usuario=request.user)
        
        notas = request.POST.get('notas', '')
        video.notas = notas
        video.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notas guardadas exitosamente'
        })
        
    except VideoGuardado.DoesNotExist:
        return JsonResponse({
            'error': 'Video no encontrado',
            'success': False
        }, status=404)


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def _obtener_info_video_youtube(video_id, user):
    """
    Obtener información de un video desde YouTube API.
    """
    try:
        # Intentar usar la cuenta YouTube del usuario
        youtube_account = YouTubeAccount.objects.get(user=user)
        
        if youtube_account.esta_autenticado():
            headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
            
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video_id,
            }
            
            response = requests.get(videos_url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if 'items' in data and data['items']:
                item = data['items'][0]
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                
                # Formatear fecha
                fecha_str = snippet.get('publishedAt', '')
                fecha_publicacion = None
                if fecha_str:
                    try:
                        fecha_publicacion = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Obtener mejor thumbnail
                thumbnails = snippet.get('thumbnails', {})
                thumbnail_url = ''
                for size in ['maxres', 'high', 'medium', 'default']:
                    if size in thumbnails:
                        thumbnail_url = thumbnails[size].get('url', '')
                        if thumbnail_url:
                            break
                
                # Convertir duración ISO 8601
                duracion_iso = content_details.get('duration', '')
                duracion_formateada = _formatear_duracion_iso(duracion_iso)
                
                return {
                    'titulo': snippet.get('title', ''),
                    'descripcion': snippet.get('description', ''),
                    'canal_nombre': snippet.get('channelTitle', ''),
                    'canal_id': snippet.get('channelId', ''),
                    'url_thumbnail': thumbnail_url,
                    'fecha_publicacion': fecha_publicacion,
                    'vistas': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comentarios': int(stats.get('commentCount', 0)),
                    'duracion': duracion_formateada,
                    'categoria': snippet.get('categoryId', ''),
                    'etiquetas': ','.join(snippet.get('tags', [])),
                }
        
    except YouTubeAccount.DoesNotExist:
        print(f"[INFO] Usuario {user.username} no tiene cuenta YouTube, usando API pública")
    
    # Si no hay cuenta YouTube o falló, usar información mínima
    return {
        'titulo': '',
        'descripcion': '',
        'canal_nombre': '',
        'canal_id': '',
        'url_thumbnail': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
        'fecha_publicacion': None,
        'vistas': 0,
        'likes': 0,
        'comentarios': 0,
        'duracion': '',
        'categoria': '',
        'etiquetas': '',
    }


def _actualizar_info_video_youtube(video, user):
    """
    Actualizar información de un video desde YouTube API.
    """
    try:
        youtube_account = YouTubeAccount.objects.get(user=user)
        
        if youtube_account.esta_autenticado():
            headers = {'Authorization': f'Bearer {youtube_account.access_token}'}
            
            videos_url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': video.video_id,
            }
            
            response = requests.get(videos_url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if 'items' in data and data['items']:
                item = data['items'][0]
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                content_details = item.get('contentDetails', {})
                
                # Actualizar información
                video.titulo = snippet.get('title', video.titulo)
                video.descripcion = snippet.get('description', video.descripcion)
                video.canal_nombre = snippet.get('channelTitle', video.canal_nombre)
                video.canal_id = snippet.get('channelId', video.canal_id)
                
                # Thumbnail
                thumbnails = snippet.get('thumbnails', {})
                for size in ['maxres', 'high', 'medium', 'default']:
                    if size in thumbnails:
                        video.url_thumbnail = thumbnails[size].get('url', video.url_thumbnail)
                        if video.url_thumbnail:
                            break
                
                # Estadísticas
                video.vistas = int(stats.get('viewCount', video.vistas))
                video.likes = int(stats.get('likeCount', video.likes))
                video.comentarios = int(stats.get('commentCount', video.comentarios))
                
                # Duración
                duracion_iso = content_details.get('duration', '')
                video.duracion = _formatear_duracion_iso(duracion_iso)
                
                # Categoría y etiquetas
                video.categoria = snippet.get('categoryId', video.categoria)
                video.etiquetas = ','.join(snippet.get('tags', []))
                
                video.save()
                print(f"[DEBUG] Video actualizado: {video.video_id}")
                
    except Exception as e:
        print(f"[WARNING] Error al actualizar video desde YouTube: {e}")


def _actualizar_info_video_public_api(video):
    """
    Intentar obtener información básica usando API pública (sin autenticación).
    Esto es limitado pero puede funcionar para estadísticas básicas.
    """
    try:
        # Esta es una técnica simple para obtener info básica
        # Nota: YouTube API requiere autenticación para la mayoría de endpoints
        # Podrías usar web scraping o APIs de terceros aquí si es necesario
        pass
        
    except Exception as e:
        print(f"[WARNING] Error en API pública: {e}")


def _formatear_duracion_iso(duracion_iso):
    """
    Convertir duración ISO 8601 a formato legible.
    Ej: PT1H15M30S -> 01:15:30
    """
    if not duracion_iso:
        return ""
    
    # Extraer horas, minutos y segundos usando regex
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duracion_iso)
    
    if not match:
        return duracion_iso
    
    horas = int(match.group(1) or 0)
    minutos = int(match.group(2) or 0)
    segundos = int(match.group(3) or 0)
    
    if horas > 0:
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    return f"{minutos:02d}:{segundos:02d}"