import os
import ffmpeg
from pyrogram.types import Message
import nest_asyncio
import asyncio
from pyrogram import Client, filters
import psutil
import time
import sys
import re
import threading
from pyrogram import Client

nest_asyncio.apply()

# Paso 3: Definir tu API ID y Hash
API_ID = 'api_id'  # Reemplaza con tu api_id
API_HASH = 'api_hash'  # Reemplaza con tu api_hash
BOT_TOKEN = 'token'


# Paso 4: Crear una instancia del bot
app = Client("video_compressor_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


async def mostrar_barra_progreso(client, chat_id, mensaje_id, completado, total, velocidad, peso_original, peso_comprimido, texto_anterior):
    porcentaje = min(completado / total * 100, 100) if total else 0
    num_barras = int(porcentaje / 10)  # 10 barras de progreso
    barra = '■ ' * num_barras + '▣' * (10 - num_barras)

    message_text = (f"╔𓊈{barra}𓊉 {porcentaje:.2f}%\n"
                    f"╠➤𝗩𝗲𝗹𝗼𝗰𝗶𝗱𝗮𝗱: {velocidad:.2f} kbs\n"
                    f"╠➤𝗣𝗲𝘀𝗼 𝗼𝗿𝗶𝗴𝗶𝗻𝗮𝗹: {peso_original:.2f} MB\n"
                    f"╚➤𝗣𝗲𝗻𝗿𝗮𝗴𝗼 𝗰𝗼𝗺𝗽𝗿𝗶𝗺𝗶𝗱𝗼: {peso_comprimido:.2f} MB")

    # Solo edita el mensaje si el texto ha cambiado
    if message_text != texto_anterior:
        await client.edit_message_text(chat_id=chat_id, message_id=mensaje_id, text=message_text)
        return message_text  # Devolver el nuevo texto para comparaciones futuras
    return texto_anterior  # Devolver el texto anterior si no hubo cambios

async def comprimir_video(client, archivo_entrada, chat_id):
    nombre_original = os.path.basename(archivo_entrada)
    nombre_salida = f"{os.path.splitext(nombre_original)[0]}_A-Tv Movie.mp4"

    if not os.path.exists(archivo_entrada):
        print("El video no se descargó correctamente.")
        return None

    peso_original = os.path.getsize(archivo_entrada) / (1024 * 1024)  # En MB

    start_time = time.time()
    last_update_time = start_time  # Inicializando la última actualización al tiempo de inicio

    total_frames = None  # Inicializar variable para el total de frames
    velocidad_kbps = 0

    # Intentar obtener el número total de frames
    try:
        probe = ffmpeg.probe(archivo_entrada)
        total_frames = int(probe['streams'][0]['nb_frames']) if 'nb_frames' in probe['streams'][0] else None
    except Exception as e:
        print(f"No se pudieron obtener los frames del video: {e}")

    process = (
        ffmpeg
        .input(archivo_entrada)
        .output(nombre_salida, vf="scale=786x432,fps=30", crf=23, vcodec='libx264', audio_bitrate='64k', preset='veryfast')
        .overwrite_output()
        .global_args('-progress', 'pipe:1', '-nostats')
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )

    # Enviar el primer mensaje de progreso (al inicio)
    message = await client.send_message(chat_id=chat_id, text="Compresión en progreso...")
    mensaje_id = message.id
    texto_anterior = "Compresión en progreso..."  # Texto inicial

    frames_completados = 0  # Contador de frames completados

    while True:
        output = process.stdout.readline()
        if output == b"" and process.poll() is not None:
            break
        if output:
            # Aquí procesamos la salida para obtener el progreso
            try:
                line = output.decode('utf-8').strip()
                if line.startswith('frame='):
                    # Extraer número de frames procesados
                    frames_completados = int(line.split('=')[1].strip())

                    # Actualizar el peso comprimido
                    peso_comprimido = os.path.getsize(nombre_salida) / (1024 * 1024)  # En MB

                    # Evitar errores al dividir si total_frames es None
                    completado = frames_completados if total_frames is None else min(frames_completados, total_frames)
                    velocidad_kbps = (peso_comprimido * 1024) / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
                    # Actualiza la barra de progreso cada 10 segundos
                    current_time = time.time()
                    if current_time - last_update_time > 10:
                        last_update_time = current_time
                        texto_anterior = await mostrar_barra_progreso(
                            client, chat_id, mensaje_id, completado, total_frames, velocidad_kbps, peso_original, peso_comprimido, texto_anterior
                        )
            except Exception as e:
                print(f"Error al procesar la salida de ffmpeg: {e}")

    process.wait()
    await mostrar_barra_progreso(
        client, chat_id, mensaje_id, frames_completados, total_frames, velocidad_kbps, peso_original, peso_comprimido, texto_anterior
    )

    total_time = time.time() - start_time
    print(f"\nCompresión completada en {total_time:.2f} segundos.")

    await client.edit_message_text(chat_id=chat_id, message_id=mensaje_id, text="Compresión completada.")

    return nombre_salida

@app.on_message(filters.video)
async def handle_video(client, message: Message):
    progress_message = await client.send_message(chat_id=message.chat.id, text="📥•𝐃𝐄𝐒𝐂𝐀𝐑𝐆𝐀𝐍𝐃𝐎 𝐕𝐈𝐃𝐄𝐎•📥")

    start_time = time.time()
    video_path = await message.download()
    await client.edit_message_text(chat_id=message.chat.id, message_id=progress_message.id, text="⚙️•𝐂𝐎𝐌𝐏𝐑𝐄𝐒𝐈𝐎𝐍 𝐄𝐍 𝐏𝐑𝐎𝐂𝐄𝐒𝐎•⚙️")

    original_size = os.path.getsize(video_path)

    print("Descarga completada. Iniciando la compresión del video...")
    video_comprimido = await comprimir_video(client, video_path, message.chat.id)  # Pasar client
    if video_comprimido is None:
        print("No se pudo comprimir el video.")
        await client.send_message(chat_id=message.chat.id, text="❌ No se pudo comprimir el video.")
        await client.delete_messages(chat_id=message.chat.id, message_ids=[progress_message.id])
        return

    compressed_size = os.path.getsize(video_comprimido)
    elapsed_time = time.time() - start_time


    # Mensaje final con resultados
    resultado_text = (f"✅¡𝗖𝗢𝗠𝗣𝗥𝗘𝗦𝗜𝗢𝗡 𝗘𝗫𝗜𝗧𝗢𝗦𝗔!✅\n\n"
                      f"╔➤Tiempo Total: {elapsed_time:.2f} segundos\n"
                      f"╠➤Tamaño Original: {original_size / (1024 * 1024):.2f} MB\n"
                      f"╚➤Tamaño Comprimido: {compressed_size / (1024 * 1024):.2f} MB\n\n"
                      f"¡𝗖𝗢𝗠𝗣𝗥𝗘𝗦𝗦𝗘𝗗 𝗕𝗬! ➤ Anzel_Tech")

    # Enviar el video comprimido y el mensaje de resultado en un solo envío
    await client.send_document(chat_id=message.chat.id, document=video_comprimido, caption=resultado_text)

    await client.delete_messages(chat_id=message.chat.id, message_ids=[progress_message.id])  # Eliminar el mensaje de progreso

    # Limpiar archivos temporales
    os.remove(video_path)
    os.remove(video_comprimido)

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("¡Hola! Soy un bot para comprimir videos. Por favor, envíame un video para comenzar.")

# Paso 8: Función principal para iniciar el bot
async def main():
    async with app:
        print("✅•𝐁𝐎𝐓 𝐂𝐎𝐍𝐄𝐂𝐓𝐀𝐃𝐎 𝐄𝐗𝐈𝐓𝐎𝐒𝐀𝐌𝐄𝐍𝐓𝐄•✅")
        await asyncio.sleep(float("inf"))  # Esto mantiene el bot ejecutándose

# Ejecutar la función principal
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("El programa se detuvo de forma segura.")
