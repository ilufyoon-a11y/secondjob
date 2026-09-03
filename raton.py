import datos
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = None

def configurar(bot_recibido):
    global bot
    bot = bot_recibido
    print("RATON CARGADO")
    registrar_raton()

def registrar_raton():

    @bot.message_handler(commands=["raton"])
    def iniciar_raton_comando(message):

        try:
            miembro = bot.get_chat_member(
                message.chat.id,
                message.from_user.id
            )

            if miembro.status not in ["administrator", "creator"]:
                bot.reply_to(
                    message,
                    "❌ Solo los administradores pueden iniciar una partida."
                )
                return

        except Exception as e:
            print("ERROR RATON ADMIN:", e)
            return

        if datos.raton["activa"]:
            bot.reply_to(
                message,
                "❌ Ya hay una partida de Ratón en curso."
            )
            return

        texto = message.text.split("-")

        if len(texto) != 3:
            bot.reply_to(
                message,
                "Uso:\n/raton - premio - cupos\n\nEjemplo:\n/raton - 10 - 8"
            )
            return

        try:
            premio = int(texto[1].strip())
            cupos = int(texto[2].strip())

        except ValueError:
            bot.reply_to(
                message,
                "El premio y los cupos deben ser números."
            )
            return

        if premio <= 0 or cupos < 2:
            bot.reply_to(
                message,
                "❌ El premio debe ser mayor a 0 y debe haber al menos 2 cupos."
            )
            return

        datos.raton["activa"] = True
        datos.raton["inscripciones_cerradas"] = False
        datos.raton["iniciando_ronda"] = False

        datos.raton["premio"] = premio
        datos.raton["cupos"] = cupos
        datos.raton["participantes"] = []

        datos.raton["raton"] = None
        datos.raton["roles_revisados"] = []

        datos.raton["ronda"] = 0
        datos.raton["elecciones"] = {}
        datos.raton["votos"] = {}

        datos.raton["resultado_enviado"] = False

        datos.grupo_raton = message.chat.id
        datos.admin_raton = message.from_user.id

        markup = InlineKeyboardMarkup()

        btn_unirse = InlineKeyboardButton(
            "ᰔUnirse",
            callback_data="raton_unirse"
        )

        btn_salir = InlineKeyboardButton(
            "ᰔSalir",
            callback_data="raton_salir"
        )

        markup.add(btn_unirse, btn_salir)

        bot.send_message(
            message.chat.id,
            f"""🐭 ¡Atrapa al Ratón! (˶ᵔ ᵕ ᵔ˶)

Uno de ustedes será el Ratón...
¿Podrán descubrir quién es antes de que escape? 👀

𖹭˚࿔ Premio: {premio} Robux
𖹭˚࿔ Cupos: {cupos}""",
            reply_markup=markup
        )

        datos.timer_raton = threading.Timer(
            60,
            cerrar_inscripciones_raton
        )

        datos.timer_raton.start()

    # OJO: este handler solo debe capturar unirse/salir.
    # Antes usaba startswith("raton_"), lo que interceptaba TODOS los
    # callbacks del juego (ver_rol, escondites, votos) porque este
    # handler se registra primero y telebot ejecuta solo el primer
    # handler cuyo filtro haga match. Por eso nunca llegaban a
    # dispararse los otros handlers.
    @bot.callback_query_handler(
        func=lambda call: call.data in ["raton_unirse", "raton_salir"]
    )
    def botones_raton(call):

        # FIX: sin esto, un botón viejo de OTRO grupo (de una partida
        # anterior que ya no está activa en ese chat) podía manipular
        # la única partida global de datos.raton, aunque fuera de un
        # grupo distinto al de la partida actual.
        if call.message.chat.id != datos.grupo_raton:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida activa aquí."
            )
            return

        if not datos.raton["activa"]:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida de Ratón activa."
            )
            return

        usuario = (
            f"@{call.from_user.username}"
            if call.from_user.username
            else call.from_user.first_name
        )

        if call.data == "raton_unirse":

            if usuario in datos.vetados:
                bot.answer_callback_query(
                    call.id,
                    "🚫 Has sido expulsado."
                )
                return

            if datos.raton["inscripciones_cerradas"]:
                bot.answer_callback_query(
                    call.id,
                    "⌛ El tiempo acabó."
                )
                return

            if usuario in datos.raton["participantes"]:
                bot.answer_callback_query(
                    call.id,
                    "Ya estás unido."
                )
                return

            if len(datos.raton["participantes"]) >= datos.raton["cupos"]:
                bot.answer_callback_query(
                    call.id,
                    "🐭 ¡Los cupos se han llenado!"
                )
                return

            datos.raton["participantes"].append(usuario)

            bot.answer_callback_query(
                call.id,
                "¡Te uniste al Ratón! 🐭"
            )

            bot.send_message(
                call.message.chat.id,
                f"✅ {usuario} se unió al juego."
            )

            if len(datos.raton["participantes"]) >= datos.raton["cupos"]:

                datos.raton["inscripciones_cerradas"] = True

                if datos.timer_raton is not None:
                    datos.timer_raton.cancel()
                    datos.timer_raton = None

                bot.send_message(
                    call.message.chat.id,
                    """(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!

🐭 Preparando la partida..."""
                )

                iniciar_partida_raton()

        elif call.data == "raton_salir":

            # Antes se podía salir en cualquier momento, incluso con
            # roles ya asignados o votación en curso, lo que rompía
            # las comparaciones de longitud contra "participantes"
            # más adelante. Ahora, una vez cerradas las inscripciones
            # ya no se puede abandonar la partida.
            if datos.raton["inscripciones_cerradas"]:
                bot.answer_callback_query(
                    call.id,
                    "❌ La partida ya comenzó, no puedes salir.",
                    show_alert=True
                )
                return

            if usuario not in datos.raton["participantes"]:
                bot.answer_callback_query(
                    call.id,
                    "No estás participando."
                )
                return

            datos.raton["participantes"].remove(usuario)

            bot.answer_callback_query(
                call.id,
                "Has salido del juego."
            )

            bot.send_message(
                call.message.chat.id,
                f"( ˶°ㅁ°) !! {usuario} salió del juego."
            )

    @bot.callback_query_handler(
        func=lambda call: call.data == "raton_ver_rol"
    )
    def ver_rol_raton(call):

        # FIX: misma validación de chat que en botones_raton.
        if call.message.chat.id != datos.grupo_raton:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida activa aquí."
            )
            return

        usuario = (
            f"@{call.from_user.username}"
            if call.from_user.username
            else call.from_user.first_name
        )

        # Verificar que siga participando
        if usuario not in datos.raton["participantes"]:
            bot.answer_callback_query(
                call.id,
                "❌ No estás participando en esta partida.",
                show_alert=True
            )
            return

        if usuario in datos.raton["roles_revisados"]:
            bot.answer_callback_query(
                call.id,
                "👀 Ya revisaste tu rol.",
                show_alert=True
            )
            return

        datos.raton["roles_revisados"].append(usuario)

        if usuario == datos.raton["raton"]:

            bot.answer_callback_query(
                call.id,
                """🐭 ¡ERES EL RATÓN!

🤫 Tu identidad es secreta.

🎯 Tu objetivo es sobrevivir
sin que los gatos te descubran.""",
                show_alert=True
            )

        else:

            bot.answer_callback_query(
                call.id,
                """🐱 ¡ERES UN GATO!

🔍 Tu objetivo es descubrir
quién es el Ratón.

🤫 No sabes quién tiene
el otro rol.""",
                show_alert=True
            )

        if (
            len(datos.raton["roles_revisados"])
            == len(datos.raton["participantes"])
        ):

            datos.raton["ronda"] = 1

            bot.send_message(
                datos.grupo_raton,
                """𓂃 ࣪˖ ִֶָ🐭 ࣪˖ ִֶָ𓂃

        🌙 Ronda 1/4

El Ratón está buscando dónde esconderse... 👀"""
            )

            iniciar_ronda_raton()

    @bot.callback_query_handler(
        func=lambda call: call.data in [
            "raton_bosque",
            "raton_casa",
            "raton_lago",
            "raton_alcantarilla"
        ]
    )
    def elegir_escondite(call):

        # FIX: misma validación de chat que en botones_raton.
        if call.message.chat.id != datos.grupo_raton:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida activa aquí."
            )
            return

        usuario = (
            f"@{call.from_user.username}"
            if call.from_user.username
            else call.from_user.first_name
        )

        if usuario not in datos.raton["participantes"]:
            bot.answer_callback_query(
                call.id,
                "❌ No estás participando.",
                show_alert=True
            )
            return

        if usuario in datos.raton["elecciones"]:
            bot.answer_callback_query(
                call.id,
                "👀 Ya elegiste tu escondite.",
                show_alert=True
            )
            return

        lugares = {
            "raton_bosque": "🌳 Bosque",
            "raton_casa": "🏠 Casa",
            "raton_lago": "🌊 Lago",
            "raton_alcantarilla": "🕳️ Alcantarilla"
        }

        eleccion = lugares[call.data]

        datos.raton["elecciones"][usuario] = eleccion

        bot.answer_callback_query(
            call.id,
            "🤫 Elección guardada.",
            show_alert=True
        )

        bot.send_message(
            datos.grupo_raton,
            f"✅ {usuario} ya eligió dónde esconderse."
        )

        if len(datos.raton["elecciones"]) == len(
            datos.raton["participantes"]
        ):

            bot.send_message(
                datos.grupo_raton,
                """✨ Todos han elegido.

🤫 Las elecciones permanecen en secreto...
👀 Preparando las pistas..."""
            )

            mostrar_pistas_raton()

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("raton_votar_")
    )
    def votar_raton(call):

        # FIX: misma validación de chat que en botones_raton.
        if call.message.chat.id != datos.grupo_raton:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida activa aquí."
            )
            return

        usuario = (
            f"@{call.from_user.username}"
            if call.from_user.username
            else call.from_user.first_name
        )

        if usuario not in datos.raton["participantes"]:
            bot.answer_callback_query(
                call.id,
                "❌ No estás participando.",
                show_alert=True
            )
            return

        if usuario in datos.raton["votos"]:
            bot.answer_callback_query(
                call.id,
                "👀 Ya votaste.",
                show_alert=True
            )
            return

        elegido = call.data.replace(
            "raton_votar_",
            "",
            1
        )

        # FIX: antes se podía votar por uno mismo. En un juego de
        # "encuentra al impostor" no tiene sentido permitirlo.
        if elegido == usuario:
            bot.answer_callback_query(
                call.id,
                "❌ No puedes votar por ti mismo.",
                show_alert=True
            )
            return

        if elegido not in datos.raton["participantes"]:
            bot.answer_callback_query(
                call.id,
                "❌ Ese jugador ya no está disponible.",
                show_alert=True
            )
            return

        datos.raton["votos"][usuario] = elegido

        bot.answer_callback_query(
            call.id,
            "🗳️ ¡Voto registrado!",
            show_alert=True
        )

        bot.send_message(
            datos.grupo_raton,
            f"🗳️ {usuario} ya realizó su voto."
        )

        if len(datos.raton["votos"]) == len(
            datos.raton["participantes"]
        ):

            mostrar_resultado_votacion_raton()

def cerrar_inscripciones_raton():

    if not datos.raton["activa"]:
        return

    if datos.raton["inscripciones_cerradas"]:
        return

    datos.raton["inscripciones_cerradas"] = True

    if datos.grupo_raton is None:
        return

    bot.send_message(
        datos.grupo_raton,
        """⏰ Se acabó el tiempo de inscripción.

🐭 Preparando la partida..."""
    )

    iniciar_partida_raton()

def iniciar_partida_raton():

    if not datos.raton["activa"]:
        return

    if datos.raton["iniciando_ronda"]:
        return

    datos.raton["iniciando_ronda"] = True
    datos.raton["inscripciones_cerradas"] = True

    if len(datos.raton["participantes"]) < 2:

        bot.send_message(
            datos.grupo_raton,
            "(｡•́︿•̀｡) No hay suficientes participantes para comenzar."
        )

        reiniciar_estado_raton()
        return

    datos.raton["raton"] = random.choice(
        datos.raton["participantes"]
    )

    datos.raton["roles_revisados"] = []

    texto = "── .ꕥ Participantes:\n\n"

    for i, participante in enumerate(
        datos.raton["participantes"],
        start=1
    ):
        texto += f"{i}. {participante}\n"

    texto += "\n🐭 Los roles han sido asignados."

    bot.send_message(
        datos.grupo_raton,
        texto
    )

    markup = InlineKeyboardMarkup()

    btn = InlineKeyboardButton(
        "🔍 Ver mi rol",
        callback_data="raton_ver_rol"
    )

    markup.add(btn)

    bot.send_message(
        datos.grupo_raton,
        """(˶>⩊<˶) Cada jugador tiene un rol secreto.

Pulsa el botón para descubrir quién eres.

🔍 Nadie podrá ver el rol de los demás.""",
        reply_markup=markup
    )

    datos.raton["iniciando_ronda"] = False

def iniciar_ronda_raton():

    if not datos.raton["activa"]:
        return

    datos.raton["elecciones"] = {}

    markup = InlineKeyboardMarkup()

    btn_bosque = InlineKeyboardButton(
        "🌳 Bosque",
        callback_data="raton_bosque"
    )

    btn_casa = InlineKeyboardButton(
        "🏠 Casa",
        callback_data="raton_casa"
    )

    btn_lago = InlineKeyboardButton(
        "🌊 Lago",
        callback_data="raton_lago"
    )

    btn_alcantarilla = InlineKeyboardButton(
        "🕳️ Alcantarilla",
        callback_data="raton_alcantarilla"
    )

    markup.row(btn_bosque, btn_casa)
    markup.row(btn_lago, btn_alcantarilla)

    bot.send_message(
        datos.grupo_raton,
        """𖹭˚࿔ Elige dónde esconderte:

Cada jugador debe elegir un lugar.
🤫 Tu elección será secreta.""",
        reply_markup=markup
    )

def mostrar_pistas_raton():

    if not datos.raton["activa"]:
        return

    elecciones = datos.raton["elecciones"]

    bosque = 0
    casa = 0
    lago = 0
    alcantarilla = 0

    for eleccion in elecciones.values():

        if eleccion == "🌳 Bosque":
            bosque += 1

        elif eleccion == "🏠 Casa":
            casa += 1

        elif eleccion == "🌊 Lago":
            lago += 1

        elif eleccion == "🕳️ Alcantarilla":
            alcantarilla += 1

    mensaje = f"""𓂃 ࣪˖ ִֶָ🔍 ࣪˖ ִֶָ𓂃

        ✦ Pistas de la ronda ✦

🌳 Bosque → {bosque} jugador(es)
🏠 Casa → {casa} jugador(es)
🌊 Lago → {lago} jugador(es)
🕳️ Alcantarilla → {alcantarilla} jugador(es)

👀 El Ratón está entre ellos...

🤔 ¿Quién será?"""

    bot.send_message(
        datos.grupo_raton,
        mensaje
    )

    iniciar_votacion_raton()

def iniciar_votacion_raton():

    if not datos.raton["activa"]:
        return

    datos.raton["votos"] = {}

    markup = InlineKeyboardMarkup()

    for participante in datos.raton["participantes"]:

        boton = InlineKeyboardButton(
            f"🐱 {participante}",
            callback_data=f"raton_votar_{participante}"
        )

        markup.add(boton)

    bot.send_message(
        datos.grupo_raton,
        """𓂃 ࣪˖ ִֶָ🗳️ ࣪˖ ִֶָ𓂃

        ¿Quién es el Ratón? 👀

Vota por el jugador que
crees que es el Ratón.

୨୧ Tu voto será secreto.""",
        reply_markup=markup
    )

def _pagar_robux(usuario, monto):
    """
    Aplica el resultado económico de la partida a un participante,
    igual que hace adivinador_bot.py con datos.historial /
    datos.historial_juegos / datos.sumar_historial.
    monto puede ser positivo (ganancia) o negativo (pérdida).
    """
    signo = "+" if monto >= 0 else ""

    datos.historial[usuario] = f"{signo}{monto} Robux"

    if usuario not in datos.historial_juegos:
        datos.historial_juegos[usuario] = []

    datos.historial_juegos[usuario].append(
        ("Ratón", f"{signo}{monto} Robux")
    )

    datos.sumar_historial[usuario] = (
        datos.sumar_historial.get(usuario, 0) + monto
    )

def mostrar_resultado_votacion_raton():

    if not datos.raton["activa"]:
        return

    conteo = {}

    for elegido in datos.raton["votos"].values():

        conteo[elegido] = conteo.get(elegido, 0) + 1

    mayor = max(conteo.values())

    empatados = [
        jugador
        for jugador, votos in conteo.items()
        if votos == mayor
    ]

    texto = """𓂃 ࣪˖ ִֶָ🗳️ ࣪˖ ִֶָ𓂃

        ✦ Resultado de la votación ✦

"""

    for jugador, votos in conteo.items():

        texto += f"🐾 {jugador} → {votos} voto(s)\n"

    texto += "\n"

    premio = datos.raton["premio"]
    raton = datos.raton["raton"]
    participantes = datos.raton["participantes"]

    # FIX: antes nadie ganaba ni perdía robux al terminar la partida.
    # Reparto: si atrapan al Ratón, cada gato (todos menos el Ratón)
    # gana el premio y el Ratón lo pierde. Si el Ratón escapa (votación
    # errada, sin empate), el Ratón gana el premio y nadie más cobra.
    # En caso de empate no se paga nada, como ya decía el mensaje.
    if len(empatados) > 1:

        texto += """⚠️ ¡Hay un empate!

Nadie será eliminado esta ronda. 👀"""

    else:

        elegido = empatados[0]

        if elegido == raton:

            texto += f"""🎯 ¡Encontraron al Ratón!

🐭 El Ratón era {elegido}.

✨ Los gatos ganan esta ronda.
🏆 Cada gato gana {premio} Robux."""

            for participante in participantes:
                if participante == raton:
                    _pagar_robux(participante, -premio)
                else:
                    _pagar_robux(participante, premio)

        else:

            texto += f"""😭 ¡Se equivocaron!

🐭 {elegido} NO era el Ratón.

El verdadero Ratón sigue escondido... 👀
🏆 {raton} (el Ratón) gana {premio} Robux."""

            _pagar_robux(raton, premio)

    bot.send_message(
        datos.grupo_raton,
        texto
    )

    # Antes la partida quedaba "activa" para siempre después de la
    # votación, así que nunca se podía iniciar un /raton nuevo hasta
    # reiniciar el bot. Ahora se cierra y se limpia el estado.
    reiniciar_estado_raton()

def reiniciar_estado_raton():

    if datos.timer_raton is not None:
        datos.timer_raton.cancel()
        datos.timer_raton = None

    datos.raton["activa"] = False
    datos.raton["inscripciones_cerradas"] = False
    datos.raton["iniciando_ronda"] = False

    datos.raton["premio"] = 0
    datos.raton["cupos"] = 0
    datos.raton["participantes"] = []

    datos.raton["raton"] = None
    datos.raton["roles_revisados"] = []

    datos.raton["ronda"] = 0
    datos.raton["elecciones"] = {}
    datos.raton["votos"] = {}

    datos.raton["resultado_enviado"] = False

    datos.grupo_raton = None
    datos.admin_raton = None
