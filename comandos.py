import datos

bot = None

def es_admin(chat_id, user_id):
    try:
        miembro = bot.get_chat_member(chat_id, user_id)
        return miembro.status in ["administrator", "creator"]
    except Exception as e:
        print("ERROR ADMIN:", e)
        return False

def configurar(bot_recibido):
    global bot
    bot = bot_recibido
    print("COMANDOS CARGADOS")
    registrar_comandos()

def registrar_comandos():

    @bot.message_handler(commands=["participantes"])
    def participantes(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return

        participantes_actuales = []
        
        if datos.juego["creada"] or datos.juego["activa"]:
            participantes_actuales = datos.juego["participantes"]

        elif datos.dividir["activa"]:
            participantes_actuales = datos.dividir["participantes"]

        # FIX: /participantes no contemplaba la partida de Ratón, así
        # que si esa era la partida activa, el comando reportaba
        # "no hay participantes" aunque sí los hubiera.
        elif datos.raton["activa"]:
            participantes_actuales = datos.raton["participantes"]

        if not participantes_actuales:
            bot.send_message(
                message.chat.id,
                "❌ Aún no hay participantes."
            )
            return

        lista = "\n".join(participantes_actuales)

        bot.send_message(
            message.chat.id,
            f"──.ʚଓ Participantes:\n\n{lista}"
        )

    @bot.message_handler(commands=["cancelar"])
    def cancelar(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return        
        
        # Cancelar adivinador
        if datos.juego["creada"] or datos.juego["activa"]:

            datos.juego["creada"] = False
            datos.juego["activa"] = False
            datos.juego["participantes"] = []
            datos.juego["adivinanza"] = ""
            datos.juego["respuesta"] = ""
            datos.juego["inscripciones_cerradas"] = False
            datos.juego["premio"] = 0
            datos.juego["cupos"] = 0
            datos.juego["ganador"] = None

            datos.grupo_juego = None
            datos.admin_juego = None

            datos.oportunidades.clear()
            datos.eliminados.clear()
            datos.avisados_eliminados.clear()

            # Nota: el timer de cierre de inscripciones del adivinador
            # no se guarda en ninguna variable de datos.py, así que no
            # se puede cancelar desde acá. No es un problema porque
            # ese timer valida el "id" de la partida antes de actuar
            # (ver cerrar_inscripciones en adivinador_bot.py), así que
            # un timer viejo no puede afectar una partida cancelada.

            bot.send_message(
                message.chat.id,
                "(ᵕ—ᴗ—) El adivinador fue cancelado."
            )
            return

        # Cancelar dividir
        if datos.dividir["activa"]:

            # FIX: antes no se cancelaban los timers de Dividir. Si
            # timer_dividir, timer_jugador1 o timer_jugador2 llegaban
            # a dispararse después de este reset, iban a intentar
            # mandar mensajes a datos.grupo_dividir ya en None, lo
            # que revienta con una excepción.
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
            datos.dividir["iniciando_ronda"] = False
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
            datos.dividir["premio"] = 0
            datos.dividir["cupos"] = 0

            datos.grupo_dividir = None
            datos.admin_dividir = None

            bot.send_message(
                message.chat.id,
                "(ᵕ—ᴗ—) La partida fue cancelada."
            )
            return

        # FIX: /cancelar no contemplaba la partida de Ratón, así que
        # si esa era la partida activa, caía siempre al mensaje de
        # "No hay ninguna partida activa" sin poder cancelarla.
        if datos.raton["activa"]:

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

            bot.send_message(
                message.chat.id,
                "(ᵕ—ᴗ—) La partida de Ratón fue cancelada."
            )
            return

        bot.send_message(
            message.chat.id,
            "❌ No hay ninguna partida activa."
        )
            
    @bot.message_handler(commands=["sumarrbx"])
    def sumarrbx(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return
            
        if not datos.sumar_historial:
            bot.send_message(
                message.chat.id,
                "No hay nada que sumar( •̀ - • )."
            )
            return
            
        texto = "𐚁 Robux Ganados ˖ ࣪⊹\n\n"

        total = 0

        # FIX: el bucle usaba "total" como nombre de la variable de
        # iteración, pisando el acumulador, y sumaba una variable
        # "cantidad" que nunca existía (NameError garantizado). Ahora
        # se usa "cantidad" para el valor de cada jugador y "total"
        # queda libre como acumulador real.
        for jugador, cantidad in datos.sumar_historial.items():

            if cantidad > 0:
                texto += f"✿ {jugador} → +{cantidad} Robux\n"

            elif cantidad < 0:
                texto += f"✿ {jugador} → {cantidad} Robux\n"

            else:
                texto += f"✿ {jugador} → 0 Robux\n"

            total += cantidad

        texto += f"\n     ✮⋆˙ Total : {total} Robux"
      
        bot.send_message(
            message.chat.id,
            texto
        )
        
    @bot.message_handler(commands=["limpiarronda"])
    def limpiarronda(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return
            
        if not datos.historial_juegos:
            bot.send_message(
                message.chat.id,
                "❌ No hay historial que limpiar."
            )
            return

        datos.historial_juegos.clear()
        datos.historial.clear()

        bot.send_message(
            message.chat.id,
            "🗑️ El historial fue eliminado correctamente."
        )

    @bot.message_handler(commands=["banwiwi"])
    def banwiwi(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return
            
        if len(message.text.split()) != 2:
            bot.reply_to(
                message,
                "Uso:\n/banwiwi @usuario"
            )
            return

        usuario = message.text.split()[1]

        datos.vetados[usuario] = True

        if usuario in datos.juego["participantes"]:
            datos.juego["participantes"].remove(usuario)

        if usuario in datos.dividir["participantes"]:
            datos.dividir["participantes"].remove(usuario)

        # FIX: banwiwi no removía al usuario de la partida de Ratón,
        # a diferencia de juego y dividir. Quedaba vetado pero seguía
        # contando como participante activo en esa partida.
        if usuario in datos.raton["participantes"]:
            datos.raton["participantes"].remove(usuario)

        if usuario in datos.oportunidades:
            del datos.oportunidades[usuario]

        if usuario in datos.eliminados:
            del datos.eliminados[usuario]

        bot.send_message(
            message.chat.id,
            f"🚫 {usuario}, quedaste fuera (ᴗ_ ᴗ。)."
        )

    @bot.message_handler(commands=["offwiwi"])
    def offwiwi(message):        

        if message.from_user.id != datos.TU_ID:
            bot.reply_to(
                message,
                "❌ Solo el creador del bot puede usar este comando."
            )
            return

        if len(message.text.split()) != 2:
            bot.reply_to(
                message,
                "Uso:\n/offwiwi @usuario"
            )
            return

        usuario = message.text.split()[1]

        if usuario not in datos.vetados:
            bot.reply_to(
                message,
                "Ese usuario no está vetado."
            )
            return

        del datos.vetados[usuario]

        bot.send_message(
            message.chat.id,
            f"(*ᴗ͈ˬᴗ͈)ꕤ {usuario}, ya puede volver a participar."
        )

    @bot.message_handler(commands=["historialwiwi"])
    def historialwiwi(message):
        
        if not es_admin(message.chat.id, message.from_user.id):
            bot.reply_to(
                message,
                "❌ Solo los administradores pueden usar este comando."
            )
            return
            
        if not datos.historial_juegos:
            bot.send_message(
                message.chat.id,
                "(˶˃⤙˂˶) Aún no hay historial."
            )
            return

        texto = "ꫂʚɞ Historial wiwi 𓂃˖˳⋆\n\n"

        for usuario, juegos in datos.historial_juegos.items():

            texto += f"˚˖𓍢ִ໋ {usuario} → {len(juegos)} veces\n"

            for nombre, resultado in juegos:
                texto += f"   ⚝˖ {nombre} → {resultado}\n"

            texto += "\n"

        bot.send_message(
            message.chat.id,
            texto
        )
