import telebot
import requests
from functools import wraps
from datetime import datetime, timedelta
import os
import logging
from telebot import TeleBot
import base64
from io import BytesIO

# Configuración
BOT_TOKEN = '7280597025:AAEHXfJUoh5zcVKJSRH3XdgzbmOYeydnZPE'
# Tokens para las diferentes IPs de Render
API_TOKENS = {
    '35.160.120.126': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpcCI6IjM1LjE2MC4xMjAuMTI2IiwicGxhdGZvcm0iOiJBUEkiLCJ1c3VhcmlvIjp7Il9pZCI6IjY4NjhiYTIwMzAyNzc4YTA5Mjc2ZDU0NSIsIm5hbWUiOiJraW5nbG90dXNwIiwicmFuZ28iOiJ1c2VyIiwic3BhbSI6MzAsImNfZXhwaXJ5IjoxNzU0Mjg1OTg4fSwiaWF0IjoxNzUzMjUwNzMxLCJleHAiOjE3NTQyMDExMzF9.yRrxcB1bXsgED99BuLPidB4YXFE8-MsoebYZDWiFG9DsRWqqwwOJ0WNZT-RinMt0eA_IKjllzGm_WHo0vLfeVQ',
    '44.233.151.27': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpcCI6IjQ0LjIzMy4xNTEuMjciLCJwbGF0Zm9ybSI6IkFQSSIsInVzdWFyaW8iOnsiX2lkIjoiNjg2OGJhMjAzMDI3NzhhMDkyNzZkNTQ1IiwibmFtZSI6Imtpbmdsb3R1c3AiLCJyYW5nbyI6InVzZXIiLCJzcGFtIjozMCwiY19leHBpcnkiOjE3NTQyODU5ODh9LCJpYXQiOjE3NTMyNTA3NTYsImV4cCI6MTc1NDIwMTE1Nn0.BCESqMO0bFD5GEjU6uDggyKtQdYiTe5j5ERgUIn2kEk-JHZ27lzGYzJppH60vQHfL3PM_031e3EFJuAWPQxMAw', 
    '34.211.200.85': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpcCI6IjM0LjIxMS4yMDAuODUiLCJwbGF0Zm9ybSI6IkFQSSIsInVzdWFyaW8iOnsiX2lkIjoiNjg2OGJhMjAzMDI3NzhhMDkyNzZkNTQ1IiwibmFtZSI6Imtpbmdsb3R1c3AiLCJyYW5nbyI6InVzZXIiLCJzcGFtIjozMCwiY19leHBpcnkiOjE3NTQyODU5ODh9LCJpYXQiOjE3NTMyNTA3ODYsImV4cCI6MTc1NDIwMTE4Nn0.p9DL7LwwpRjbd0mykDgjgw0Pq5qrOO-cetVVG7fi5UBKPZYqkOH9moy6UGjah8CnrKNhvfGbeTSSCFxJShNr5A'
}

# Token por defecto (el actual)
API_TOKEN = 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpcCI6IjUyLjkxLjkyLjI1NCIsInBsYXRmb3JtIjoiQVBJIiwidXN1YXJpbyI6eyJfaWQiOiI2ODY4YmEyMDMwMjc3OGEwOTI3NmQ1NDUiLCJuYW1lIjoia2luZ2xvdHVzcCIsInJhbmdvIjoidXNlciIsInNwYW0iOjMwLCJjX2V4cGlyeSI6MTc1NDI4NTk4OH0sImlhdCI6MTc1MzI0NzE3MCwiZXhwIjoxNzU0MjgzOTcwfQ.VbsjrG7bDj60h0_0scCNpWscvwf99OVXL6GA8As0biEkedMB4-t6vPFFwuYsfWpgizrE3D-0HOhB4LTThdB2rw'
API_BASE = 'https://lookfriends.xyz/api'
USUARIOS = 'usuarios.txt'
BANEADOS = 'baneados.txt'
ADMIN_ID = 6453239779

bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- Sistema de Antispam -------------------
user_last_command = {}  # Diccionario para guardar el último comando de cada usuario

def verificar_antispam(user_id):
    """Verifica si el usuario puede enviar un comando (60 segundos de cooldown)"""
    if user_id == ADMIN_ID:
        return True, 0  # El admin no tiene restricciones
    
    ahora = datetime.now()
    
    if user_id in user_last_command:
        tiempo_transcurrido = (ahora - user_last_command[user_id]).total_seconds()
        if tiempo_transcurrido < 120:  # 120 segundos de cooldown (2 minutos)
            return False, int(120 - tiempo_transcurrido)
    
    user_last_command[user_id] = ahora
    return True, 0

# ------------------- Funciones de Usuario -------------------
def registrar_usuario(user_id, username, nombre):
    """Registra un nuevo usuario en el archivo"""
    linea = f"{user_id}|{username}|{nombre}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    # Verificar si ya existe
    usuarios_existentes = []
    if os.path.exists(USUARIOS):
        with open(USUARIOS, 'r', encoding='utf-8') as f:
            usuarios_existentes = f.readlines()
    
    # Si no existe, agregarlo
    usuario_existe = any(line.startswith(f"{user_id}|") for line in usuarios_existentes)
    if not usuario_existe:
        with open(USUARIOS, 'a', encoding='utf-8') as f:
            f.write(linea)
        return True
    return False

def obtener_todos_usuarios():
    """Obtiene lista de todos los usuarios registrados"""
    usuarios = []
    if os.path.exists(USUARIOS):
        with open(USUARIOS, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    partes = line.strip().split('|')
                    if len(partes) >= 3:
                        usuarios.append({
                            'user_id': int(partes[0]),
                            'username': partes[1],
                            'nombre': partes[2],
                            'fecha_registro': partes[3] if len(partes) > 3 else 'N/A'
                        })
    return usuarios

# ------------------- Funciones de Permisos Temporales -------------------
PERMISOS_SPAM = 'permisos_spam.txt'

def dar_permiso_spam(user_id, username, dias):
    """Da permiso temporal para usar /spam"""
    fecha_expiracion = datetime.now() + timedelta(days=dias)
    linea = f"{user_id}|{username}|{fecha_expiracion.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    # Verificar si ya tiene permiso y actualizarlo
    permisos_actualizados = []
    usuario_encontrado = False
    
    if os.path.exists(PERMISOS_SPAM):
        with open(PERMISOS_SPAM, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(f"{user_id}|"):
                    # Actualizar permiso existente
                    permisos_actualizados.append(linea)
                    usuario_encontrado = True
                else:
                    permisos_actualizados.append(line)
    
    if not usuario_encontrado:
        permisos_actualizados.append(linea)
    
    # Escribir permisos actualizados
    with open(PERMISOS_SPAM, 'w', encoding='utf-8') as f:
        f.writelines(permisos_actualizados)
    
    return True

def quitar_permiso_spam(user_id):
    """Quita el permiso para usar /spam"""
    if not os.path.exists(PERMISOS_SPAM):
        return False
    
    permisos_actualizados = []
    usuario_encontrado = False
    
    with open(PERMISOS_SPAM, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.startswith(f"{user_id}|"):
                permisos_actualizados.append(line)
            else:
                usuario_encontrado = True
    
    if usuario_encontrado:
        with open(PERMISOS_SPAM, 'w', encoding='utf-8') as f:
            f.writelines(permisos_actualizados)
        return True
    return False

def tiene_permiso_spam(user_id):
    """Verifica si un usuario tiene permiso para usar /spam"""
    if user_id == ADMIN_ID:
        return True  # El admin siempre tiene permiso
    
    if not os.path.exists(PERMISOS_SPAM):
        return False
    
    ahora = datetime.now()
    permisos_validos = []
    
    with open(PERMISOS_SPAM, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line:
                partes = line.strip().split('|')
                if len(partes) >= 3:
                    try:
                        user_id_archivo = int(partes[0])
                        fecha_expiracion = datetime.strptime(partes[2], '%Y-%m-%d %H:%M:%S')
                        
                        if fecha_expiracion > ahora:  # Permiso aún válido
                            permisos_validos.append(line)
                            if user_id_archivo == user_id:
                                return True
                        # Si el permiso expiró, no lo agregamos a permisos_validos
                    except:
                        continue
    
    # Limpiar permisos expirados
    with open(PERMISOS_SPAM, 'w', encoding='utf-8') as f:
        f.writelines(permisos_validos)
    
    return False

def obtener_permisos_spam():
    """Obtiene lista de usuarios con permiso de spam activo"""
    if not os.path.exists(PERMISOS_SPAM):
        return []
    
    permisos = []
    ahora = datetime.now()
    
    with open(PERMISOS_SPAM, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line:
                partes = line.strip().split('|')
                if len(partes) >= 3:
                    try:
                        user_id = int(partes[0])
                        username = partes[1]
                        fecha_expiracion = datetime.strptime(partes[2], '%Y-%m-%d %H:%M:%S')
                        
                        if fecha_expiracion > ahora:  # Permiso aún válido
                            tiempo_restante = fecha_expiracion - ahora
                            dias_restantes = tiempo_restante.days
                            horas_restantes = tiempo_restante.seconds // 3600
                            
                            permisos.append({
                                'user_id': user_id,
                                'username': username,
                                'expira': fecha_expiracion.strftime('%Y-%m-%d %H:%M:%S'),
                                'dias_restantes': dias_restantes,
                                'horas_restantes': horas_restantes
                            })
                    except:
                        continue
    
    return permisos

# ------------------- Funciones de Baneos -------------------
def banear_usuario(user_id, username, razon="Sin razón especificada"):
    """Banea un usuario agregándolo al archivo de baneados"""
    linea = f"{user_id}|{username}|{razon}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    # Verificar si ya está baneado
    if os.path.exists(BANEADOS):
        with open(BANEADOS, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(f"{user_id}|"):
                    return False  # Ya está baneado
    
    # Agregar al archivo de baneados
    with open(BANEADOS, 'a', encoding='utf-8') as f:
        f.write(linea)
    return True

def desbanear_usuario(user_id):
    """Desbanea un usuario eliminándolo del archivo de baneados"""
    if not os.path.exists(BANEADOS):
        return False
    
    lineas_actualizadas = []
    usuario_encontrado = False
    
    with open(BANEADOS, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.startswith(f"{user_id}|"):
                lineas_actualizadas.append(line)
            else:
                usuario_encontrado = True
    
    if usuario_encontrado:
        with open(BANEADOS, 'w', encoding='utf-8') as f:
            f.writelines(lineas_actualizadas)
        return True
    return False

def esta_baneado(user_id):
    """Verifica si un usuario está baneado"""
    if not os.path.exists(BANEADOS):
        return False
    
    with open(BANEADOS, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(f"{user_id}|"):
                return True
    return False

def obtener_usuario_por_username(username):
    """Obtiene el user_id de un usuario por su username"""
    if not os.path.exists(USUARIOS):
        return None
    
    username_clean = username.lower().replace('@', '')
    
    with open(USUARIOS, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line:
                partes = line.strip().split('|')
                if len(partes) >= 2:
                    user_username = partes[1].lower().replace('@', '')
                    if user_username == username_clean:
                        return int(partes[0])
    return None

def auto_registrar_usuario(message):
    """Auto-registra un usuario y envía notificaciones"""
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.first_name}"
    nombre = message.from_user.first_name or "Usuario"
    
    # Verificar si está baneado
    if esta_baneado(user_id):
        bot.reply_to(message, "🚫 *Has sido baneado del bot.*\n\nNo puedes usar ningún comando.", parse_mode='Markdown')
        return False
    
    es_nuevo = registrar_usuario(user_id, username, nombre)
    if es_nuevo:
        # Notificar al admin
        try:
            bot.send_message(ADMIN_ID, f"🆕 *Nuevo usuario registrado:*\n👤 {nombre}\n🆔 {username}\n📱 ID: `{user_id}`", parse_mode='Markdown')
        except:
            pass
        
        # Enviar mensaje de bienvenida al nuevo usuario
        try:
            mensaje_bienvenida = "🤖 BOT gratuito actualmente con un antispam de 30 segundos si quieres colaborar para quitar el antispam comunicate con @Kinglotusp"
            bot.send_message(user_id, mensaje_bienvenida)
        except:
            pass
    
    return True

# ------------------- Explicador de Errores -------------------
def explicar_error_http(status_code, error_message=""):
    """Explica al usuario qué significa cada código de error HTTP"""
    explicaciones = {
        400: "❌ **Error 400 - Solicitud Incorrecta**\n📝 Los datos enviados no son válidos. Verifica que hayas ingresado correctamente el DNI, RUC o información solicitada.",
        
        401: "🔐 **Error 401 - No Autorizado**\n🚫 El bot no tiene permisos para acceder a esta información. El token de acceso puede haber expirado. Contacta al administrador @Kinglotusp",
        
        403: "⛔ **Error 403 - Acceso Prohibido**\n🚨 El servidor rechazó la solicitud. Posibles causas:\n• Has excedido el límite de consultas\n• Tu IP está bloqueada temporalmente\n• El servicio está restringido",
        
        404: "🔍 **Error 404 - No Encontrado**\n📋 No se encontró información para los datos proporcionados. Verifica que el DNI, RUC o número sea correcto.",
        
        408: "⏰ **Error 408 - Tiempo Agotado**\n🐌 La consulta tardó demasiado tiempo. El servidor está sobrecargado, intenta nuevamente en unos minutos.",
        
        429: "🚦 **Lo siento, hay muchas consultas en cola hacia la API**\n⏰ Si quieres que no haya esta espera, colabora dando tu limosna al admin @Kinglotusp para que compre las APIs sin tiempo de espera.",
        
        500: "🔧 **Error 500 - Error del Servidor**\n💥 Problema interno del servidor. Esto no es tu culpa, intenta más tarde o contacta al administrador @Kinglotusp",
        
        502: "🌐 **Error 502 - Puerta de Enlace Incorrecta**\n🔗 Problema de comunicación entre servidores. Intenta nuevamente en unos minutos.",
        
        503: "🚧 **Error 503 - Servicio No Disponible**\n⚠️ El servidor está temporalmente fuera de servicio por mantenimiento. Intenta más tarde.",
        
        504: "⏳ **Error 504 - Tiempo de Espera Agotado**\n🕐 El servidor tardó demasiado en responder. Intenta nuevamente en unos minutos."
    }
    
    explicacion_base = explicaciones.get(status_code, f"❓ **Error {status_code} - Error Desconocido**\n🤔 Ocurrió un error inesperado. Contacta al administrador @Kinglotusp con este código de error.")
    
    if error_message and error_message != "{}":
        return f"{explicacion_base}\n\n🔍 **Detalles técnicos:** {error_message}"
    else:
        return explicacion_base

# ------------------- API POST -------------------
def post_api(endpoint, payload, reintentos=3):
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'TelegramBot/1.0'
    }
    
    for intento in range(reintentos):
        try:
            # Agregar delay entre reintentos
            if intento > 0:
                import time
                time.sleep(2 ** intento)  # Backoff exponencial: 2s, 4s, 8s
            
            # Sistema de proxies rotativos - ACTIVADO para evitar bloqueo IP
            proxies_list = [
                # Proxies gratuitos (puedes agregar más)
                {'http': 'http://proxy-server.com:8080', 'https': 'https://proxy-server.com:8080'},
                # Agrega más proxies aquí si los tienes
            ]
            
            # Seleccionar proxy rotativo basado en el intento
            proxies = None
            if proxies_list and len(proxies_list) > 0:
                proxy_index = intento % len(proxies_list)
                proxies = proxies_list[proxy_index]
                
            # NOTA: Para usar proxies, descomenta la línea proxies=proxies en requests.post
            
            # Configuración especial para PythonAnywhere
            # Si estás en PythonAnywhere con cuenta gratuita, puedes usar un proxy
            proxies = None
            
            # Detectar si estamos en PythonAnywhere
            import os
            hostname = os.environ.get('HOSTNAME', '').lower()
            if 'pythonanywhere' in hostname or 'pa-user' in hostname:
                # Configuración especial para PythonAnywhere
                # Usar un servicio proxy público que esté en la lista blanca
                # NOTA: Esto es solo para cuentas gratuitas con restricciones
                
                # Opción 1: Usar un proxy público (descomenta si tienes uno)
                # proxies = {
                #     'http': 'http://free-proxy.com:8080',
                #     'https': 'https://free-proxy.com:8080'
                # }
                
                # Opción 2: Intentar con diferentes User-Agents
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                
                # Mensaje de diagnóstico para el admin
                if intento == 0:  # Solo en el primer intento
                    try:
                        bot.send_message(ADMIN_ID, 
                            f"⚠️ *Detectado PythonAnywhere*\n"
                            f"🖥️ Hostname: `{hostname}`\n"
                            f"💡 Si hay errores de conexión, considera upgrade a cuenta de pago para acceso completo a internet.",
                            parse_mode='Markdown')
                    except:
                        pass
            
            response = requests.post(
                f"{API_BASE}/{endpoint}", 
                json=payload, 
                headers=headers, 
                timeout=30,
                verify=True,  # Verificar certificados SSL
                proxies=proxies
            )
            
            # Si la respuesta no es JSON válida
            try:
                json_response = response.json()
            except:
                if intento == reintentos - 1:  # Último intento
                    return response.status_code, {"error": f"La API devolvió una respuesta inválida (HTTP {response.status_code}). El servidor puede estar experimentando problemas."}
                continue
                
            return response.status_code, json_response
            
        except requests.exceptions.Timeout:
            if intento == reintentos - 1:  # Último intento
                return 408, {"error": "La consulta tardó demasiado tiempo después de varios intentos. El servidor está sobrecargado."}
            continue
            
        except requests.exceptions.ConnectionError as e:
            if intento == reintentos - 1:  # Último intento
                # Obtener IP del servidor y enviar al admin
                try:
                    import socket
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    
                    # Obtener IP pública
                    try:
                        public_ip_response = requests.get('https://api.ipify.org', timeout=5)
                        public_ip = public_ip_response.text if public_ip_response.status_code == 200 else "No disponible"
                    except:
                        public_ip = "No disponible"
                    
                    # Diagnóstico adicional - Test de conectividad HTTP
                    try:
                        test_response = requests.get('https://httpbin.org/ip', timeout=5)
                        internet_status = "✅ Internet OK" if test_response.status_code == 200 else "❌ Internet FALLO"
                    except:
                        internet_status = "❌ Sin acceso a internet"
                    
                    # Test específico de la API
                    try:
                        api_test = requests.get('https://lookfriends.xyz', timeout=5)
                        api_status = f"✅ API accesible (HTTP {api_test.status_code})" if api_test.status_code else "❌ API no accesible"
                    except Exception as api_error:
                        api_status = f"❌ API no accesible: {str(api_error)}"
                    
                    # Enviar información al admin
                    error_info = f"🚨 *Error de Conexión API* (Intento {intento + 1}/{reintentos})\n\n" \
                                f"📍 *IP Local:* `{local_ip}`\n" \
                                f"🌐 *IP Pública:* `{public_ip}`\n" \
                                f"🖥️ *Hostname:* `{hostname}`\n" \
                                f"� *Test  Internet:* {internet_status}\n" \
                                f"🎯 *Test API:* {api_status}\n" \
                                f"⚠️ *Error:* {str(e)}\n" \
                                f"🎯 *Endpoint:* {API_BASE}/{endpoint}\n" \
                                f"🕐 *Hora:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    bot.send_message(ADMIN_ID, error_info, parse_mode='Markdown')
                except Exception as diag_error:
                    # Si falla el envío del diagnóstico, continuar normalmente
                    pass
                
                return 503, {"error": "No se pudo conectar con el servidor después de varios intentos. Verifica tu conexión a internet o intenta más tarde."}
            continue
            
        except requests.exceptions.HTTPError as e:
            if intento == reintentos - 1:  # Último intento
                return 500, {"error": f"Error HTTP: {str(e)}. Problema con la comunicación del servidor."}
            continue
            
        except Exception as e:
            if intento == reintentos - 1:  # Último intento
                return 500, {"error": f"Error inesperado: {str(e)}. Contacta al administrador @Kinglotusp si persiste."}
            continue
    
    return 500, {"error": "Error después de múltiples intentos. Contacta al administrador @Kinglotusp."}

# ------------------- Formateador -------------------
def dict_to_readable(response):
    def format_value(v, indent=1):
        indent_str = "    " * indent
        if isinstance(v, dict):
            lines = []
            for kk, vv in v.items():
                lines.append(f"{indent_str}• {kk.replace('_', ' ').title()}: {format_value(vv, indent+1)}")
            return "\n".join(lines)
        elif isinstance(v, list):
            lines = []
            for i, item in enumerate(v, 1):
                if isinstance(item, dict):
                    lines.append(f"{indent_str}• Item {i}:")
                    lines.append(format_value(item, indent+1))
                else:
                    lines.append(f"{indent_str}• {item}")
            return "\n".join(lines)
        else:
            return str(v)

    if isinstance(response, dict):
        lines = []
        for k, v in response.items():
            key = k.replace('_', ' ').title()
            val = format_value(v)
            if "\n" in val:
                lines.append(f"🔹 {key}:\n{val}")
            else:
                lines.append(f"🔹 {key}: {val}")
        return "\n".join(lines)

    elif isinstance(response, list):
        lines = []
        for i, item in enumerate(response, 1):
            lines.append(f"--- Item {i} ---")
            if isinstance(item, dict):
                lines.append(dict_to_readable(item))
            else:
                lines.append(str(item))
        return "\n".join(lines)

    else:
        return str(response)

def escape_markdown(text):
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return ""
    special_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

# ------------------- COMANDOS -------------------

@bot.message_handler(commands=['nm'])
def buscar_por_nombre(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /nm Nombres|ApellidoPaterno|ApellidoMaterno")
            return

        partes = " ".join(args).split('|')
        if len(partes) != 3:
            bot.reply_to(message, "⚠️ Formato incorrecto.\nEjemplo: /nm Karol|Huaman|Ramos")
            return

        nombres, ap_pat, ap_mat = [x.strip().upper() for x in partes]

        status, response = post_api("nombres", {
            "nombres": nombres,
            "ap_pat": ap_pat,
            "ap_mat": ap_mat
        })

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"🔍 Resultado:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['sunarp'])
def buscar_por_placa(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /sunarp PLACA (mínimo 6 caracteres)")
            return

        placa = args[0].strip().upper()

        if len(placa) < 6 or not placa.isalnum():
            bot.reply_to(message, "⚠️ La placa debe tener al menos 6 caracteres alfanuméricos.")
            return

        status, response = post_api("sunarp", {"placa": placa})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"🚗 Resultado SUNARP:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['sbs'])
def buscar_en_sbs(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /sbs DNI (8 dígitos numéricos)")
            return

        dni = args[0].strip()

        if not dni.isdigit() or len(dni) != 8:
            bot.reply_to(message, "⚠️ El DNI debe contener exactamente 8 dígitos numéricos.")
            return

        status, response = post_api("sbs", {"dni": dni})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"💼 Resultado SBS:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['sueldos'])
def buscar_sueldos_por_dni(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /sueldos DNI (8 dígitos numéricos)")
            return

        dni = args[0].strip()

        if not dni.isdigit() or len(dni) != 8:
            bot.reply_to(message, "⚠️ El DNI debe contener exactamente 8 dígitos numéricos.")
            return

        status, response = post_api("sueldos", {"dni": dni})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"💰 Resultado SUELDOS:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['familia'])
def buscar_familia_por_dni(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /familia DNI (8 dígitos numéricos)")
            return

        dni = args[0].strip()

        if not dni.isdigit() or len(dni) != 8:
            bot.reply_to(message, "⚠️ El DNI debe contener exactamente 8 dígitos numéricos.")
            return

        status, response = post_api("familia", {"dni": dni})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"👨‍👩‍👧 Resultado FAMILIA:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['virtual_dni'])
def obtener_dni_virtual(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /virtual_dni DNI (8 dígitos numéricos)")
            return

        dni = args[0].strip()

        if not dni.isdigit() or len(dni) != 8:
            bot.reply_to(message, "⚠️ El DNI debe contener exactamente 8 dígitos numéricos.")
            return

        status, response = post_api("virtual_dni", {"dni": dni})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response or not all(k in response for k in ("anverso", "reverso")):
            bot.reply_to(message, "⚠️ No se obtuvo imagen válida del DNI.")
        else:
            try:
                anverso_img = BytesIO(base64.b64decode(response['anverso']))
                reverso_img = BytesIO(base64.b64decode(response['reverso']))

                bot.send_photo(message.chat.id, photo=anverso_img, caption="🪪 *DNI Virtual - Anverso*", parse_mode='Markdown')
                bot.send_photo(message.chat.id, photo=reverso_img, caption="🔄 *DNI Virtual - Reverso*", parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(message, f"⚠️ Error al procesar imágenes:\n{e}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['sunat'])
def buscar_datos_sunat(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /sunat RUC (11 dígitos numéricos)")
            return

        ruc = args[0].strip()

        if not ruc.isdigit() or len(ruc) != 11:
            bot.reply_to(message, "⚠️ El RUC debe contener exactamente 11 dígitos numéricos.")
            return

        status, response = post_api("sunat", {"ruc": ruc})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            msg = (
                f"🏢 *Datos SUNAT*\n\n"
                f"🔹 *RUC:* {response.get('ruc', '—')}\n"
                f"🔹 *Razón Social:* {response.get('razon_social', '—')}\n"
                f"🔹 *Estado:* {response.get('estado', '—')}\n"
                f"🔹 *Dirección:* {response.get('direccion', '—')}\n"
                f"📍 *Ubigeo:* {response.get('ubigeo', '—')}\n"
                f"📌 *Departamento:* {response.get('departamento', '—')}\n"
                f"📌 *Provincia:* {response.get('provincia', '—')}\n"
                f"📌 *Distrito:* {response.get('distrito', '—')}"
            )
            bot.reply_to(message, msg, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['telf'])
def buscar_por_solo_numero(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if len(args) != 1 or not args[0].isdigit() or len(args[0]) < 7:
            bot.reply_to(message, "⚠️ Uso: /telf NUMERO\nEjemplo: /telf 987654321")
            return

        numb = args[0]
        status, response = post_api("telefonos", {
            "dni": None,
            "numb": numb
        })

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"📞 Resultado TELEFONO:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['fonos'])
def buscar_fonos_por_dni(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if len(args) != 1 or not args[0].isdigit() or len(args[0]) != 8:
            bot.reply_to(message, "⚠️ Uso: /fonos DNI\nEjemplo: /fonos 12345678")
            return

        dni = args[0]
        status, response = post_api("telefonos", {
            "dni": dni,
            "numb": None
        })

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
        elif not response:
            bot.reply_to(message, "⚠️ Sin resultados.")
        else:
            if isinstance(response, list):
                msg = "\n\n".join([dict_to_readable(r) for r in response])
            else:
                msg = dict_to_readable(response)
            bot.reply_to(message, f"📞 Resultado FONOS por DNI:\n\n{msg}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

@bot.message_handler(commands=['reniec'])
def obtener_datos_reniec(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    # Verificar antispam
    puede_usar, tiempo_restante = verificar_antispam(message.from_user.id)
    if not puede_usar:
        bot.reply_to(message, f"⏰ Debes esperar {tiempo_restante} segundos antes de usar otro comando.")
        return
    
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Uso: /reniec DNI (8 dígitos numéricos)")
            return

        dni = args[0].strip()

        if not dni.isdigit() or len(dni) != 8:
            bot.reply_to(message, "⚠️ El DNI debe contener exactamente 8 dígitos numéricos.")
            return

        bot.send_chat_action(message.chat.id, 'upload_photo')
        status, response = post_api("reniec", {"dni": dni})

        if status != 200:
            error_msg = response.get('error', str(response)) if isinstance(response, dict) else str(response)
            bot.reply_to(message, explicar_error_http(status, error_msg))
            return

        if not response or not isinstance(response, list):
            bot.reply_to(message, "⚠️ No se encontró información para este DNI.")
            return

        persona = response[0]

        sexo = "Masculino" if persona.get("sexo") == "1" else "Femenino" if persona.get("sexo") == "2" else "No especificado"

        nombre_completo = f"{persona.get('nombres', '')} {persona.get('ap_pat', '')} {persona.get('ap_mat', '')}"
        
        caption = f"""🧾 *Datos RENIEC*
👤 *Nombre:* {escape_markdown(nombre_completo)}
🆔 *DNI:* {escape_markdown(persona.get('dni', ''))}
🎂 *Nacimiento:* {escape_markdown(persona.get('fecha_nac', ''))}
📍 *Dirección:* {escape_markdown(persona.get('direccion', ''))}
⚧️ *Género:* {escape_markdown(sexo)}
💍 *Estado Civil:* {escape_markdown(persona.get('est_civil', ''))}
🎓 *Instrucción:* {escape_markdown(persona.get('gradoInstruccion', ''))}
📧 *Email:* {escape_markdown(persona.get('emailPersonal', ''))}
👨 *Padre:* {escape_markdown(persona.get('padre', ''))}
👩 *Madre:* {escape_markdown(persona.get('madre', ''))}
"""

        if persona.get('foto') and len(persona['foto']) > 50:
            try:
                img_bytes = BytesIO(base64.b64decode(persona['foto']))
                img_bytes.name = f"{dni}.png"
                bot.send_photo(message.chat.id, photo=img_bytes, caption=caption, parse_mode='Markdown')
            except Exception as e:
                try:
                    caption_plain = f"""🧾 Datos RENIEC
👤 Nombre: {nombre_completo}
🆔 DNI: {persona.get('dni', '')}
🎂 Nacimiento: {persona.get('fecha_nac', '')}
📍 Dirección: {persona.get('direccion', '')}
⚧️ Género: {sexo}
💍 Estado Civil: {persona.get('est_civil', '')}
🎓 Instrucción: {persona.get('gradoInstruccion', '')}
📧 Email: {persona.get('emailPersonal', '')}
👨 Padre: {persona.get('padre', '')}
👩 Madre: {persona.get('madre', '')}
"""
                    bot.send_photo(message.chat.id, photo=img_bytes, caption=caption_plain)
                except Exception as e2:
                    bot.reply_to(message, f"⚠️ Error al mostrar foto:\n{e2}")
        else:
            bot.send_message(message.chat.id, caption, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error interno:\n{e}")

# ------------------- COMANDOS ADMINISTRATIVOS -------------------

@bot.message_handler(commands=['dar'])
def dar_permiso_comando(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    try:
        args = message.text.split()[1:]
        if len(args) != 2:
            bot.reply_to(message, "⚠️ *Uso:* `/dar @usuario dias`\n\n*Ejemplos:*\n• `/dar @kinglotusp 7`\n• `/dar kinglotusp 30`", parse_mode='Markdown')
            return

        username_input = args[0].strip()
        try:
            dias = int(args[1])
            if dias <= 0:
                bot.reply_to(message, "⚠️ Los días deben ser un número positivo.")
                return
        except ValueError:
            bot.reply_to(message, "⚠️ Los días deben ser un número válido.")
            return

        # Buscar el usuario por username
        user_id = obtener_usuario_por_username(username_input)
        if not user_id:
            bot.reply_to(message, f"⚠️ No se encontró el usuario `{username_input}` en la base de datos.\n\nEl usuario debe haber usado al menos un comando del bot para estar registrado.", parse_mode='Markdown')
            return

        # Dar permiso
        username_clean = username_input if username_input.startswith('@') else f"@{username_input}"
        dar_permiso_spam(user_id, username_clean, dias)
        
        fecha_expiracion = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d %H:%M:%S')
        
        bot.reply_to(message, f"✅ *Permiso otorgado exitosamente*\n\n👤 *Usuario:* {username_clean}\n🆔 *ID:* `{user_id}`\n📅 *Días:* {dias}\n⏰ *Expira:* {fecha_expiracion}", parse_mode='Markdown')
        
        # Notificar al usuario
        try:
            bot.send_message(user_id, f"🎉 *¡Felicidades!*\n\nHas recibido acceso al comando `/spam` por {dias} días.\n\n⏰ *Expira:* {fecha_expiracion}\n\n💡 Ahora puedes enviar mensajes a todos los usuarios del bot.", parse_mode='Markdown')
        except:
            bot.reply_to(message, "⚠️ Permiso otorgado, pero no se pudo notificar al usuario.")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al procesar comando:\n{e}")

@bot.message_handler(commands=['quitar'])
def quitar_permiso_comando(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    try:
        args = message.text.split()[1:]
        if len(args) != 1:
            bot.reply_to(message, "⚠️ *Uso:* `/quitar @usuario`\n\n*Ejemplo:* `/quitar @kinglotusp`", parse_mode='Markdown')
            return

        username_input = args[0].strip()
        
        # Buscar el usuario por username
        user_id = obtener_usuario_por_username(username_input)
        if not user_id:
            bot.reply_to(message, f"⚠️ No se encontró el usuario `{username_input}` en la base de datos.", parse_mode='Markdown')
            return

        # Quitar permiso
        if quitar_permiso_spam(user_id):
            username_clean = username_input if username_input.startswith('@') else f"@{username_input}"
            bot.reply_to(message, f"✅ *Permiso removido exitosamente*\n\n👤 *Usuario:* {username_clean}\n🆔 *ID:* `{user_id}`", parse_mode='Markdown')
            
            # Notificar al usuario
            try:
                bot.send_message(user_id, "⚠️ *Permiso revocado*\n\nTu acceso al comando `/spam` ha sido removido por el administrador.", parse_mode='Markdown')
            except:
                pass
        else:
            bot.reply_to(message, f"⚠️ El usuario `{username_input}` no tenía permisos de spam.", parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al procesar comando:\n{e}")

@bot.message_handler(commands=['permisos'])
def listar_permisos_comando(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    try:
        permisos = obtener_permisos_spam()
        
        if not permisos:
            bot.reply_to(message, "📋 *Lista de Permisos de Spam*\n\n⚠️ No hay usuarios con permisos activos.", parse_mode='Markdown')
            return

        mensaje = "📋 *Lista de Permisos de Spam*\n\n"
        
        for i, permiso in enumerate(permisos, 1):
            tiempo_restante = ""
            if permiso['dias_restantes'] > 0:
                tiempo_restante = f"{permiso['dias_restantes']}d {permiso['horas_restantes']}h"
            else:
                tiempo_restante = f"{permiso['horas_restantes']}h"
            
            mensaje += f"{i}. {permiso['username']}\n"
            mensaje += f"   🆔 `{permiso['user_id']}`\n"
            mensaje += f"   ⏰ Expira: {permiso['expira']}\n"
            mensaje += f"   ⏳ Restante: {tiempo_restante}\n\n"

        bot.reply_to(message, mensaje, parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error al listar permisos:\n{e}")

@bot.message_handler(commands=['spam'])
def comando_spam(message):
    # Verificar permisos
    if not tiene_permiso_spam(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.\n\n💡 Solo el administrador y usuarios autorizados pueden usar `/spam`.", parse_mode='Markdown')
        return

    usuarios = obtener_todos_usuarios()
    if not usuarios:
        bot.reply_to(message, "⚠️ No hay usuarios registrados.")
        return

    # Verificar si el mensaje tiene una foto adjunta directamente
    if message.photo:
        foto = message.photo[-1]  # Obtener la foto de mayor resolución
        caption = message.caption.replace('/spam', '').strip() if message.caption else None
        
        enviados = 0
        errores = 0

        bot.reply_to(message, f"📤 Enviando foto a {len(usuarios)} usuarios...")

        for usuario in usuarios:
            try:
                bot.send_photo(usuario['user_id'], foto.file_id, caption=caption)
                enviados += 1
            except Exception as e:
                errores += 1

        resultado = f"✅ *Foto enviada:*\n📤 Enviados: {enviados}\n❌ Errores: {errores}\n👥 Total usuarios: {len(usuarios)}"
        bot.reply_to(message, resultado, parse_mode='Markdown')
        return

    # Verificar si es una respuesta a un mensaje con foto
    if message.reply_to_message:
        # Si es respuesta a un mensaje con foto
        if message.reply_to_message.photo:
            foto = message.reply_to_message.photo[-1]  # Obtener la foto de mayor resolución
            caption = message.text.replace('/spam', '').strip()
            
            enviados = 0
            errores = 0

            bot.reply_to(message, f"📤 Enviando foto con mensaje a {len(usuarios)} usuarios...")

            for usuario in usuarios:
                try:
                    bot.send_photo(usuario['user_id'], foto.file_id, caption=caption if caption else None)
                    enviados += 1
                except Exception as e:
                    errores += 1

            resultado = f"✅ *Foto enviada:*\n📤 Enviados: {enviados}\n❌ Errores: {errores}\n👥 Total usuarios: {len(usuarios)}"
            bot.reply_to(message, resultado, parse_mode='Markdown')
            return
        
        # Si es respuesta a un mensaje normal
        elif message.reply_to_message.text:
            mensaje_original = message.reply_to_message.text
            mensaje_adicional = message.text.replace('/spam', '').strip()
            mensaje_final = f"{mensaje_original}\n\n{mensaje_adicional}" if mensaje_adicional else mensaje_original
            
            enviados = 0
            errores = 0

            bot.reply_to(message, f"📤 Enviando mensaje a {len(usuarios)} usuarios...")

            for usuario in usuarios:
                try:
                    bot.send_message(usuario['user_id'], mensaje_final)
                    enviados += 1
                except Exception as e:
                    errores += 1

            resultado = f"✅ *Mensaje enviado:*\n📤 Enviados: {enviados}\n❌ Errores: {errores}\n👥 Total usuarios: {len(usuarios)}"
            bot.reply_to(message, resultado, parse_mode='Markdown')
            return

    # Comando normal con texto
    args = message.text.split(' ', 1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ *Uso del comando /spam:*\n\n" +
                              "📝 `/spam MENSAJE` → Enviar mensaje de texto\n" +
                              "🖼️ Enviar foto con `/spam` en el caption → Enviar foto directamente\n" +
                              "🖼️ Responder a una foto con `/spam CAPTION` → Enviar foto con texto\n" +
                              "💬 Responder a un mensaje con `/spam` → Reenviar mensaje\n\n" +
                              "*Ejemplos:*\n" +
                              "• `/spam Hola a todos!`\n" +
                              "• Enviar foto con caption: `/spam Nueva actualización`\n" +
                              "• Responder a foto: `/spam Texto adicional`\n" +
                              "• Responder a mensaje: `/spam`", parse_mode='Markdown')
        return

    mensaje = args[1]
    
    enviados = 0
    errores = 0

    bot.reply_to(message, f"📤 Enviando mensaje a {len(usuarios)} usuarios...")

    for usuario in usuarios:
        try:
            bot.send_message(usuario['user_id'], mensaje)
            enviados += 1
        except Exception as e:
            errores += 1

    resultado = f"✅ *Mensaje enviado:*\n📤 Enviados: {enviados}\n❌ Errores: {errores}\n👥 Total usuarios: {len(usuarios)}"
    bot.reply_to(message, resultado, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
def comando_ban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    args = message.text.split(' ', 2)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ *Uso del comando /ban:*\n\n" +
                              "📝 `/ban @usuario` → Banear usuario\n" +
                              "📝 `/ban @usuario razón` → Banear con razón\n\n" +
                              "*Ejemplos:*\n" +
                              "• `/ban @usuario123`\n" +
                              "• `/ban @usuario123 Spam excesivo`", parse_mode='Markdown')
        return

    username_target = args[1].strip()
    razon = args[2].strip() if len(args) > 2 else "Sin razón especificada"

    if not username_target.startswith('@'):
        bot.reply_to(message, "⚠️ El usuario debe comenzar con @\nEjemplo: `/ban @usuario123`", parse_mode='Markdown')
        return

    # Obtener user_id del username
    user_id_target = obtener_usuario_por_username(username_target)
    if not user_id_target:
        bot.reply_to(message, f"❌ Usuario {username_target} no encontrado en la base de datos.")
        return

    # No permitir banear al admin
    if user_id_target == ADMIN_ID:
        bot.reply_to(message, "⚠️ No puedes banear al administrador.")
        return

    # Intentar banear
    if banear_usuario(user_id_target, username_target, razon):
        bot.reply_to(message, f"✅ *Usuario baneado exitosamente:*\n" +
                              f"👤 Usuario: {username_target}\n" +
                              f"🆔 ID: `{user_id_target}`\n" +
                              f"📝 Razón: {razon}", parse_mode='Markdown')
        
        # Notificar al usuario baneado
        try:
            bot.send_message(user_id_target, f"🚫 *Has sido baneado del bot.*\n\n" +
                                           f"📝 Razón: {razon}\n\n" +
                                           f"No podrás usar ningún comando hasta que seas desbaneado.", parse_mode='Markdown')
        except:
            pass
    else:
        bot.reply_to(message, f"⚠️ El usuario {username_target} ya está baneado.")

@bot.message_handler(commands=['unban', 'desban'])
def comando_unban(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    args = message.text.split(' ', 1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ *Uso del comando /unban:*\n\n" +
                              "📝 `/unban @usuario` → Desbanear usuario\n\n" +
                              "*Ejemplo:*\n" +
                              "• `/unban @usuario123`", parse_mode='Markdown')
        return

    username_target = args[1].strip()

    if not username_target.startswith('@'):
        bot.reply_to(message, "⚠️ El usuario debe comenzar con @\nEjemplo: `/unban @usuario123`", parse_mode='Markdown')
        return

    # Obtener user_id del username
    user_id_target = obtener_usuario_por_username(username_target)
    if not user_id_target:
        bot.reply_to(message, f"❌ Usuario {username_target} no encontrado en la base de datos.")
        return

    # Intentar desbanear
    if desbanear_usuario(user_id_target):
        bot.reply_to(message, f"✅ *Usuario desbaneado exitosamente:*\n" +
                              f"👤 Usuario: {username_target}\n" +
                              f"🆔 ID: `{user_id_target}`", parse_mode='Markdown')
        
        # Notificar al usuario desbaneado
        try:
            bot.send_message(user_id_target, f"✅ *Has sido desbaneado del bot.*\n\n" +
                                           f"Ya puedes usar todos los comandos normalmente.", parse_mode='Markdown')
        except:
            pass
    else:
        bot.reply_to(message, f"⚠️ El usuario {username_target} no está baneado.")

@bot.message_handler(commands=['baneados'])
def ver_baneados(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    if not os.path.exists(BANEADOS):
        bot.reply_to(message, "✅ No hay usuarios baneados.")
        return

    baneados = []
    with open(BANEADOS, 'r', encoding='utf-8') as f:
        for line in f:
            if '|' in line:
                partes = line.strip().split('|')
                if len(partes) >= 4:
                    baneados.append({
                        'user_id': partes[0],
                        'username': partes[1],
                        'razon': partes[2],
                        'fecha': partes[3]
                    })

    if not baneados:
        bot.reply_to(message, "✅ No hay usuarios baneados.")
        return

    msg = f"🚫 *Usuarios Baneados ({len(baneados)}):*\n\n"
    
    for i, usuario in enumerate(baneados[:15], 1):  # Mostrar solo los primeros 15
        msg += f"{i}. {usuario['username']}\n"
        msg += f"   🆔 ID: `{usuario['user_id']}`\n"
        msg += f"   📝 Razón: {usuario['razon']}\n"
        msg += f"   📅 Fecha: {usuario['fecha']}\n\n"
    
    if len(baneados) > 15:
        msg += f"... y {len(baneados) - 15} usuarios más."

    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['usuarios'])
def ver_usuarios(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ No tienes permiso para usar este comando.")
        return

    usuarios = obtener_todos_usuarios()
    
    if not usuarios:
        bot.reply_to(message, "⚠️ No hay usuarios registrados.")
        return

    msg = f"👥 *Usuarios Registrados ({len(usuarios)}):*\n\n"
    
    for i, usuario in enumerate(usuarios[:20], 1):  # Mostrar solo los primeros 20
        msg += f"{i}. {usuario['nombre']} ({usuario['username']})\n"
        msg += f"   📅 {usuario['fecha_registro']}\n\n"
    
    if len(usuarios) > 20:
        msg += f"... y {len(usuarios) - 20} usuarios más."

    bot.reply_to(message, msg, parse_mode='Markdown')

# ------------------- COMANDOS GENERALES -------------------

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.first_name}"
    nombre = message.from_user.first_name

    texto = (
        f"👋 ¡Hola, *{nombre}*!\n\n"
        f"Bienvenido al bot. Tu ID es `{user_id}` y tu usuario es *{username}*.\n\n"
        f"🤖 *Comandos Disponibles:*\n"
        f"• `/cmds` → Ver todos los comandos\n"
        f"• `/start` → Mostrar este mensaje\n\n"
        f"¡Usa cualquier comando para empezar!"
    )

    bot.reply_to(message, texto, parse_mode='Markdown')

@bot.message_handler(commands=['cmds'])
def cmd_comandos(message):
    if not auto_registrar_usuario(message):
        return  # Usuario baneado
    
    nombre = message.from_user.first_name

    texto = (
        f"👋 ¡Hola, *{nombre}*!\n"
        f"Bienvenido al bot.\n\n"
        f"🤖 *Comandos Disponibles:*\n\n"
        f"🆔 `/fonos 12345678` → Buscar teléfonos por DNI\n"
        f"📱 `/telf 987654321` → Buscar por número\n"
        f"🔍 `/nm Nombres|Apellido1|Apellido2` → Buscar por nombre completo\n"
        f"🧾 `/reniec 12345678` → Datos completos RENIEC\n"
        f"💳 `/sbs 12345678` → Riesgo crediticio (SBS)\n"
        f"🚗 `/sunarp ABC123` → Buscar vehículo por placa\n"
        f"💼 `/sueldos 12345678` → Buscar sueldos por DNI\n"
        f"👨‍👩‍👧 `/familia 12345678` → Grupo familiar por DNI\n"
        f"🪪 `/virtual_dni 12345678` → Imagen virtual del DNI\n"
        f"🏢 `/sunat 12345678901` → Información de RUC (SUNAT)\n"
    )

    bot.reply_to(message, texto, parse_mode='Markdown')

if __name__ == "__main__":
    print("🤖 Bot iniciado...")
    
    # Para Render Web Service: crear servidor HTTP básico en thread separado
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        
        def log_message(self, format, *args):
            pass  # Silenciar logs HTTP
    
    def start_health_server():
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"🌐 Servidor HTTP iniciado en puerto {port}")
        server.serve_forever()
    
    # Iniciar servidor HTTP en thread separado
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    try:
        # Obtener información del servidor
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Obtener IP pública
        try:
            public_ip_response = requests.get('https://api.ipify.org', timeout=10)
            public_ip = public_ip_response.text if public_ip_response.status_code == 200 else "No disponible"
        except:
            public_ip = "No disponible"
        
        print(f"🖥️ Hostname: {hostname}")
        print(f"📍 IP Local: {local_ip}")
        print(f"🌐 IP Pública: {public_ip}")
        
        bot_info = bot.get_me()
        print(f"📱 Bot username: @{bot_info.username}")
        print(f"👤 Bot name: {bot_info.first_name}")
        print("🔄 Iniciando polling...")
        
        # Notificar al admin que el bot está activo con información del servidor
        server_info = f"✅ *El bot está activo y listo para usar.*\n\n" \
                     f"🖥️ *Hostname:* `{hostname}`\n" \
                     f"📍 *IP Local:* `{local_ip}`\n" \
                     f"🌐 *IP Pública:* `{public_ip}`\n" \
                     f"📱 *Bot:* @{bot_info.username}"
        
        bot.send_message(ADMIN_ID, server_info, parse_mode='Markdown')
        
        # Configurar para producción (más robusto)
        bot.infinity_polling(
            timeout=10, 
            long_polling_timeout=5,
            none_stop=True,
            interval=0
        )
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
        # Intentar con polling básico si falla infinity_polling
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e2:
            print(f"❌ Error crítico: {e2}")
