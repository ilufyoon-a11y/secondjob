TU_ID = 5760026959
# Estado adivinador

juego = {
    "activa": False,
    "creada": False,
    "inscripciones_cerradas": False,
    "iniciando_ronda": False,
    "adivinanza": "",
    "respuesta": "",
    "premio": 0,
    "cupos": 0,
    "participantes": [],
    "ganador": None
}


# Estado dividir


dividir = {
    "activa": False,
    "inscripciones_cerradas": False,
    "iniciando_ronda": False,

    "premio": 0,
    "cupos": 0,
    "participantes": [],

    "jugador1": None,
    "jugador2": None,

    "eleccion1": None,
    "eleccion2": None,

    # Selección
    "elegidos": [],
    "revisaron": [],

    # Turnos
    "turno_iniciado": False,
    "turno2_enviado": False,

    # Resultado
    "resultado_enviado": False,

    # Tiempo
    "perdio_tiempo1": False,
    "perdio_tiempo2": False
}

raton = {
    "activa": False,
    "inscripciones_cerradas": False,
    "iniciando_ronda": False,

    "premio": 0,
    "cupos": 0,
    "participantes": [],

    # Rol secreto
    "raton": None,
    "roles_revisados": [],

    # Rondas
    "ronda": 0,
    "max_rondas": 4,

    # Elecciones de escondite
    "elecciones": {},

    # Votaciones
    "votos": {},

    # Resultado
    "resultado_enviado": False
}

# Historial

historial = {}
sumar_historial = {}
historial_juegos = {}

# Sistema adivinador

oportunidades = {}
avisados_eliminados = {}
eliminados = {}
vetados = {}

# Creación privada

admins_creando = {}

# Chats activos

grupo_juego = None
admin_juego = None

grupo_dividir = None
admin_dividir = None

grupo_raton = None
admin_raton = None

# Timer del dividir
timer_dividir = None
timer_raton = None
