import datos
import os
import logging
import threading
import uuid

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# ----------------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("adivinador_bot")

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN no está definido en las variables de entorno.")

bot = telebot.TeleBot(TOKEN)

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Lia, si ves esto, ya está vivoo"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


def keep_alive():
    threading.Thread(target=run_web, daemon=True).start()


import dividir
import raton
import comandos

dividir.configurar(bot)
raton.configurar(bot)
comandos.configurar(bot)


# ----------------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------------
def nombre_visible(user):
    """Nombre solo para mostrar en mensajes. NUNCA usar como clave de datos."""
    return f"@{user.username}" if user.username else user.first_name


def es_admin(chat_id, user_id):
    """Devuelve (es_admin: bool, error: str|None)."""
    try:
        miembro = bot.get_chat_member(chat_id, user_id)
        return miembro.status in ("administrator", "creator"), None
    except Exception as e:
        log.exception("Error consultando get_chat_member")
        return False, str(e)


def enviar_seguro(chat_id, texto, **kwargs):
    """Envuelve bot.send_message para que un fallo de envío no tumbe el handler."""
    try:
        bot.send_message(chat_id, texto, **kwargs)
    except Exception:
        log.exception(f"No se pudo enviar mensaje a {chat_id}")


# ----------------------------------------------------------------------------
# TEMPORIZADOR DE INSCRIPCIONES
# ----------------------------------------------------------------------------
def cerrar_inscripciones(id_partida):
    """
    Recibe el id de la partida para la que se programó el timer.
    Si para cuando se dispara ya hay OTRA partida (o ninguna), no hace nada.
    Esto evita que timers de partidas viejas afecten a partidas nuevas.
    """
    log.info("TEMPORIZADOR EJECUTADO para partida %s", id_partida)

    if datos.juego.get("id") != id_partida:
        log.info("Timer obsoleto, ignorado (partida actual: %s)", datos.juego.get("id"))
        return

    if datos.juego["creada"] and not datos.juego["activa"]:
        log.info("CERRANDO INSCRIPCIONES")

        datos.juego["inscripciones_cerradas"] = True

        enviar_seguro(
            datos.grupo_juego,
            "⏰ Se acabó el tiempo de espera.\n\n(•؎ •)La ronda comenzará con los participantes actuales.",
        )


# ----------------------------------------------------------------------------
# /crearadivinanza
# ----------------------------------------------------------------------------
@bot.message_handler(commands=["crearadivinanza"])
def crear_adivinanza(message):

    if message.chat.type != "private":
        bot.reply_to(message, "(ᵕ—ᴗ—) Usa este comando por privado con el bot.")
        return

    if datos.grupo_juego is None:
        bot.reply_to(message, "(·•᷄‎ࡇ•᷅ ) No hay ninguna partida creada.")
        return

    es_admin_ok, error = es_admin(datos.grupo_juego, message.from_user.id)

    if error is not None:
        bot.reply_to(
            message,
            "⚠️ No pude verificar tus permisos en el grupo. Intenta de nuevo en unos segundos.",
        )
        return

    if not es_admin_ok:
        bot.reply_to(message, "❌ Solo los administradores pueden iniciar una partida.")
        return

    datos.admins_creando[message.from_user.id] = {"paso": "adivinanza"}

    bot.reply_to(message, "ʚଓ Escribe la adivinanza:")


@bot.message_handler(commands=["cancelaradivinanza"])
def cancelar_adivinanza(message):
    """Permite a un admin salir del flujo de creación si quedó atascado."""
    if message.chat.type != "private":
        return

    usuario = message.from_user.id

    if usuario in datos.admins_creando:
        del datos.admins_creando[usuario]
        bot.reply_to(message, "✅ Creación de adivinanza cancelada.")
    else:
        bot.reply_to(message, "No tienes ninguna creación en curso.")


@bot.message_handler(func=lambda m: m.chat.type == "private")
def recibir_datos(message):

    usuario = message.from_user.id

    if usuario not in datos.admins_creando:
        return

    if message.text is None:
        bot.reply_to(message, "Por favor envía texto.")
        return

    paso = datos.admins_creando[usuario]["paso"]

    if paso == "adivinanza":

        datos.juego["adivinanza"] = message.text

        datos.admins_creando[usuario]["paso"] = "respuesta"

        bot.reply_to(message, "( ‘• ω • `) ahora escribe la respuesta.")

    elif paso == "respuesta":

        # Sanity check: la partida podría haberse cancelado/perdido mientras
        # el admin escribía (por ejemplo si otro admin la cerró).
        if not datos.juego.get("creada"):
            del datos.admins_creando[usuario]
            bot.reply_to(message, "❌ La partida ya no existe. Operación cancelada.")
            return

        datos.juego["respuesta"] = message.text.lower().strip()

        datos.juego["activa"] = True

        del datos.admins_creando[usuario]

        bot.reply_to(message, "✅ Adivinanza guardada correctamente.")

        adivinanza = datos.juego["adivinanza"].rstrip(".!?")

        enviar_seguro(
            datos.grupo_juego,
            f"(๑>؂•̀๑) ¡Adivina el adivinador!\n\n᭝ ᨳଓ ՟ ¿{adivinanza}?",
        )

        enviar_seguro(
            datos.grupo_juego,
            "Escribe tu respuesta en este grupo.\n\n( •̀ᴗ•́ )و ¡Mucha suerte a todos los participantes!",
        )


# ----------------------------------------------------------------------------
# /adivinador
# ----------------------------------------------------------------------------
@bot.message_handler(commands=["adivinador"])
def iniciar_juego(message):

    es_admin_ok, error = es_admin(message.chat.id, message.from_user.id)

    if error is not None:
        bot.reply_to(
            message,
            "⚠️ No pude verificar tus permisos. Intenta de nuevo en unos segundos.",
        )
        return

    if not es_admin_ok:
        bot.reply_to(message, "❌ Solo los administradores pueden iniciar una partida.")
        return

    if datos.juego["creada"]:
        bot.reply_to(message, "❌ Ya hay una partida creada.")
        return

    texto = message.text.split("-")

    if len(texto) != 3:
        bot.reply_to(
            message,
            "Uso:\n/adivinador - premio - cupos\n\nEjemplo:\n/adivinador - 20 - 5",
        )
        return

    try:
        premio = int(texto[1].strip())
        cupos = int(texto[2].strip())
    except ValueError:
        bot.reply_to(message, "El premio y los cupos deben ser números.")
        return

    if premio <= 0 or cupos <= 0:
        bot.reply_to(message, "El premio y los cupos deben ser números positivos.")
        return

    if cupos > 200:
        bot.reply_to(message, "Ese número de cupos es demasiado alto.")
        return

    id_partida = str(uuid.uuid4())

    datos.juego["id"] = id_partida
    datos.juego["premio"] = premio
    datos.juego["cupos"] = cupos
    datos.juego["participantes"] = []       # lista de user_id (int)
    datos.juego["nombres"] = {}             # user_id -> nombre visible
    datos.juego["ganador"] = None
    datos.juego["activa"] = False
    datos.juego["creada"] = True
    datos.juego["inscripciones_cerradas"] = False

    datos.oportunidades = {}
    datos.eliminados = {}
    datos.avisados_eliminados = {}

    datos.grupo_juego = message.chat.id
    datos.admin_juego = message.from_user.id

    markup = InlineKeyboardMarkup()

    btn_unirse = InlineKeyboardButton("ᰔUnirse", callback_data="unirse")
    btn_salir = InlineKeyboardButton("ᰔSalir", callback_data="salir")

    markup.add(btn_unirse, btn_salir)

    bot.send_message(
        message.chat.id,
        f"""ᯓ★ ¡Juguemos al adivinador! ¡Únete! ( • ̀ω•́ )✧ 
        
𖹭 ֶָ֢. Premio: {datos.juego['premio']} robux
𖹭 ֶָ֢. Cupos: {datos.juego['cupos']}""",
        reply_markup=markup,
    )

    threading.Timer(60, cerrar_inscripciones, args=(id_partida,)).start()


# ----------------------------------------------------------------------------
# BOTONES (unirse / salir)
# ----------------------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def botones(call):

    # Ignorar interacciones que no vienen del grupo donde corre la partida.
    if datos.grupo_juego is None or call.message.chat.id != datos.grupo_juego:
        bot.answer_callback_query(call.id, "❌ No hay ninguna partida activa aquí.")
        return

    if not datos.juego["creada"]:
        bot.answer_callback_query(call.id, "❌ No hay ninguna partida activa.")
        return

    user_id = call.from_user.id
    nombre = nombre_visible(call.from_user)

    if call.data == "unirse":

        if user_id in datos.vetados:
            bot.answer_callback_query(call.id, "🚫 Has sido expulsado.")
            return

        if datos.juego["activa"]:
            bot.answer_callback_query(
                call.id, "⏳ La ronda ya comenzó. No puedes unirte ahora."
            )
            return

        if datos.juego["inscripciones_cerradas"]:
            bot.answer_callback_query(call.id, "⏳ El tiempo acabo.")
            return

        if user_id in datos.juego["participantes"]:
            bot.answer_callback_query(call.id, "Ya estas unido.")
            return

        if len(datos.juego["participantes"]) >= datos.juego["cupos"]:
            bot.answer_callback_query(call.id, "(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!")
            return

        datos.juego["participantes"].append(user_id)
        datos.juego["nombres"][user_id] = nombre

        bot.answer_callback_query(call.id, "¡Te uniste!")

        enviar_seguro(call.message.chat.id, f"✅ {nombre} se ha unido.")

        if len(datos.juego["participantes"]) == datos.juego["cupos"]:
            enviar_seguro(
                call.message.chat.id,
                "(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!\n\n⏳ Esperando que el administrador envíe la adivinanza.",
            )

    elif call.data == "salir":

        if user_id not in datos.juego["participantes"]:
            bot.answer_callback_query(call.id, "No estás participando.")
            return

        datos.juego["participantes"].remove(user_id)
        datos.juego["nombres"].pop(user_id, None)

        bot.answer_callback_query(call.id, "Has salido del juego.")

        enviar_seguro(call.message.chat.id, f"( ˶°ㅁ°) !! {nombre} salió del adivinador.")


# ----------------------------------------------------------------------------
# RESPUESTAS AL ADIVINADOR
# ----------------------------------------------------------------------------
@bot.message_handler(func=lambda m: True)
def respuesta(message):

    if message.text is None or message.text.startswith("/"):
        return

    if not datos.juego["activa"]:
        return

    # FIX CRÍTICO: sin esto, el juego respondía a mensajes en CUALQUIER chat
    # donde estuviera el bot (otros grupos, o DMs), no solo en el grupo activo.
    if message.chat.id != datos.grupo_juego:
        return

    user_id = message.from_user.id
    nombre = datos.juego["nombres"].get(user_id, nombre_visible(message.from_user))

    if user_id not in datos.juego["participantes"]:
        return

    if user_id in datos.vetados:
        enviar_seguro(message.chat.id, f"🚫 {nombre}, quedaste fuera (ᴗ_ ᴗ。).")
        return

    if user_id in datos.eliminados:

        if user_id not in datos.avisados_eliminados:
            enviar_seguro(
                message.chat.id, f"(╥﹏╥) {nombre}, ya agotaste tus oportunidades."
            )
            datos.avisados_eliminados[user_id] = True

        return

    if user_id not in datos.oportunidades:
        datos.oportunidades[user_id] = 3

    texto = message.text.lower().strip()

    if texto == datos.juego["respuesta"]:

        datos.juego["ganador"] = user_id

        datos.historial[user_id] = f"+{datos.juego['premio']} Robux"

        if user_id not in datos.historial_juegos:
            datos.historial_juegos[user_id] = []

        datos.historial_juegos[user_id].append(("Adivinador", f"+{datos.juego['premio']} Robux"))

        log.info("HISTORIAL: %s", datos.historial)

        datos.sumar_historial[user_id] = (
            datos.sumar_historial.get(user_id, 0) + datos.juego["premio"]
        )

        datos.oportunidades.pop(user_id, None)

        datos.juego["activa"] = False
        datos.juego["creada"] = False
        datos.juego["participantes"] = []

        enviar_seguro(message.chat.id, f"Pin pon ♡(੭´͈ ᐜ `͈)੭ ¡{nombre} acertó!")

        enviar_seguro(
            message.chat.id,
            f"""ꫂ❁ Ganador\n\n ✎ᝰ. {nombre}\n\n 🏆 Premio: {datos.juego['premio']} Robux\n\n 🎉 ¡Felicidades! Puedes reclamar tu premio por (DM) al finalizar el juego.""",
        )

    else:

        datos.oportunidades[user_id] -= 1

        if datos.oportunidades[user_id] == 2:
            enviar_seguro(
                message.chat.id,
                f"(｡>﹏<) {nombre}, esa no es la respuesta.\n\nಇ. Te quedan 2 oportunidades.",
            )

        elif datos.oportunidades[user_id] == 1:
            enviar_seguro(
                message.chat.id,
                f"(｡>﹏<) {nombre}, esa no es la respuesta.\n\nಇ. Te queda 1 oportunidad.",
            )

        else:
            datos.historial[user_id] = "-1 Robux"

            if user_id not in datos.historial_juegos:
                datos.historial_juegos[user_id] = []

            datos.historial_juegos[user_id].append(("Adivinador", "-1 Robux"))

            datos.sumar_historial[user_id] = datos.sumar_historial.get(user_id, 0) - 1

            datos.eliminados[user_id] = True

            enviar_seguro(
                message.chat.id,
                f"(╥﹏╥) {nombre}, agotaste tus 3 oportunidades.\n\n➜ -1 RBX.",
            )

            del datos.oportunidades[user_id]


# ----------------------------------------------------------------------------
# ARRANQUE
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    bot.remove_webhook()

    log.info("Bot iniciado...")

    keep_alive()

    bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
