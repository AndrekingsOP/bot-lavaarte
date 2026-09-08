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
    'gemini-3.6-flash',
    'gemini-3.5-flash',
    'gemini-3.1-flash-lite',
    'gemini-3-flash',
    'gemini-flash-latest'
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
    "dann_empleados": {"ruta": "Norte", "hotel": "Dann", "servicio": "Empleados / Códigos", "hoja": "DANN_EMPLEADOS_DATOS", "tipo": "HUESPEDES", "base_defecto": "DANN EMPLEADOS"},
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

def homologar_prenda_telegram(nombre_prenda, es_lenceria=False):
    norm = limpiar_texto_simple(nombre_prenda)
    
    # Si contiene la palabra 'cortesia' (con o sin tilde, sola o combinada), SIEMPRE es Sábana cortesía
    if "cortesia" in norm:
        return "Sábana cortesía"
        
    if es_lenceria:
        if norm in ["mano", "toalla mano", "toalla de mano"]:
            return "Toalla mano"
        if norm in ["cuerpo", "toalla cuerpo", "toalla de cuerpo"]:
            return "Toalla cuerpo"
        if norm in ["tapete", "toalla tapete"]:
            return "Toalla tapete"
            
    return nombre_prenda

def llamar_gemini_rotativo(contents):
    ultimo_error = None
    for modelo in MODELOS_ROTACION:
        for intento in range(2):
            try:
                resp = client.models.generate_content(model=modelo, contents=contents)
                if resp and resp.text:
                    return resp.text
            except Exception as e:
                err_str = str(e)
                ultimo_error = e
                if any(k in err_str for k in ["429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "404", "NOT_FOUND"]):
                    time.sleep(0.8)
                    break
                else:
                    time.sleep(1.0)
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
    ruta = config_sesion.get('ruta', 'Oriente')
    tipo_op = config_sesion.get('tipo', 'HUESPEDES')
    key = config_sesion.get('key', '')
    
    es_wyndham_huespedes = (key == "wyndham_huespedes")
    es_hilton = (key == "hilton")
    es_fontana = (key == "fontana")
    es_oceania = (key == "oceania")
    es_bogotap_datos = (key == "bogotap_datos")
    es_dann_emp = (key == "dann_empleados")
    es_lenceria_matriz = (tipo_op == "LENCERIA_MATRIZ" or es_fontana or es_oceania)

    prompt = f"""
    Eres el auditor contable oficial de Lavaarte Lavandería SAS.
    Operación activa: Hotel '{hotel}', Servicio '{servicio}', Clave: '{key}'.
    
    REGLAS ESTRICTAS Y AISLADAS POR HOTEL:
    
    1. REGLA ESTRICTA WYNDHAM HUÉSPEDES (wyndham_huespedes):
       - ¿Es Wyndham Huéspedes?: {es_wyndham_huespedes}
       - EXCLUSIÓN TOTAL DE EMPLEADOS: Los empleados pagan de contado en caja diariamente. Si la lista contiene bloques, firmas o nombres propios de personas que son empleados (sin número de habitación de hotel), IGNORA Y DESCARTA POR COMPLETO esos nombres y todas las prendas asociadas a ellos.
       - PROCESAR ÚNICAMENTE HABITACIONES NUMÉRICAS DE HUÉSPEDES (ej: 204, 315, 501).
       - PRIORIDAD AL PRIMER ÍTEM LEÍDO: Si una anotación describe una prenda compuesta o ambigua como '1 blusa de pijama', '1 pantalón de sudadera', '1 camisa tipo polo', clasifícala SIEMPRE por el PRIMER sustantivo/prenda mencionado. Ejemplo: 'blusa de pijama' DEBE clasificarse como 'Blusa/Blouse' (código 6) y NUNCA como 'Pijama'.
       - UNIFICACIÓN Y SUMA DE PRENDAS IDÉNTICAS: Si dentro de una misma habitación anotan prendas iguales separadas por color o detalle (ej: '1 pantalón verde' y '1 pantalón azul'), unifícalas en un solo registro del catálogo base ('Pantalón/Pants', cantidad 2) en lugar de crear líneas separadas.

    2. REGLA HILTON:
       - ¿Es Hilton?: {es_hilton}
       - Ignora cualquier número de remisión.
       - Descarta y excluye empleados o uniformes sin habitación de huéspedes.

    3. REGLAS FONTANA Y OCEANIA (LENCERÍA INSTITUCIONAL):
       - ¿Es Fontana u Oceania?: {es_fontana or es_oceania}
       - Toda la ropa recibida es Lencería institucional.
       - REGLA CORTESÍA OBLIGATORIA: Si el usuario escribe 'cortesía', 'cortesia' o 'toalla cortesia', DEBES clasificar la prenda como 'Sábana cortesía' (NUNCA como toalla cortesía).
       - REGLA TOALLAS: Clasifica estrictamente como 'Toalla cuerpo', 'Toalla mano' y 'Toalla tapete'. No uses 'Toalla de mano'.

    4. REGLAS BOGOTÁ PLAZA UNIFORMES / SUITE MANTELERÍA / DANN LENCERÍA:
       - Si es Bogotá Plaza Uniformes (bogotap_datos): Los textos son compuestos de Cargo + Prenda (ej: 'MESERO(EV) CHAQUETA', 'COCINA DELANTAL', 'CAPITAN CAMISA'). Detecta ambos componentes para ubicar la cantidad exacta en la fila de la matriz horizontal.
       - Suite Mantelería: Rango estricto de filas 3 a 18. No crear filas abajo.

    5. REGLAS DANN EMPLEADOS:
       - ¿Es Dann Empleados?: {es_dann_emp}
       - La persona puede tener un nombre propio (ej: 'Ricardo') o un código compuesto (ej: '13-514'). Asigna dicho identificador en la columna de habitación/persona.
       - Cruza correctamente con la lista de precios Norte 2026.

    6. REGLAS GENERALES:
       - 'remision': Número de remisión (Hampton en Columna B; Hilton vacío).
       - 'habitacion': Número de habitación, nombre de empleado o código (ej: '13-514').
       - 'extra': 'Sí' o 'No' según recargo.

    CATÁLOGO DE REFERENCIA:
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
        contents.extend(contenido_multimodal)
    elif contenido_multimodal is not None:
        contents.append(contenido_multimodal)
        
    texto_raw = llamar_gemini_rotativo(contents)
    texto = texto_raw.strip().replace("```json", "").replace("```", "").strip()
    filas = json.loads(texto)

    # POST-PROCESAMIENTO PROGRAMÁTICO DE HOMOLOGACIÓN (FONTANA, OCEANIA Y MATRICES)
    if isinstance(filas, list):
        for f in filas:
            f["prenda"] = homologar_prenda_telegram(f.get("prenda", ""), es_lenceria=es_lenceria_matriz)

    # DOBLE FILTRO PROGRAMÁTICO PARA WYNDHAM HUÉSPEDES
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

def analizar_financiero_ia(contenido_multimodal, tipo_forzado="EGRESO", cuenta_destino="LAVAARTE"):
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    
    if cuenta_destino == "CARLOS":
        prompt = f"""
        Eres el asistente financiero personal de Carlos Andrés Suárez.
        Analiza el comprobante, factura, recibo, audio o texto financiero de GASTO O INGRESO PERSONAL.
        Tipo de movimiento: {tipo_forzado}.
        Categorías sugeridas: Alimentación, Transporte, Deporte / Ciclismo, Ocio / Cine, Hogar / Servicios, Salud, Ropa, Ahorro / Inversión, Otros.
        Devuelve EXCLUSIVAMENTE un JSON con:
        {{
          "fecha": "{fecha_hoy}",
          "tipo": "{tipo_forzado}",
          "categoria": "Alimentación / Transporte / Deporte / etc.",
          "concepto": "Descripción concisa del gasto o ingreso",
          "metodo_pago": "Efectivo / Nequi / Daviplata / Tarjeta Débito / Tarjeta Crédito / Transferencia",
          "valor": 50000
        }}
        """
    else:
        prompt = f"""
        Eres el asistente contable financiero de Lavaarte Lavandería SAS.
        Analiza el comprobante, factura, recibo, audio o texto financiero recibido.
        Tipo de movimiento: {tipo_forzado}.
        Devuelve EXCLUSIVAMENTE un JSON con:
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
    if isinstance(contenido_multimodal, list):
        contents.extend(contenido_multimodal)
    elif contenido_multimodal is not None:
        contents.append(contenido_multimodal)
    texto_raw = llamar_gemini_rotativo(contents)
    texto = texto_raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(texto)

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
    tipo_op = filas[0].get('tipo_operacion_detectada', config_sesion.get('tipo', 'HUESPEDES'))
    mov = config_sesion.get('movimiento', '')
    es_eficacia = (config_sesion.get('key') == "eficacia")
    
    r_lavaarte = config_sesion.get('resp_lavaarte', 'Conductor Lavaarte')
    r_hotel = config_sesion.get('resp_hotel', 'Recepción / Ama de llaves')
    
    resumen = "🏨 *HOTEL / SERVICIO:* " + hotel_txt
    if mov:
        resumen += " (*" + str(mov) + "*)"
    resumen += "\n📅 *FECHA:* " + str(fecha_reg) + "\n"
    resumen += "👤 *Responsable Lavaarte:* `" + str(r_lavaarte) + "`\n"
    resumen += "🏨 *Responsable Hotel:* `" + str(r_hotel) + "`\n"
    
    if es_eficacia or tipo_op == "MATRIZ_FILAS_CLIENTE":
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
    elif tipo_op == "LENCERIA_MATRIZ":
        total_p = sum(item.get('cantidad', 0) for item in filas)
        resumen += "📊 *Total Lencería:* " + str(total_p) + " prendas\n"
        resumen += "📋 *DETALLE:*\n"
        for it in filas:
            resumen += "• " + str(it.get('prenda', '')) + " - Cant: *" + str(it.get('cantidad', 0)) + "*\n"
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

@bot.callback_query_handler(func=lambda call: call.data in ['menu_inicio', 'ruta_oriente', 'ruta_norte', 'modo_consulta', 'modo_corregir', 'menu_financiero'])
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
        bot.edit_message_text("🔍 *MODO AUDITORÍA / CONSULTAS CON IA*\n\nEscribe tu pregunta en lenguaje natural.", chat_id, call.message.message_id, parse_mode='Markdown')
    elif call.data == 'modo_corregir':
        sesiones[chat_id] = {"modo": "CORREGIR"}
        bot.edit_message_text("✏️ *MODO CORRECCIÓN DE REGISTRO*\n\nEscribe el ajuste que deseas realizar de forma explícita.", chat_id, call.message.message_id, parse_mode='Markdown')
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
    
    bot.send_message(chat_id, "🔎 Buscando despacho pendiente para *" + str(hotel_nom) + "*...", parse_mode='Markdown')
    try:
        payload = {"accion": "CONSULTAR_DESPACHO", "ruta": cfg.get("ruta", "Oriente"), "hotel": hotel_nom}
        resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=30).json()
        
        if resp.get("status") == "SUCCESS":
            desp = resp.get("despacho", {})
            sesiones[chat_id]["despacho_pendiente"] = desp
            sesiones[chat_id]["paso_custodia"] = "CONFIRMAR_QUIEN_RECIBE_HOTEL"
            
            txt_info = "📋 *DESPACHO DETALLADO ENCONTRADO EN SISTEMA:*\n\n"
            txt_info += "📅 *Fecha Despacho:* " + str(desp.get("fecha")) + " (" + str(desp.get("hora")) + ")\n"
            txt_info += "👤 *Despachado por:* " + str(desp.get("despachado_por")) + "\n"
            txt_info += "📊 *Total Prendas:* *" + str(desp.get("total_prendas")) + "*\n"
            txt_info += "📝 *Detalle:* " + str(desp.get("notas", "N/A")) + "\n\n"
            txt_info += "✍️ *Por favor escribe el nombre de la persona que recibe en el hotel (Nombre y cargo):*"
            bot.send_message(chat_id, txt_info, parse_mode='Markdown')
        else:
            bot.send_message(chat_id, "⚠️ No hay un despacho pendiente registrado en planta para *" + str(hotel_nom) + "*.", parse_mode='Markdown')
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

def procesar_lote_fotos(chat_id):
    with lock:
        if chat_id not in cola_fotos or not cola_fotos[chat_id]:
            return
        imgs = list(cola_fotos[chat_id])
        cola_fotos[chat_id] = []
        if chat_id in timers:
            timers[chat_id].cancel()
            
    cfg = sesiones.get(chat_id, ARBOL_SERVICIOS["wyndham_huespedes"])
    
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

    bot.send_message(chat_id, "🔍 Procesando " + str(len(imgs)) + " foto(s) con reglas específicas de hotel...", parse_mode='Markdown')
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
    if chat_id not in sesiones or (not sesiones[chat_id].get("hotel") and sesiones[chat_id].get("modulo") != "FINANCIERO"):
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
    
    if ses.get("movimiento_fin_pendiente"):
        m_fin = ses["movimiento_fin_pendiente"]
        cuenta = ses.get("cuenta_destino", "LAVAARTE")
        bot.reply_to(m, "⏳ Guardando en el libro contable...", parse_mode='Markdown')
        try:
            if cuenta == "CARLOS":
                payload = {
                    "tipo": m_fin.get("tipo", "GASTO"),
                    "categoria": m_fin.get("categoria", "Varios"),
                    "valor": m_fin.get("valor", 0),
                    "metodo": m_fin.get("metodo_pago", "Transferencia/Nequi"),
                    "descripcion": m_fin.get("concepto", "")
                }
                resp = requests.post(URL_APPS_SCRIPT_CARLOS, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=40).json()
                if resp.get("status") == "SUCCESS":
                    val_fmt = f"{m_fin.get('valor', 0):,.2f}"
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
                payload = {
                    "accion": "REGISTRAR_FINANCIERO",
                    "movimiento_financiero": m_fin
                }
                resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=45).json()
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

    if ses.get("filas"):
        cfg = ses
        filas = cfg["filas"]
        tipo_op = filas[0].get("tipo_operacion_detectada", cfg.get("tipo", "HUESPEDES"))
        
        bot.reply_to(m, "⏳ Guardando datos y registrando custodia (con hora de Bogotá)...", parse_mode='Markdown')
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
                "dia": dia_actual,
                "filas": filas
            }
            
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=90)
            data_resp = resp.json()
            
            if resp.status_code == 200 and data_resp.get("status") == "SUCCESS":
                hoja_dest = data_resp.get("hoja_guardada", cfg['hotel'])
                bot.reply_to(m, "✅ *¡Datos guardados con éxito!*\n📋 Registrado en: `" + str(hoja_dest) + "`\n⏱️ Auditoría generada en `TIEMPOS` y `RECEPCION_ENTREGA` (Hora Colombia OK).", parse_mode='Markdown')
                sesiones[chat_id]["filas"] = []
                bot.send_message(chat_id, "¿Qué deseas hacer a continuación?", reply_markup=menu_post_guardado())
            else:
                bot.reply_to(m, "⚠️ Error del servidor: " + str(data_resp.get("mensaje", resp.text)))
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
    
    if ses.get("modulo") == "FINANCIERO":
        tipo_mov = ses.get("tipo_fin", "EGRESO")
        cuenta = ses.get("cuenta_destino", "LAVAARTE")
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

    if paso == "RESP_LAVAARTE_DESPACHO":
        ses["resp_lavaarte"] = m.text.strip()
        ses["resp_hotel"] = "Por entregar en hotel"
        ses["paso_custodia"] = None
        bot.reply_to(m, f"✅ Registrado despachador: *{m.text.strip()}*\n\n📸 Ahora puedes enviar las fotos, audio o texto de las prendas despachadas:", parse_mode='Markdown')
        return

    if paso == "CONFIRMAR_QUIEN_RECIBE_HOTEL":
        quien_recibe = m.text.strip()
        desp = ses.get("despacho_pendiente", {})
        bot.reply_to(m, "⏳ Confirmando entrega detallada en Google Sheets...")
        try:
            payload = {
                "accion": "CONFIRMAR_ENTREGA_HOTEL",
                "ruta": ses.get("ruta", "Oriente"),
                "hotel": ses.get("hotel", "Hotel"),
                "fila_despacho": desp.get("fila"),
                "total_prendas": desp.get("total_prendas", 0),
                "responsable_lavaarte": desp.get("despachado_por", "Conductor"),
                "responsable_hotel": quien_recibe,
                "detalle_resumen": f"Entregado a {quien_recibe}. Total prendas: {desp.get('total_prendas')}."
            }
            resp = requests.post(URL_APPS_SCRIPT, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=40).json()
            if resp.get("status") == "SUCCESS":
                txt_ok = f"🤝 *¡ENTREGA CONFIRMADA EXITOSAMENTE!*\n\n"
                txt_ok += f"🏨 *Hotel:* {ses.get('hotel')}\n"
                txt_ok += f"👤 *Entregado por:* {desp.get('despachado_por')}\n"
                txt_ok += f"✍️ *Recibido por:* {quien_recibe}\n"
                txt_ok += f"📊 *Prendas entregadas:* {desp.get('total_prendas')}\n"
                txt_ok += f"⏱️ *Hora sellada (Bogotá):* {datetime.datetime.now().strftime('%I:%M %p')}\n\n"
                txt_ok += "Guardado en `RECEPCION_ENTREGA` y `TIEMPOS` con detalle completo."
                bot.send_message(chat_id, txt_ok, parse_mode='Markdown')
                sesiones[chat_id] = {}
                bot.send_message(chat_id, "Selecciona una nueva opción:", reply_markup=menu_principal())
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

    if not ses.get("hotel"):
        sesiones[chat_id] = dict(ARBOL_SERVICIOS["wyndham_huespedes"])
        
    cfg = sesiones[chat_id]
    bot.reply_to(m, "📝 Procesando texto para *" + str(cfg['hotel']) + "* con reglas específicas...", parse_mode='Markdown')
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
print("🚀 Bot Maestro Lavaarte en línea (Reglas Aisladas por Hotel / Zona Horaria Bogotá / Wyndham Huéspedes Blindado / Finanzas Duales Lavaarte-Carlos)")
bot.infinity_polling()
