import streamlit as st
import time
import client
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# Configuración inicial del estado de la sesión
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'server_selection'
if 'chat_client' not in st.session_state:
    st.session_state.chat_client = client.chat_client()
if 'interlocutor' not in st.session_state:
    st.session_state.interlocutor = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0

def discover_servers():
    try:
        servers = st.session_state.chat_client.discover_servers()
        return servers
    except Exception as e:
        st.error(f"Error discovering servers: {e}")
        return []

def register_user(username):
    try:
        message_ip, message_port = st.session_state.chat_client.message_socket.getsockname()
        response = st.session_state.chat_client.send_command(f"REGISTER {username} {message_port}")
        if response.startswith("OK"):
            st.session_state.chat_client.set_user(username)
            return True
        return False
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False

def render_server_selection():
    st.title("✨ Spark Chat - Server Selection")
    servers = discover_servers()
    
    if not servers:
        st.warning("No servers found. Retrying...")
        time.sleep(2)
        st.experimental_rerun()
    
    for i, (name, ip) in enumerate(servers):
        if st.button(f"{name} ({ip})", key=f"server_{i}"):
            st.session_state.chat_client.connect_to_server((name, ip))
            st.session_state.current_view = 'registration'
            st.experimental_rerun()

def render_registration():
    st.title("✨ Spark Chat - Registration")
    username = st.text_input("Choose your username", max_chars=20)
    
    if st.button("Register"):
        if not username or ' ' in username or '-' in username:
            st.error("Invalid username. No spaces or hyphens allowed.")
        elif register_user(username):
            st.session_state.username = username
            st.session_state.current_view = 'main_menu'
            st.experimental_rerun()
        else:
            st.error("Username already taken")

def render_main_menu():
    st.title(f"✨ Spark Chat - Welcome {st.session_state.username}")
    
    # Mostrar mensajes no leídos
    resume = st.session_state.chat_client.db.get_unseen_resume(st.session_state.username)
    if resume:
        st.subheader("New Messages")
        for user, count in resume:
            if st.button(f"{user}: {count} new messages", key=f"chat_{user}"):
                st.session_state.interlocutor = user
                st.session_state.current_view = 'private_chat'
                st.experimental_rerun()
    else:
        st.info("No new messages")
    
    # Selección de usuario
    interlocutor = st.text_input("Start chat with user (@username)")
    if interlocutor:
        st.session_state.interlocutor = interlocutor.lstrip('@')
        st.session_state.current_view = 'private_chat'
        st.experimental_rerun()
    
    if st.button("Exit"):
        st.session_state.current_view = 'exit'
        st.experimental_rerun()

def render_private_chat():
    st.title(f"💬 Chat with {st.session_state.interlocutor}")
    
    # Cargar historial de chat
    chat = st.session_state.chat_client.load_chat(st.session_state.interlocutor)
    for msg in chat:
        with st.chat_message("user" if msg[1] != st.session_state.username else "ai"):
            st.write(f"{msg[1]}: {msg[3]}")
            st.caption(f"ID: {msg[0]} | {msg[4]}")
    
    # Actualizar mensajes nuevos periódicamente
    if time.time() - st.session_state.last_update > 2:
        unseen = st.session_state.chat_client.db.get_unseen_messages(
            st.session_state.username, 
            st.session_state.interlocutor
        )
        for msg in unseen:
            with st.chat_message("user"):
                st.write(f"{msg[1]}: {msg[3]}")
                st.caption(f"ID: {msg[0]} | {msg[4]}")
        st.session_state.chat_client.db.set_messages_as_seen(
            st.session_state.username, 
            st.session_state.interlocutor
        )
        st.session_state.last_update = time.time()
    
    # Input de mensaje
    message = st.chat_input("Type your message...")
    if message:
        if message.lower() == '/back':
            st.session_state.current_view = 'main_menu'
            st.experimental_rerun()
        else:
            msg = f"MESSAGE {st.session_state.username} {message}"
            if not st.session_state.chat_client.send_message(st.session_state.interlocutor, msg):
                st.session_state.chat_client.add_to_pending_list(st.session_state.interlocutor, msg)
            st.experimental_rerun()
    
    if st.button("Back to main menu"):
        st.session_state.current_view = 'main_menu'
        st.experimental_rerun()

# Router principal de vistas
views = {
    'server_selection': render_server_selection,
    'registration': render_registration,
    'main_menu': render_main_menu,
    'private_chat': render_private_chat,
    'exit': lambda: st.stop()
}

# Configurar auto-actualización
if st.session_state.current_view == 'private_chat':
    st_autorefresh(interval=2000, key="chat_refresh")

# Ejecutar la vista actual
current_view = views.get(st.session_state.current_view, render_server_selection)
current_view()