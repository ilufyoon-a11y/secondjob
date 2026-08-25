import datos
import os
import telebot
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Lia, si ves esto, ya está vivoo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

def keep_alive():
    threading.Thread(target=run_web).start()

import dividir
import raton
import comandos

dividir.configurar(bot)
raton.configurar(bot)
comandos.configurar(bot)

def cerrar_inscripciones():
    
    print("TEMPORIZADOR EJECUTADO")
    
    if datos.juego["creada"] and not datos.juego["activa"]:
        print("CERRANDO INSCRIPCIONES")
        
        datos.juego["inscripciones_cerradas"] = True
        
        bot.send_message(
            datos.grupo_juego,
            "⏰ Se acabó el tiempo de espera.\n\n(•؎ •)La ronda comenzará con los participantes actuales."
        )

@bot.message_handler(commands=["crearadivinanza"])
def crear_adivinanza(message):

    if message.chat.type != "private": 
        bot.reply_to(
          message, 
          "(ᵕ—ᴗ—) Usa este comando por privado con el bot."
        )
        return 

    if datos.grupo_juego is None:
        bot.reply_to(
            message,
            "(·•᷄‎ࡇ•᷅ ) No hay ninguna partida creada."
        )
        return
        
    try:
        miembro = bot.get_chat_member(
            datos.grupo_juego,
            message.from_user.id
        )

        if miembro.status not in ["administrator", "creator"]:
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden iniciar una partida."
            )
            return

    except Exception as e:
        print("ERROR CREAR ADIVINANZA ADMIN:", e)
        return
        
    datos.admins_creando[message.from_user.id] = {
        "paso": "adivinanza"
    }
        
    bot.reply_to(
        message,
        "ʚଓ Escribe la adivinanza:"
    )

@bot.message_handler(func=lambda m: m.chat.type == "private")
def recibir_datos(message):
    
    usuario = message.from_user.id
    
    if usuario not in datos.admins_creando:
        return

    paso = datos.admins_creando[usuario]["paso"]
    
    if paso == "adivinanza":
        
        datos.juego["adivinanza"] = message.text
        
        datos.admins_creando[usuario]["paso"] = "respuesta"

        bot.reply_to(
            message,
            "( ‘• ω • `) ahora escribe la respuesta."
        )

    elif paso == "respuesta":

        datos.juego["respuesta"] = message.text.lower().strip()
        
        datos.juego["activa"] = True 

        del datos.admins_creando[usuario]

        bot.reply_to(
            message,
            "✅ Adivinanza guardada correctamente."
        )

        adivinanza = datos.juego["adivinanza"].rstrip(".!?")

        bot.send_message(
            datos.grupo_juego,
            f"(๑>؂•̀๑) ¡Adivina el adivinador!\n\n᭝ ᨳଓ ՟ ¿{adivinanza}?"
        )
            
        bot.send_message(
            datos.grupo_juego,
            """Escribe tu respuesta en este grupo.\n\n( •̀ᴗ•́ )و ¡Mucha suerte a todos los participantes!"""
        )
 
@bot.message_handler(commands=["adivinador"])
def iniciar_juego(message):
    
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
        print("ERROR ADIVINADOR ADMIN:", e)
        return

    if datos.juego["creada"]:
        bot.reply_to(
            message,
            "❌ Ya hay una partida creada."
        )
        return
        
    texto = message.text.split("-")
    
    if len(texto) != 3:
        bot.reply_to(
            message,
            "Uso:\n/adivinador - premio - cupos\n\nEjemplo:\n/adivinador - 20 - 5"
        )
        return

    try:
        premio = int(texto[1].strip())
        cupos = int(texto[2].strip())
    except ValueError:
        bot.reply_to(message, "El premio y los cupos deben ser números."
        )
        return

    datos.juego["premio"] = premio
    datos.juego["cupos"] = cupos
    datos.juego["participantes"] = []
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

    btn_unirse = InlineKeyboardButton(
        "ᰔUnirse",
        callback_data="unirse"
    )

    btn_salir = InlineKeyboardButton(
        "ᰔSalir",
        callback_data="salir"
    )

    markup.add(btn_unirse, btn_salir)
 
    bot.send_message(
        message.chat.id,
        f"""ᯓ★ ¡Juguemos al adivinador! ¡Únete! ( • ̀ω•́ )✧ 
        
𖹭 ֶָ֢. Premio: {datos.juego['premio']} robux
𖹭 ֶָ֢. Cupos: {datos.juego['cupos']}""",
        reply_markup=markup
    )
    
    threading.Timer(60, cerrar_inscripciones).start()
       
@bot.callback_query_handler(func=lambda call: True)
def botones(call):
    
    if not datos.juego["creada"]:
        bot.answer_callback_query(
            call.id,
            "❌ No hay ninguna partida activa."
        )
        return
    
    usuario = (
        f"@{call.from_user.username}"
        if call.from_user.username
        else call.from_user.first_name
    )

    if call.data == "unirse": 

        if usuario in datos.vetados:
            bot.answer_callback_query(
                call.id,
                "🚫 Has sido expulsado."
            )
            return
        
        if datos.juego["activa"]:
            bot.answer_callback_query(
                call.id,
                "⏳ La ronda ya comenzó. No puedes unirte ahora."
            )
            return
            
        if datos.juego["inscripciones_cerradas"]:
            bot.answer_callback_query(
                call.id,
                "⏳ El tiempo acabo."
            )
            return
            
        if usuario in datos.juego["participantes"]: 
            bot.answer_callback_query(
                call.id,
                "Ya estas unido."
            )
            return

        if len(datos.juego["participantes"]) >= datos.juego["cupos"]:
            bot.answer_callback_query(
                call.id, 
                 "(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!"
            )
            return

        datos.juego["participantes"].append(usuario)

        bot.answer_callback_query(
            call.id,
            "¡Te uniste!"
        )

        bot.send_message(
            call.message.chat.id,
            f"✅ {usuario} se ha unido."
        )
        
        if len(datos.juego["participantes"]) == datos.juego["cupos"]:
            bot.send_message(
                call.message.chat.id,
                "(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!\n\n⏳ Esperando que el administrador envíe la adivinanza."
            )

    elif call.data == "salir":

        if usuario not in datos.juego["participantes"]:
            bot.answer_callback_query(
                call.id, 
                "No estás participando."
            )
            return

        datos.juego["participantes"].remove(usuario)
            
        bot.answer_callback_query(
            call.id,
            "Has salido del juego."
        )

        bot.send_message(
            call.message.chat.id,
            f"( ˶°ㅁ°) !! {usuario} salió del adivinador."
        )
                        
@bot.message_handler(func=lambda m: True)
def respuesta(message):
    
    if message.text.startswith("/"):
        return

    if not datos.juego["activa"]:
        return

    usuario = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else message.from_user.first_name
        )

    if usuario not in datos.juego["participantes"]:
        return
        
    if usuario in datos.vetados:
        bot.send_message(
            message.chat.id,
            f"🚫 {usuario}, quedaste fuera (ᴗ_ ᴗ。)."
        )
        return
        
    if usuario in datos.eliminados:
        
        if usuario not in datos.avisados_eliminados:
            bot.send_message(
                message.chat.id,
                f"(╥﹏╥) {usuario}, ya agotaste tus oportunidades."
            )
            
            datos.avisados_eliminados[usuario] = True 
            
        return
        
    if usuario not in datos.oportunidades:
        datos.oportunidades[usuario] = 3

    texto = message.text.lower().strip()

    if texto == datos.juego["respuesta"]:

        datos.juego["ganador"] = usuario

        datos.historial[usuario] = f"+{datos.juego['premio']} Robux"
        
        if usuario not in datos.historial_juegos:
            datos.historial_juegos[usuario] = []

        datos.historial_juegos[usuario].append(
            ("Adivinador", f"+{datos.juego['premio']} Robux")
        )

        print("HISTORIAL:", datos.historial)
        
        datos.sumar_historial[usuario] = (
            datos.sumar_historial.get(usuario, 0) + datos.juego["premio"]
        )

        if usuario in datos.oportunidades:
            del datos.oportunidades[usuario]

        datos.juego["activa"] = False
        datos.juego["creada"] = False
        datos.juego["participantes"] = []

        bot.send_message(
            message.chat.id,
            f"Pin pon ♡(੭´͈ ᐜ `͈)੭ ¡{usuario} acertó!"
        )

        bot.send_message(
            message.chat.id,
            f"""ꫂ❁ Ganador\n\n ✎ᝰ. {usuario}\n\n 🏆 Premio: {datos.juego['premio']} Robux\n\n 🎉 ¡Felicidades! Puedes reclamar tu premio por (DM) al finalizar el juego."""
        )

    else:

        datos.oportunidades[usuario] -= 1

        if datos.oportunidades[usuario] == 2:
            
            bot.send_message(
                message.chat.id,
                f"(｡>﹏<) {usuario}, esa no es la respuesta.\n\nಇ. Te quedan 2 oportunidades."
            )
            
        elif datos.oportunidades[usuario] == 1:
            
            bot.send_message(
                message.chat.id,
                f"(｡>﹏<) {usuario}, esa no es la respuesta.\n\nಇ. Te queda 1 oportunidad."
            )
        
        else:
            
            datos.historial[usuario] = "-1 Robux"

            if usuario not in datos.historial_juegos:
                datos.historial_juegos[usuario] = []

            datos.historial_juegos[usuario].append(
                ("Adivinador", "-1 Robux")
            )

            datos.sumar_historial[usuario] = (
                datos.sumar_historial.get(usuario, 0) - 1
            )
            
            datos.eliminados[usuario] = True
        
            bot.send_message(
                message.chat.id,
                 f"(╥﹏╥) {usuario}, agotaste tus 3 oportunidades.\n\n➜ -1 RBX."
            )
            
            del datos.oportunidades[usuario]

bot.remove_webhook()

print("Bot iniciado...")

keep_alive()

bot.infinity_polling(
    timeout=60,
    long_polling_timeout=60,
    skip_pending=True
)
