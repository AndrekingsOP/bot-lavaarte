# =========================================================================
# BOT CENTRAL LAVAARTE SAS - AUDITORÍA Y TRAZABILIDAD LOGÍSTICA COMPLETA
# MODELOS 100% FLASH + OCR COMPRIMIDO + HOMOLOGACIÓN BLINDADA (OCEANÍA / WYNDHAM)
# GESTIÓN FINANCIERA (LAVAARTE + CARLOS) + FIRMAS DIGITALES DRIVE + AUDITORÍA IA
# =========================================================================

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import datetime
import json
import io
import time
import threading
import base64
import unicodedata
from PIL import Image
from google import genai
from google.genai import types

TOKEN = '8816786492:AAEb6VgZzP07JJ9MegbVjiItuS-oopL5728'
GEMINI_API_KEY = 'AQ.Ab8RN6KHh9xczXiYb-Bm2DSL1Q8zsTyd695lbn3CF74Qc4OzGg'
URL_APPS_SCRIPT = 'https://script.google.com/macros/s/AKfycbxqnfe5kd_b0gB50r0IKw69pkRdsYq4vEHLIpwpRZpDYeTMq5TvWVCnsstm7Tj2W0we/exec'
URL_APPS_SCRIPT_CARLOS = 'https://script.google.com/macros/s/AKfycbwv-D7RZLLaxVe1mA8h7iyMblV5ZhGCZG4PggzCppAt8T5Y79t-j_Rt7Pe95lcuQ9-6Fg/exec'

bot = telebot.TeleBot(TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

MODELOS_ROTACION = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-3.5-flash-lite'
]

sesiones = {}
cola_fotos = {}
timers = {}
lock = threading.Lock()

ARBOL_SERVICIOS = {
    # RUTA ORIENTE
    "wyndham_huespedes": {"ruta": "Oriente", "hotel": "Wyndham", "servicio": "Huéspedes", "hoja": "WYNDHAM_HUESPEDES_DATOS", "tipo": "HUESPEDES", "base_defecto": "WYNDHAM HUÉSPEDES"},
    "wyndham_lenceria": {"ruta": "Oriente", "hotel": "Wyndham", "servicio": "Lencería", "hoja": "WYNDHAM_LENCERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "WYNDHAM LENCERÍA"},
    "wyndham_manteleria": {"ruta": "Oriente", "hotel": "Wyndham", "servicio": "Mantelería", "hoja": "WYNDHAM_MANTELERIA_DATOS", "tipo": "LENCERIA_MATRIZ", "base_defecto": "WYNDHAM MANTELERÍA"},
    "hilton": {"ruta": "Oriente", "hotel": "Hilton", "servicio": "General", "hoja": "HILTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HILTON HUÉSPEDES"},
    "hampton": {"ruta": "Oriente", "hotel": "Hampton", "servicio": "General", "hoja": "HAMPTON_DATOS", "tipo": "HUESPEDES", "base_defecto": "HAMPTON HUÉSPEDES"},
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

[PRECIOS NORTE 2026 - HUÉSPEDES DANN / VIRREY / ANDES / BOGOTÁ PLAZA]
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
40|Traje/Suit|Lavado in seco|19836
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

def homologar_prenda_telegram(nombre_prenda, es_lenceria=False, es_wyndham_huespedes=False):
    norm = limpiar_texto_simple(nombre_prenda)
    
    # 1. REGLA ESTRICTA WYNDHAM HUÉSPEDES (LEGGINS = PANTALÓN / TOP = BRASSIERE)
    if es_wyndham_huespedes or "wyndham" in norm:
        if any(w in norm for w in ["leggin", "leggis", "licra", "pantalon de licra", "malla"]):
            return "Pantalón/Pants"
        if any(w in norm for w in ["top", "crop top", "crop", "bra", "corpin"]):
            return "Brassiere/Brassiere"

    # 2. REGLA OCEANÍA Y LENCERÍA GENERAL
    # Ajustable sencilla / sensilla / sensillo
    if "ajustable" in norm and any(w in norm for w in ["sensill", "sencill"]):
        return "Sábana ajustable sencilla"
    if "plana" in norm and any(w in norm for w in ["sensill", "sencill"]):
        return "Sábana plana sencilla"

    # Cojín (con o sin tilde)
    if "cojin" in norm or "cojines" in norm:
        return "Cojín"

    # Funda / Fundas (Singularización obligatoria)
    if norm in ["funda", "fundas", "funda de almohada", "fundas de almohada"]:
        return "Funda"

    # Facial (Unificación total)
    if "facial" in norm:
        return "FACIAL"
        
    # Protector de colchón
    if "protector" in norm and "colchon" in norm:
        return "PROTECTOR DE COLCHON"
        
    # Cortesía
    if "cortesia" in norm:
        return "Sábana cortesía"
        
    if es_lenceria:
        if norm in ["mano", "toalla mano", "toalla de mano", "toallas de mano", "toallas mano"]:
            return "Toalla mano"
        if norm in ["cuerpo", "toalla cuerpo", "toalla de cuerpo", "toallas cuerpo", "toallas de cuerpo"]:
            return "Toalla cuerpo"
        if norm in ["tapete", "toalla tapete", "toallas tapete"]:
            return "Toalla tapete"
            
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
    ultimo_error = None
    config_llamada = types.GenerateContentConfig(
        temperature=0.1,
        thinking_config=types.ThinkingConfig(thinking_budget=512)
    )

    for modelo in MODELOS_ROTACION:
        for _ in range(2):
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
                if any(k in err_str for k in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "404", "NOT_FOUND", "403", "PERMISSION_DENIED"]):
                    time.sleep(1.0)
                    break
                else:
                    time.sleep(0.8)
                    continue
    raise ultimo_error

def a_entero(val):
    try:
        return int(val)
    except:
        return 1

def analizar_con_ia(contenido_multimodal, config_sesion, correccion_usuario=None):
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    hotel = config_sesion['hotel']
    servicio = config_sesion['servicio']
    tipo_op = config_sesion.get('tipo', 'HUESPEDES')
    key = config_sesion.get('key', '')
    
    es_wyndham_huespedes = (key == "wyndham_huespedes")
    es_lenceria = es_servicio_lista_limpia(config_sesion)

    prompt = f"""
    Eres el auditor contable oficial de Lavaarte Lavandería SAS.
    Operación activa: Hotel '{hotel}', Servicio '{servicio}', Clave: '{key}'.
    
    REGLAS ESTRICTAS Y HOMOLOGACIÓN BLINDADA:
    
    1. REGLA ESTRICTA WYNDHAM HUÉSPEDES (wyndham_huespedes):
       - ¿Es Wyndham Huéspedes?: {es_wyndham_huespedes}
       - EXCLUSIÓN TOTAL DE EMPLEADOS: Si la lista describe empleados por nombre sin habitación numérica de hotel, DESCÁRTALOS por completo junto con sus prendas.
       - HABITACIONES NUMÉRICAS ÚNICAMENTE (ej: 204, 315, 501).
       - REGLA OBLIGATORIA LEGGINS: Los leggins, leggings o licras deportivas DEBEN registrarse como 'Pantalón/Pants' (Código 25, Lavado en seco, $5.950).
       - REGLA OBLIGATORIA TOP: Los tops, crop top o similares DEBEN registrarse como 'Brassiere/Brassiere' (Código 4, Lavado, $3.500).
       - UNIFICACIÓN Y SUMA DE PRENDAS IDÉNTICAS: Si en una misma habitación anotan prendas iguales ('1 pantalón verde' y '1 pantalón azul'), unifícalas en un solo registro ('Pantalón/Pants', cantidad 2).

    2. REGLA OCEANÍA / FONTANA / LENCERÍA:
       - 'ajustable sensilla', 'ajustable sencilla', 'sensillo' -> 'Sábana ajustable sencilla'.
       - 'cojin', 'cojín', 'cojines' -> 'Cojín'.
       - 'fundas', 'funda' -> 'Funda'.
       - 'facial', 'toalla facial' -> 'FACIAL'.
       - 'protector colchon' -> 'PROTECTOR DE COLCHON'.
       - 'cortesia' -> 'Sábana cortesía'.
       - Toallas: 'Toalla cuerpo', 'Toalla mano', 'Toalla tapete'.

    3. REGLA BOGOTÁ PLAZA UNIFORMES / SUITE MANTELERÍA / DANN EMPLEADOS:
       - Bogotá Plaza Uniformes (bogotap_datos): Detectar Cargo + Prenda (ej: 'MESERO(EV) CHAQUETA').
       - Suite Mantelería: Rango de filas 3 a 18.
       - Dann Empleados: Código o nombre asignado como identificador.

    4. GENERAL:
       - 'remision': Número de remisión (Hampton obligatorio en Col B; Hilton vacío).
       - 'habitacion': Número de habitación o persona.
       - 'extra': 'Sí' o 'No'.

    CATÁLOGO GLOBAL:
    {CATALOGO_GLOBAL}
    
    {f"AJUSTE DEL USUARIO: {correccion_usuario}" if correccion_usuario else ""}
    
    Devuelve EXCLUSIVAMENTE un JSON válido (array de objetos sin bloques markdown):
    [
      {{
        "fecha": "{fecha_hoy}",
        "remision": "1234",
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

    if isinstance(filas, list):
        for f in filas:
            f["prenda"] = homologar_prenda_telegram(
                f.get("prenda", ""), 
                es_lenceria=es_lenceria, 
                es_wyndham_huespedes=es_wyndham_huespedes
            )
            # Doble blindaje: Re-asegurar código y precio para Leggins y Top en Wyndham
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

    if es_wyndham_huespedes and isinstance(filas, list):
        filas_consolidadas = {}
        for f in filas:
            hab = str(f.get("habitacion", "")).strip()
            if not any(char.isdigit() for char in hab):
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
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    extra_contexto = ""
    if datos_existentes:
        extra_contexto = f"\nDATOS PREVIAMENTE DETECTADOS: {json.dumps(datos_existentes, ensure_ascii=False)}\nCORRECCIÓN SOLICITADA: {ajuste_texto}\nIMPORTANTE: Conserva todos los campos previos a menos que el usuario pida cambiarlos explícitamente."

    if cuenta_destino == "CARLOS":
        prompt = f"""
        Eres el asistente financiero personal de Carlos Andrés Suárez.
        Analiza el comprobante, factura, recibo, audio o texto financiero de GASTO O INGRESO PERSONAL.
        Tipo de movimiento: {tipo_forzado}.
        Fecha obligatoria: Si no se especifica una fecha explícita, usa SIEMPRE la fecha de hoy '{fecha_hoy}'.
        Categorías: Alimentación, Transporte, Deporte / Ciclismo, Ocio / Cine, Hogar / Servicios, Salud, Ropa, Ahorro / Inversión, Otros.
        {extra_contexto}
        Devuelve EXCLUSIVAMENTE un JSON:
        {{
          "fecha": "{fecha_hoy}",
          "tipo": "{tipo_forzado}",
          "categoria": "Alimentación / Transporte / etc.",
          "concepto": "Descripción concisa del movimiento",
          "metodo_pago": "Efectivo / Nequi / Daviplata / Tarjeta Débito / Tarjeta Crédito / Transferencia",
          "valor": 50000
        }}
        """
    else:
        prompt = f"""
        Eres el asistente contable financiero de Lavaarte Lavandería SAS.
        Analiza el comprobante, factura, recibo, audio o texto financiero.
        Tipo de movimiento: {tipo_forzado}.
        Fecha obligatoria: Si no se menciona una fecha explícita, usa SIEMPRE la fecha de hoy '{fecha_hoy}'.
        Categorías: Combustible / Insumos Químicos / Mantenimiento / Servicios Públicos / Nómina / Papelería / Arriendo / Facturación Hoteles / Servicios Mostrador / Otros.
        {extra_contexto}
        Devuelve EXCLUSIVAMENTE un JSON:
        {{
          "fecha": "{fecha_hoy}",
          "tipo": "{tipo_forzado}",
          "categoria": "Combustible / Insumos Químicos / etc.",
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
    texto = texto_raw.strip().replace("```json", "").replace("```", "").strip()
    res = json.loads(texto)
    
    try:
        res["valor"] = float(res.get("valor", 0))
    except:
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

# ==========================================
# MENÚS EN TELEGRAM
# ==========================================
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

def menu_confirmacion_firma(hotel_key):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📸 Adjuntar Foto de la Firma", callback_data="adjuntar_foto_firma"),
        InlineKeyboardButton("⏩ Omitir Firma por Ahora", callback_data="omitir_firma")
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
        InlineKeyboardButton("🏨 Hotel Hampton", callback_data="sel_hampton"),
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
    fecha_reg = filas[0].get('fecha', datetime.datetime.now().strftime("%d/%m/%Y"))
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
    
    # 1. CASO EFICACIA DOTACIONES
    if es_eficacia:
        total_p = sum(item.get('cantidad', 0) for item in filas)
        resumen += "📊 *Total Dotaciones:* " + str(total_p) + " prendas\n"
        resumen += "📋 *DESGLOSE CONSOLIDADO POR EMPRESA:*\n"
        cuenta_act = ""
        for it in filas:
            cta = str(it.get('habitacion', it.get('habitacion_o_persona', 'GENERAL')))
            if cta != cuenta_act:
                cuenta_act = cta
                resumen += "\n🏢 *Empresa:* `" + cuenta_act + "`\n"
            resumen += "• " + str(it.get('prenda', '')) + " - Cant: *" + str(it.get('cantidad', 0)) + "*\n"
            
    # 2. CASO LENCERÍA, MANTELERÍA Y UNIFORMES
    elif es_limpio:
        total_p = sum(item.get('cantidad', 0) for item in filas)
        resumen += "📊 *Total Prendas:* " + str(total_p) + "\n"
        resumen += "📋 *LISTA DE CONTEO:*\n"
        for it in filas:
            resumen += "• " + str(it.get('prenda', '')) + " - Cant: *" + str(it.get('cantidad', 0)) + "*\n"
            
    # 3. CASO HUÉSPEDES GENERALES
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
            p_cant = str(it.get('cantidad', 0))
            p_unit = f"{it.get('valorUnitario', 0):,.2f}"
            p_tot = f"{it.get('valorTotal', 0):,.2f}"
            p_extra = str(it.get('extra', 'No'))
            resumen += f"• [Cód {p_cod}] {p_nom} - Cant: {p_cant} - Unit: ${p_unit} - Total: ${p_tot} [Extra: {p_extra}]\n"
            
    resumen += "\n💬 *¿Qué deseas hacer?*\n"
    resumen += "• Escribe *SI* para guardar en Google Sheets.\n"
    resumen += "• Escribe *NO* para cancelar.\n"
    resumen += "• O escribe cualquier corrección directa."
    return resumen

# ==========================================
# MANEJADORES TELEGRAM
# ==========================================
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
    tipo_str = "EGRESO" if call.data == 'fin_egreso' else "INGRESO"
    emoji = "🔴" if tipo_str == "EGRESO" else "🟢"
    
    bot.edit_message_text(
        f"{emoji} *REGISTRAR {tipo_str}*\n\n¿A qué cuenta corresponde este movimiento?",
        chat_id,
        call.message.message_id,
        reply_markup=menu_destino_cuenta(tipo_str),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('cta_'))
def seleccionar_cuenta_destino(call):
    chat_id = call.message.chat.id
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
    txt += "🎙️ *O enviar:* Nota de voz (ej: _'Pagué 35 mil de almuerzo con Nequi'_).\n"
    txt += "✍️ *O escribirlo:* Directamente en un mensaje de texto."
    
    bot.edit_message_text(txt, chat_id, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('sel_'))
def seleccionar_hotel(call):
    key = call.data.replace('sel_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    if not cfg:
        bot.answer_callback_query(call.id, "Hotel no encontrado.")
        return
        
    sesiones[call.message.chat.id] = dict(cfg)
    sesiones[call.message.chat.id]["key"] = key
    sesiones[call.message.chat.id]["filas"] = []
    
    bot.edit_message_text(
        "🏨 Operación: *" + str(cfg['hotel']) + " (" + str(cfg['servicio']) + ")*\n\n¿Qué movimiento deseas registrar?",
        call.message.chat.id, call.message.message_id,
        reply_markup=menu_recibir_entregar(key),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('mov_entregar_'))
def manejar_opciones_entrega(call):
    key = call.data.replace('mov_entregar_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    sesiones[call.message.chat.id] = dict(cfg)
    sesiones[call.message.chat.id]["key"] = key
    sesiones[call.message.chat.id]["movimiento"] = "ENTREGA"
    
    bot.edit_message_text(
        "📤 *ENTREGA DE ROPA - " + str(cfg['hotel']) + "*\n\nSelecciona el momento de la entrega:",
        call.message.chat.id, call.message.message_id,
        reply_markup=menu_sub_entrega(key),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('despacho_planta_'))
def iniciar_despacho_planta(call):
    chat_id = call.message.chat.id
    sesiones[chat_id]["sub_op"] = "DESPACHO_PLANTA"
    sesiones[chat_id]["paso_custodia"] = "RESP_LAVAARTE_DESPACHO"
    bot.send_message(chat_id, "📦 *DESPACHO EN PLANTA*\n\nEscribe el nombre de quién despacha la ropa en planta:", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirmar_hotel_'))
def iniciar_confirmacion_hotel(call):
    chat_id = call.message.chat.id
    cfg = sesiones.get(chat_id, {})
    hotel_nom = cfg.get("hotel", "Hotel")
    dia_actual = datetime.datetime.now().day
    
    bot.send_message(chat_id, f"🔎 Buscando despacho activo del día {dia_actual} para *{hotel_nom}*...", parse_mode='Markdown')
    try:
        payload = {
            "accion": "CONSULTAR_DESPACHO",
            "ruta": cfg.get("ruta", "Oriente"),
            "hotel": hotel_nom,
            "destino": cfg.get("hoja", ""),
            "dia": dia_actual
        }
        resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=30).json()
        
        if resp.get("status") == "SUCCESS":
            desp = resp.get("despacho", {})
            items_detalle = desp.get("items_detalle", [])
            sesiones[chat_id]["despacho_pendiente"] = desp
            sesiones[chat_id]["paso_custodia"] = "CONFIRMAR_QUIEN_RECIBE_HOTEL"
            
            txt_info = "📦 *DESPACHO ACTIVO DE PLANTA PARA HOY:*\n"
            txt_info += f"🏨 *Hotel:* {hotel_nom}\n"
            txt_info += f"📅 *Fecha:* {desp.get('fecha')} ({desp.get('hora')})\n"
            txt_info += f"👤 *Despachador en Planta:* {desp.get('despachado_por')}\n"
            txt_info += "──────────────────────────\n"
            
            if items_detalle:
                txt_info += "📋 *PRENDAS A ENTREGAR:*\n"
                for it in items_detalle:
                    txt_info += f"• *{it['prenda']}:* {it['cantidad']} unidades\n"
            else:
                txt_info += f"📝 *Detalle:* {desp.get('notas', 'Despacho registrado')}\n"
                
            txt_info += "──────────────────────────\n"
            txt_info += f"📊 *Total Piezas:* *{desp.get('total_prendas')}*\n\n"
            txt_info += "✍️ *Por favor escribe el nombre de la persona que recibe en el hotel (Nombre y cargo):*"
            bot.send_message(chat_id, txt_info, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, f"⚠️ No hay un despacho activo registrado en planta para hoy en *{hotel_nom}*.\n\nVerifica que planta ya haya registrado las cantidades en la columna E.", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(chat_id, "❌ Error consultando: " + str(e))

@bot.callback_query_handler(func=lambda call: call.data.startswith('mov_recibir_'))
def iniciar_recepcion(call):
    chat_id = call.message.chat.id
    key = call.data.replace('mov_recibir_', '')
    cfg = ARBOL_SERVICIOS.get(key)
    sesiones[chat_id] = dict(cfg)
    sesiones[chat_id]["key"] = key
    sesiones[chat_id]["movimiento"] = "RECEPCIÓN"
    sesiones[chat_id]["paso_custodia"] = "REC_QUIEN_ENTREGA_HOTEL"
    bot.send_message(chat_id, "📥 *RECEPCIÓN EN HOTEL - " + str(cfg['hotel']) + "*\n\n1️⃣ ¿Quién entrega la ropa por parte del hotel? (Escribe nombre y cargo):", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data in ['accion_seguir', 'menu_inicio'])
def manejar_post_guardado(call):
    chat_id = call.message.chat.id
    if call.data == 'accion_seguir':
        cfg = sesiones.get(chat_id, {})
        bot.send_message(chat_id, "📸 Envíame los siguientes datos para *" + str(cfg.get('hotel', '')) + "*.", parse_mode='Markdown')
    else:
        cmd_start(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ['adjuntar_foto_firma', 'omitir_firma'])
def manejar_opcion_firma(call):
    chat_id = call.message.chat.id
    if call.data == 'adjuntar_foto_firma':
        sesiones[chat_id]["paso_custodia"] = "SUBIR_FOTO_FIRMA"
        bot.send_message(chat_id, "📸 *Toma una foto clara de la firma de la camarera / recepcionista y envíala:*", parse_mode='Markdown')
    else:
        bot.send_message(chat_id, "✅ Entrega finalizada sin firma fotográfica.", reply_markup=menu_principal())

def procesar_lote_fotos(chat_id):
    with lock:
        if chat_id not in cola_fotos or not cola_fotos[chat_id]:
            return
        imgs = list(cola_fotos[chat_id])
        cola_fotos[chat_id] = []
        if chat_id in timers:
            timers[chat_id].cancel()
            
    cfg = sesiones.get(chat_id, ARBOL_SERVICIOS["wyndham_huespedes"])
    
    # 1. SUBIR FOTO DE FIRMA DIGITAL A GOOGLE DRIVE
    if cfg.get("paso_custodia") == "SUBIR_FOTO_FIRMA":
        bot.send_message(chat_id, "✍️ Guardando firma digital en Google Drive de Lavaarte...", parse_mode='Markdown')
        try:
            img_firma = imgs[0]
            buf = io.BytesIO()
            img_firma.save(buf, format="JPEG", quality=90)
            b64_firma = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            payload = {
                "accion": "GUARDAR_FIRMA_ENTREGA",
                "hotel": cfg.get("hotel", "Hotel"),
                "ruta": cfg.get("ruta", "Oriente"),
                "fecha": datetime.datetime.now().strftime("%Y-%m-%d"),
                "hora": datetime.datetime.now().strftime("%I-%M-%p"),
                "firma_base64": b64_firma,
                "recibido_por": cfg.get("recibido_por_hotel", "Personal Hotel")
            }
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=40).json()
            
            if resp.get("status") == "SUCCESS":
                txt_f = f"✅ *¡FIRMA ARCHIVADA EN GOOGLE DRIVE!*\n\n"
                txt_f += f"📁 *Archivo:* `{resp.get('nombre_archivo')}`\n"
                txt_f += f"🔗 [Ver Firma en Drive]({resp.get('url_firma')})\n"
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

    # 3. PROCESAMIENTO OPERATIVO GENERAL
    bot.send_message(chat_id, "🔍 Procesando " + str(len(imgs)) + " foto(s) con homologación blindada...", parse_mode='Markdown')
    try:
        filas = analizar_con_ia(imgs, cfg)
        sesiones[chat_id]["filas"] = filas
        sesiones[chat_id]["total_fotos"] = len(imgs)
        resumen_txt = generar_resumen(filas, cfg, len(imgs))
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.send_message(chat_id, "❌ Error analizando imágenes: " + str(e))

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
        if chat_id in timers:
            timers[chat_id].cancel()
        t = threading.Timer(2.5, procesar_lote_fotos, args=[chat_id])
        timers[chat_id] = t
        t.start()

@bot.message_handler(content_types=['voice', 'audio'])
def recibir_audio(message):
    chat_id = message.chat.id
    if chat_id not in sesiones or (not sesiones[chat_id].get("hotel") and sesiones[chat_id].get("modulo") != "FINANCIERO"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    cfg = sesiones[chat_id]
    bot.reply_to(message, "🎙️ Procesando audio...", parse_mode='Markdown')
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        audio_bytes = bot.download_file(file_info.file_path)
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
        sesiones[chat_id]["filas"] = filas
        resumen_txt = generar_resumen(filas, cfg, 1)
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.reply_to(message, "❌ Error procesando audio: " + str(e))

@bot.message_handler(func=lambda m: m.text and m.text.strip().upper() in ['SI', 'SÍ'])
def confirmar_guardado(m):
    chat_id = m.chat.id
    ses = sesiones.get(chat_id, {})
    
    # CONFIRMAR FINANCIERO (LAVAARTE O CARLOS)
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
                resp = requests.post(URL_APPS_SCRIPT_CARLOS, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=40).json()
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
                    "movimiento_financiero": m_fin
                }
                resp_raw = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=45)
                try:
                    resp = resp_raw.json()
                except Exception:
                    bot.reply_to(m, f"❌ Error servidor Sheets: {resp_raw.text[:200]}")
                    return

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

    # CONFIRMAR PRENDAS OPERATIVAS
    if ses.get("filas"):
        cfg = ses
        filas = cfg["filas"]
        tipo_op = filas[0].get("tipo_operacion_detectada", cfg.get("tipo", "HUESPEDES"))
        hora_bogota = datetime.datetime.now().strftime("%I:%M %p")
        
        bot.reply_to(m, f"⏳ Guardando datos y registrando custodia (Hora Bogotá: {hora_bogota})...", parse_mode='Markdown')
        try:
            dia_actual = datetime.datetime.now().day
            if filas and filas[0].get('fecha'):
                try:
                    dia_actual = int(filas[0]['fecha'].split('/')[0])
                except:
                    pass
                    
            payload = {
                "accion": "GUARDAR",
                "ruta": cfg.get("ruta", "Oriente"),
                "destino": cfg["hoja"],
                "tipo_operacion": tipo_op,
                "movimiento": cfg.get("movimiento", "RECEPCIÓN"),
                "responsable_lavaarte": cfg.get("resp_lavaarte", "Conductor Lavaarte"),
                "responsable_hotel": cfg.get("resp_hotel", "Recepción / Ama de llaves"),
                "hora_sellada": hora_bogota,
                "dia": dia_actual,
                "filas": filas
            }
            
            resp_raw = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=90)
            data_resp = resp_raw.json()
            
            if resp_raw.status_code == 200 and data_resp.get("status") == "SUCCESS":
                hoja_dest = data_resp.get("hoja_guardada", cfg['hotel'])
                bot.reply_to(m, f"✅ *¡Datos guardados con éxito!*\n📋 Registrado en: `{hoja_dest}`\n⏱️ Hora sellada oficial: *{hora_bogota}*\n⏱️ Auditoría generada en `TIEMPOS` y `RECEPCION_ENTREGA`.", parse_mode='Markdown')
                sesiones[chat_id]["filas"] = []
                bot.send_message(chat_id, "¿Qué deseas hacer a continuación?", reply_markup=menu_post_guardado())
            else:
                bot.reply_to(m, "⚠️ Error del servidor: " + str(data_resp.get("mensaje", resp_raw.text)))
        except Exception as e:
            bot.reply_to(m, "❌ Error enviando a Google Sheets: " + str(e))
    else:
        bot.reply_to(m, "No hay datos pendientes por confirmar. Escribe *Hola* para abrir el menú.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and m.text.strip().upper() == 'NO')
def cancelar_guardado(m):
    chat_id = m.chat.id
    if chat_id in sesiones and (sesiones[chat_id].get("filas") or sesiones[chat_id].get("movimiento_fin_pendiente")):
        sesiones[chat_id]["filas"] = []
        sesiones[chat_id]["movimiento_fin_pendiente"] = None
        bot.reply_to(m, "❌ Operación cancelada. Puedes enviar nuevos datos o escribir *Hola*.", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.content_type == 'text' and m.text not in ['/start', '/menu'])
def procesar_texto_general(m):
    chat_id = m.chat.id
    ses = sesiones.get(chat_id, {})
    paso = ses.get("paso_custodia")
    modo = ses.get("modo")
    
    # 1. MODO CONSULTA / AUDITORÍA IA
    if modo == "CONSULTA":
        bot.reply_to(m, "🔍 Consultando libros y bases de datos con IA...", parse_mode='Markdown')
        try:
            payload = {
                "accion": "AUDITORIA_CONSULTA_UNIVERSAL",
                "pregunta": m.text
            }
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=45).json()
            
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
            Instrucción: '{m.text}'.
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
                "texto_original": m.text
            }
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=45).json()
            
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
                datos_fin = analizar_financiero_ia(None, tipo_mov, cuenta, datos_existentes=datos_previos, ajuste_texto=m.text)
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
            datos_fin = analizar_financiero_ia(m.text, tipo_mov, cuenta)
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

    # 4. PASOS DE CUSTODIA Y CONFIRMACIÓN DE ENTREGA
    if paso == "RESP_LAVAARTE_DESPACHO":
        ses["resp_lavaarte"] = m.text.strip()
        ses["resp_hotel"] = "Por entregar en hotel"
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Registrado despachador: *{m.text.strip()}*\n\n📸 Ahora puedes enviar las fotos, audio o texto de las prendas despachadas:", parse_mode='Markdown')
        return

    if paso == "CONFIRMAR_QUIEN_RECIBE_HOTEL":
        quien_recibe = m.text.strip()
        desp = ses.get("despacho_pendiente", {})
        hora_bogota = datetime.datetime.now().strftime("%I:%M %p")
        
        bot.reply_to(m, "⏳ Confirmando entrega y generando sello de hora en Google Sheets...")
        try:
            payload = {
                "accion": "CONFIRMAR_ENTREGA_HOTEL",
                "ruta": ses.get("ruta", "Oriente"),
                "hotel": ses.get("hotel", "Hotel"),
                "fila_despacho": desp.get("fila"),
                "total_prendas": desp.get("total_prendas", 0),
                "responsable_lavaarte": desp.get("despachado_por", "Conductor"),
                "responsable_hotel": quien_recibe,
                "hora_sellada": hora_bogota,
                "detalle_resumen": f"Entregado a {quien_recibe}. Total prendas: {desp.get('total_prendas')}."
            }
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=40).json()
            if resp.get("status") == "SUCCESS":
                ses["recibido_por_hotel"] = quien_recibe
                ses["paso_custodia"] = "SUBIR_FOTO_FIRMA"
                
                txt_ok = f"🤝 *¡ENTREGA CONFIRMADA EXITOSAMENTE!*\n\n"
                txt_ok += f"🏨 *Hotel:* {ses.get('hotel')}\n"
                txt_ok += f"👤 *Entregado por:* {desp.get('despachado_por')}\n"
                txt_ok += f"✍️ *Recibido por:* {quien_recibe}\n"
                txt_ok += f"📊 *Prendas entregadas:* {desp.get('total_prendas')}\n"
                txt_ok += f"⏱️ *Hora sellada oficial (Bogotá):* *{hora_bogota}*\n\n"
                txt_ok += "📝 *RESPALDO DE SEGURIDAD (FIRMA DIGITAL):*\n"
                txt_ok += "¿Deseas capturar y archivar la firma de la persona que recibió en Google Drive?"
                
                bot.send_message(chat_id, txt_ok, reply_markup=menu_confirmacion_firma(ses.get("key", "hotel")), parse_mode='Markdown')
            else:
                bot.reply_to(m, "⚠️ Error: " + str(resp.get("mensaje")))
        except Exception as e:
            bot.reply_to(m, "❌ Error sellando entrega: " + str(e))
        return

    if paso == "REC_QUIEN_ENTREGA_HOTEL":
        ses["resp_hotel"] = m.text.strip()
        ses["paso_custodia"] = "REC_QUIEN_RECIBE_LAVAARTE"
        bot.reply_to(m, f"✅ Entrega por hotel: *{m.text.strip()}*\n\n2️⃣ ¿Quién recibe por parte de Lavaarte? (Nombre del conductor):", parse_mode='Markdown')
        return

    if paso == "REC_QUIEN_RECIBE_LAVAARTE":
        ses["resp_lavaarte"] = m.text.strip()
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Recibe por Lavaarte: *{m.text.strip()}*\n\n📸 *¡Listo!* Ya puedes enviar las fotos de las planillas, notas de voz o texto de la ropa recibida:", parse_mode='Markdown')
        return

    # 5. CORRECCIÓN DE PRENDAS PREVIO A CONFIRMAR
    if ses.get("filas"):
        bot.reply_to(m, "⚙️ Aplicando ajustes a la lista...")
        try:
            datos_previos = json.dumps(ses["filas"], ensure_ascii=False)
            filas_actualizadas = analizar_con_ia(None, ses, correccion_usuario="Lista actual: " + datos_previos + ". Modificación solicitada: " + str(m.text))
            sesiones[chat_id]["filas"] = filas_actualizadas
            resumen_txt = "✏️ *Lista actualizada:*\n\n" + generar_resumen(filas_actualizadas, ses)
            enviar_mensaje_segmentado(chat_id, resumen_txt)
        except Exception as e:
            bot.reply_to(m, "❌ Error aplicando cambio: " + str(e))
        return

    # 6. INGRESO DE PRENDAS POR TEXTO DIRECTO
    if not ses.get("hotel"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    cfg = sesiones[chat_id]
    bot.reply_to(m, "📝 Procesando texto para *" + str(cfg['hotel']) + "*...", parse_mode='Markdown')
    try:
        filas = analizar_con_ia([m.text], cfg)
        sesiones[chat_id]["filas"] = filas
        resumen_txt = generar_resumen(filas, cfg, 1)
        enviar_mensaje_segmentado(chat_id, resumen_txt)
    except Exception as e:
        bot.reply_to(m, "❌ Error procesando texto: " + str(e))

# ==========================================
# INICIO DEL SERVICIO
# ==========================================
print("🚀 Bot Maestro Lavaarte en línea (100% Flash / Homologación Blindada)")
bot.infinity_polling()
