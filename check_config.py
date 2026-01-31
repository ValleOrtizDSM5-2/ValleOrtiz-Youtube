# check_config.py
import os
import sys

# Añade el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_project.settings')

import django
django.setup()

from django.conf import settings

print("=" * 50)
print("VERIFICACIÓN DE CONFIGURACIÓN YOUTUBE API")
print("=" * 50)

print(f"✅ Client ID configurado: {'SÍ' if settings.YOUTUBE_CLIENT_ID else 'NO'}")
print(f"✅ Client Secret configurado: {'SÍ' if settings.YOUTUBE_CLIENT_SECRET else 'NO'}")
print(f"✅ Redirect URI: {settings.YOUTUBE_REDIRECT_URI}")
print(f"✅ Scopes: {settings.YOUTUBE_SCOPES}")

# Verificar que la URI termine correctamente
if settings.YOUTUBE_REDIRECT_URI.endswith('/oauth/callback/'):
    print("✅ Redirect URI termina correctamente con '/oauth/callback/'")
else:
    print(f"❌ Redirect URI NO termina correctamente: {settings.YOUTUBE_REDIRECT_URI}")

print("=" * 50)
print("INSTRUCCIONES FINALES:")
print("1. Asegúrate de que la URI en Google Cloud Console coincida EXACTAMENTE")
print("2. Usa SOLO una URI (localhost O 127.0.0.1) a la vez")
print("3. Reinicia el servidor después de cambios")
print("=" * 50)