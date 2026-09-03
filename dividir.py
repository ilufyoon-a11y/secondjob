import datos
import random
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = None

def configurar(bot_recibido):
    global bot
    bot = bot_recibido
    print("DIVIDIR CARGADO")
    registrar_dividir()

def registrar_dividir():

    @bot.message_handler(commands=["dividir"])
    def iniciar_dividir(message):
        
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
            print("ERROR DIVIDIR ADMIN:", e)
            return
                
        if datos.dividir["activa"]:
            bot.reply_to(
                message,
                "❌ Ya hay una partida en curso."
            )
            return
            
        texto = message.text.split("-")
        
        if len(texto) != 3:
            bot.reply_to(
                message,
                "Uso:\n/dividir - premio - cupos\n\nEjemplo:\n/dividir - 20 - 6"
            )
            return
            
        try:
            premio = int(texto[1].strip())
            cupos = int(texto[2].strip())
        except ValueError:
            bot.reply_to(message,"El premio y los cupos deben ser números."
            )
            return
            
        datos.dividir["activa"] = True
        datos.dividir["inscripciones_cerradas"] = False
        datos.dividir["iniciando_ronda"] = False
        datos.dividir["premio"] = premio
        datos.dividir["cupos"] = cupos
        datos.dividir["participantes"] = []
        datos.dividir["jugador1"] = None
        datos.dividir["jugador2"] = None
        datos.dividir["eleccion1"] = None
        datos.dividir["eleccion2"] = None
        datos.dividir["elegidos"] = []
        datos.dividir["revisaron"] = []
        datos.dividir["turno_iniciado"] = False
        datos.dividir["turno2_enviado"] = False
        datos.dividir["resultado_enviado"] = False
        datos.dividir["perdio_tiempo1"] = False
        datos.dividir["perdio_tiempo2"] = False
        
        datos.grupo_dividir = message.chat.id
        datos.admin_dividir = message.from_user.id
    
        markup = InlineKeyboardMarkup()

        btn_unirse = InlineKeyboardButton(
            "ᰔUnirse",
            callback_data="dividir_unirse"
        )

        btn_salir = InlineKeyboardButton(
            "ᰔSalir",
            callback_data="dividir_salir"
        )

        markup.add(btn_unirse, btn_salir)
    
        bot.send_message(
            message.chat.id,
            f"""( ߬⚈ o⚈ꪷ)  ¡Dividir o Robar!  🎲
            
🎭 Solo dos jugadores serán elegidos...

¿Compartirán el premio,
o uno traicionará al otro?

𖹭 ֶָ֢. Premio: {premio} Robux
𖹭 ֶָ֢. Cupos: {cupos}""",
            reply_markup=markup
        )
    
        datos.timer_dividir = threading.Timer(
            60,
            iniciar_ronda_dividir
        )
        datos.timer_dividir.start()
        
    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("dividir_"))   
    def botones_dividir(call):

        # FIX: sin esto, un botón viejo de OTRO grupo (de una partida
        # anterior) podía manipular la única partida global de
        # datos.dividir, aunque fuera de un grupo distinto al de la
        # partida actual. Mismo bug que ya se corrigió en raton.py.
        if call.message.chat.id != datos.grupo_dividir:
            bot.answer_callback_query(
                call.id,
                "❌ No hay ninguna partida activa aquí."
            )
            return
        
        if not datos.dividir["activa"]:
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
        
        if call.data == "dividir_unirse":

            # FIX: raton.py ya validaba vetados al unirse, dividir.py
            # no lo hacía, así que un usuario expulsado podía seguir
            # jugando Dividir/Robar con normalidad.
            if usuario in datos.vetados:
                bot.answer_callback_query(
                    call.id,
                    "🚫 Has sido expulsado."
                )
                return
            
            if usuario in datos.dividir["participantes"]:
                bot.answer_callback_query(
                    call.id,
                    "Ya estas unido."
                )
                return
                 
            if datos.dividir["inscripciones_cerradas"]:
                bot.answer_callback_query(
                    call.id,
                    "⌛ el tiempo acabo."
                )
                return
                
            datos.dividir["participantes"].append(usuario)
            
            bot.answer_callback_query(
                call.id,
                "¡Te uniste!"
            )
                
            bot.send_message(
                call.message.chat.id,
                f"✅ {usuario} se unió."
            )
            
            if len(datos.dividir["participantes"]) >= datos.dividir["cupos"]:
            
                if datos.dividir["inscripciones_cerradas"]:
                    return
            
                datos.dividir["inscripciones_cerradas"] = True
                
                if datos.timer_dividir is not None:
                    datos.timer_dividir.cancel()
                    datos.timer_dividir = None
                
                bot.send_message(
                    call.message.chat.id,
                    "(๑˃‌ᴗ˂‌) ¡Los cupos se han llenado!\n\n🎲 La partida comenzará."
                )
                
                iniciar_ronda_dividir()
                return
                
        elif call.data == "dividir_salir":
            
            if usuario not in datos.dividir["participantes"]:
                bot.answer_callback_query(
                    call.id,
                    "No estás participando."
                )
                return
                
            datos.dividir["participantes"].remove(usuario)
            
            bot.answer_callback_query(
                call.id,
                "Has salido del juego."
            )
            
            bot.send_message(
                call.message.chat.id,
                f"( ˶°ㅁ°) !! {usuario} salió del juego."
            )
            
    def iniciar_ronda_dividir():
        
        if not datos.dividir["activa"]:
            return
            
        if datos.grupo_dividir is None:
            return
            
        if datos.dividir["iniciando_ronda"]:
            return            
            
        if datos.dividir["turno_iniciado"]:
            return
            
        datos.dividir["iniciando_ronda"] = True
        datos.dividir["inscripciones_cerradas"] = True
        
        if len(datos.dividir["participantes"]) < 2: 
            
            bot.send_message(
                datos.grupo_dividir,
                "(｡•́︿•̀｡) No hay suficientes participantes para comenzar la partida."
            )
            
            reiniciar_estado_dividir()
            return
            
        texto = "── .ꕥ Participantes:\n\n"
        
        for i, participante in enumerate(datos.dividir["participantes"], start=1):
            texto += f"{i}. {participante}\n"
            
        texto += "\n٩(๑❛ᴗ❛๑)۶ Seleccionando jugadores..."

        bot.send_message(
            datos.grupo_dividir,
            texto
        )
        
        jugadores = random.sample(datos.dividir["participantes"], 2)
        
        datos.dividir["jugador1"] = jugadores[0]
        datos.dividir["jugador2"] = jugadores[1]
        
        datos.dividir["elegidos"] = jugadores
        datos.dividir["revisaron"] = []

        # FIX: este envío por DM al admin no tenía try/except. Si el
        # admin nunca le escribió antes al bot en privado, Telegram
        # rechaza el mensaje (el bot no puede iniciar conversaciones)
        # y la excepción cortaba la función a la mitad: el botón
        # "Ver resultado" nunca se mandaba y la partida quedaba
        # colgada para siempre. Ahora se avisa en el grupo y se
        # cancela la partida de forma limpia si el DM falla.
        try:
            bot.send_message(
                datos.admin_dividir,
                f"""(૭ ｡•̀ ᵕ •́｡ )૭ Resultado secreto
        
Jugador secreto 1:
{jugadores[0]}

Jugador secreto 2:
{jugadores[1]}"""
            )
        except Exception as e:
            print("ERROR DM ADMIN DIVIDIR:", e)

            bot.send_message(
                datos.grupo_dividir,
                """⚠️ No pude enviarle el resultado secreto al
administrador por privado.

Para jugar Dividir o Robar, el administrador debe
escribirle primero al bot por DM (cualquier mensaje,
por ejemplo /start) y luego iniciar la partida de nuevo.

❌ Esta partida fue cancelada."""
            )

            reiniciar_estado_dividir()
            return

        datos.dividir["iniciando_ronda"] = False
        
        markup = InlineKeyboardMarkup()
        
        btn = InlineKeyboardButton(
            "(๑•᎑•๑) Ver resultado",
            callback_data="ver_resultado_dividir"
        )
        
        markup.add(btn)
        
        bot.send_message(
            datos.grupo_dividir,
            """ꉂ(˵˃ ᗜ ˂˵) ¡Selección terminada!
            
 Pulsa el botón para descubrir si fuiste seleccionado.""",
            reply_markup=markup
        )
        
    @bot.callback_query_handler(
        func=lambda call: call.data == "ver_resultado_dividir"
    )
    def ver_resultado_dividir(call):

        # FIX: misma validación de chat que en botones_dividir.
        if call.message.chat.id != datos.grupo_dividir:
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

        if usuario in datos.dividir["revisaron"]:
            bot.answer_callback_query(
                call.id,
                "Ya revisaste tu resultado."
            )
            return
            
        datos.dividir["revisaron"].append(usuario)
        
        if usuario == datos.dividir["jugador1"]:
            
            bot.answer_callback_query(
                call.id,
                """🎉 ¡Felicidades!
                
Fuiste seleccionado para esta ronda.

(˶ˆᗜˆ˵) Eres el Jugador secreto 1.
Prepárate para comenzar.""",
                show_alert=True
            )

        elif usuario == datos.dividir["jugador2"]:  
            
            bot.answer_callback_query(
                call.id,
                """🎉 ¡Felicidades!
                
Fuiste seleccionado para esta ronda.

(˶ˆᗜˆ˵) Eres el Jugador secreto 2.
Espera tu turno.""",
                show_alert=True
            )
            
        else:
            
            bot.answer_callback_query(
                call.id,
                """(╥ᆺ╥;)
                
Esta vez no te tocó.

¡Suerte en la próxima ronda! ✨""",
                show_alert=True
            )
            
        if (
            datos.dividir["jugador1"] in datos.dividir["revisaron"]
            and datos.dividir["jugador2"] in datos.dividir["revisaron"]
            and not datos.dividir["turno_iniciado"]
        ):
            
            datos.dividir["turno_iniciado"] = True
            
            bot.send_message(
                datos.grupo_dividir,
                """🎲 Orden de elección (•؎ •)
                
𑣲⋆ Jugador secreto 1
𑣲⋆ Jugador secreto 2

ଘ(੭˃ᴗ˂)੭ El primer jugador ya puede elegir."""
            )
            
            enviar_turno_jugador1()
            
    def enviar_turno_jugador1():
        
        markup = InlineKeyboardMarkup()
        
        btn_dividir = InlineKeyboardButton(
            "ˊᗜˋ Dividir",
            callback_data="elegir_dividir"
        )
        
        btn_robar = InlineKeyboardButton(
            "🐭 Robar",
            callback_data="elegir_robar"
        )
        
        markup.add(btn_dividir, btn_robar)
        
        bot.send_message(
            datos.grupo_dividir,
            """𑣲⋆ Jugador secreto 1..
            
Es tu turno.       

(•̀ᴗ•́ )و elige con cuidado.""",
            reply_markup=markup
        )
        
        datos.timer_jugador1 = threading.Timer(
            30,
            tiempo_jugador1
        )
        datos.timer_jugador1.start()
        
    def tiempo_jugador1():
        
        if datos.dividir["eleccion1"] is not None:
            return
            
        datos.dividir["eleccion1"] = "tiempo"
        
        enviar_turno_jugador2()
        
    def enviar_turno_jugador2():
        
        if datos.dividir["turno2_enviado"]:
            return

        datos.dividir["turno2_enviado"] = True
        
        markup = InlineKeyboardMarkup()
        
        btn_dividir = InlineKeyboardButton(
            "ˊᗜˋ Dividir",
            callback_data="elegir_dividir"
        )
        
        btn_robar = InlineKeyboardButton(
            "🐭 Robar",
            callback_data="elegir_robar"
        )
        
        markup.add(btn_dividir, btn_robar)
        
        bot.send_message(
            datos.grupo_dividir,
            """𑣲⋆ Jugador secreto 2...
            
Es tu turno.       

(•̀ᴗ•́ )و elige con cuidado.""",
            reply_markup=markup
        )
        
        datos.timer_jugador2 = threading.Timer(
            30,
            tiempo_jugador2
        )
        datos.timer_jugador2.start()
        
    def tiempo_jugador2():
        
        if datos.dividir["eleccion2"] is not None:
            return
            
        datos.dividir["eleccion2"] = "tiempo"
        
        resultado_dividir()
        
    @bot.callback_query_handler(
        func=lambda call: call.data in ["elegir_dividir", "elegir_robar"]
    )
    def elegir_opcion(call):

        # FIX: misma validación de chat que en botones_dividir.
        if call.message.chat.id != datos.grupo_dividir:
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
        
        if usuario not in [datos.dividir["jugador1"], datos.dividir["jugador2"]]:
            bot.answer_callback_query(
                call.id,
                "❌ No eres uno de los jugadores seleccionados."
            )
            return
            
        if usuario == datos.dividir["jugador1"]:
            
            if datos.dividir["eleccion1"] is not None:
                bot.answer_callback_query(
                    call.id,
                    "Ya registraste tu decisión."
                )
                return
                
            if datos.timer_jugador1 is not None:
                datos.timer_jugador1.cancel()
                datos.timer_jugador1 = None
                
            datos.dividir["eleccion1"] = (
                "dividir"
                if call.data == "elegir_dividir"
                else "robar"
            )
            
            bot.answer_callback_query(
                call.id,
                "✅ Decisión registrada."
            )
            
            bot.send_message(
                datos.grupo_dividir,
                "✅ El Jugador secreto 1 ya tomó su decisión."
            )
            
            enviar_turno_jugador2()
            return
            
        if datos.dividir["eleccion1"] is None:
             bot.answer_callback_query(
                 call.id,
                 "⏳ Aún no es tu turno."
             )
             return
        
        if datos.dividir["eleccion2"] is not None:
            bot.answer_callback_query(
                call.id,
                "Ya registraste tu decisión."
            )
            return
            
        if datos.timer_jugador2 is not None:
            datos.timer_jugador2.cancel()
            datos.timer_jugador2 = None
            
        datos.dividir["eleccion2"] = (
            "dividir"
            if call.data == "elegir_dividir"
            else "robar"
        )
        
        bot.answer_callback_query(
            call.id,
            "✅ Decisión registrada."
        )
        
        bot.send_message(
            datos.grupo_dividir,
            "✅ El Jugador secreto 2 ya tomó su decisión."
        )
        
        resultado_dividir()
            
    def resultado_dividir():
        
        if datos.dividir["resultado_enviado"]:
            return
            
        if datos.dividir["jugador1"] is None or datos.dividir["jugador2"] is None:
            return
            
        datos.dividir["resultado_enviado"] = True
        datos.dividir["turno_iniciado"] = False
        
        e1 = datos.dividir["eleccion1"]
        e2 = datos.dividir["eleccion2"] 
            
        if e1 == "tiempo" and e2 != "tiempo":
            e1 = "dividir"
            e2 = "robar"
            
        elif e2 == "tiempo" and e1 != "tiempo":
            e1 = "robar"
            e2 = "dividir"
            
        elif e1 == "tiempo" and e2 == "tiempo":
            e1 = "robar"
            e2 = "robar"

        def nombre(eleccion):
            if eleccion == "dividir":
                return "Dividir"
            elif eleccion == "robar":
                return "Robar"
            else:
                return "No respondió"
                
        nombre1 = nombre(datos.dividir["eleccion1"])
        nombre2 = nombre(datos.dividir["eleccion2"])

        mensaje = f"""˚˖𓍢ִ໋❀ ¡Resultados!
        
♪(๑ᴖ◡ᴖ๑)♪ Se revela el anonimato...

𑣲⋆ Jugador secreto 1 → {datos.dividir["jugador1"]}
𑣲⋆ Jugador secreto 2 → {datos.dividir["jugador2"]}
        
𖹭 ֶָ֢ {datos.dividir["jugador1"]} eligió {nombre1}.
𖹭 ֶָ֢ {datos.dividir["jugador2"]} eligió {nombre2}.

"""
        
        if e1 == "dividir" and e2 == "dividir":
            
            premio = datos.dividir["premio"] // 2
            
            mensaje += f"""🎉 Ambos decidieron dividir.
            
🐾 {datos.dividir["jugador1"]} gana {premio} Robux.
🐾 {datos.dividir["jugador2"]} gana {premio} Robux.""" 
            
            for jugador in [datos.dividir["jugador1"], datos.dividir["jugador2"]]:
                
                datos.historial[jugador] = f"+{premio} Robux"
                
                datos.sumar_historial[jugador] = (
                    datos.sumar_historial.get(jugador, 0) + premio
                )
                
                if jugador not in datos.historial_juegos:
                    datos.historial_juegos[jugador] = []
                    
                datos.historial_juegos[jugador].append(
                    ("Dividir", f"+{premio} Robux")
                )
                
        elif e1 == "robar" and e2 == "dividir": 
            
            ganador = datos.dividir["jugador1"]
            
            mensaje += f"""(๑•́ ᎔ ก̀๑) Uno decidió robar.
              
🐾 {datos.dividir["jugador1"]} gana {datos.dividir["premio"]} Robux."""
            
            if ganador:
                
                datos.historial[datos.dividir["jugador1"]] = f"+{datos.dividir['premio']} Robux"
                
                datos.sumar_historial[datos.dividir["jugador1"]] = (
                    datos.sumar_historial.get(datos.dividir["jugador1"], 0)
                    + datos.dividir["premio"]
                )
                
                if datos.dividir["jugador1"] not in datos.historial_juegos:
                    datos.historial_juegos[datos.dividir["jugador1"]] = []
                    
                datos.historial_juegos[datos.dividir["jugador1"]].append(
                    ("Dividir", f"+{datos.dividir['premio']} Robux")
                )
        
        elif e1 == "dividir" and e2 == "robar":
            
            ganador = datos.dividir["jugador2"]
             
            mensaje += f"""(๑•́ ᎔ ก̀๑) Uno decidió robar.
             
🐾 {datos.dividir["jugador2"]} gana {datos.dividir["premio"]} Robux."""
            
            if ganador:
                
                datos.historial[ganador] = f"+{datos.dividir['premio']} Robux"
                
                datos.sumar_historial[ganador] = (
                    datos.sumar_historial.get(ganador, 0)
                    + datos.dividir["premio"]
                )
                
                if ganador not in datos.historial_juegos:
                    datos.historial_juegos[ganador] = []
                    
                datos.historial_juegos[ganador].append(
                    ("Dividir", f"+{datos.dividir['premio']} Robux")
                )
                    
        else:
            
            mensaje += """(≖_≖ ) Ambos decidieron robar. 
            
Nadie gana el premio."""
            
        bot.send_message(
            datos.grupo_dividir,
            mensaje
        )
        
        reiniciar_estado_dividir()

    def reiniciar_estado_dividir():

        if datos.timer_dividir is not None:
            datos.timer_dividir.cancel()
            datos.timer_dividir = None

        if datos.timer_jugador1 is not None:
            datos.timer_jugador1.cancel()
            datos.timer_jugador1 = None

        if datos.timer_jugador2 is not None:
            datos.timer_jugador2.cancel()
            datos.timer_jugador2 = None

        datos.dividir["activa"] = False
        datos.dividir["inscripciones_cerradas"] = False
        datos.dividir["premio"] = 0
        datos.dividir["cupos"] = 0
        datos.dividir["participantes"] = []
        datos.dividir["jugador1"] = None
        datos.dividir["jugador2"] = None
        datos.dividir["eleccion1"] = None
        datos.dividir["eleccion2"] = None
        datos.dividir["elegidos"] = []
        datos.dividir["revisaron"] = []
        datos.dividir["turno_iniciado"] = False
        datos.dividir["turno2_enviado"] = False
        datos.dividir["resultado_enviado"] = False
        datos.dividir["perdio_tiempo1"] = False
        datos.dividir["perdio_tiempo2"] = False
        datos.dividir["iniciando_ronda"] = False
        
        datos.grupo_dividir = None
        datos.admin_dividir = None
