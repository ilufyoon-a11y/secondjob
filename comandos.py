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

            bot.send_message(
                message.chat.id,
                "(ᵕ—ᴗ—) El adivinador fue cancelado."
            )
            return

        # Cancelar dividir
        if datos.dividir["activa"]:

            datos.dividir["activa"] = False
            datos.dividir["inscripciones_cerradas"] = False
            datos.dividir["participantes"] = []
            datos.dividir["jugador1"] = None
            datos.dividir["jugador2"] = None
            datos.dividir["eleccion1"] = None
            datos.dividir["eleccion2"] = None
            datos.dividir["premio"] = 0
            datos.dividir["cupos"] = 0

            datos.grupo_dividir = None
            datos.admin_dividir = None

            bot.send_message(
                message.chat.id,
                "(ᵕ—ᴗ—) La partida fue cancelada."
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
        
        for jugador, total in datos.sumar_historial.items():
            
            if total > 0:
                texto += f"✿ {jugador} → +{total} Robux\n"
                
            elif total < 0:
                texto += f"✿ {jugador} → {total} Robux\n"
                
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
