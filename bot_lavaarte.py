# LAVAARTE_BOT_DEFINITIVO_3.0.0 — HILTON ORIENTE BLINDADO + MOTOR LENCERIA/MANTELERIA
# =========================================================================
# BOT CENTRAL LAVAARTE SAS - AUDITORÍA Y TRAZABILIDAD LOGÍSTICA COMPLETA
# MODELOS 100% FLASH + HOMOLOGACIÓN AISLADA POR HOTEL (FONTANA / OCEANÍA / WYNDHAM)
# GESTIÓN FINANCIERA (LAVAARTE + CARLOS) + FIRMAS DIGITALES DRIVE + HORA BOGOTÁ
# EDICIÓN EN DESTINO + CIERRE DEFINITIVO ANTI-DOBLE FIRMA + DÍA CORRIDO AUTOMÁTICO
# SERVIDOR WEB FLASK EMBEBIDO ANTI-SUSPENSIÓN (RENDER 24/7)
# CONTROL ESTRICTO ANTI-DUPLICADOS + ARCHIVADO DE SOPORTE FOTOS (NORTE / ORIENTE)
# =========================================================================

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import requests
import datetime
import json
import io
import time
import threading
import base64
import unicodedata
import os
import re
import uuid
from flask import Flask
from PIL import Image
from google import genai
from google.genai import types

try:
    import zoneinfo
    ZONA_BOGOTA = zoneinfo.ZoneInfo("America/Bogota")
except Exception:
    ZONA_BOGOTA = datetime.timezone(datetime.timedelta(hours=-5))

TOKEN = '8816786492:AAEb6VgZzP07JJ9MegbVjiItuS-oopL5728'
GEMINI_API_KEY = 'AQ.Ab8RN6KHh9xczXiYb-Bm2DSL1Q8zsTyd695lbn3CF74Qc4OzGg'
URL_APPS_SCRIPT = 'https://script.google.com/macros/s/AKfycbxqnfe5kd_b0gB50r0IKw69pkRdsYq4vEHLIpwpRZpDYeTMq5TvWVCnsstm7Tj2W0we/exec'
URL_APPS_SCRIPT_CARLOS = 'https://script.google.com/macros/s/AKfycbwv-D7RZLLaxVe1mA8h7iyMblV5ZhGCZG4PggzCppAt8T5Y79t-j_Rt7Pe95lcuQ9-6Fg/exec'

bot = telebot.TeleBot(TOKEN, threaded=True)
client = genai.Client(api_key=GEMINI_API_KEY)

# =========================================================================
# ROTACIÓN DE MODELOS GEMINI
# Sistema de respaldo automático para texto + imágenes + audio
# =========================================================================

MODELOS_ROTACION = [
    # Principal
    "gemini-3.8-flash",

    # Respaldos principales
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",

    # Respaldos ligeros / alto volumen
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",

    # Último respaldo
    "gemini-2.5-flash"
]


def llamar_gemini_rotativo(contents):
    """
    Ejecuta Gemini con rotación automática.

    Si un modelo devuelve:
        429
        503
        404
        403
        RESOURCE_EXHAUSTED
        UNAVAILABLE
        NOT_FOUND

    pasa automáticamente al siguiente modelo.

    Funciona con el mismo 'contents' para:
        - texto
        - imágenes
        - audio
        - combinaciones de los anteriores
    """

    ultimo_error = None

    config_llamada = types.GenerateContentConfig(
        temperature=0.1
    )

    for modelo in MODELOS_ROTACION:

        try:
            print(f"[GEMINI] Intentando modelo: {modelo}")

            resp = client.models.generate_content(
                model=modelo,
                contents=contents,
                config=config_llamada
            )

            if resp and resp.text:
                print(f"[GEMINI] OK -> {modelo}")
                return resp.text

            print(f"[GEMINI] {modelo} respondió sin texto")

        except Exception as e:

            err_str = str(e).upper()
            ultimo_error = e

            print(f"[GEMINI] ERROR en {modelo}: {e}")

            # Errores que justifican cambiar inmediatamente de modelo
            errores_rotacion = [
                "429",
                "503",
                "403",
                "404",
                "RESOURCE_EXHAUSTED",
                "UNAVAILABLE",
                "NOT_FOUND",
                "HIGH DEMAND",
                "RATE LIMIT",
                "QUOTA"
            ]

            if any(error in err_str for error in errores_rotacion):

                print(
                    f"[GEMINI] {modelo} no disponible. "
                    f"Pasando al siguiente modelo..."
                )

                # Pausa mínima para no bombardear la API
                time.sleep(0.3)

                continue

            # Si es un error que NO parece temporal,
            # lo conservamos como error real.
            raise

    # Ningún modelo funcionó
    raise Exception(
        f"Todos los modelos Gemini de respaldo fallaron. "
        f"Último error: {ultimo_error}"
    )
sesiones = {}
cola_fotos = {}
timers = {}
lock = threading.Lock()

# -------------------------------------------------------------------------
# SERVIDOR WEB FLASK PARA MANTENER ACTIVO EL SERVICIO EN RENDER (24/7)
# -------------------------------------------------------------------------
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot de Telegram Lavaarte Activo 24/7"

def correr_web():
    puerto = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=puerto)

def obtener_ahora_bogota():
    """Garantiza la hora legal de Bogotá Colombia (GMT-5) sin desfase de servidor."""
    try:
        return datetime.datetime.now(ZONA_BOGOTA)
    except Exception:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        return utc_now - datetime.timedelta(hours=5)

def calcular_dia_corrido_logistica():
    """
    Calcula el día hábil anterior para despacho de lencería:
    - Si es lunes (weekday 0), retrocede al sábado (2 días antes).
    - Para cualquier otro día, retrocede 1 día.
    """
    ahora = obtener_ahora_bogota()
    if ahora.weekday() == 0:  # Lunes
        dia_logistico = ahora - datetime.timedelta(days=2)
    else:
        dia_logistico = ahora - datetime.timedelta(days=1)
    return dia_logistico.day

def ejecutar_post_apps_script(url, payload, timeout=85):
    """Ejecución tolerante a redirecciones de Apps Script.
    Las operaciones de escritura aceptan una respuesta HTTP 2xx/3xx aunque
    Apps Script no entregue JSON por una redirección/intermediario.
    Las consultas, en cambio, EXIGEN JSON para no convertir una respuesta
    vacía/HTML en un falso "SUCCESS".
    """
    accion = str(payload.get("accion", "")).upper()
    acciones_que_requieren_json = {
        "CONSULTAR_DESPACHO",
        "AUDITORIA_CONSULTA_UNIVERSAL",
        "OBTENER_PRECIOS_HOTEL"
    }

    try:
        session = requests.Session()
        resp = session.post(
            url,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*'
            },
            timeout=timeout,
            allow_redirects=True
        )
        txt = resp.text.strip()

        if txt.startswith('{') or txt.startswith('['):
            try:
                return json.loads(txt)
            except Exception:
                pass

        match_json = re.search(r'(\{.*\}|\[.*\])', txt, re.DOTALL)
        if match_json:
            try:
                return json.loads(match_json.group(1))
            except Exception:
                pass

        if accion in acciones_que_requieren_json:
            raise ValueError(
                "Google Sheets respondió sin datos JSON para la consulta."
            )

        if 200 <= resp.status_code < 400:
            return {
                "status": "SUCCESS",
                "respuesta_ambigua": True,
                "mensaje": "Operación recibida y procesada por Google Sheets."
            }

        raise ValueError(
            f"Google Sheets respondió con código HTTP {resp.status_code}."
        )

    except requests.exceptions.Timeout:
        if accion not in acciones_que_requieren_json:
            return {
                "status": "SUCCESS",
                "respuesta_ambigua": True,
                "mensaje": "Operación enviada a Google Sheets y puede haber quedado registrada."
            }
        raise ValueError("Tiempo de espera agotado consultando Google Sheets.")

    except ValueError:
        raise

    except Exception as e:
        raise ValueError(f"Error de comunicación con Google Sheets: {str(e)}")


# -------------------------------------------------------------------------
# PRECIOS OFICIALES HAMPTON / HILTON
# -------------------------------------------------------------------------
VERSION_BOT = "HILTON_HUESPEDES_MANUAL_2.0.0"

PRECIOS_HOTEL_CACHE = {}
PRECIOS_HOTEL_KEYS = {
    "hampton": "HUESPEDES",
    "hampton_empleados": "EMPLEADOS",
    "hilton": "HUESPEDES",
    "hilton_empleados": "EMPLEADOS"
}

def _clave_precio_hotel(config_sesion):
    """Determina exclusivamente la lista oficial de precios del hotel.

    Hilton/Hampton pertenecen a RUTA ORIENTE y nunca consultan catálogos
    de huéspedes de la RUTA NORTE. El tipo de precio se fija por la clave
    de sesión: huéspedes o empleados.
    """
    key = str(config_sesion.get("key", "")).strip().lower()

    # BLINDAJE HILTON
    if key == "hilton":
        return "hilton_oriente", "HUESPEDES"
    if key == "hilton_empleados":
        return "hilton_oriente", "EMPLEADOS"

    # BLINDAJE HAMPTON
    if key == "hampton":
        return "hampton_oriente", "HUESPEDES"
    if key == "hampton_empleados":
        return "hampton_oriente", "EMPLEADOS"

    # Fallback solamente para sesiones antiguas que no tengan key.
    hotel = limpiar_texto_simple(config_sesion.get("hotel", ""))
    tipo = str(config_sesion.get("tipo_precio", "HUESPEDES")).upper()

    if "hilton" in hotel:
        return "hilton_oriente", "EMPLEADOS" if "empleado" in limpiar_texto_simple(config_sesion.get("servicio", "")) else "HUESPEDES"
    if "hampton" in hotel:
        return "hampton_oriente", "EMPLEADOS" if "empleado" in limpiar_texto_simple(config_sesion.get("servicio", "")) else "HUESPEDES"

    return None, None

def obtener_precios_oficiales_hotel(config_sesion):
    key, tipo_precio = _clave_precio_hotel(config_sesion)
    if not key:
        return []

    cache_key = f"{key}_{tipo_precio}"
    if cache_key in PRECIOS_HOTEL_CACHE and PRECIOS_HOTEL_CACHE[cache_key]:
        return PRECIOS_HOTEL_CACHE[cache_key]

    hotel = config_sesion.get("hotel", "")

    # Hilton/Hampton: la consulta oficial SIEMPRE pertenece a ORIENTE.
    # Se envían hotel + ruta + tipo_precio para que Apps Script no pueda
    # resolver accidentalmente una tabla/catálogo de Norte.
    hotel_consulta = "Hilton" if key == "hilton_oriente" else (
        "Hampton" if key == "hampton_oriente" else hotel
    )
    payload = {
        "accion": "OBTENER_PRECIOS_HOTEL",
        "hotel": hotel_consulta,
        "ruta": "Oriente" if key in ("hilton_oriente", "hampton_oriente") else config_sesion.get("ruta", ""),
        "tipo_precio": tipo_precio
    }

    ultimo_error = None
    for intento in range(2):
        try:
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=25)
            if resp.get("status") == "SUCCESS" and isinstance(resp.get("precios"), list) and resp.get("precios"):
                PRECIOS_HOTEL_CACHE[cache_key] = resp["precios"]
                return resp["precios"]
            ultimo_error = ValueError(resp.get("mensaje", "No se recibió la lista oficial de precios."))
        except Exception as e:
            ultimo_error = e
            time.sleep(0.4)

    # Si ya hubo una lectura exitosa anteriormente, se conserva como respaldo
    # ante una caída temporal de la consulta.
    if cache_key in PRECIOS_HOTEL_CACHE and PRECIOS_HOTEL_CACHE[cache_key]:
        return PRECIOS_HOTEL_CACHE[cache_key]

    raise ValueError(
        f"No se pudo validar la lista oficial de precios de {hotel} ({tipo_precio}). "
        "No se utilizarán precios inventados por la IA."
    ) from ultimo_error

def _valor_item_case_insensitive(item, *campos):
    """Obtiene un campo de un item de Sheets tolerando mayúsculas y nombres alternativos."""
    if not isinstance(item, dict):
        return None

    # Primero intenta las claves exactas.
    for campo in campos:
        if campo in item and item.get(campo) not in (None, ""):
            return item.get(campo)

    # Después intenta ignorando mayúsculas/minúsculas y espacios.
    mapa = {}
    for k, v in item.items():
        clave = str(k).strip().lower().replace(" ", "_")
        mapa[clave] = v

    for campo in campos:
        clave = str(campo).strip().lower().replace(" ", "_")
        if clave in mapa and mapa[clave] not in (None, ""):
            return mapa[clave]

    return None


def _nombre_item_oficial(item):
    """Obtiene el nombre de prenda independientemente de cómo Apps Script lo llame."""
    return _valor_item_case_insensitive(
        item,
        "prenda",
        "nombre_prenda",
        "nombre",
        "articulo",
        "artículo",
        "item",
        "descripcion",
        "descripción",
        "concepto"
    ) or ""


def _precio_item_oficial(item):
    """Obtiene el precio oficial sin depender de una única clave de Apps Script."""
    valor = _valor_item_case_insensitive(
        item,
        "precio",
        "valorUnitario",
        "valor_unitario",
        "precio_unitario",
        "valor",
        "tarifa"
    )
    if valor in (None, ""):
        return 0.0
    try:
        if isinstance(valor, str):
            limpio = valor.replace("$", "").replace(".", "").replace(",", ".").strip()
            return float(limpio)
        return float(valor)
    except Exception:
        return 0.0


def _normalizar_clave_precio(txt):
    """Normaliza nombres de prendas de forma MUY tolerante para comparar Gemini vs Sheets."""
    if not txt:
        return ""

    s = limpiar_texto_simple(txt)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Separadores y variantes de escritura.
    s = s.replace("t-shirt", "tshirt")
    s = s.replace("t shirt", "tshirt")
    s = s.replace("dress shirt", "dressshirt")
    s = s.replace("tennis shoes", "tennisshoes")
    s = s.replace("tenis shoes", "tennisshoes")
    s = s.replace("tenis", "tennis")
    s = s.replace("sweater", "sweter")
    s = s.replace("underwear", "interiores")
    s = s.replace("undershorts", "undershort")
    s = s.replace("shorts", "short")

    # Quitar puntuación/espacios que no aportan significado.
    s = re.sub(r"[|;]+", " ", s)
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Estas variantes son conceptualmente equivalentes para huéspedes.
    alias = _clave_prenda_hotel_alias_base(s)
    return alias if alias else s


def _clave_prenda_hotel_alias_base(n):
    """Devuelve la clave canónica de huésped sin depender de Sheets."""
    if not n:
        return ""

    # Ropa interior: todas estas palabras significan el mismo artículo de huésped.
    if any(x in n for x in (
        "boxer", "bóxer", "interior", "interiores", "ropa interior",
        "ropa interior/panties", "ropa interior/underwear",
        "panty", "panties", "calzoncillo", "undershort", "underwear"
    )):
        return "interiores/panties"

    # Bermuda de vestir es un artículo distinto de pantaloneta/short.
    if "bermuda de vestir" in n:
        return "bermuda de vestir"

    if n in ("bermuda", "pantaloneta", "short"):
        return "pantaloneta/short"

    if n in ("camisa", "camisa/dressshirt", "dressshirt") or "dressshirt" in n:
        return "camisa/dressshirt"

    if "camiseta sport" in n or n == "sport camiseta":
        return "camiseta sport"

    if n in ("camiseta", "tshirt", "camiseta/tshirt", "tshirt/camiseta"):
        return "camiseta/tshirt"

    if n in ("pantalon", "pantalones", "pantalon/pants", "pants"):
        return "pantalon/pants"

    if n in ("jean", "jeans", "blue jeans"):
        return "jeans"

    if n in ("calcetines", "calcetin", "medias", "media", "socks", "sock", "calcetines/socks"):
        return "calcetines/socks"

    if n in ("sueter", "sweter", "sweater", "sueter/sweter"):
        return "sueter/sweter"

    if n in ("pijama", "pijamas", "pyjamas"):
        return "pijama"

    return ""


def _clave_prenda_hotel_alias(nombre_prenda):
    n = _normalizar_clave_precio_sin_alias(nombre_prenda)
    return _clave_prenda_hotel_alias_base(n) or n


def _normalizar_clave_precio_sin_alias(txt):
    if not txt:
        return ""
    s = limpiar_texto_simple(txt)
    s = s.replace("t-shirt", "tshirt")
    s = s.replace("t shirt", "tshirt")
    s = s.replace("dress shirt", "dressshirt")
    s = s.replace("tennis shoes", "tennisshoes")
    s = s.replace("tenis shoes", "tennisshoes")
    s = s.replace("tenis", "tennis")
    s = s.replace("sweater", "sweter")
    s = s.replace("underwear", "interiores")
    s = s.replace("undershorts", "undershort")
    s = s.replace("shorts", "short")
    s = re.sub(r"\s*/\s*", "/", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _codigo_item(item):
    """Obtiene el código aunque Apps Script lo devuelva con otra capitalización."""
    valor = _valor_item_case_insensitive(
        item, "codigo", "codigo_prenda", "id", "code", "cod", "codigo item", "codigo_item"
    )
    if valor not in (None, ""):
        try:
            return int(float(str(valor).strip()))
        except Exception:
            pass
    return None


def _buscar_por_nombre_normalizado(precios, clave_objetivo):
    for item in precios:
        clave = _normalizar_clave_precio(_nombre_item_oficial(item))
        if clave == clave_objetivo:
            return item
    return None


def _buscar_por_codigo_oficial(precios, codigo):
    if codigo is None:
        return None
    candidatos = [item for item in precios if _codigo_item(item) == codigo]
    if len(candidatos) == 1:
        return candidatos[0]
    return None


def _buscar_precio_oficial(nombre_prenda, precios):
    """Homologa una prenda de Gemini contra la LISTA OFICIAL recibida de Sheets.

    Importante: esta función jamás consulta catálogos históricos ni inventa precios.
    Solo puede devolver un artículo que exista en `precios`.
    """
    if not nombre_prenda or not precios:
        return None

    def norm(s):
        if not s:
            return ""
        s = limpiar_texto_simple(str(s))
        # CRÍTICO: Sheets puede devolver "Pantalón", "Camiséta", etc.
        # La comparación anterior eliminaba las letras acentuadas al pasar
        # por [a-z0-9], provocando que TODOS los artículos en español fallaran.
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.lower()
        s = s.replace("t-shirt", "tshirt").replace("t shirt", "tshirt")
        s = s.replace("dress shirt", "dressshirt")
        s = s.replace("sweater", "sweter")
        s = s.replace("underwear", "interiores")
        s = s.replace("undershorts", "undershort")
        s = s.replace("shorts", "short")
        s = re.sub(r"[^a-z0-9]+", " ", s).strip()
        return s

    def semantic(s):
        n = norm(s)
        # Orden importante: jeans antes de pantalon para no convertir jeans en pantalon.
        if "jeans" in n or re.search(r"\bjean\b", n):
            return "jeans"
        if any(x in n for x in ["boxer", "interior", "panty", "panties", "calzoncillo", "undershort", "underwear"]):
            return "interiores/panties"
        if "bermuda de vestir" in n:
            return "bermuda de vestir"
        if "pantaloneta" in n or re.search(r"\bshort\b", n) or "bermuda" in n:
            return "pantaloneta/short"
        if "camiseta sport" in n or ("sport" in n and "camiseta" in n):
            return "camiseta sport"
        if "camiseta" in n or "tshirt" in n:
            return "camiseta/tshirt"
        if "camisa" in n or "dressshirt" in n:
            return "camisa/dressshirt"
        if "pantalon" in n or re.search(r"\bpants\b", n):
            return "pantalon/pants"
        if "calcetin" in n or "calcetines" in n or re.search(r"\bmedia\b", n) or re.search(r"\bmedias\b", n) or "socks" in n:
            return "calcetines/socks"
        if "sueter" in n or "sweter" in n:
            return "sueter/sweter"
        if "pijama" in n or "pyjama" in n:
            return "pijama"
        return ""

    objetivo = semantic(nombre_prenda) or _clave_prenda_hotel_alias_base(norm(nombre_prenda)) or norm(nombre_prenda)

    # 1) Coincidencia semántica exacta. Permite que Sheets use variantes como
    # "Pantalón/Pants/JEANS" sin salir del artículo oficial correspondiente.
    candidatos = []
    for item in precios:
        oficial = _nombre_item_oficial(item)
        if not oficial:
            continue
        sem = semantic(oficial)
        canon = _clave_prenda_hotel_alias_base(_normalizar_clave_precio_sin_alias(oficial))
        if sem == objetivo or canon == objetivo:
            candidatos.append(item)

    if len(candidatos) == 1:
        return candidatos[0]

    # 2) Coincidencia normalizada exacta.
    objetivo_norm = norm(nombre_prenda)
    exactos = [
        item for item in precios
        if norm(_nombre_item_oficial(item)) == objetivo_norm
    ]
    if len(exactos) == 1:
        return exactos[0]

    # 3) Coincidencia por todas las palabras significativas del objetivo.
    #    Solo acepta una única coincidencia para evitar precios ambiguos.
    palabras_obj = set(re.findall(r"[a-z0-9]+", objetivo_norm))
    palabras_obj -= {"dress", "shirt", "tshirt", "sweter", "pants", "socks"}
    candidatos = []
    if palabras_obj:
        for item in precios:
            nom = norm(_nombre_item_oficial(item))
            palabras = set(re.findall(r"[a-z0-9]+", nom))
            if palabras_obj.issubset(palabras):
                candidatos.append(item)
        if len(candidatos) == 1:
            return candidatos[0]

    return None

def aplicar_precios_oficiales_hotel(filas, config_sesion, precios_oficiales):
    """Reemplaza cualquier precio generado por IA por el precio oficial.
    Si una prenda no existe en la lista oficial, se detiene para no guardar
    un valor incorrecto.
    """
    errores = []

    for f in filas:
        item = _buscar_precio_oficial(f.get("prenda", ""), precios_oficiales)
        if not item:
            errores.append(str(f.get("prenda", "Prenda sin nombre")))
            continue

        cantidad = a_entero(f.get("cantidad", 1))
        precio = _precio_item_oficial(item)

        f["prenda"] = str(_nombre_item_oficial(item) or f.get("prenda", ""))
        f["valorUnitario"] = precio
        f["valorTotal"] = cantidad * precio

        codigo_oficial = _codigo_item(item)
        if codigo_oficial is not None:
            f["codigo"] = codigo_oficial

        f["precio_fuente"] = "LISTA OFICIAL DE PRECIOS - ORIENTE" if str(config_sesion.get("key", "")).lower() in ("hilton", "hilton_empleados", "hampton", "hampton_empleados") else "LISTA OFICIAL DE PRECIOS"
        f["tipo_precio"] = (
            "HUESPEDES" if str(config_sesion.get("key", "")).lower() == "hilton" else
            "EMPLEADOS" if str(config_sesion.get("key", "")).lower() == "hilton_empleados" else
            config_sesion.get("tipo_precio", "HUESPEDES")
        )

    if errores:
        raise ValueError(
            "No se pudo homologar exactamente a la lista oficial de precios: "
            + ", ".join(errores)
            + ". No se guardaron precios inventados."
        )

    return filas

ARBOL_SERVICIOS = {
    # RUTA ORIENTE
    "wyndham_huespedes": {"ruta": "Oriente", "hotel": "Wyndham", "servicio": "Huéspedes", "hoja": "WYNDHAM_HUESPEDES_DATOS", "tipo": "HUESPEDES", "base_defecto": "WYNDHAM HUÉSPEDES"},
    "wyndham_lenceria": {"ruta": "Oriente", "hotel": "Wyndham Lencería", "servicio": "Lencería", "hoja": "WYNDHAM_LENCERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "WYNDHAM LENCERÍA"},
    "wyndham_manteleria": {"ruta": "Oriente", "hotel": "Wyndham Mantelería", "servicio": "Mantelería", "hoja": "WYNDHAM_MANTELERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "WYNDHAM MANTELERÍA"},
    "hilton": {"ruta": "Oriente", "hotel": "Hilton", "servicio": "General", "hoja": "HILTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HILTON HUÉSPEDES", "tipo_precio": "HUESPEDES"},
    "hilton_empleados": {"ruta": "Oriente", "hotel": "Hilton", "servicio": "Empleados", "hoja": "HILTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HILTON EMPLEADOS", "tipo_precio": "EMPLEADOS"},
    "hampton": {"ruta": "Oriente", "hotel": "Hampton", "servicio": "General", "hoja": "HAMPTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HAMPTON HUÉSPEDES", "tipo_precio": "HUESPEDES"},
    "hampton_empleados": {"ruta": "Oriente", "hotel": "Hampton", "servicio": "Empleados", "hoja": "HAMPTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HAMPTON EMPLEADOS", "tipo_precio": "EMPLEADOS"},
    "oceania": {"ruta": "Oriente", "hotel": "Oceania", "servicio": "Lencería", "hoja": "OCEANIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "OCEANIA LENCERÍA"},
    "fontana": {"ruta": "Oriente", "hotel": "Fontana", "servicio": "Lencería", "hoja": "FONTANA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "FONTANA LENCERÍA"},
    "almacen": {"ruta": "Mostrador", "hotel": "Almacén Central", "servicio": "Control", "hoja": "ALMACEN_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "ALMACÉN"},
    
    # RUTA NORTE
    "dann_huespedes": {"ruta": "Norte", "hotel": "Dann", "servicio": "Huéspedes", "hoja": "DANN_HUESPEDES_DATOS", "tipo": "HUESPEDES", "base_defecto": "DANN HUÉSPEDES"},
    "dann_empleados": {"ruta": "Norte", "hotel": "Dann", "servicio": "Empleados / Códigos", "hoja": "DANN_EMPLEADOS_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "DANN EMPLEADOS"},
    "dann_lenceria": {"ruta": "Norte", "hotel": "Dann", "servicio": "Lencería Horizontal", "hoja": "DANN_LENCERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "DANN LENCERÍA"},
    "suite": {"ruta": "Norte", "hotel": "Suite", "servicio": "General", "hoja": "SUITE_DATOS", "tipo": "HUESPEDES", "base_defecto": "SUITE HUÉSPEDES"},
    "suite_manteleria": {"ruta": "Norte", "hotel": "Suite", "servicio": "Mantelería (Fila 3-18)", "hoja": "SUITE_MANTELERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "SUITE MANTELERÍA"},
    "virrey": {"ruta": "Norte", "hotel": "Virrey", "servicio": "General", "hoja": "VIRREY_DATOS", "tipo": "HUESPEDES", "base_defecto": "VIRREY HUÉSPEDES"},
    "andes_plaza": {"ruta": "Norte", "hotel": "Andes Plaza", "servicio": "General", "hoja": "ANDES_PLAZA_DATOS", "tipo": "HUESPEDES", "base_defecto": "ANDES PLAZA HUÉSPEDES"},
    "bogotap_datos": {"ruta": "Norte", "hotel": "Bogotá Plaza", "servicio": "Uniformes (Cargo + Prenda)", "hoja": "BOGOTAP_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "BOGOTÁ PLAZA UNIFORMES"},
    "bogotap_huespedes": {"ruta": "Norte", "hotel": "Bogotá Plaza", "servicio": "Huéspedes/Empleados", "hoja": "BOGOTAP_HUESPEDES_DATOS", "tipo": "HUESPEDES", "base_defecto": "BOGOTÁ PLAZA HUÉSPEDES"},
    "eficacia": {"ruta": "Norte", "hotel": "Eficacia", "servicio": "Dotaciones", "hoja": "EFICACIA_DATOS", "tipo": "MATRIZ_FILAS_CLIENTE", "base_defecto": "EFICACIA DOTACIONES"}
}

CATALOGO_GLOBAL = """
[WYNDHAM HUÉSPEDES]
1|Abrigo/Coat|Lavado en seco|13200
2|Bata/Dress|Lavado en seco|11000
3|Bermuda|Lavado|4800
4|Brassiere/Brassiere|Lavado|3500
5|Bufanda/Scarf/Pasmina|Lavado en seco|5950
6|Blusa/Blouse|Lavado|5950
7|Blusa en seda/ Silk blouse|Lavado en seco|5950
8|Camisa/Dress Shirt|Lavado|5950
9|Camiseta Sport|Lavado|5950
10|Camiseta/T Shirt|Lavado|3800
11|Calzoncillo/Undershort|Lavado|1700
12|Calcetines/Socks|Lavado|1700
13|Corbata/Tie|Lavado en seco|5950
14|Chaleco/Vest|Lavado|5950
15|Chaqueta|Lavado|10400
16|Chaqueta plumas/Down Jacket|Lavado en seco|15800
17|Falda/ Skirt|Lavado en seco|5950
18|Faja|Lavado|7450
19|Gorro/Cap|Lavado|4800
20|Guante/Glove|Lavado|4800
21|Interiores/ Panties|Lavado|1700
22|Jeans|Lavado|5950
23|Maleta / Morral|Lavado|12650
24|Overol/Overalls|Lavado|12300
25|Pantalón/Pants|Lavado en seco|5950
26|Pantaloneta/Short|Lavado|2700
27|Pijama|Lavado|8650
28|Suéter/Sweter|Lavado|5950
29|Pañuelo|Lavado|1700
30|Ruana|Lavado en seco|13200
31|Sudadera|Lavado en seco|11000
32|Toalla|Lavado|5250
33|Traje/Suit|Lavado en seco|11000
34|Vestido dama seda|Lavado en seco|26300
35|Vestido baño|Lavado|11000
36|Zapatos tenis/ Tenis Shoes|Lavado|16400

[PRECIOS NORTE 2026 - HUÉSPEDES DANN / VIRREY / ANDES / BOGOTÁ PLAZA / HAMPTON / HILTON]
1|Abrigo/ Coat|Lavado en seco|19950
2|Bata/Dress|Lavado en seco|19950
3|Bermuda de vestir|Lavado|9918
4|Blazer (chaqueta paño)|Lavado en seco|12543
5|Blusa en seda/ Silk blouse|Lavado en seco|10602
6|Blusa/Blouse|Lavado|10431
7|Body|Lavado|12198
8|Brassiere/Brassiere|Lavado|5814
9|Bufanda/Scarf|Lavado en seco|6156
10|Calcetines/Socks|Lavado|3306
11|Calzoncillo/Undershort|Lavado|3306
12|Camisa/Dress Shirt|Lavado|9918
13|Camiseta Sport|Lavado|9918
14|Camiseta/T Shirt|Lavado|7410
15|Chaleco/Vest|Lavado|14022
16|Chaqueta plumas/Down Jacket|Lavado en seco|20520
17|Chaqueta/Jacket|Lavado|14022
18|Cobija huésped pequeña|Lavado|12350
19|Corbata/Tie|Lavado en seco|9918
20|Faja|Lavado|11286
21|Falda/ Skirt|Lavado en seco|9918
22|Gabardina / Trench coat|Lavado en seco|21950
23|Gorro/Cap|Lavado|4902
24|Guante/Glove|Lavado|4902
25|Interiores/ Panties|Lavado|3306
26|Jeans|Lavado|9918
27|Leggis / leggings|Lavado|9918
28|Licra deportiva|Lavado|5850
29|Maleta - morral|Lavado|15350
30|Overol/Overalls|Lavado|9918
31|Pantalón/Pants|Lavado en seco|9918
32|Pantaloneta/Short|Lavado|7125
33|Pañuelo|Lavado|3306
34|Pashmina|Lavado en seco|12846
35|Pijama|Lavado|11400
36|Ruana|Lavado en seco|15860
37|Smoking / Tuxedo|Lavado en seco|26350
38|Sudadera/Sweatshirt|Lavado|11799
39|Suéter/Sweter|Lavado|10944
40|Traje/Suit|Lavado en seco|19836
41|Vestido Dama Corto|Lavado en seco|25000
42|Vestido Dama Largo|Lavado en seco|59500
43|vestido de baño/Bathing dress|Lavado|12198
44|Zapatos tennis / Tennis Shoes|Lavado|17100

[EFICACIA DOTACIONES]
1|Bata paño|Lavado|15755
2|Blusa/ Camisa|Lavado|7878
3|Bolsa Grande|Lavado|24150
4|Camiseta Sport|Lavado|7015
5|Canguro|Lavado|7878
6|Casco moto|Lavado|20585
7|Cinturon|Lavado|6349
8|Chaqueta/Jacket|Lavado|7878
9|Delantal|Lavado|5463
10|Gorra/Cap|Lavado|4140
11|Guantes|Lavado|7878
12|Impermeable x2|Lavado|14386
13|Maleta de viaje|Lavado|29095
14|Morral / Maleta|Lavado|14548
15|Overol|Lavado|9315
16|Pantalón/Pants/JEANS|Lavado|7878
17|Pañoleta / Pañuelo|Lavado|5463
18|Rodillera|Lavado|5568
19|Suéter|Lavado|7878
20|Tennis / Zapato|Lavado|18170
"""

def limpiar_texto_simple(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize('NFD', str(txt))
    txt = ''.join(c for c in txt if unicodedata.category(c) != 'Mn')
    return txt.lower().strip()

def homologar_prenda_telegram(nombre_prenda, hotel_nom="", es_lenceria=False, es_wyndham_huespedes=False, es_manteleria=False, es_eficacia=False):
    norm = limpiar_texto_simple(nombre_prenda)
    hotel_clean = limpiar_texto_simple(hotel_nom)
    
    # EFICACIA DOTACIONES
    if es_eficacia or "eficacia" in hotel_clean:
        if "bolso" in norm or "bolsa" in norm:
            return "Bolsa Grande"
        if "morral" in norm or "maleta" in norm:
            return "Morral / Maleta"
        if "pantalon" in norm or "pantalones" in norm or "jean" in norm or "jeans" in norm:
            return "Pantalón/Pants/JEANS"
        if "chaqueta" in norm:
            return "Chaqueta/Jacket"
        if "camisa" in norm or "blusa" in norm:
            return "Blusa/ Camisa"
        if "camiseta" in norm:
            return "Camiseta Sport"
        if "chaleco" in norm or "chalecos" in norm:
            return "Chaleco"
        if "delantal" in norm or "delantales" in norm:
            return "Delantal"
        if "overol" in norm:
            return "Overol"
        if "gorra" in norm or "gorro" in norm:
            return "Gorra/Cap"
        return nombre_prenda.title()

    # 1. REGLA UNIVERSAL BÓXER = CALZONCILLO
    if "boxer" in norm:
        return "Calzoncillo/Undershort"

    # 2. REGLA MANTELERÍA (WYNDHAM / SUITE)
    if es_manteleria or "manteleria" in hotel_clean:
        if "blanco" in norm or norm == "mantel blanco":
            return "Mantel blanco"
        if "azul" in norm or norm == "mantel azul":
            return "Mantel azul"
        if "servilleta" in norm or "servilletas" in norm:
            return "Servilleta"

    # 3. WYNDHAM HUÉSPEDES
    if es_wyndham_huespedes or "wyndham" in hotel_clean:
        if any(w in norm for w in ["leggin", "leggis", "licra", "pantalon de licra", "malla"]):
            return "Pantalón/Pants"
        if any(w in norm for w in ["top", "crop top", "crop", "bra", "corpin"]):
            return "Brassiere/Brassiere"

    # 4. REGLA FONTANA (CERO FACIAL, MANO = TOALLA MANO, SÁBANA/SOBRESÁBANA)
    if "fontana" in hotel_clean:
        if "mano" in norm:
            return "Toalla mano"
        if any(w in norm for w in ["sobresabana", "lisa", "sabana"]):
            if "cortesia" not in norm and "ajustable" not in norm:
                return "Sábana"
        if "ajustable" in norm:
            return "Ajustable"
        if "cuerpo" in norm:
            return "Toalla cuerpo"
        if "tapete" in norm:
            return "Toalla tapete"

    # 5. REGLA OCEANÍA (DOBLE VS SENCILLA)
    if "oceania" in hotel_clean:
        if "ajustable" in norm:
            if any(w in norm for w in ["doble", "semidoble", "king", "queen"]):
                return "Sábana ajustable doble"
            return "Sábana ajustable sencilla"
        if any(w in norm for w in ["sobresabana", "plana", "lisa", "sabana"]):
            if "cortesia" not in norm and "ajustable" not in norm:
                if any(w in norm for w in ["doble", "semidoble", "king", "queen"]):
                    return "Sábana plana doble"
                return "Sábana plana sencilla"
        if "cojin" in norm or "cojines" in norm:
            return "Cojín"
        if norm in ["funda", "fundas"]:
            return "Funda"

    # 6. REGLA EXCLUSIVA FACIAL (SOLO WYNDHAM LENCERÍA)
    if "facial" in norm:
        if "wyndham" in hotel_clean and "lenceria" in hotel_clean:
            return "FACIAL"
        return "Toalla mano"

    # 7. PROTECTOR Y CORTESÍA GENERAL
    if "protector" in norm and "colchon" in norm:
        return "PROTECTOR DE COLCHON"
    if "cortesia" in norm:
        return "Sábana cortesía"
        
    if es_lenceria:
        if any(w in norm for w in ["mano", "toalla mano", "toallas mano"]):
            return "Toalla mano"
        if any(w in norm for w in ["cuerpo", "toalla cuerpo", "toallas cuerpo"]):
            return "Toalla cuerpo"
        if any(w in norm for w in ["tapete", "toalla tapete", "toallas tapete"]):
            return "Toalla tapete"
        if "cojin" in norm or "cojines" in norm:
            return "Cojín"
        if norm in ["funda", "fundas"]:
            return "Funda"
            
    return nombre_prenda

def es_servicio_lista_limpia(config_sesion):
    key = config_sesion.get('key', '')
    servicios_limpios = [
        "fontana", "oceania", "wyndham_lenceria", "wyndham_manteleria",
        "dann_lenceria", "dann_empleados", "bogotap_datos", "suite_manteleria", "almacen"
    ]
    if key in servicios_limpios:
        return True
    tipo = config_sesion.get('tipo', '')
    if tipo in ["LENCERIA_MATRIZ", "MATRIZ_FILAS_CLIENTE"]:
        return True
    return False

def optimizar_imagen_para_ia(img_pil):
    max_dim = 1600
    w, h = img_pil.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img_pil = img_pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    if img_pil.mode in ("RGBA", "P"):
        img_pil = img_pil.convert("RGB")
    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=85, optimize=True)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")

def llamar_gemini_rotativo(contents):
    """Rotación anti-503 entre modelos Flash vigentes de Google GenAI."""
    ultimo_error = None
    config_llamada = types.GenerateContentConfig(
        temperature=0.1
    )

    for modelo in MODELOS_ROTACION:
        for intento in range(2):
            try:
                resp = client.models.generate_content(
                    model=modelo, 
                    contents=contents, 
                    config=config_llamada
                )
                if resp and resp.text:
                    return resp.text
            except Exception as e:
                err_str = str(e)
                ultimo_error = e
                # Ante 503 UNAVAILABLE, alta demanda o 429, conmutar inmediatamente al siguiente Flash
                if any(k in err_str for k in ["503", "UNAVAILABLE", "high demand", "429", "RESOURCE_EXHAUSTED"]):
                    time.sleep(0.3)
                    break
                else:
                    time.sleep(0.4)
                    continue
    raise ultimo_error

def a_entero(val):
    try:
        return int(val)
    except Exception:
        return 1

def extraer_fecha_formato(texto):
    if not texto:
        return None
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b', texto.strip())
    if m:
        dia, mes, anio = m.groups()
        if len(anio) == 2:
            anio = "20" + anio
        return f"{int(dia):02d}/{int(mes):02d}/{anio}"
    return None


def fecha_operacion_sesion(sesion, texto=None):
    """Devuelve la fecha que debe usar la operación.
    Prioridad: fecha escrita explícitamente en el mensaje > fecha programada en sesión > hoy.
    """
    if texto:
        detectada = extraer_fecha_formato(texto)
        if detectada:
            return detectada
    for clave in ("fecha_forzada", "fecha_operacion"):
        val = sesion.get(clave)
        if val and extraer_fecha_formato(str(val)):
            return extraer_fecha_formato(str(val))
    return obtener_ahora_bogota().strftime("%d/%m/%Y")

def respaldar_lote_fotos_en_drive(imgs, hotel_nom, ruta_nom):
    """Genera un archivo consolidado con todas las fotos del lote y lo guarda en SOPORTE."""
    try:
        if not imgs:
            return
        ahora_bog = obtener_ahora_bogota()
        fecha_arch = ahora_bog.strftime("%Y-%m-%d")
        hora_arch = ahora_bog.strftime("%I-%M-%p")
        hotel_clean = re.sub(r'[^A-Za-z0-9_]', '', hotel_nom.replace(" ", "_")).upper()
        nombre_archivo = f"{fecha_arch}_{hora_arch}_{hotel_clean}_SOPORTE.pdf"
        
        # Convertir ráfaga de imágenes a un único PDF en memoria
        imgs_rgb = []
        for im in imgs:
            if im.mode != "RGB":
                imgs_rgb.append(im.convert("RGB"))
            else:
                imgs_rgb.append(im)
                
        pdf_buf = io.BytesIO()
        imgs_rgb[0].save(pdf_buf, format="PDF", save_all=True, append_images=imgs_rgb[1:])
        pdf_b64 = base64.b64encode(pdf_buf.getvalue()).decode('utf-8')
        
        payload_soporte = {
            "accion": "GUARDAR_SOPORTE_FOTOS",
            "ruta": ruta_nom,
            "hotel": hotel_nom,
            "nombre_archivo": nombre_archivo,
            "archivo_base64": pdf_b64,
            "mime_type": "application/pdf"
        }
        ejecutar_post_apps_script(URL_APPS_SCRIPT, payload_soporte, timeout=50)
    except Exception as e:
        print(f"Aviso: Respaldo de soporte en Drive omitido o fallido: {e}")


# -------------------------------------------------------------------------
# HILTON HUÉSPEDES — MÓDULO AISLADO Y MANUAL
# -------------------------------------------------------------------------
# Este módulo NO consulta Apps Script para precios. La tabla fue suministrada
# por el usuario y es la única fuente de precio para Hilton Huéspedes.
# La hoja destino sigue siendo HILTON_DATOS y la ruta Oriente.
# Los IDs son internos y estables, asignados en el mismo orden de la tabla.
HILTON_HUESPEDES_CATALOGO = {
    "abrigo/coat":                 {"id": 1,  "prenda": "Abrigo/ Coat",                 "servicio": "Lavado en seco", "precio": 15800},
    "bata/dress":                  {"id": 2,  "prenda": "Bata/Dress",                  "servicio": "Lavado en seco", "precio": 15500},
    "bermuda de vestir":           {"id": 3,  "prenda": "Bermuda de vestir",           "servicio": "Lavado",          "precio": 7850},
    "brassiere/brassiere":         {"id": 4,  "prenda": "Brassiere/Brassiere",         "servicio": "Lavado",          "precio": 4850},
    "bufanda/scarf":               {"id": 5,  "prenda": "Bufanda/Scarf",               "servicio": "Lavado en seco", "precio": 7950},
    "blusa/blouse":                {"id": 6,  "prenda": "Blusa/Blouse",                "servicio": "Lavado en seco", "precio": 7950},
    "blusa en seda/silk blouse":   {"id": 7,  "prenda": "Blusa en seda/ Silk blouse",  "servicio": "Lavado en seco", "precio": 7950},
    "camisa/dress shirt":          {"id": 8,  "prenda": "Camisa/Dress Shirt",          "servicio": "Lavado en seco", "precio": 7950},
    "camiseta sport":              {"id": 9,  "prenda": "Camiseta Sport",              "servicio": "Lavado",          "precio": 7950},
    "camiseta/t shirt":            {"id": 10, "prenda": "Camiseta/T Shirt",            "servicio": "Lavado",          "precio": 7350},
    "calzoncillo/undershort":      {"id": 11, "prenda": "Calzoncillo/Undershort",      "servicio": "Lavado",          "precio": 2700},
    "calcetines/socks":            {"id": 12, "prenda": "Calcetines/Socks",            "servicio": "Lavado",          "precio": 2700},
    "corbata/tie":                 {"id": 13, "prenda": "Corbata/Tie",                 "servicio": "Lavado en seco", "precio": 7950},
    "chaleco/vest":                {"id": 14, "prenda": "Chaleco/Vest",                "servicio": "Lavado",          "precio": 9525},
    "chaqueta/jacket":             {"id": 15, "prenda": "Chaqueta/Jacket",             "servicio": "Lavado en seco", "precio": 9750},
    "chaqueta plumas/down jacket": {"id": 16, "prenda": "Chaqueta plumas/Down Jacket", "servicio": "Lavado en seco", "precio": 18509},
    "falda/skirt":                 {"id": 17, "prenda": "Falda/ Skirt",                 "servicio": "Lavado en seco", "precio": 7850},
    "faja":                        {"id": 18, "prenda": "Faja",                        "servicio": "Lavado",          "precio": 9550},
    "gorro/cap":                   {"id": 19, "prenda": "Gorro/Cap",                   "servicio": "Lavado",          "precio": 6780},
    "guante/glove":                {"id": 20, "prenda": "Guante/Glove",                "servicio": "Lavado",          "precio": 6780},
    "interiores/panties":          {"id": 21, "prenda": "Interiores/ Panties",          "servicio": "Lavado",          "precio": 2700},
    "jeans":                       {"id": 22, "prenda": "Jeans",                       "servicio": "Lavado",          "precio": 7950},
    "maleta/morral":               {"id": 23, "prenda": "Maleta / morral",               "servicio": "Lavado",          "precio": 17650},
    "media velada":                {"id": 24, "prenda": "Media velada",                "servicio": "Lavado",          "precio": 4850},
    "overol/overalls":             {"id": 25, "prenda": "Overol/Overalls",             "servicio": "Lavado en seco", "precio": 14500},
    "pantalon/pants":              {"id": 26, "prenda": "Pantalón/Pants",              "servicio": "Lavado en seco", "precio": 7950},
    "pantaloneta/short":           {"id": 27, "prenda": "Pantaloneta/Short",           "servicio": "Lavado",          "precio": 7250},
    "panuelo":                     {"id": 28, "prenda": "Pañuelo",                     "servicio": "Lavado",          "precio": 2580},
    "pijama":                      {"id": 29, "prenda": "Pijama",                      "servicio": "Lavado",          "precio": 11350},
    "ruana":                       {"id": 30, "prenda": "Ruana",                       "servicio": "Lavado en seco", "precio": 15800},
    "sueter/sweter":               {"id": 31, "prenda": "Suéter/Sweter",               "servicio": "Lavado en seco", "precio": 7950},
    "sudadera/sweatshirt":         {"id": 32, "prenda": "Sudadera/Sweatshirt",         "servicio": "Lavado",          "precio": 14500},
    "traje/suit":                  {"id": 33, "prenda": "Traje/Suit",                  "servicio": "Lavado en seco", "precio": 15500},
    "toalla/huespedes":            {"id": 34, "prenda": "Toalla/ huespedes",            "servicio": "Lavado",          "precio": 7500},
    "vestido de bano":             {"id": 35, "prenda": "Vestido baño",                "servicio": "Lavado",          "precio": 10250},
    "zapatos tenis/tenis shoes":   {"id": 36, "prenda": "Zapatos tenis/ Tenis Shoes",  "servicio": "Lavado",          "precio": 18500},
    "planchado":                   {"id": 37, "prenda": "PLANCHADO",                   "servicio": "Planchado",        "precio": 6200},
    "planchado abrigos y trajes":  {"id": 38, "prenda": "PLANCHADO ABRIGOS Y TRAJES",  "servicio": "Planchado",        "precio": 12400},
}


def _norm_hilton_huespedes(txt):
    """Normalización exclusiva de Hilton Huéspedes."""
    if not txt:
        return ""
    s = unicodedata.normalize("NFKD", str(txt))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()
    s = s.replace("ó", "o").replace("é", "e")
    s = re.sub(r"[()\[\]{}]", " ", s)
    s = re.sub(r"[^a-z0-9/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _clasificar_hilton_huespedes(nombre):
    """Convierte la escritura de la planilla a UNA clave del catálogo Hilton."""
    n = _norm_hilton_huespedes(nombre)
    compact = n.replace(" ", "")

    # Casos específicos de la planilla Hilton mostrada por el usuario.
    if "pantalon" in n and ("jean" in n or "jeans" in n):
        return "jeans"
    if "jean" in n or "jeans" in n:
        return "jeans"
    if "boxer" in n or "calzoncillo" in n or "undershort" in n or "underwear" in n:
        return "calzoncillo/undershort"
    if "media velada" in n:
        return "media velada"
    if "calcetin" in n or "calcetines" in n or "socks" in n or re.search(r"\bmedia\b", n) or re.search(r"\bmedias\b", n):
        return "calcetines/socks"
    if "ropa interior" in n or "interiores" in n or "panty" in n or "panties" in n:
        return "interiores/panties"
    if "sueter" in n or "sweter" in n or "buso" in n or "busos" in n:
        return "sueter/sweter"
    if "camiseta" in n and "sport" in n:
        return "camiseta sport"
    if "camiseta" in n or "t shirt" in n or "tshirt" in compact:
        return "camiseta/t shirt"
    if "camisa" in n or "dress shirt" in n or "dressshirt" in compact:
        return "camisa/dress shirt"
    if "pantaloneta" in n or re.search(r"\bshort\b", n):
        return "pantaloneta/short"
    if "bermuda de vestir" in n:
        return "bermuda de vestir"
    if "pantalon" in n or re.search(r"\bpants\b", n):
        return "pantalon/pants"
    if "abrigo" in n or "coat" in n:
        return "abrigo/coat"
    if "bata" in n or "dress" in n:
        return "bata/dress"
    if "brassiere" in n or "brasier" in n or "bra" in n:
        return "brassiere/brassiere"
    if "bufanda" in n or "scarf" in n or "pasmina" in n:
        return "bufanda/scarf"
    if "blusa en seda" in n or "silk blouse" in n:
        return "blusa en seda/silk blouse"
    if "blusa" in n:
        return "blusa/blouse"
    if "corbata" in n or "tie" in n:
        return "corbata/tie"
    if "chaleco" in n or re.search(r"\bvest\b", n):
        return "chaleco/vest"
    if "chaqueta plumas" in n or "down jacket" in n:
        return "chaqueta plumas/down jacket"
    if "chaqueta" in n or "jacket" in n:
        return "chaqueta/jacket"
    if "falda" in n or "skirt" in n:
        return "falda/skirt"
    if "faja" in n:
        return "faja"
    if "gorro" in n or "cap" in n:
        return "gorro/cap"
    if "guante" in n or "glove" in n:
        return "guante/glove"
    if "maleta" in n or "morral" in n:
        return "maleta/morral"
    if "overol" in n or "overalls" in n:
        return "overol/overalls"
    if "panuelo" in n or "pañuelo" in str(nombre).lower():
        return "panuelo"
    if "pijama" in n or "pyjama" in n:
        return "pijama"
    if "ruana" in n:
        return "ruana"
    if "sudadera" in n or "sweatshirt" in n:
        return "sudadera/sweatshirt"
    if "traje" in n or "suit" in n:
        return "traje/suit"
    if "vestido" in n and ("bano" in n or "baño" in str(nombre).lower()):
        return "vestido de bano"
    if "toalla" in n:
        return "toalla/huespedes"
    if "tenis" in n or "zapatos" in n or "shoes" in n:
        return "zapatos tenis/tenis shoes"
    if n == "planchado":
        return "planchado"
    if "planchado" in n and "abrigo" in n and "traje" in n:
        return "planchado abrigos y trajes"

    return None


def procesar_hilton_huespedes_manual(filas, fecha_hoy, correccion_usuario=None):
    """Procesa Hilton Huéspedes sin Apps Script: catálogo manual cerrado."""
    if not isinstance(filas, list):
        raise ValueError("Gemini no devolvió una lista válida para Hilton Huéspedes.")

    salida = []
    ultimo_habitacion = ""
    errores = []

    for idx, f in enumerate(filas, start=1):
        if not isinstance(f, dict):
            continue

        hab = str(f.get("habitacion", f.get("habitacion_o_persona", "")) or "").strip()
        # Gemini debe propagar la habitación cuando la celda viene vacía/ditto.
        if hab and any(ch.isdigit() for ch in hab):
            ultimo_habitacion = hab
        elif ultimo_habitacion:
            hab = ultimo_habitacion
        else:
            hab = "SIN HABITACION"

        clave = _clasificar_hilton_huespedes(f.get("prenda", ""))
        if not clave or clave not in HILTON_HUESPEDES_CATALOGO:
            errores.append(str(f.get("prenda", "Prenda sin nombre")))
            continue

        item = HILTON_HUESPEDES_CATALOGO[clave]
        cantidad = max(1, a_entero(f.get("cantidad", 1)))

        fila = dict(f)
        fila["fecha"] = f.get("fecha") or fecha_hoy
        fila["habitacion"] = hab
        fila["codigo"] = item["id"]
        fila["prenda"] = item["prenda"]
        fila["servicio"] = item["servicio"]
        fila["cantidad"] = cantidad
        fila["valorUnitario"] = float(item["precio"])
        fila["valorTotal"] = cantidad * float(item["precio"])
        fila["remision"] = ""
        fila["extra"] = "No"
        fila["tipo_operacion_detectada"] = "HUESPEDES"
        fila["precio_fuente"] = "CATALOGO MANUAL HILTON HUESPEDES - ORIENTE 2026"
        fila["tipo_precio"] = "HUESPEDES"
        fila["ruta_precio"] = "Oriente"
        fila["hotel_precio"] = "Hilton"
        salida.append(fila)

    if errores:
        raise ValueError(
            "Hilton Huéspedes: no pude clasificar estas prendas del catálogo manual: "
            + ", ".join(errores)
        )

    if not salida:
        raise ValueError("Hilton Huéspedes: no se detectaron prendas válidas en la imagen.")

    return salida


def analizar_con_ia(contenido_multimodal, config_sesion, correccion_usuario=None):
    ahora_bog = obtener_ahora_bogota()
    fecha_hoy = fecha_operacion_sesion(config_sesion)
    
    if isinstance(contenido_multimodal, list):
        for elem in contenido_multimodal:
            if isinstance(elem, str):
                f_det = extraer_fecha_formato(elem)
                if f_det:
                    fecha_hoy = f_det
                    break
    elif isinstance(contenido_multimodal, str):
        f_det = extraer_fecha_formato(contenido_multimodal)
        if f_det:
            fecha_hoy = f_det

    hotel = config_sesion['hotel']
    servicio = config_sesion['servicio']
    tipo_op = config_sesion.get('tipo', 'HUESPEDES')
    key = config_sesion.get('key', '')
    
    es_wyndham_huespedes = (key == "wyndham_huespedes")
    es_hilton_huespedes = (key == "hilton")
    es_manteleria = ("manteleria" in key or "manteleria" in servicio.lower())
    es_lenceria = es_servicio_lista_limpia(config_sesion)
    es_eficacia = (key == "eficacia")
    es_hampton_hilton = ("hampton" in limpiar_texto_simple(hotel) or "hilton" in limpiar_texto_simple(hotel))
    precios_oficiales = []

    # Hampton / Hilton: la IA solo clasifica la prenda. El precio SIEMPRE
    # sale de la hoja oficial de precios de Google Sheets.
    if es_hampton_hilton and key != "hilton":
        precios_oficiales = obtener_precios_oficiales_hotel(config_sesion)

    # 1. PROMPT EXCLUSIVO HILTON HUÉSPEDES
    if key == "hilton":
        prompt = f"""
        Eres el lector exclusivo de planillas de LAVADO DE ROPA HUÉSPEDES del HOTEL HILTON GARDEN INN BOGOTÁ.
        NO uses ningún catálogo externo, Norte, Hampton, Wyndham ni precios de memoria.

        TU ÚNICA TAREA ES LEER LA PLANILLA DE LA FOTO.

        REGLAS DE LECTURA DE ESTA PLANILLA:
        1. Lee HAB., CANT y PRENDA. COLOR, MARCA y OBSERVACIÓN no se guardan como prendas.
        2. Lee también la fecha de la planilla del encabezado. Si aparece, por ejemplo, "30 Sep DE 2026", devuelve "30/09/2026" en cada fila.
        3. Si una fila de HAB. está vacía, tiene una raya, comillas, ditto o marca que significa "igual que arriba", usa la ÚLTIMA HABITACIÓN NUMÉRICA visible.
        4. Si aparece una nueva habitación numérica, desde esa fila las filas siguientes pertenecen a esa nueva habitación hasta que aparezca otra.
        5. Conserva cantidades exactamente.
        6. Lee variaciones manuscritas:
           - Pantalón / Pantalones -> Pantalón
           - Pantalón Jeans / Jeans -> Jeans
           - Suéter / Sueter / Buso / Busos -> Suéter
           - Camisa / Camisas -> Camisa
           - Camiseta / Camisetas -> Camiseta
           - Boxer -> Boxer
           - Medias / Media / Calcetines -> Calcetines
           - Toalla -> Toalla
        6. NO confundas Pantalón con Jeans: si dice Jeans o Pantalón Jeans, es Jeans.
        7. NO confundas Camisa con Camiseta.
        8. Devuelve una fila por cada línea de prenda.

        FECHA: {fecha_hoy}
        {f"CORRECCIÓN DEL USUARIO: {correccion_usuario}" if correccion_usuario else ""}

        Devuelve EXCLUSIVAMENTE JSON válido, sin markdown, con este formato:
        [
          {{
            "fecha": "{fecha_hoy}",
            "habitacion": "713",
            "cantidad": 1,
            "prenda": "Pantalón"
          }}
        ]
        """

    # 2. PROMPT EFICACIA DOTACIONES
    elif es_eficacia:
        prompt = f"""
        Eres el auditor oficial de Lavaarte Lavandería SAS para el cliente 'EFICACIA DOTACIONES'.
        En las planillas o notas manuscritas de Eficacia, cada línea o bloque pertenece a una EMPRESA / CLIENTE cliente de Eficacia.
        Estructura típica de las notas:
        [Nombre Empresa] = [Cantidad] [Prenda] + [Cantidad] [Prenda]
        
        Reglas de extracción:
        - Cada empresa debe colocarse en el campo 'habitacion' (ej: 'Kikes', 'Mondelez', 'Seguridad', 'Novous', 'Henkel', 'Exito', 'Pajoy', 'Nivea', 'Galderma', 'Central Cervecero', 'Alpina', 'Eficacia').
        - Si dice '1 Bolso eficacia', la empresa es 'Eficacia' y la prenda es 'Bolsa Grande'.
        - Homologa las prendas al catálogo de Eficacia: 'Bolsa Grande', 'Morral / Maleta', 'Pantalón/Pants/JEANS', 'Chaqueta/Jacket', 'Blusa/ Camisa', 'Camiseta Sport', 'Chaleco', 'Delantal', 'Overol', 'Gorra/Cap'.
        
        {f"AJUSTE DEL USUARIO: {correccion_usuario}" if correccion_usuario else ""}

        Devuelve EXCLUSIVAMENTE un JSON válido (array de objetos sin markdown):
        [
          {{
            "fecha": "{fecha_hoy}",
            "habitacion": "Nombre Empresa (Ej: Kikes / Mondelez / Alpina)",
            "prenda": "Pantalón/Pants/JEANS",
            "cantidad": 2,
            "tipo_operacion_detectada": "MATRIZ_FILAS_CLIENTE"
          }}
        ]
        """

    # 2. PROMPT LENCERÍA / MATRICES
    elif es_lenceria:
        prompt = f"""
        Eres el auditor de control de lavandería industrial para Lavaarte Lavandería SAS.
        Operación: Lencería / Mantelería de Hotel '{hotel}', Servicio '{servicio}'.
        
        REGLAS DE HOMOLOGACIÓN PARA ESTE HOTEL:
        - Hotel Oceanía: 'ajustable doble' -> Sábana ajustable doble, 'ajustable'/'ajustable sensilla' -> Sábana ajustable sencilla, 'sabana doble' -> Sábana plana doble, 'sabana sensilla' -> Sábana plana sencilla, 'cuerpo' -> Toalla cuerpo, 'mano' -> Toalla mano, 'tapete' -> Toalla tapete, 'cortesia' -> Sábana cortesía, 'fundas'/'funda' -> Funda.
        - Hotel Fontana: NO EXISTE FACIAL. 'mano' -> Toalla mano, 'cuerpo' -> Toalla cuerpo, 'tapete' -> Toalla tapete, 'ajustable' -> Ajustable, 'sabana'/'sobresabana' -> Sábana.
        - Wyndham Lencería: Es el único con 'FACIAL'.
        - Wyndham / Suite Mantelería: 'blanco' -> Mantel blanco, 'azul' -> Mantel azul, 'servilleta' -> Servilleta.
        
        {f"AJUSTE DEL USUARIO: {correccion_usuario}" if correccion_usuario else ""}
        
        Extrae cada ítem y su cantidad exacta. Devuelve EXCLUSIVAMENTE un JSON válido (array de objetos sin markdown):
        [
          {{
            "fecha": "{fecha_hoy}",
            "prenda": "Nombre de la prenda",
            "cantidad": 10,
            "tipo_operacion_detectada": "{tipo_op}"
          }}
        ]
        """

    # 3. PROMPT HUÉSPEDES GENERAL
    else:
        prompt = f"""
        Eres el auditor contable oficial de Lavaarte Lavandería SAS.
        Operación activa: Hotel '{hotel}', Servicio '{servicio}', Clave: '{key}'.
        
        REGLAS ESTRICTAS Y AISLADAS POR HOTEL:
        0. REGLA ABSOLUTA HILTON: Si Clave = 'hilton', trabaja ÚNICAMENTE con Hilton Huéspedes de RUTA ORIENTE.
           NO uses, consultes, nombres ni deduzcas precios/códigos de ningún catálogo Norte.
           El precio final SIEMPRE será reemplazado por la lista oficial devuelta por Google Sheets.
        1. REGLAS DE HOMOLOGACIÓN DE PRENDAS: conserva el significado exacto de lo escrito.
           - 'boxer', 'bóxer', 'interior', 'interiores', 'panty' y 'panties' representan ROPA INTERIOR.
           - 'bermuda', 'pantaloneta' y 'short' representan PANTALONETA/SHORT.
           - 'camisa' representa CAMISA/DRESS SHIRT.
           - 'camiseta' representa CAMISETA/T SHIRT, salvo que diga explícitamente 'sport'.
           - 'jeans' representa JEANS.
           - 'pantalón'/'pantalon' representa PANTALÓN/PANTS.
           - 'medias'/'media'/'calcetines' representan CALCETINES/SOCKS.
           - 'suéter'/'sueter' representa SUÉTER/SWETER.
           Estas equivalencias son de clasificación; el nombre y precio finales se toman de la lista oficial de Google Sheets.
        2. REGLA SIN REMISIÓN EN HILTON Y WYNDHAM: En '{hotel}' el campo remision debe quedar vacío ("").
        3. Clasifica cada prenda con máxima precisión. NO conviertas una prenda en otra solo porque el nombre inglés sea parecido.
        4. NUNCA inventes ni reutilices precios de memoria. Para Hampton y Hilton,
           el precio oficial será colocado posteriormente por el sistema desde la
           hoja PRECIOS de Google Sheets.

        {"CATÁLOGO GLOBAL DE APOYO:\n" + CATALOGO_GLOBAL if not es_hampton_hilton else ""}

        {(
            "CATÁLOGO OFICIAL DE PRENDAS PARA ESTE HOTEL / TIPO DE PRECIO:\n" +
            "\n".join("- " + str(_nombre_item_oficial(x)) for x in precios_oficiales) +
            "\nUsa exactamente el nombre oficial más cercano de esta lista. No inventes prendas."
        ) if es_hampton_hilton else ""}

        {f"AJUSTE DEL USUARIO: {correccion_usuario}" if correccion_usuario else ""}

        Devuelve EXCLUSIVAMENTE un JSON válido:
        [
          {{
            "fecha": "{fecha_hoy}",
            "remision": "{'' if (es_hilton_huespedes or es_wyndham_huespedes) else '1234'}",
            "habitacion": "402",
            "codigo": 25,
            "prenda": "Pantalón/Pants",
            "servicio": "Lavado en seco",
            "cantidad": 2,
            "valorUnitario": 5950,
            "valorTotal": 11900,
            "extra": "No",
            "tipo_operacion_detectada": "{tipo_op}"
          }}
        ]
        """
    
    contents = [prompt]
    if isinstance(contenido_multimodal, list):
        for item in contenido_multimodal:
            if isinstance(item, Image.Image):
                contents.append(optimizar_imagen_para_ia(item))
            else:
                contents.append(item)
    elif isinstance(contenido_multimodal, Image.Image):
        contents.append(optimizar_imagen_para_ia(contenido_multimodal))
    elif contenido_multimodal is not None:
        contents.append(contenido_multimodal)
        
    texto_raw = llamar_gemini_rotativo(contents)
    texto = texto_raw.strip().replace("```json", "").replace("```", "").strip()
    filas = json.loads(texto)

    # Hilton Huéspedes queda COMPLETAMENTE aislado del flujo genérico.
    # No consulta Apps Script para precios ni pasa por homologación de Norte.
    if key == "hilton":
        return procesar_hilton_huespedes_manual(
            filas,
            fecha_hoy,
            correccion_usuario=correccion_usuario
        )

    if isinstance(filas, list):
        for f in filas:
            if not f.get("fecha"):
                f["fecha"] = fecha_hoy
            f["prenda"] = homologar_prenda_telegram(
                f.get("prenda", ""), 
                hotel_nom=hotel, 
                es_lenceria=es_lenceria, 
                es_wyndham_huespedes=es_wyndham_huespedes, 
                es_manteleria=es_manteleria,
                es_eficacia=es_eficacia
            )
            if not es_lenceria and not es_eficacia:
                if not f.get("servicio") or f.get("servicio") == "":
                    f["servicio"] = "Lavado en seco" if any(w in f["prenda"].lower() for w in ["pantalón", "pantalon", "chaqueta", "vestido", "abrigo", "traje", "blazer"]) else "Lavado"

                if es_hilton_huespedes or es_wyndham_huespedes:
                    f["remision"] = ""

                if es_wyndham_huespedes:
                    if f["prenda"] == "Pantalón/Pants":
                        f["codigo"] = 25
                        f["servicio"] = "Lavado en seco"
                        f["valorUnitario"] = 5950
                        f["valorTotal"] = a_entero(f.get("cantidad", 1)) * 5950
                    elif f["prenda"] == "Brassiere/Brassiere":
                        f["codigo"] = 4
                        f["servicio"] = "Lavado"
                        f["valorUnitario"] = 3500
                        f["valorTotal"] = a_entero(f.get("cantidad", 1)) * 3500
                    elif f["prenda"] == "Calzoncillo/Undershort":
                        f["codigo"] = 11
                        f["servicio"] = "Lavado"
                        f["valorUnitario"] = 1700
                        f["valorTotal"] = a_entero(f.get("cantidad", 1)) * 1700

    # FUENTE ÚNICA DE PRECIOS: Hampton / Hilton
    if es_hampton_hilton and key != "hilton" and isinstance(filas, list):
        aplicar_precios_oficiales_hotel(
            filas,
            config_sesion,
            precios_oficiales
        )

    # Consolidación de filas en Eficacia Dotaciones
    if es_eficacia and isinstance(filas, list):
        filas_consolidadas_ef = {}
        for f in filas:
            emp = str(f.get("habitacion", f.get("empresa", "GENERAL"))).strip().title()
            if not emp:
                emp = "GENERAL"
            pr = f.get("prenda", "")
            cant = a_entero(f.get("cantidad", 1))
            k_ef = f"{emp}_{pr}"
            if k_ef in filas_consolidadas_ef:
                filas_consolidadas_ef[k_ef]["cantidad"] += cant
            else:
                f["habitacion"] = emp
                f["cantidad"] = cant
                filas_consolidadas_ef[k_ef] = f
        return list(filas_consolidadas_ef.values())

    if es_wyndham_huespedes and isinstance(filas, list):
        filas_consolidadas = {}
        for f in filas:
            hab = str(f.get("habitacion", "")).strip()
            es_nn = ("nn" in hab.lower() or "n.n" in hab.lower())
            if not (any(char.isdigit() for char in hab) or es_nn):
                continue
            cod = f.get("codigo", 0)
            extra = f.get("extra", "No")
            clave_unica = f"{hab}_{cod}_{extra}"
            cant = a_entero(f.get("cantidad", 1))
            v_unit = float(f.get("valorUnitario", 0))
            
            if clave_unica in filas_consolidadas:
                filas_consolidadas[clave_unica]["cantidad"] += cant
                filas_consolidadas[clave_unica]["valorTotal"] = filas_consolidadas[clave_unica]["cantidad"] * v_unit
            else:
                f["cantidad"] = cant
                f["valorTotal"] = cant * v_unit
                filas_consolidadas[clave_unica] = f
                
        return list(filas_consolidadas.values())
        
    return filas

def analizar_financiero_ia(contenido_multimodal, tipo_forzado="EGRESO", cuenta_destino="LAVAARTE", datos_existentes=None, ajuste_texto=None):
    ahora_bog = obtener_ahora_bogota()
    fecha_hoy = ahora_bog.strftime("%d/%m/%Y")
    extra_contexto = ""
    if datos_existentes:
        extra_contexto = f"\nDATOS PREVIAMENTE DETECTADOS: {json.dumps(datos_existentes, ensure_ascii=False)}\nCORRECCIÓN: {ajuste_texto}"

    if cuenta_destino == "CARLOS":
        prompt = f"""
        Eres el asistente financiero personal de Carlos Andrés Suárez.
        Movimiento personal: {tipo_forzado}. Fecha: '{fecha_hoy}'.
        Categorías: Alimentación, Transporte, Deporte / Ciclismo, Ocio / Cine, Hogar / Servicios, Salud, Ropa, Ahorro / Inversión, Otros.
        {extra_contexto}
        Devuelve EXCLUSIVAMENTE JSON:
        {{
          "fecha": "{fecha_hoy}",
          "tipo": "{tipo_forzado}",
          "categoria": "Alimentación / Transporte / etc.",
          "concepto": "Descripción concisa",
          "metodo_pago": "Efectivo / Nequi / Daviplata / Tarjeta Débito / Tarjeta Crédito / Transferencia",
          "valor": 50000
        }}
        """
    else:
        prompt = f"""
        Eres el asistente contable financiero de Lavaarte Lavandería SAS.
        Movimiento: {tipo_forzado}. Fecha: '{fecha_hoy}'.
        {extra_contexto}
        Devuelve EXCLUSIVAMENTE JSON:
        {{
          "fecha": "{fecha_hoy}",
          "tipo": "{tipo_forzado}",
          "categoria": "Combustible / Insumos Químicos / Mantenimiento / Servicios Públicos / Nómina / Papelería / Arriendo / Facturación Hoteles / Servicios Mostrador / Otros",
          "concepto": "Descripción clara",
          "tercero": "Proveedor o Cliente",
          "metodo_pago": "Efectivo / Transferencia Bancolombia / Nequi / Daviplata",
          "responsable": "Nombre",
          "valor": 120000,
          "estado": "PAGADO / CONCILIADO",
          "observaciones": ""
        }}
        """
        
    contents = [prompt]
    if isinstance(contenido_multimodal, Image.Image):
        contents.append(optimizar_imagen_para_ia(contenido_multimodal))
    elif isinstance(contenido_multimodal, list):
        for it in contenido_multimodal:
            if isinstance(it, Image.Image):
                contents.append(optimizar_imagen_para_ia(it))
            else:
                contents.append(it)
    elif contenido_multimodal is not None:
        contents.append(contenido_multimodal)
        
    texto_raw = llamar_gemini_rotativo(contents)
    res = json.loads(texto_raw.strip().replace("```json", "").replace("```", "").strip())
    try:
        res["valor"] = float(res.get("valor", 0))
    except Exception:
        res["valor"] = 0.0
    if not res.get("fecha"):
        res["fecha"] = fecha_hoy
    return res

def enviar_mensaje_segmentado(chat_id, texto, reply_markup=None):
    MAX_CHARS = 3800
    if len(texto) <= MAX_CHARS:
        bot.send_message(chat_id, texto, reply_markup=reply_markup, parse_mode='Markdown')
        return
    partes = []
    lineas = texto.split('\n')
    bloque = ""
    for l in lineas:
        if len(bloque) + len(l) + 1 > MAX_CHARS:
            partes.append(bloque)
            bloque = l + "\n"
        else:
            bloque += l + "\n"
    if bloque:
        partes.append(bloque)
    for i, p in enumerate(partes):
        markup = reply_markup if i == len(partes) - 1 else None
        bot.send_message(chat_id, p, reply_markup=markup, parse_mode='Markdown')


# =========================================================================
# MOTOR PROFESIONAL DE LENCERÍA / MANTELERÍA — MENÚ SIN GEMINI
# Catálogo base extraído de ITEMS COMPLETOS.xlsx.
# Los precios del Excel NO se utilizan aquí. Solo artículos.
# Los artículos nuevos se persisten en la hoja CATALOGO_BOT mediante Apps Script.
# =========================================================================
CATALOGOS_MANUALES_BASE = {
    "wyndham_lenceria": [
        "BATA", "COBIJA", "COJIN", "DUVET", "FACIAL", "FALDON", "FUNDA",
        "PIE DE CAMA", "PLUMON", "PROTECTOR ALMOHADA", "PROTECTOR DE COLCHON",
        "SABANAS AJUSTABLES", "SABANAS PLANAS", "TOALLA COSTURAS A LOS LADOS",
        "TOALLAS DE CUERPO", "TOALLAS DE MANO", "TOALLAS DE TAPETE"
    ],
    "wyndham_manteleria": [
        "LICRA", "MANTEL", "MANTEL AZUL", "MANTEL AMARILLO", "MANTEL ROJO",
        "MANTEL SINTETICO", "MULETON", "SERVILLETA", "REPASADOR"
    ],
    "fontana": [
        "BATA", "COBIJA", "COJÍN", "ALMOHADA", "DUVET", "FALDON CAMA", "FUNDA",
        "PIECERO", "PLUMÓN", "PROTECTOR ALMOHADA", "PROTECTOR COLCHÓN",
        "SABANA AJUSTABLE", "SABANA", "SABANA CORTESIA", "TOALLA CUERPO",
        "TOALLA MANO", "TOALLA TAPETE"
    ],
    "oceania": [
        "TOALLA CUERPO", "TOALLA MANO", "TOALLA TAPETE", "SABANA AJUSTABLE DOBLE",
        "SABANA AJUSTABLE SENCILLA", "SOBRE SABANA DOBLE", "SOBRE SABANA SENCILLA",
        "SABANA CORTESIA", "FUNDA RAYAS", "FUNDA LISA", "PROTECTOR COLCHON DOBLE",
        "PROTECTOR COLCHON SENCILLO", "PROTECTOR ALMOHADA", "PIE DE CAMA", "FALDON",
        "COJIN DECORATIVO", "COBIJAS", "BANDERA", "MANTEL"
    ],
    "suite_manteleria": [
        "Faldon Prensado", "Licra Grande - café", "Licra Pequeña - Azul", "Mantel",
        "Mantel lanudo", "Mantel redondo", "Mantel Rectangular", "Servilleta",
        "Velo", "Tapas"
    ],
    "dann_lenceria": [
        "AJUSTABLE", "COJIN GRANDE", "COJIN SASTRERIA", "COJIN.", "DUVET", "FALDON",
        "FUNDA", "MANTEL", "PLUMON", "SABANA", "PIE DE CAMA", "ARREGLO TOALLAS",
        "COBIJA SPA"
    ]
}

MANUAL_CATALOGO_KEYS = set(CATALOGOS_MANUALES_BASE.keys())
MANUAL_CATALOGO_PAGE_SIZE = 8

def _catalogo_nombre_servicio(key):
    cfg = ARBOL_SERVICIOS.get(key, {})
    return str(cfg.get("servicio", "Lencería"))

def obtener_catalogo_manual(chat_id, key):
    """Carga catálogo base + artículos persistidos en Google Sheets."""
    ses = sesiones.setdefault(chat_id, {})
    base = list(CATALOGOS_MANUALES_BASE.get(key, []))
    try:
        cfg = ARBOL_SERVICIOS.get(key, {})
        resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, {
            "accion": "OBTENER_CATALOGO",
            "ruta": cfg.get("ruta", "Oriente"),
            "hotel": cfg.get("hotel", ""),
            "servicio": cfg.get("servicio", ""),
            "clave_catalogo": key
        }, timeout=30)
        if resp.get("status") == "SUCCESS":
            for item in resp.get("items", []):
                nombre = str(item.get("item", "")).strip()
                if nombre and nombre not in base:
                    base.append(nombre)
    except Exception as e:
        print(f"[CATALOGO] Usando catálogo base para {key}: {e}")
    ses["catalogo_items"] = base
    return base

def _manual_resumen(chat_id):
    ses = sesiones.get(chat_id, {})
    items = ses.get("manual_cantidades", {})
    activos = [(k, int(v)) for k, v in items.items() if int(v) > 0]
    if not activos:
        return "📋 *Sin cantidades seleccionadas todavía.*"
    total = sum(v for _, v in activos)
    txt = "📋 *RESUMEN ACTUAL*\n\n"
    for nombre, cant in activos:
        txt += f"• `{nombre}` — *{cant}*\n"
    txt += f"\n📊 *TOTAL: {total}*"
    return txt

def _manual_menu_catalogo(chat_id, page=0):
    ses = sesiones[chat_id]
    key = ses["key"]
    items = ses.get("catalogo_items") or obtener_catalogo_manual(chat_id, key)
    ses["manual_page"] = max(0, min(page, max(0, (len(items)-1)//MANUAL_CATALOGO_PAGE_SIZE)))
    page = ses["manual_page"]
    inicio = page * MANUAL_CATALOGO_PAGE_SIZE
    bloque = items[inicio:inicio + MANUAL_CATALOGO_PAGE_SIZE]

    markup = InlineKeyboardMarkup(row_width=2)
    for idx, nombre in enumerate(bloque, start=inicio):
        cant = int(ses.get("manual_cantidades", {}).get(nombre, 0))
        etiqueta = f"{nombre[:28]} [{cant}]"
        markup.add(InlineKeyboardButton(etiqueta, callback_data=f"ml_item|{idx}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"ml_page|{page-1}"))
    if inicio + MANUAL_CATALOGO_PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"ml_page|{page+1}"))
    if nav:
        markup.row(*nav)

    markup.add(InlineKeyboardButton("🧾 Ver resumen", callback_data="ml_summary"))
    markup.add(InlineKeyboardButton("➕ Agregar artículo", callback_data="ml_new"))
    markup.add(InlineKeyboardButton("❌ Cancelar", callback_data="ml_cancel"))

    movimiento = "RECEPCIÓN" if ses.get("movimiento") == "RECEPCIÓN" else "DESPACHO EN PLANTA"
    texto = f"🧺 *{movimiento} — {ses.get('hotel', 'Hotel')}*\n"
    texto += f"Servicio: *{ses.get('servicio', 'Lencería')}*\n\n"
    texto += "Selecciona un artículo. Al abrirlo podrás sumar +1, +5, +10, +25, +50 o escribir una cantidad.\n\n"
    texto += _manual_resumen(chat_id)
    return texto, markup

def _manual_editor(chat_id, idx):
    ses = sesiones[chat_id]
    items = ses.get("catalogo_items", [])
    if idx < 0 or idx >= len(items):
        return "⚠️ Artículo no encontrado.", InlineKeyboardMarkup()
    nombre = items[idx]
    ses["manual_item_index"] = idx
    cant = int(ses.get("manual_cantidades", {}).get(nombre, 0))
    markup = InlineKeyboardMarkup(row_width=3)
    markup.row(InlineKeyboardButton("−1", callback_data="ml_dec|1"), InlineKeyboardButton(str(cant), callback_data="ml_noop"), InlineKeyboardButton("+1", callback_data="ml_inc|1"))
    markup.row(InlineKeyboardButton("+5", callback_data="ml_inc|5"), InlineKeyboardButton("+10", callback_data="ml_inc|10"), InlineKeyboardButton("+25", callback_data="ml_inc|25"))
    markup.row(InlineKeyboardButton("+50", callback_data="ml_inc|50"), InlineKeyboardButton("✏️ Escribir cantidad", callback_data="ml_custom"))
    markup.add(InlineKeyboardButton("⬅️ Volver a artículos", callback_data="ml_backcat"))
    texto = f"🧺 *{nombre}*\n\nCantidad actual: *{cant}*\n\nUsa los incrementos rápidos o escribe directamente la cantidad total."
    return texto, markup

def menu_manual_operacion(key):
    cfg = ARBOL_SERVICIOS.get(key, {})
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📥 Recibir", callback_data="ml_start|RECIBIR"),
        InlineKeyboardButton("📤 Despachar en planta", callback_data="ml_start|DESPACHAR")
    )
    markup.add(InlineKeyboardButton("🤝 Entregar en hotel", callback_data="ml_entrega_hotel"))
    markup.add(InlineKeyboardButton("📋 Ver catálogo", callback_data="ml_viewcat"))
    markup.add(InlineKeyboardButton("➕ Agregar artículo", callback_data="ml_new"))
    markup.add(InlineKeyboardButton("⬅️ Cambiar hotel", callback_data="ruta_" + str(cfg.get("ruta", "Oriente")).lower()))
    return markup

def _manual_summary_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("💾 Guardar", callback_data="ml_save"), InlineKeyboardButton("✏️ Volver", callback_data="ml_backcat"))
    markup.add(InlineKeyboardButton("❌ Cancelar", callback_data="ml_cancel"))
    return markup

def _guardar_operacion_manual(chat_id):
    ses = sesiones.get(chat_id, {})
    cantidades = ses.get("manual_cantidades", {})
    filas = []
    fecha = fecha_operacion_sesion(ses)
    for prenda, cantidad in cantidades.items():
        cantidad = int(cantidad)
        if cantidad <= 0:
            continue
        filas.append({
            "fecha": fecha,
            "prenda": prenda,
            "cantidad": cantidad,
            "tipo_operacion_detectada": "LENCERIA_MATRIZ",
            "extra": "No",
            "habitacion": "",
            "remision": ""
        })
    if not filas:
        bot.send_message(chat_id, "⚠️ Selecciona al menos un artículo antes de guardar.")
        return

    cfg = ses
    hora = obtener_ahora_bogota().strftime("%I:%M %p")
    if cfg.get("movimiento") == "ENTREGA" and cfg.get("dia_despacho_corrido"):
        dia = cfg.get("dia_despacho_corrido")
    else:
        try:
            dia = int(fecha.split('/')[0])
        except Exception:
            dia = obtener_ahora_bogota().day
    token = f"{cfg.get('hotel','HOTEL')}_{dia}_MANUAL_{str(uuid.uuid4())[:10]}"
    payload = {
        "accion": "GUARDAR",
        "ruta": cfg.get("ruta", "Oriente"),
        "hotel": cfg.get("hotel", "Hotel"),
        "destino": cfg.get("hoja", ""),
        "tipo_operacion": "LENCERIA_MATRIZ",
        "movimiento": "RECEPCIÓN" if cfg.get("movimiento") == "RECEPCIÓN" else "ENTREGA",
        "responsable_lavaarte": cfg.get("resp_lavaarte", "Conductor Lavaarte"),
        "responsable_hotel": cfg.get("resp_hotel", "Recepción / Ama de llaves"),
        "hora_sellada": hora,
        "dia": dia,
        "filas": filas,
        "id_transaccion": token
    }
    bot.send_message(chat_id, "⏳ Guardando operación en Google Sheets...")
    try:
        resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=90)
        if resp.get("status") == "SUCCESS":
            hoja = resp.get("hoja_guardada", cfg.get("hoja", "Google Sheets"))
            total = sum(x["cantidad"] for x in filas)
            sesiones[chat_id]["manual_cantidades"] = {}
            sesiones[chat_id]["filas"] = []
            bot.send_message(chat_id, f"✅ *OPERACIÓN GUARDADA*\n\n🏨 {cfg.get('hotel')} — {cfg.get('servicio')}\n📦 Movimiento: *{payload['movimiento']}*\n📊 Total: *{total}*\n📅 Día: *{dia}*\n📋 Hoja: `{hoja}`", parse_mode='Markdown', reply_markup=menu_post_guardado())
        else:
            bot.send_message(chat_id, "⚠️ Google Sheets no confirmó el guardado: " + str(resp.get("mensaje", "respuesta desconocida")))
    except Exception as e:
        bot.send_message(chat_id, "❌ Error guardando operación: " + str(e))

def menu_principal():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧭 Ruta Oriente", callback_data="ruta_oriente"),
        InlineKeyboardButton("🧭 Ruta Norte", callback_data="ruta_norte"),
        InlineKeyboardButton("🔍 Auditoría / Consultas IA", callback_data="modo_consulta"),
        InlineKeyboardButton("✏️ Corregir Registro", callback_data="modo_corregir")
    )
    markup.add(
        InlineKeyboardButton("💸 Control Financiero (Gastos / Ingresos)", callback_data="menu_financiero")
    )
    return markup

def menu_post_consulta():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✏️ Corregir / Modificar Este Registro", callback_data="corregir_desde_consulta"),
        InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_inicio")
    )
    return markup

def menu_confirmacion_despacho_en_sitio():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✅ Todo Conforme (Proceder a Entrega)", callback_data="despacho_ok_proceder"),
        InlineKeyboardButton("✏️ Modificar Entrega (Falta / Quedó Paquete)", callback_data="despacho_modificar_en_sitio"),
        InlineKeyboardButton("🏠 Cancelar y Menú", callback_data="menu_inicio")
    )
    return markup

def menu_firma_pantalla(hotel_nom, ses=None):
    ses = ses or {}
    params = {
        "hotel": str(hotel_nom),
        "ruta": str(ses.get("ruta", "Oriente")),
        "fila_despacho": str(ses.get("despacho_pendiente", {}).get("fila", "")),
        "total_prendas": str(ses.get("despacho_pendiente", {}).get("total_prendas", 0)),
        "responsable_lavaarte": str(ses.get("resp_lavaarte", ses.get("despacho_pendiente", {}).get("despachado_por", "Conductor Lavaarte"))),
        "recibido_por": str(ses.get("recibido_por_hotel", "Personal Hotel"))
    }
    query = "&".join(f"{requests.utils.quote(str(k))}={requests.utils.quote(str(v))}" for k, v in params.items())
    url_pantalla = f"{URL_APPS_SCRIPT}?{query}"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("✍️ Abrir Pantalla para Firmar Aquí", web_app=WebAppInfo(url=url_pantalla)),
        InlineKeyboardButton("📸 O Adjuntar Foto de la Firma", callback_data="adjuntar_foto_firma"),
        InlineKeyboardButton("⏩ Omitir Firma y Finalizar", callback_data="omitir_firma")
    )
    return markup

def menu_financiero():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔴 Registrar Gasto / Egreso", callback_data="fin_egreso"),
        InlineKeyboardButton("🟢 Registrar Ingreso", callback_data="fin_ingreso")
    )
    markup.add(InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="menu_inicio"))
    return markup

def menu_destino_cuenta(tipo_mov):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👔 Lavaarte SAS", callback_data=f"cta_lavaarte_{tipo_mov}"),
        InlineKeyboardButton("👤 Personal Carlos", callback_data=f"cta_carlos_{tipo_mov}")
    )
    markup.add(InlineKeyboardButton("⬅️ Cancelar", callback_data="menu_financiero"))
    return markup

def menu_hoteles_oriente():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👔 Wyndham Huéspedes", callback_data="sel_wyndham_huespedes"),
        InlineKeyboardButton("🛏️ Wyndham Lencería", callback_data="sel_wyndham_lenceria"),
        InlineKeyboardButton("🍽️ Wyndham Mantelería", callback_data="sel_wyndham_manteleria"),
        InlineKeyboardButton("🏨 Hotel Hilton", callback_data="sel_hilton"),
        InlineKeyboardButton("👤 Hilton Empleados", callback_data="sel_hilton_empleados"),
        InlineKeyboardButton("🏨 Hotel Hampton", callback_data="sel_hampton"),
        InlineKeyboardButton("👤 Hampton Empleados", callback_data="sel_hampton_empleados"),
        InlineKeyboardButton("🏨 Hotel Oceania", callback_data="sel_oceania"),
        InlineKeyboardButton("🏨 Hotel Fontana", callback_data="sel_fontana"),
        InlineKeyboardButton("📦 Almacén Central", callback_data="sel_almacen"),
        InlineKeyboardButton("⬅️ Volver al Menú", callback_data="menu_inicio")
    )
    return markup

def menu_hoteles_norte():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("👔 Dann Huéspedes", callback_data="sel_dann_huespedes"),
        InlineKeyboardButton("👤 Dann Empleados / Códigos", callback_data="sel_dann_empleados"),
        InlineKeyboardButton("🛏️ Dann Lencería", callback_data="sel_dann_lenceria"),
        InlineKeyboardButton("🏨 Hotel Suite", callback_data="sel_suite"),
        InlineKeyboardButton("🍽️ Suite Mantelería", callback_data="sel_suite_manteleria"),
        InlineKeyboardButton("🏨 Hotel Virrey", callback_data="sel_virrey"),
        InlineKeyboardButton("🏨 Hotel Andes Plaza", callback_data="sel_andes_plaza"),
        InlineKeyboardButton("👔 Bogotá Plaza Huéspedes", callback_data="sel_bogotap_huespedes"),
        InlineKeyboardButton("👔 Bogotá Plaza Uniformes", callback_data="sel_bogotap_datos"),
        InlineKeyboardButton("🏭 Eficacia Dotaciones", callback_data="sel_eficacia"),
        InlineKeyboardButton("⬅️ Volver al Menú", callback_data="menu_inicio")
    )
    return markup

def menu_recibir_entregar(hotel_key):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📥 Recibir Ropa", callback_data="mov_recibir_" + str(hotel_key)),
        InlineKeyboardButton("📤 Entregar Ropa", callback_data="mov_entregar_" + str(hotel_key))
    )
    markup.add(InlineKeyboardButton("⬅️ Cambiar Hotel", callback_data="menu_inicio"))
    return markup

def menu_sub_entrega(hotel_key):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📦 1. Cargar Despacho (En Planta)", callback_data="despacho_planta_" + str(hotel_key)),
        InlineKeyboardButton("🤝 2. Confirmar Entrega en Hotel (Conductor)", callback_data="confirmar_hotel_" + str(hotel_key)),
        InlineKeyboardButton("⬅️ Volver", callback_data="sel_" + str(hotel_key))
    )
    return markup

def menu_post_guardado():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📸 Enviar más datos a este hotel", callback_data="accion_seguir"),
        InlineKeyboardButton("🏠 Terminar y volver al Menú", callback_data="menu_inicio")
    )
    return markup

def generar_resumen(filas, config_sesion, total_fotos=1):
    if not filas:
        return "⚠️ No se detectaron prendas válidas para procesar."
    
    hotel_txt = str(config_sesion.get('hotel', '')) + " - " + str(config_sesion.get('servicio', ''))
    fecha_reg = filas[0].get('fecha', obtener_ahora_bogota().strftime("%d/%m/%Y"))
    mov = config_sesion.get('movimiento', '')
    es_limpio = es_servicio_lista_limpia(config_sesion)
    es_eficacia = (config_sesion.get('key') == "eficacia")
    
    r_lavaarte = config_sesion.get('resp_lavaarte', 'Conductor Lavaarte')
    r_hotel = config_sesion.get('resp_hotel', 'Recepción / Ama de llaves')
    
    resumen = "🏨 *HOTEL / SERVICIO:* " + hotel_txt
    if mov:
        resumen += " (*" + str(mov) + "*)"
    resumen += "\n📅 *FECHA:* " + str(fecha_reg) + "\n"
    resumen += "👤 *Responsable Lavaarte:* `" + str(r_lavaarte) + "`\n"
    resumen += "🏨 *Responsable Hotel:* `" + str(r_hotel) + "`\n"
    
    if es_eficacia:
        total_p = sum(item.get('cantidad', 0) for item in filas)
        resumen += "📊 *Total Dotaciones:* " + str(total_p) + " prendas\n"
        resumen += "📋 *DESGLOSE CONSOLIDADO POR EMPRESA:*\n"
        
        filas_por_empresa = {}
        for it in filas:
            cta = str(it.get('habitacion', it.get('empresa', 'GENERAL'))).strip().title()
            if cta not in filas_por_empresa:
                filas_por_empresa[cta] = []
            filas_por_empresa[cta].append(it)
            
        for cta, items_cta in sorted(filas_por_empresa.items()):
            resumen += f"\n🏢 *Empresa:* `{cta}`\n"
            for it in items_cta:
                resumen += f"• {it.get('prenda', '')} - Cant: *{it.get('cantidad', 0)}*\n"
            
    elif es_limpio:
        total_p = sum(item.get('cantidad', 0) for item in filas)
        resumen += "📊 *Total Prendas:* " + str(total_p) + "\n"
        resumen += "📋 *LISTA DE CONTEO:*\n"
        filas_ord = sorted(filas, key=lambda x: str(x.get('prenda', '')).lower())
        for it in filas_ord:
            resumen += f"• {it.get('prenda', '')} - Cant: *{it.get('cantidad', 0)}*\n"
            
    else:
        total_factura = sum(item.get('valorTotal', 0) for item in filas)
        resumen += "💰 *Total Liquidado:* $" + f"{total_factura:,.2f}" + "\n"
        resumen += "📋 *DETALLE AUDITADO:*\n"
        hab_actual = ""
        for it in filas:
            ident = str(it.get('habitacion', it.get('habitacion_o_persona', 'General')))
            if ident != hab_actual:
                hab_actual = ident
                es_ex = it.get('extra', 'No')
                tag_ex = " ⚡ EXTRA (+50%)" if str(es_ex).upper() in ['SI', 'SÍ'] else " (Estándar)"
                rem_txt = f" [Rem: {it.get('remision')}]" if it.get('remision') and it.get('remision') != ident else ""
                resumen += "\n🚪 *Habitación / Registro:* `" + hab_actual + "`" + rem_txt + tag_ex + "\n"
            p_cod = str(it.get('codigo', '-'))
            p_nom = str(it.get('prenda', ''))
            p_srv = str(it.get('servicio', 'Lavado'))
            p_cant = str(it.get('cantidad', 0))
            p_unit = f"{it.get('valorUnitario', 0):,.2f}"
            p_tot = f"{it.get('valorTotal', 0):,.2f}"
            p_extra = str(it.get('extra', 'No'))
            resumen += f"• [Cód {p_cod}] {p_nom} ({p_srv}) - Cant: {p_cant} - Unit: ${p_unit} - Total: ${p_tot} [Extra: {p_extra}]\n"
            
    resumen += "\n💬 *¿Qué deseas hacer?*\n"
    resumen += "• Escribe *SI* para guardar en Google Sheets.\n"
    resumen += "• Escribe *NO* para cancelar.\n"
    resumen += "• O escribe cualquier corrección directa."
    return resumen

def armar_texto_despacho(desp, hotel_nom, servicio_nom="Lencería", resp_conductor="Conductor Lavaarte"):
    items_detalle = desp.get("items_detalle", [])
    txt_info = f"🏨 *HOTEL / SERVICIO:* {hotel_nom} - {servicio_nom} (*ENTREGA*)\n"
    txt_info += f"📅 *FECHA:* {desp.get('fecha')} ({desp.get('hora')})\n"
    txt_info += f"👤 *Responsable Lavaarte:* `{resp_conductor}`\n"
    txt_info += f"🏨 *Responsable Hotel:* `Recepción / Ama de llaves`\n"
    txt_info += f"📊 *Total Prendas:* {desp.get('total_prendas', 0)}\n"
    txt_info += "📋 *LISTA DE CONTEO:*\n"
    
    if items_detalle:
        items_ord = sorted(items_detalle, key=lambda x: str(x.get('prenda', '')).lower())
        for it in items_ord:
            txt_info += f"• {it['prenda']} - Cant: *{it['cantidad']}*\n"
    else:
        txt_info += f"• {desp.get('notas', 'Despacho registrado en planta')}\n"
        
    txt_info += "\n💬 *¿Qué deseas hacer?*\n"
    txt_info += "• Selecciona *✅ Todo Conforme* para proceder a la entrega.\n"
    txt_info += "• O selecciona *✏️ Modificar Entrega* si falta o quedó algún paquete."
    return txt_info

@bot.message_handler(commands=['start', 'menu'])
def cmd_start(m):
    sesiones[m.chat.id] = {}
    bot.send_message(m.chat.id, "👋 ¡Hola! Bienvenido al sistema central de *Lavaarte Lavanderia SAS*.\n\nSelecciona una opción de trabajo:", reply_markup=menu_principal(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() in ['hola', 'menu', 'inicio', 'cambiar hotel', 'rutas'])
def saludo_texto(m):
    cmd_start(m)

@bot.callback_query_handler(func=lambda call: call.data in ['menu_inicio', 'ruta_oriente', 'ruta_norte', 'modo_consulta', 'modo_corregir', 'menu_financiero', 'corregir_desde_consulta'])
def manejar_menu_principal(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    if call.data == 'menu_inicio':
        sesiones[chat_id] = {}
        bot.edit_message_text("Selecciona una opción de trabajo:", chat_id, call.message.message_id, reply_markup=menu_principal())
    elif call.data == 'ruta_oriente':
        bot.edit_message_text("🧭 *RUTA ORIENTE* - Selecciona el hotel:", chat_id, call.message.message_id, reply_markup=menu_hoteles_oriente(), parse_mode='Markdown')
    elif call.data == 'ruta_norte':
        bot.edit_message_text("🧭 *RUTA NORTE* - Selecciona el hotel:", chat_id, call.message.message_id, reply_markup=menu_hoteles_norte(), parse_mode='Markdown')
    elif call.data == 'modo_consulta':
        sesiones[chat_id] = {"modo": "CONSULTA"}
        bot.edit_message_text("🔍 *AUDITORÍA Y CONSULTAS CON IA EN TIEMPO REAL*\n\nPuedes preguntarme cualquier detalle contable u operativo.\n\nEjemplos:\n- _'¿Quién entregó lencería en Oceanía el 10 de septiembre?'_\n- _'¿Cuántas prendas se despacharon a Wyndham hoy?'_\n- _'Revisar las habitaciones del reporte de Hilton'_", chat_id, call.message.message_id, parse_mode='Markdown')
    elif call.data in ['modo_corregir', 'corregir_desde_consulta']:
        sesiones[chat_id]["modo"] = "CORREGIR_REGISTRO_BD"
        bot.edit_message_text("✏️ *MODO CORRECCIÓN UNIVERSAL EN TIEMPO REAL*\n\nIndícame qué dato deseas cambiar de cualquier hotel o fecha.\n\nEjemplos:\n- _'En Oceanía día 10 cambiar toalla cuerpo de 15 a 18'_\n- _'En Wyndham habitación 304 cambiar cantidad de 2 a 1 pantalón'_\n- _'Corregir habitación 501 por 502 en Hilton hoy'_", chat_id, call.message.message_id, parse_mode='Markdown')
    elif call.data == 'menu_financiero':
        sesiones[chat_id] = {"modulo": "FINANCIERO"}
        bot.edit_message_text("💸 *MÓDULO DE CONTROL FINANCIERO*\n\n¿Qué tipo de movimiento deseas registrar?", chat_id, call.message.message_id, reply_markup=menu_financiero(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in ['fin_egreso', 'fin_ingreso'])
def seleccionar_tipo_financiero(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    tipo_str = "EGRESO" if call.data == 'fin_egreso' else "INGRESO"
    emoji = "🔴" if tipo_str == "EGRESO" else "🟢"
    bot.edit_message_text(
        f"{emoji} *REGISTRAR {tipo_str}*\n\n¿A qué cuenta corresponde este movimiento?",
        chat_id, call.message.message_id,
        reply_markup=menu_destino_cuenta(tipo_str),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('cta_'))
def seleccionar_cuenta_destino(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    partes = call.data.split('_')
    cuenta = "LAVAARTE" if partes[1] == "lavaarte" else "CARLOS"
    tipo_str = partes[2]
    emoji = "🔴" if tipo_str == "EGRESO" else "🟢"
    nombre_cuenta = "👔 Lavaarte SAS" if cuenta == "LAVAARTE" else "👤 Personal Carlos"

    sesiones[chat_id] = {
        "modulo": "FINANCIERO",
        "tipo_fin": tipo_str,
        "cuenta_destino": cuenta
    }

    txt = f"{emoji} *{tipo_str} → {nombre_cuenta}*\n\n"
    txt += "📸 *Puedes enviar:* Foto del recibo o factura.\n"
    txt += "🎙️ *O enviar:* Nota de voz.\n"
    txt += "✍️ *O escribirlo:* Directamente en un mensaje de texto."
    bot.edit_message_text(txt, chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def seleccionar_hotel(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    key = call.data.replace('sel_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    if not cfg:
        bot.send_message(chat_id, "Hotel no encontrado.")
        return
        
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]["key"] = key
    sesiones[chat_id]["filas"] = []
    
    if key in MANUAL_CATALOGO_KEYS:
        sesiones[chat_id]["catalogo_items"] = obtener_catalogo_manual(chat_id, key)
        sesiones[chat_id]["manual_cantidades"] = {}
        bot.edit_message_text(
            "🧺 *" + str(cfg['hotel']) + " — " + str(cfg['servicio']) + "*\n\nSelecciona una operación:",
            chat_id, call.message.message_id,
            reply_markup=menu_manual_operacion(key),
            parse_mode='Markdown'
        )
        return

    bot.edit_message_text(
        "🏨 Operación: *" + str(cfg['hotel']) + " (" + str(cfg['servicio']) + ")*\n\n¿Qué movimiento deseas registrar?",
        chat_id, call.message.message_id,
        reply_markup=menu_recibir_entregar(key),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('ml_start|'))
def iniciar_operacion_manual(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    ses = sesiones.get(chat_id, {})
    movimiento = call.data.split('|',1)[1]
    ses["movimiento"] = "RECEPCIÓN" if movimiento == "RECIBIR" else "ENTREGA"
    if movimiento == "DESPACHAR":
        ses["dia_despacho_corrido"] = calcular_dia_corrido_logistica()
    else:
        ses.pop("dia_despacho_corrido", None)
    ses["manual_cantidades"] = {}
    ses["paso_custodia"] = "MANUAL_RESP_HOTEL" if movimiento == "RECIBIR" else "MANUAL_RESP_LAVAARTE"
    if movimiento == "RECIBIR":
        texto = f"📥 *RECEPCIÓN — {ses.get('hotel','Hotel')}*\n\n¿Quién entrega la ropa por parte del hotel? (Nombre y cargo):"
    else:
        texto = f"📤 *DESPACHO EN PLANTA — {ses.get('hotel','Hotel')}*\n\n¿Quién despacha la ropa por parte de Lavaarte? (Nombre del conductor/responsable):"
    bot.edit_message_text(texto, chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_viewcat')
def ver_catalogo_manual(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    ses = sesiones.get(chat_id, {})
    if ses.get('key') not in MANUAL_CATALOGO_KEYS:
        return
    ses['catalogo_items'] = obtener_catalogo_manual(chat_id, ses['key'])
    texto, markup = _manual_menu_catalogo(chat_id, 0)
    bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_new')
def nuevo_item_manual(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    ses = sesiones.get(chat_id, {})
    if ses.get('key') not in MANUAL_CATALOGO_KEYS:
        return
    ses['manual_return_to'] = 'MENU' if not ses.get('movimiento') else 'CATALOGO'
    ses['paso_custodia'] = 'MANUAL_NUEVO_ITEM'
    bot.send_message(chat_id, "➕ *NUEVO ARTÍCULO*\n\nEscribe el nombre exacto del nuevo artículo. No necesitas tocar el código ni Google Sheets.", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_entrega_hotel')
def manual_entrega_hotel(call):
    # Reutiliza el flujo de custodia y firma existente; el despacho manual
    # ya quedó guardado con el mismo formato que los despachos anteriores.
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    ses = sesiones.get(chat_id, {})
    key = ses.get('key')
    cfg = ARBOL_SERVICIOS.get(key, ses)
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]['key'] = key
    sesiones[chat_id]['movimiento'] = 'ENTREGA'
    sesiones[chat_id]['paso_custodia'] = 'ENT_QUIEN_ENTREGA_LAVAARTE'
    bot.edit_message_text(f"🤝 *ENTREGA EN HOTEL — {cfg.get('hotel','Hotel')}*\n\n¿Quién entrega la ropa por parte de Lavaarte? (Nombre del conductor):", chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ml_page|'))
def manual_pagina(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    page = int(call.data.split('|',1)[1])
    texto, markup = _manual_menu_catalogo(chat_id, page)
    bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ml_item|'))
def manual_seleccionar_item(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    idx = int(call.data.split('|',1)[1])
    texto, markup = _manual_editor(chat_id, idx)
    bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('ml_inc|') or call.data.startswith('ml_dec|'))
def manual_incrementar_cantidad(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    ses = sesiones.get(chat_id, {})
    idx = int(ses.get('manual_item_index', -1))
    items = ses.get('catalogo_items', [])
    if idx < 0 or idx >= len(items): return
    nombre = items[idx]
    delta = int(call.data.split('|',1)[1])
    if call.data.startswith('ml_dec|'): delta = -delta
    cantidades = ses.setdefault('manual_cantidades', {})
    cantidades[nombre] = max(0, int(cantidades.get(nombre, 0)) + delta)
    texto, markup = _manual_editor(chat_id, idx)
    bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_custom')
def manual_cantidad_personalizada(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    sesiones[chat_id]['paso_custodia'] = 'MANUAL_CANTIDAD'
    bot.send_message(chat_id, "✏️ Escribe la cantidad total para este artículo. Ejemplo: `100`", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_backcat')
def manual_volver_catalogo(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    sesiones[chat_id]['paso_custodia'] = None
    texto, markup = _manual_menu_catalogo(chat_id, sesiones[chat_id].get('manual_page',0))
    bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_summary')
def manual_resumen_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    bot.edit_message_text(_manual_resumen(chat_id), chat_id, call.message.message_id, reply_markup=_manual_summary_markup(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'ml_save')
def manual_guardar_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    _guardar_operacion_manual(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == 'ml_cancel')
def manual_cancelar_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    key = sesiones.get(chat_id, {}).get('key')
    if key in ARBOL_SERVICIOS:
        sesiones[chat_id]['manual_cantidades'] = {}
        sesiones[chat_id]['paso_custodia'] = None
        bot.edit_message_text(f"🧺 *{sesiones[chat_id].get('hotel','Hotel')}*\n\nOperación cancelada. Selecciona otra opción:", chat_id, call.message.message_id, reply_markup=menu_manual_operacion(key), parse_mode='Markdown')
    else:
        cmd_start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'ml_noop')
def manual_noop(call):
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('mov_entregar_'))
def manejar_opciones_entrega(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    key = call.data.replace('mov_entregar_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]["key"] = key
    sesiones[chat_id]["movimiento"] = "ENTREGA"
    
    bot.edit_message_text(
        "📤 *ENTREGA DE ROPA - " + str(cfg['hotel']) + "*\n\nSelecciona el momento de la entrega:",
        chat_id, call.message.message_id,
        reply_markup=menu_sub_entrega(key),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('despacho_planta_'))
def iniciar_despacho_planta(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    sesiones[chat_id]["sub_op"] = "DESPACHO_PLANTA"
    sesiones[chat_id]["paso_custodia"] = "RESP_LAVAARTE_DESPACHO"
    
    dia_corrido = calcular_dia_corrido_logistica()
    sesiones[chat_id]["dia_despacho_corrido"] = dia_corrido
    
    txt = f"📦 *DESPACHO EN PLANTA*\n\n"
    txt += f"📅 Se asignará por defecto a la lencería recibida el día *{dia_corrido}* (día hábil anterior).\n"
    txt += "Escribe el nombre de quién despacha la ropa en planta:"
    bot.edit_message_text(txt, chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmar_hotel_'))
def iniciar_confirmacion_hotel(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    key = call.data.replace('confirmar_hotel_', '')
    cfg = ARBOL_SERVICIOS.get(key, sesiones.get(chat_id, {}))
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]["key"] = key
    sesiones[chat_id]["movimiento"] = "ENTREGA"
    sesiones[chat_id]["paso_custodia"] = "ENT_QUIEN_ENTREGA_LAVAARTE"
    
    bot.edit_message_text(
        f"🤝 *ENTREGA EN HOTEL - {cfg.get('hotel', 'Hotel')}*\n\n1️⃣ ¿Quién entrega la ropa por parte de Lavaarte? (Escribe el nombre del conductor):",
        chat_id, call.message.message_id,
        parse_mode='Markdown'
    )

def _consultar_despacho_async(chat_id, cfg, hotel_nom, dia_logistico, resp_conductor):
    """Busca el último despacho activo real, no solamente el día hábil anterior.
    Reintenta automáticamente ante una respuesta temporalmente inválida.
    """
    ultimo_error = None

    for intento in range(3):
        try:
            payload = {
                "accion": "CONSULTAR_DESPACHO",
                "ruta": cfg.get("ruta", "Oriente"),
                "hotel": hotel_nom,
                "destino": cfg.get("hoja", ""),
                "dia": dia_logistico,
                "usar_ultimo_despacho": True
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=35)

            if resp.get("status") == "SUCCESS" and isinstance(resp.get("despacho"), dict):
                desp = resp.get("despacho", {})
                if not desp.get("fecha") or desp.get("total_prendas") is None:
                    raise ValueError("El despacho devuelto no contiene datos completos.")

                desp["despachado_por"] = resp_conductor
                sesiones[chat_id]["despacho_pendiente"] = desp
                sesiones[chat_id]["dia_despacho_corrido"] = dia_logistico

                txt_info = armar_texto_despacho(
                    desp,
                    hotel_nom,
                    cfg.get("servicio", "Lencería"),
                    resp_conductor
                )
                bot.send_message(
                    chat_id,
                    txt_info,
                    reply_markup=menu_confirmacion_despacho_en_sitio(),
                    parse_mode='Markdown'
                )
                return

            if resp.get("status") == "EMPTY":
                bot.send_message(
                    chat_id,
                    f"⚠️ No se encontró un despacho activo registrado de planta para *{hotel_nom}*.\n"
                    "El sistema revisó el último despacho pendiente, sin limitarse al día hábil anterior.",
                    parse_mode='Markdown'
                )
                return

            ultimo_error = ValueError(resp.get("mensaje", "Respuesta incompleta de Google Sheets."))

        except Exception as e:
            ultimo_error = e
            if intento < 2:
                time.sleep(1.2)

    sesiones[chat_id]["paso_custodia"] = "REINTENTAR_CONSULTA_DESPACHO"
    sesiones[chat_id]["despacho_pendiente"] = None
    bot.send_message(
        chat_id,
        "🔄 No pude leer temporalmente el despacho. La información de planta no se ha modificado.\n"
        "Escribe *REINTENTAR* para volver a consultarlo.",
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data in ['despacho_ok_proceder', 'despacho_modificar_en_sitio'])
def manejar_decision_entrega_sitio(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    cfg = sesiones.get(chat_id, {})
    hotel_nom = cfg.get("hotel", "Hotel")
    
    if call.data == 'despacho_ok_proceder':
        sesiones[chat_id]["paso_custodia"] = "CONFIRMAR_QUIEN_RECIBE_HOTEL"
        bot.edit_message_text(
            f"✅ *Cantidades verificadas para {hotel_nom}*.\n\n✍️ *Por favor escribe el nombre y cargo de la persona que recibe en el hotel:*",
            chat_id,
            call.message.message_id,
            parse_mode='Markdown'
        )
    elif call.data == 'despacho_modificar_en_sitio':
        sesiones[chat_id]["paso_custodia"] = "AJUSTAR_PRENDAS_DESPACHO_SITIO"
        bot.edit_message_text(
            f"✏️ *Ajuste de Entrega en {hotel_nom}*\n\nEscribe qué prendas o cantidades reales estás entregando (por ejemplo: _'Solo entregué 12 toallas cuerpo y 8 manos'_ o _'Se quedaron 2 sábanas'_):",
            chat_id,
            call.message.message_id,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('mov_recibir_'))
def iniciar_recepcion(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    key = call.data.replace('mov_recibir_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]["key"] = key
    sesiones[chat_id]["movimiento"] = "RECEPCIÓN"
    sesiones[chat_id]["paso_custodia"] = "REC_QUIEN_ENTREGA_HOTEL"
    bot.edit_message_text("📥 *RECEPCIÓN EN HOTEL - " + str(cfg['hotel']) + "*\n\n1️⃣ ¿Quién entrega la ropa por parte del hotel? (Escribe nombre y cargo):", chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in ['accion_seguir', 'menu_inicio'])
def manejar_post_guardado(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    if call.data == 'accion_seguir':
        cfg = sesiones.get(chat_id, {})
        bot.send_message(chat_id, "📸 Envíame los siguientes datos para *" + str(cfg.get('hotel', '')) + "*.", parse_mode='Markdown')
    else:
        cmd_start(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ['adjuntar_foto_firma', 'omitir_firma'])
def manejar_opcion_firma_callback(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass

    if call.data == 'adjuntar_foto_firma':
        sesiones[chat_id]["paso_custodia"] = "SUBIR_FOTO_FIRMA"
        sesiones[chat_id]["msg_firma_id"] = call.message.message_id
        bot.send_message(chat_id, "📸 *Toma una foto clara de la firma manuscrita y envíala:*", parse_mode='Markdown')
    else:
        sesiones[chat_id] = {}
        bot.send_message(chat_id, "✅ *Entrega finalizada con éxito sin firma.*", parse_mode='Markdown')
        bot.send_message(chat_id, "Selecciona una nueva opción:", reply_markup=menu_principal())

@bot.message_handler(content_types=['web_app_data'])
def recibir_firma_web_app(message):
    chat_id = message.chat.id
    ses = sesiones.get(chat_id, {})
    ahora_bog = obtener_ahora_bogota()
    hotel_activo = ses.get("hotel", "Hotel")
    
    # Cierre y desactivación de botones anti-doble firma
    msg_f_id = ses.get("msg_firma_id")
    if msg_f_id:
        try:
            bot.edit_message_reply_markup(chat_id, msg_f_id, reply_markup=None)
        except Exception:
            pass

    try:
        data_web = json.loads(message.web_app_data.data)
        if data_web.get("tipo") == "FIRMA_DIGITAL":
            bot.send_message(chat_id, "✍️ Guardando firma digital en Google Drive (Carpeta FIRMAS)...", parse_mode='Markdown')
            
            payload = {
                "accion": "GUARDAR_FIRMA_ENTREGA",
                "hotel": hotel_activo,
                "ruta": ses.get("ruta", "Oriente"),
                "fecha": ahora_bog.strftime("%Y-%m-%d"),
                "hora": ahora_bog.strftime("%I-%M-%p"),
                "firma_base64": data_web.get("firma_b64"),
                "recibido_por": ses.get("recibido_por_hotel", "Personal Hotel"),
                "responsable_lavaarte": ses.get("resp_lavaarte", "Conductor Lavaarte"),
                "fila_despacho": ses.get("despacho_pendiente", {}).get("fila", ""),
                "total_prendas": ses.get("despacho_pendiente", {}).get("total_prendas", 0)
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=45)
            
            if resp.get("status") == "SUCCESS":
                txt_f = f"✅ *¡ENTREGA FINALIZADA Y FIRMA ARCHIVADA!*\n\n"
                txt_f += f"🏨 *Hotel:* {hotel_activo}\n"
                txt_f += f"📁 *Carpeta Drive:* `FIRMAS`\n"
                txt_f += f"📄 *Archivo:* `{resp.get('nombre_archivo')}`\n"
                if resp.get('url_firma'):
                    txt_f += f"🔗 [Ver Firma en Google Drive]({resp.get('url_firma')})\n\n"
                txt_f += "🔒 *Proceso cerrado definitivamente.*"
                bot.send_message(chat_id, txt_f, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, "⚠️ No se pudo archivar la firma: " + str(resp.get("mensaje")))
                
            sesiones[chat_id] = {}
            bot.send_message(chat_id, "¿Qué deseas hacer ahora?", reply_markup=menu_principal())
    except Exception as e:
        bot.send_message(chat_id, "❌ Error procesando firma en pantalla: " + str(e))

def _ejecutar_procesamiento_fotos_hilo(chat_id, imgs, cfg):
    ahora_bog = obtener_ahora_bogota()
    hotel_activo = cfg.get("hotel", "Hotel")
    ruta_activa = cfg.get("ruta", "Oriente")
    
    # 1. SUBIR FOTO DE FIRMA DIGITAL
    if cfg.get("paso_custodia") == "SUBIR_FOTO_FIRMA":
        bot.send_message(chat_id, "✍️ Guardando firma digital en Google Drive (Carpeta FIRMAS)...", parse_mode='Markdown')
        try:
            img_firma = imgs[0]
            buf = io.BytesIO()
            img_firma.save(buf, format="JPEG", quality=90)
            b64_firma = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            payload = {
                "accion": "GUARDAR_FIRMA_ENTREGA",
                "hotel": hotel_activo,
                "ruta": ruta_activa,
                "fecha": ahora_bog.strftime("%Y-%m-%d"),
                "hora": ahora_bog.strftime("%I-%M-%p"),
                "firma_base64": b64_firma,
                "recibido_por": cfg.get("recibido_por_hotel", "Personal Hotel"),
                "responsable_lavaarte": cfg.get("resp_lavaarte", "Conductor Lavaarte"),
                "fila_despacho": cfg.get("despacho_pendiente", {}).get("fila", ""),
                "total_prendas": cfg.get("despacho_pendiente", {}).get("total_prendas", 0)
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=45)
            
            if resp.get("status") == "SUCCESS":
                txt_f = f"✅ *¡ENTREGA FINALIZADA Y FIRMA ARCHIVADA!*\n\n"
                txt_f += f"🏨 *Hotel:* {hotel_activo}\n"
                txt_f += f"📁 *Carpeta:* `FIRMAS`\n"
                txt_f += f"📄 *Archivo:* `{resp.get('nombre_archivo')}`\n"
                if resp.get('url_firma'):
                    txt_f += f"🔗 [Ver Firma en Drive]({resp.get('url_firma')})\n\n"
                txt_f += "🔒 *Proceso cerrado definitivamente.*"
                bot.send_message(chat_id, txt_f, parse_mode='Markdown')
            else:
                bot.send_message(chat_id, "⚠️ Error guardando firma: " + str(resp.get("mensaje")))
                
            sesiones[chat_id] = {}
            bot.send_message(chat_id, "¿Qué deseas hacer ahora?", reply_markup=menu_principal())
        except Exception as e:
            bot.send_message(chat_id, "❌ Error guardando firma: " + str(e))
        return

    # 2. PROCESAMIENTO FINANCIERO
    if cfg.get("modulo") == "FINANCIERO":
        bot.send_message(chat_id, "🧾 Analizando comprobante financiero con IA...", parse_mode='Markdown')
        try:
            img_obj = imgs[0]
            buffer_io = io.BytesIO()
            img_obj.save(buffer_io, format="JPEG", quality=85)
            b64_str = base64.b64encode(buffer_io.getvalue()).decode('utf-8')
            
            tipo_mov = cfg.get("tipo_fin", "EGRESO")
            cuenta = cfg.get("cuenta_destino", "LAVAARTE")
            datos_fin = analizar_financiero_ia(img_obj, tipo_mov, cuenta)
            datos_fin["foto_base64"] = b64_str
            sesiones[chat_id]["movimiento_fin_pendiente"] = datos_fin
            
            val_fmt = f"{datos_fin.get('valor', 0):,.2f}"
            nombre_cuenta = "👔 Lavaarte SAS" if cuenta == "LAVAARTE" else "👤 Personal Carlos"

            resumen_fin = f"📊 *CONFIRMACIÓN ({nombre_cuenta}):*\n\n"
            resumen_fin += f"📌 *Tipo:* `{tipo_mov}`\n"
            resumen_fin += f"📅 *Fecha:* `{datos_fin.get('fecha')}`\n"
            resumen_fin += f"🏷️ *Categoría:* *{datos_fin.get('categoria')}*\n"
            resumen_fin += f"📝 *Concepto:* {datos_fin.get('concepto')}\n"
            if cuenta == "LAVAARTE":
                resumen_fin += f"🏢 *Tercero / Proveedor:* {datos_fin.get('tercero', 'N/A')}\n"
                resumen_fin += f"👤 *Responsable:* {datos_fin.get('responsable', 'N/A')}\n"
            resumen_fin += f"💳 *Método de Pago:* {datos_fin.get('metodo_pago')}\n"
            resumen_fin += f"💰 *Valor:* *${val_fmt}*\n\n"
            resumen_fin += "💬 Escribe *SI* para registrar en Sheets o *NO* para cancelar."
            bot.send_message(chat_id, resumen_fin, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(chat_id, "❌ Error analizando comprobante: " + str(e))
        return

    # 3. RESPALDO AUTOMÁTICO DE SOPORTE EN DRIVE (CARPETA SOPORTE EN RUTA CORRESPONDIENTE)
    threading.Thread(target=respaldar_lote_fotos_en_drive, args=[imgs, hotel_activo, ruta_activa], daemon=True).start()

    # 4. PROCESAMIENTO OPERATIVO GENERAL
    try:
        bot.send_chat_action(chat_id, 'typing')
        filas = analizar_con_ia(imgs, cfg)
        if not filas:
            bot.send_message(chat_id, "⚠️ No se detectaron prendas legibles en la imagen. Intenta con una toma más clara o escribe los datos directamente.")
            return
        sesiones[chat_id]["filas"] = filas
        sesiones[chat_id]["total_fotos"] = len(imgs)
        resumen_txt = generar_resumen(filas, cfg, len(imgs))
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.send_message(chat_id, "❌ Error analizando imágenes: " + str(e))

def procesar_lote_fotos(chat_id):
    with lock:
        if chat_id not in cola_fotos or not cola_fotos[chat_id]:
            return
        imgs = list(cola_fotos[chat_id])
        cola_fotos[chat_id] = []
        if chat_id in timers:
            timers[chat_id].cancel()
            
    cfg = sesiones.get(chat_id, ARBOL_SERVICIOS["wyndham_huespedes"])
    hotel_activo = cfg.get("hotel", "Hotel")
    bot.send_message(chat_id, f"🔍 Analizando {len(imgs)} foto(s) para *{hotel_activo}* (y respaldando soporte en Drive)...", parse_mode='Markdown')
    threading.Thread(target=_ejecutar_procesamiento_fotos_hilo, args=[chat_id, imgs, cfg], daemon=True).start()

@bot.message_handler(content_types=['photo'])
def recibir_fotos(message):
    chat_id = message.chat.id
    if chat_id not in sesiones or (not sesiones[chat_id].get("hotel") and sesiones[chat_id].get("modulo") != "FINANCIERO" and sesiones[chat_id].get("paso_custodia") != "SUBIR_FOTO_FIRMA"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    file_info = bot.get_file(message.photo[-1].file_id)
    file_bytes = bot.download_file(file_info.file_path)
    img = Image.open(io.BytesIO(file_bytes))
    
    with lock:
        if chat_id not in cola_fotos:
            cola_fotos[chat_id] = []
        cola_fotos[chat_id].append(img)
        cant = len(cola_fotos[chat_id])
        if chat_id in timers:
            timers[chat_id].cancel()
        t = threading.Timer(2.0, procesar_lote_fotos, args=[chat_id])
        timers[chat_id] = t
        t.start()
        
    bot.send_chat_action(chat_id, 'typing')
    if cant == 1:
        bot.reply_to(message, "⚡ Foto recibida. Agrupando lote y procesando...")

def _procesar_audio_hilo(chat_id, audio_bytes, cfg):
    try:
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
        if cfg.get("modulo") == "FINANCIERO":
            tipo_mov = cfg.get("tipo_fin", "EGRESO")
            cuenta = cfg.get("cuenta_destino", "LAVAARTE")
            datos_fin = analizar_financiero_ia(audio_part, tipo_mov, cuenta)
            sesiones[chat_id]["movimiento_fin_pendiente"] = datos_fin
            val_fmt = f"{datos_fin.get('valor', 0):,.2f}"
            nombre_cuenta = "👔 Lavaarte SAS" if cuenta == "LAVAARTE" else "👤 Personal Carlos"

            resumen_fin = f"📊 *CONFIRMACIÓN ({nombre_cuenta}):*\n\n"
            resumen_fin += f"📌 *Tipo:* `{tipo_mov}`\n"
            resumen_fin += f"📅 *Fecha:* `{datos_fin.get('fecha')}`\n"
            resumen_fin += f"🏷️ *Categoría:* *{datos_fin.get('categoria')}*\n"
            resumen_fin += f"📝 *Concepto:* {datos_fin.get('concepto')}\n"
            if cuenta == "LAVAARTE":
                resumen_fin += f"🏢 *Tercero / Proveedor:* {datos_fin.get('tercero', 'N/A')}\n"
                resumen_fin += f"👤 *Responsable:* {datos_fin.get('responsable', 'N/A')}\n"
            resumen_fin += f"💳 *Método de Pago:* {datos_fin.get('metodo_pago')}\n"
            resumen_fin += f"💰 *Valor:* *${val_fmt}*\n\n"
            resumen_fin += "💬 Escribe *SI* para registrar en Sheets o *NO* para cancelar."
            bot.send_message(chat_id, resumen_fin, parse_mode='Markdown')
            return

        filas = analizar_con_ia([audio_part], cfg)
        if not filas:
            bot.send_message(chat_id, "⚠️ No se detectaron prendas válidas en el audio.")
            return
        sesiones[chat_id]["filas"] = filas
        resumen_txt = generar_resumen(filas, cfg, 1)
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.send_message(chat_id, "❌ Error procesando audio: " + str(e))

@bot.message_handler(content_types=['voice', 'audio'])
def recibir_audio(message):
    chat_id = message.chat.id
    if chat_id not in sesiones or (not sesiones[chat_id].get("hotel") and sesiones[chat_id].get("modulo") != "FINANCIERO"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    cfg = sesiones[chat_id]
    bot.reply_to(message, "🎙️ Audio recibido, procesando...", parse_mode='Markdown')
    bot.send_chat_action(chat_id, 'typing')
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        audio_bytes = bot.download_file(file_info.file_path)
        threading.Thread(target=_procesar_audio_hilo, args=[chat_id, audio_bytes, cfg], daemon=True).start()
    except Exception as e:
        bot.reply_to(message, "❌ Error descargando audio: " + str(e))

@bot.message_handler(func=lambda m: m.text and m.text.strip().upper() in ['SI', 'SÍ'])
def confirmar_guardado(m):
    chat_id = m.chat.id
    ses = sesiones.get(chat_id, {})
    ahora_bog = obtener_ahora_bogota()
    
    # 1. CONFIRMAR FINANCIERO
    if ses.get("movimiento_fin_pendiente"):
        m_fin = ses["movimiento_fin_pendiente"]
        cuenta = ses.get("cuenta_destino", "LAVAARTE")
        bot.reply_to(m, "⏳ Guardando en el libro contable...", parse_mode='Markdown')
        try:
            val_num = float(m_fin.get("valor", 0))
            if val_num <= 0:
                bot.reply_to(m, "⚠️ El valor detectado es $0. Por favor escribe: 'El valor es 50000' antes de confirmar.")
                return

            if cuenta == "CARLOS":
                payload = {
                    "tipo": m_fin.get("tipo", "GASTO"),
                    "categoria": m_fin.get("categoria", "Varios"),
                    "valor": val_num,
                    "metodo": m_fin.get("metodo_pago", "Transferencia/Nequi"),
                    "descripcion": m_fin.get("concepto", "")
                }
                resp = ejecutar_post_apps_script(URL_APPS_SCRIPT_CARLOS, payload, timeout=40)
                if resp.get("status") == "SUCCESS":
                    val_fmt = f"{val_num:,.2f}"
                    txt_ok = f"✅ *¡Movimiento personal registrado con éxito!*\n\n"
                    txt_ok += f"👤 Cuenta: *Personal Carlos*\n"
                    txt_ok += f"📑 Hoja: *MOVIMIENTOS*\n"
                    txt_ok += f"💰 Valor: *${val_fmt}*\n"
                    bot.send_message(chat_id, txt_ok, parse_mode='Markdown')
                    sesiones[chat_id] = {}
                    bot.send_message(chat_id, "¿Qué deseas hacer ahora?", reply_markup=menu_principal())
                else:
                    bot.reply_to(m, "⚠️ Error Sheets Carlos: " + str(resp.get("mensaje")))
            else:
                m_fin["valor"] = val_num
                payload = {
                    "accion": "REGISTRAR_FINANCIERO",
                    "movimiento_financiero": m_fin,
                    "id_transaccion": str(uuid.uuid4())
                }
                resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=45)
                if resp.get("status") == "SUCCESS":
                    txt_ok = f"✅ *¡Movimiento registrado con éxito!*\n\n📑 Guardado en pestaña: *{resp.get('hoja')}*\n"
                    if resp.get("url_evidencia"):
                        txt_ok += f"📸 Evidencia fotográfica guardada en Google Drive.\n"
                    bot.send_message(chat_id, txt_ok, parse_mode='Markdown')
                    sesiones[chat_id] = {}
                    bot.send_message(chat_id, "¿Qué deseas hacer ahora?", reply_markup=menu_principal())
                else:
                    bot.reply_to(m, "⚠️ Error: " + str(resp.get("mensaje")))
        except Exception as e:
            bot.reply_to(m, "❌ Error registrando financiero: " + str(e))
        return

    # 1B. PROGRAMAR / CAMBIAR FECHA DE OPERACIÓN ANTES DE RECIBIR LAS FOTOS
    # Ejemplo: "fecha 10/10/2026". La fecha queda fijada para toda la sesión
    # hasta que el usuario indique otra fecha o cambie de operación.
    fecha_programada = extraer_fecha_formato(texto_ingresado)
    if fecha_programada and not ses.get("filas"):
        ses["fecha_forzada"] = fecha_programada
        ses["fecha_operacion"] = fecha_programada
        bot.reply_to(
            m,
            f"📅 *Fecha de operación fijada: {fecha_programada}*\n\n"
            "Todo lo que registres a continuación se guardará en ese día, aunque hoy sea otra fecha.\n"
            "Puedes cambiarla escribiendo otra fecha, por ejemplo: *fecha 11/10/2026*.",
            parse_mode='Markdown'
        )
        return

    # 2. CONFIRMAR PRENDAS OPERATIVAS (CON CLAVE DE TRANSACCIÓN ÚNICA)
    if ses.get("filas"):
        cfg = ses
        filas = cfg["filas"]
        tipo_op = filas[0].get("tipo_operacion_detectada", cfg.get("tipo", "HUESPEDES"))
        hora_bogota = ahora_bog.strftime("%I:%M %p")
        
        if cfg.get("movimiento") == "ENTREGA" and cfg.get("dia_despacho_corrido"):
            dia_actual = cfg.get("dia_despacho_corrido")
        else:
            dia_actual = ahora_bog.day
            if filas and filas[0].get('fecha'):
                try:
                    dia_actual = int(filas[0]['fecha'].split('/')[0])
                except Exception:
                    pass
            elif cfg.get("fecha_forzada"):
                try:
                    dia_actual = int(str(cfg["fecha_forzada"]).split('/')[0])
                except Exception:
                    pass

        token_transaccion = f"{cfg.get('hotel')}_{dia_actual}_{len(filas)}_{str(uuid.uuid4())[:8]}"

        bot.reply_to(m, f"⏳ Guardando en día *{dia_actual}* (Hora Bogotá: {hora_bogota})...", parse_mode='Markdown')
        try:
            payload = {
                "accion": "GUARDAR",
                "ruta": cfg.get("ruta", "Oriente"),
                "hotel": cfg.get("hotel", "Hotel"),
                "destino": cfg["hoja"],
                "tipo_operacion": tipo_op,
                "movimiento": cfg.get("movimiento", "RECEPCIÓN"),
                "responsable_lavaarte": cfg.get("resp_lavaarte", "Conductor Lavaarte"),
                "responsable_hotel": cfg.get("resp_hotel", "Recepción / Ama de llaves"),
                "hora_sellada": hora_bogota,
                "dia": dia_actual,
                "filas": filas,
                "id_transaccion": token_transaccion
            }
            
            data_resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=90)
            
            if data_resp.get("status") == "SUCCESS":
                # Solo limpiamos la sesión después de confirmar que la escritura
                # fue aceptada. Así una respuesta ambigua no rompe el ciclo.
                sesiones[chat_id]["filas"] = []
                hoja_dest = data_resp.get("hoja_guardada", cfg['hotel'])
                bot.reply_to(m, f"✅ *¡Datos guardados con éxito!*\n📋 Registrado en: `{hoja_dest}`\n📅 Columna del día: *{dia_actual}*\n⏱️ Hora sellada: *{hora_bogota}*", parse_mode='Markdown')
                bot.send_message(chat_id, "¿Qué deseas hacer a continuación?", reply_markup=menu_post_guardado())
            else:
                bot.reply_to(m, "⚠️ Error del servidor: " + str(data_resp.get("mensaje")))
        except Exception as e:
            bot.reply_to(m, "❌ Error enviando a Google Sheets: " + str(e))
    else:
        bot.reply_to(m, "No hay datos pendientes por confirmar. Escribe *Hola* para abrir el menú.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.strip().upper() == 'NO')
def cancelar_guardado(m):
    chat_id = m.chat.id
    if chat_id in sesiones:
        sesiones[chat_id]["filas"] = []
        sesiones[chat_id]["movimiento_fin_pendiente"] = None
    bot.reply_to(m, "❌ Operación cancelada. Puedes enviar nuevos datos o escribir *Hola*.", parse_mode='Markdown')

def _procesar_texto_ia_hilo(chat_id, texto_ingresado, cfg):
    bot.send_chat_action(chat_id, 'typing')
    try:
        filas = analizar_con_ia([texto_ingresado], cfg)
        if not filas:
            bot.send_message(chat_id, f"⚠️ No se detectaron prendas válidas para *{cfg['hotel']}*. Intenta reenviar el texto.", parse_mode='Markdown')
            return
        sesiones[chat_id]["filas"] = filas
        resumen_txt = generar_resumen(filas, cfg, 1)
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.send_message(chat_id, "❌ Error procesando texto: " + str(e))

def _corregir_filas_ia_hilo(chat_id, texto_ingresado, ses):
    bot.send_chat_action(chat_id, 'typing')
    try:
        datos_previos = json.dumps(ses["filas"], ensure_ascii=False)
        filas_actualizadas = analizar_con_ia(None, ses, correccion_usuario="Lista actual: " + datos_previos + ". Modificación solicitada: " + str(texto_ingresado))
        if not filas_actualizadas:
            bot.send_message(chat_id, "⚠️ No se pudieron aplicar los cambios. Se conservan los datos previos.")
            return
        sesiones[chat_id]["filas"] = filas_actualizadas
        resumen_txt = "✏️ *Lista actualizada:*\n\n" + generar_resumen(filas_actualizadas, ses)
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.send_message(chat_id, "❌ Error aplicando cambio: " + str(e))

@bot.message_handler(func=lambda m: m.content_type == 'text' and m.text not in ['/start', '/menu'])
def procesar_texto_general(m):
    chat_id = m.chat.id
    texto_ingresado = m.text.strip()
    
    # Filtro contra textos residuales de botones/menús
    if any(texto_ingresado.startswith(prefijo) for prefijo in ["📤 ENTREGA DE ROPA", "📥 RECEPCIÓN EN HOTEL", "🏨 Operación:"]):
        return

    ses = sesiones.get(chat_id, {})
    paso = ses.get("paso_custodia")
    modo = ses.get("modo")
    ahora_bog = obtener_ahora_bogota()

    # OPERACIONES MANUALES DE LENCERÍA / MANTELERÍA
    if paso == "MANUAL_RESP_HOTEL":
        ses["resp_hotel"] = texto_ingresado
        ses["paso_custodia"] = "MANUAL_RESP_LAVAARTE"
        bot.reply_to(m, "✅ Responsable del hotel registrado.\n\nAhora escribe el nombre de quien recibe por Lavaarte:", parse_mode='Markdown')
        return

    if paso == "MANUAL_RESP_LAVAARTE":
        ses["resp_lavaarte"] = texto_ingresado
        ses["paso_custodia"] = None
        ses["catalogo_items"] = obtener_catalogo_manual(chat_id, ses.get("key"))
        ses["manual_cantidades"] = {}
        texto_cat, markup_cat = _manual_menu_catalogo(chat_id, 0)
        bot.send_message(chat_id, texto_cat, reply_markup=markup_cat, parse_mode='Markdown')
        return

    if paso == "MANUAL_CANTIDAD":
        try:
            cantidad = int(texto_ingresado.replace('.', '').replace(',', ''))
            if cantidad < 0:
                raise ValueError
        except Exception:
            bot.reply_to(m, "⚠️ Escribe únicamente una cantidad válida, por ejemplo: `100`.", parse_mode='Markdown')
            return
        idx = int(ses.get('manual_item_index', -1))
        items = ses.get('catalogo_items', [])
        if 0 <= idx < len(items):
            ses.setdefault('manual_cantidades', {})[items[idx]] = cantidad
        ses['paso_custodia'] = None
        texto_cat, markup_cat = _manual_menu_catalogo(chat_id, ses.get('manual_page', 0))
        bot.send_message(chat_id, texto_cat, reply_markup=markup_cat, parse_mode='Markdown')
        return

    if paso == "MANUAL_NUEVO_ITEM":
        nombre_nuevo = texto_ingresado.strip()
        if len(nombre_nuevo) < 2:
            bot.reply_to(m, "⚠️ El nombre del artículo es demasiado corto.")
            return
        key = ses.get('key')
        cfg_manual = ARBOL_SERVICIOS.get(key, {})
        try:
            resp_cat = ejecutar_post_apps_script(URL_APPS_SCRIPT, {
                "accion": "AGREGAR_ITEM_CATALOGO",
                "ruta": cfg_manual.get("ruta", "Oriente"),
                "hotel": cfg_manual.get("hotel", ""),
                "servicio": cfg_manual.get("servicio", ""),
                "clave_catalogo": key,
                "item": nombre_nuevo
            }, timeout=30)
            if resp_cat.get("status") != "SUCCESS":
                raise ValueError(resp_cat.get("mensaje", "No fue posible guardar el artículo."))
            bot.reply_to(m, f"✅ Artículo *{nombre_nuevo}* agregado al catálogo de {cfg_manual.get('hotel','Hotel')}.", parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(m, "❌ No pude guardar el nuevo artículo en el catálogo: " + str(e))
            return
        if nombre_nuevo not in ses.setdefault('catalogo_items', []):
            ses['catalogo_items'].append(nombre_nuevo)
        ses['paso_custodia'] = None
        if ses.get('manual_return_to') == 'MENU' and not ses.get('movimiento'):
            bot.send_message(chat_id, f"🧺 *{cfg_manual.get('hotel','Hotel')}*\n\nArtículo agregado. Selecciona una operación:", reply_markup=menu_manual_operacion(key), parse_mode='Markdown')
        else:
            texto_cat, markup_cat = _manual_menu_catalogo(chat_id, len(ses['catalogo_items'])//MANUAL_CATALOGO_PAGE_SIZE)
            bot.send_message(chat_id, texto_cat, reply_markup=markup_cat, parse_mode='Markdown')
        return
    hotel_nom = ses.get("hotel", "Hotel")
    
    # AJUSTE DE PRENDAS DE DESPACHO EN SITIO
    if paso == "AJUSTAR_PRENDAS_DESPACHO_SITIO":
        bot.reply_to(m, "⚙️ Ajustando prendas para la entrega en el hotel...", parse_mode='Markdown')
        desp = ses.get("despacho_pendiente", {})
        try:
            items_previos = json.dumps(desp.get("items_detalle", []), ensure_ascii=False)
            prompt_ajuste = f"""
            Eres el auditor contable de Lavaarte. El conductor está en el hotel '{hotel_nom}' entregando un despacho.
            Lista original de prendas despachadas: {items_previos}.
            Modificación reportada por el conductor en sitio: '{texto_ingresado}'.
            Ajusta las cantidades de las prendas entregadas efectivamente.
            Devuelve EXCLUSIVAMENTE un JSON:
            {{
              "items_detalle": [
                {{"prenda": "Nombre prenda", "cantidad": 10}}
              ],
              "total_prendas": 10,
              "notas": "Nota del ajuste (ej: Faltaron 2 sabanas)"
            }}
            """
            texto_raw = llamar_gemini_rotativo([prompt_ajuste])
            ajustado = json.loads(texto_raw.strip().replace("```json", "").replace("```", "").strip())
            
            desp["items_detalle"] = ajustado.get("items_detalle", desp.get("items_detalle", []))
            desp["total_prendas"] = ajustado.get("total_prendas", sum(i['cantidad'] for i in desp["items_detalle"]))
            desp["notas"] = ajustado.get("notas", desp.get("notas", ""))
            ses["despacho_pendiente"] = desp
            
            txt_nuevo = "✏️ *DESPACHO ACTUALIZADO EN SITIO:*\n\n" + armar_texto_despacho(desp, hotel_nom, ses.get("servicio", "Lencería"), ses.get("resp_lavaarte", "Conductor Lavaarte"))
            bot.send_message(chat_id, txt_nuevo, reply_markup=menu_confirmacion_despacho_en_sitio(), parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(m, "❌ Error ajustando prendas: " + str(e))
        return

    # 1. MODO CONSULTA / AUDITORÍA IA
    if modo == "CONSULTA":
        bot.reply_to(m, "🔍 Consultando libros y bases de datos con IA...", parse_mode='Markdown')
        try:
            payload = {
                "accion": "AUDITORIA_CONSULTA_UNIVERSAL",
                "pregunta": texto_ingresado
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=45)
            if resp.get("status") == "SUCCESS":
                txt_r = f"📊 *INFORME DE AUDITORÍA:*\n\n{resp.get('respuesta')}\n\n"
                txt_r += "❓ *¿Qué deseas hacer con esta información?*"
                bot.send_message(chat_id, txt_r, reply_markup=menu_post_consulta(), parse_mode='Markdown')
            else:
                bot.reply_to(m, "ℹ️ " + str(resp.get("mensaje", "No se encontraron datos coincidentes.")))
        except Exception as e:
            bot.reply_to(m, "❌ Error en auditoría: " + str(e))
        return

    # 2. MODO CORRECCIÓN UNIVERSAL EN TIEMPO REAL
    if modo == "CORREGIR_REGISTRO_BD":
        bot.reply_to(m, "⚙️ Aplicando modificación en tiempo real a Google Sheets...", parse_mode='Markdown')
        try:
            prompt_mod = f"""
            Eres el auditor contable de Lavaarte. El usuario solicita modificar un registro en la base de datos de Google Sheets:
            Instrucción: '{texto_ingresado}'.
            Devuelve un JSON estricto:
            {{
              "hotel": "Oceania / Wyndham / etc.",
              "hoja": "OCEANIA_DATOS / WYNDHAM_HUESPEDES_DATOS / etc.",
              "dia": 10,
              "habitacion": "304 / general",
              "prenda": "Toalla cuerpo",
              "campo_modificar": "cantidad / habitacion / prenda",
              "nuevo_valor": 18
            }}
            """
            texto_raw = llamar_gemini_rotativo([prompt_mod])
            mod_data = json.loads(texto_raw.strip().replace("```json", "").replace("```", "").strip())
            
            payload = {
                "accion": "CORREGIR_DATO_BD",
                "modificacion": mod_data,
                "texto_original": texto_ingresado
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=45)
            
            if resp.get("status") == "SUCCESS":
                bot.send_message(chat_id, f"✅ *¡REGISTRO ACTUALIZADO EN TIEMPO REAL!*\n\n{resp.get('mensaje')}", reply_markup=menu_principal(), parse_mode='Markdown')
                sesiones[chat_id] = {}
            else:
                bot.reply_to(m, "⚠️ No se pudo aplicar: " + str(resp.get("mensaje")))
        except Exception as e:
            bot.reply_to(m, "❌ Error corrigiendo registro: " + str(e))
        return

    # 3. CORRECCIÓN O INGRESO FINANCIERO
    if ses.get("modulo") == "FINANCIERO":
        tipo_mov = ses.get("tipo_fin", "EGRESO")
        cuenta = ses.get("cuenta_destino", "LAVAARTE")
        
        datos_previos = ses.get("movimiento_fin_pendiente")
        if datos_previos:
            bot.reply_to(m, "⚙️ Aplicando corrección al movimiento financiero...", parse_mode='Markdown')
            try:
                datos_fin = analizar_financiero_ia(None, tipo_mov, cuenta, datos_existentes=datos_previos, ajuste_texto=texto_ingresado)
                if "foto_base64" in datos_previos:
                    datos_fin["foto_base64"] = datos_previos["foto_base64"]
                sesiones[chat_id]["movimiento_fin_pendiente"] = datos_fin
                val_fmt = f"{datos_fin.get('valor', 0):,.2f}"
                nombre_cuenta = "👔 Lavaarte SAS" if cuenta == "LAVAARTE" else "👤 Personal Carlos"

                resumen_fin = f"📊 *CONFIRMACIÓN CORREGIDA ({nombre_cuenta}):*\n\n"
                resumen_fin += f"📌 *Tipo:* `{tipo_mov}`\n"
                resumen_fin += f"📅 *Fecha:* `{datos_fin.get('fecha')}`\n"
                resumen_fin += f"🏷️ *Categoría:* *{datos_fin.get('categoria')}*\n"
                resumen_fin += f"📝 *Concepto:* {datos_fin.get('concepto')}\n"
                if cuenta == "LAVAARTE":
                    resumen_fin += f"🏢 *Tercero / Proveedor:* {datos_fin.get('tercero', 'N/A')}\n"
                    resumen_fin += f"👤 *Responsable:* {datos_fin.get('responsable', 'N/A')}\n"
                resumen_fin += f"💳 *Método de Pago:* {datos_fin.get('metodo_pago')}\n"
                resumen_fin += f"💰 *Valor:* *${val_fmt}*\n\n"
                resumen_fin += "💬 Escribe *SI* para registrar en Sheets o *NO* para cancelar."
                bot.send_message(chat_id, resumen_fin, parse_mode='Markdown')
            except Exception as e:
                bot.reply_to(m, "❌ Error aplicando corrección financiera: " + str(e))
            return
            
        bot.reply_to(m, "🧾 Analizando movimiento con IA...", parse_mode='Markdown')
        try:
            datos_fin = analizar_financiero_ia(texto_ingresado, tipo_mov, cuenta)
            sesiones[chat_id]["movimiento_fin_pendiente"] = datos_fin
            val_fmt = f"{datos_fin.get('valor', 0):,.2f}"
            nombre_cuenta = "👔 Lavaarte SAS" if cuenta == "LAVAARTE" else "👤 Personal Carlos"

            resumen_fin = f"📊 *CONFIRMACIÓN ({nombre_cuenta}):*\n\n"
            resumen_fin += f"📌 *Tipo:* `{tipo_mov}`\n"
            resumen_fin += f"📅 *Fecha:* `{datos_fin.get('fecha')}`\n"
            resumen_fin += f"🏷️ *Categoría:* *{datos_fin.get('categoria')}*\n"
            resumen_fin += f"📝 *Concepto:* {datos_fin.get('concepto')}\n"
            if cuenta == "LAVAARTE":
                resumen_fin += f"🏢 *Tercero / Proveedor:* {datos_fin.get('tercero', 'N/A')}\n"
                resumen_fin += f"👤 *Responsable:* {datos_fin.get('responsable', 'N/A')}\n"
            resumen_fin += f"💳 *Método de Pago:* {datos_fin.get('metodo_pago')}\n"
            resumen_fin += f"💰 *Valor:* *${val_fmt}*\n\n"
            resumen_fin += "💬 Escribe *SI* para registrar en Sheets o *NO* para cancelar."
            bot.send_message(chat_id, resumen_fin, parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(m, "❌ Error analizando texto financiero: " + str(e))
        return

    # 4. PASOS DE CUSTODIA Y FLUJOS DE ENTREGA/RECEPCIÓN
    if paso == "REINTENTAR_CONSULTA_DESPACHO":
        resp_conductor = ses.get("resp_lavaarte", "Conductor Lavaarte")
        dia_logistico = calcular_dia_corrido_logistica()
        ses["paso_custodia"] = "CONSULTANDO_DESPACHO"
        bot.reply_to(
            m,
            f"🔎 Volviendo a consultar el último despacho activo de *{hotel_nom}*...",
            parse_mode='Markdown'
        )
        threading.Thread(
            target=_consultar_despacho_async,
            args=[chat_id, ses, hotel_nom, dia_logistico, resp_conductor],
            daemon=True
        ).start()
        return

    if paso == "RESP_LAVAARTE_DESPACHO":
        ses["resp_lavaarte"] = texto_ingresado
        ses["resp_hotel"] = "Por entregar en hotel"
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Registrado despachador: *{texto_ingresado}*\n\n📸 Ahora puedes enviar las fotos, audio o texto de las prendas despachadas:", parse_mode='Markdown')
        return

    if paso == "ENT_QUIEN_ENTREGA_LAVAARTE":
        resp_conductor = texto_ingresado
        ses["resp_lavaarte"] = resp_conductor
        ses["paso_custodia"] = None
        
        if ses.get("tipo") == "HUESPEDES":
            ses["paso_custodia"] = "ENT_QUIEN_RECIBE_HOTEL"
            bot.reply_to(m, f"✅ Entrega por Lavaarte: *{resp_conductor}*\n\n2️⃣ ¿Quién recibe por parte del hotel? (Escribe nombre y cargo):", parse_mode='Markdown')
            return
            
        dia_logistico = calcular_dia_corrido_logistica()
        bot.reply_to(m, f"✅ Conductor: *{resp_conductor}*\n🔎 Buscando despacho activo correspondiente al día *{dia_logistico}* para *{hotel_nom}*...", parse_mode='Markdown')
        threading.Thread(target=_consultar_despacho_async, args=[chat_id, ses, hotel_nom, dia_logistico, resp_conductor], daemon=True).start()
        return

    if paso == "ENT_QUIEN_RECIBE_HOTEL":
        ses["resp_hotel"] = texto_ingresado
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Recibe por el hotel: *{texto_ingresado}*\n\n📸 *¡Listo!* Ya puedes enviar las fotos de las prendas o planillas, audios o escribir las prendas entregadas:", parse_mode='Markdown')
        return

    if paso == "CONFIRMAR_QUIEN_RECIBE_HOTEL":
        quien_recibe = texto_ingresado
        desp = ses.get("despacho_pendiente", {})
        hora_bogota = ahora_bog.strftime("%I:%M %p")
        
        bot.reply_to(m, "⏳ Confirmando entrega y sellando hora en Google Sheets...")
        try:
            detalle_notas = desp.get("notas", "")
            if not detalle_notas:
                detalle_notas = f"Entregado a {quien_recibe}. Total prendas: {desp.get('total_prendas')}."
            else:
                detalle_notas = f"Entregado a {quien_recibe}. {detalle_notas}"

            payload = {
                "accion": "CONFIRMAR_ENTREGA_HOTEL",
                "ruta": ses.get("ruta", "Oriente"),
                "hotel": hotel_nom,
                "fila_despacho": desp.get("fila"),
                "total_prendas": desp.get("total_prendas", 0),
                "responsable_lavaarte": ses.get("resp_lavaarte", desp.get("despachado_por", "Conductor")),
                "responsable_hotel": quien_recibe,
                "hora_sellada": hora_bogota,
                "detalle_resumen": detalle_notas
            }
            resp = ejecutar_post_apps_script(URL_APPS_SCRIPT, payload, timeout=40)
            if resp.get("status") == "SUCCESS":
                ses["recibido_por_hotel"] = quien_recibe
                ses["paso_custodia"] = None
                
                txt_ok = f"🤝 *¡ENTREGA CONFIRMADA EXITOSAMENTE!*\n\n"
                txt_ok += f"🏨 *Hotel:* {hotel_nom}\n"
                txt_ok += f"👤 *Entregado por:* {ses.get('resp_lavaarte', desp.get('despachado_por'))}\n"
                txt_ok += f"✍️ *Recibido por:* {quien_recibe}\n"
                txt_ok += f"📊 *Prendas entregadas:* {desp.get('total_prendas')}\n"
                txt_ok += f"⏱️ *Hora sellada oficial (Bogotá):* *{hora_bogota}*\n\n"
                txt_ok += "📝 *RESPALDO DE SEGURIDAD (FIRMA DIGITAL):*\n"
                txt_ok += "Pídele a la persona que firme en la pantalla tocando el botón azul de abajo:"
                
                msg_sent = bot.send_message(chat_id, txt_ok, reply_markup=menu_firma_pantalla(hotel_nom, ses), parse_mode='Markdown')
                ses["msg_firma_id"] = msg_sent.message_id
            else:
                bot.reply_to(m, "⚠️ Error: " + str(resp.get("mensaje")))
        except Exception as e:
            bot.reply_to(m, "❌ Error sellando entrega: " + str(e))
        return

    if paso == "REC_QUIEN_ENTREGA_HOTEL":
        ses["resp_hotel"] = texto_ingresado
        ses["paso_custodia"] = "REC_QUIEN_RECIBE_LAVAARTE"
        bot.reply_to(m, f"✅ Entrega por hotel: *{texto_ingresado}*\n\n2️⃣ ¿Quién recibe por parte de Lavaarte? (Nombre del conductor):", parse_mode='Markdown')
        return

    if paso == "REC_QUIEN_RECIBE_LAVAARTE":
        ses["resp_lavaarte"] = texto_ingresado
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Recibe por Lavaarte: *{texto_ingresado}*\n\n📸 *¡Listo!* Ya puedes enviar las fotos de las planillas, notas de voz o texto de la ropa recibida:", parse_mode='Markdown')
        return

    # 5. CORRECCIÓN DE PRENDAS O FECHA PREVIO A CONFIRMAR
    if ses.get("filas"):
        fecha_detectada = extraer_fecha_formato(texto_ingresado)
        if fecha_detectada:
            ses["fecha_forzada"] = fecha_detectada
            ses["fecha_operacion"] = fecha_detectada
            for f in ses["filas"]:
                f["fecha"] = fecha_detectada
            resumen_txt = f"📅 *Fecha actualizada a {fecha_detectada}:*\n\n" + generar_resumen(ses["filas"], ses)
            enviar_mensaje_segmentado(chat_id, resumen_txt)
            return

        bot.reply_to(m, "⚙️ Aplicando ajustes a la lista...")
        threading.Thread(target=_corregir_filas_ia_hilo, args=[chat_id, texto_ingresado, ses], daemon=True).start()
        return

    # 6. INGRESO DE PRENDAS POR TEXTO DIRECTO
    if not ses.get("hotel"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    cfg = sesiones[chat_id]
    bot.reply_to(m, f"📝 Procesando texto para *{cfg['hotel']}*...", parse_mode='Markdown')
    threading.Thread(target=_procesar_texto_ia_hilo, args=[chat_id, texto_ingresado, cfg], daemon=True).start()

# =========================================================================
# LANZAMIENTO DEL SERVIDOR WEB FLASK + POLLING DEL BOT
# =========================================================================
threading.Thread(target=correr_web, daemon=True).start()

print("🚀 Bot Maestro Lavaarte en línea (100% Flash / Día Corrido OK / Anti-Duplicado OK / Wyndham Alineado / Soporte Drive OK)")
bot.infinity_polling(skip_pending=True)
