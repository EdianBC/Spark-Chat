# import streamlit as st
# import time
# import client
# from datetime import datetime

# st.set_page_config(page_title="Spark Chat", page_icon="✨", layout="wide")

# class StreamlitApp:
#     def __init__(self):
#         # Inicializamos estados solo si no existen
#         if 'server_connected' not in st.session_state:
#             st.session_state.server_connected = False
#         if 'logged_in' not in st.session_state:
#             st.session_state.logged_in = False
#         if 'client' not in st.session_state:
#             st.session_state.client = client.chat_client()
    
#     def discover_servers(self):
#         with st.container(border=True):
#             st.subheader("🔍 Buscar servidores")
#             if st.button("Buscar servidores disponibles"):
#                 servers = st.session_state.client.discover_servers()
                
#                 if servers:
#                     st.session_state.servers = servers
#                     st.rerun()
#                 else:
#                     st.error("No se encontraron servidores disponibles")

#             if 'servers' in st.session_state:
#                 server_names = [f"{name} ({ip})" for name, ip in st.session_state.servers]
#                 selected = st.selectbox("Servidores encontrados:", server_names)
                
#                 if st.button("Conectar al servidor"):
#                     server_index = server_names.index(selected)
#                     st.session_state.client.connect_to_server(
#                         st.session_state.servers[server_index]
#                     )
#                     st.session_state.server_connected = True
#                     st.success("¡Conectado al servidor!")
#                     st.rerun()

#     def login_form(self):
#         with st.form("login_form"):
#             st.subheader("🔑 Registro de usuario")
#             username = st.text_input("Nombre de usuario", key="username_input")
            
#             if st.form_submit_button("Ingresar al chat"):
#                 if username.strip() and ' ' not in username:
#                     if st.session_state.client.register_user(username):
#                         st.session_state.logged_in = True
#                         st.session_state.username = username  # Almacenamos el username en otra clave
#                         st.rerun()
#                     else:
#                         st.error("Error en el registro. Intenta con otro nombre")
#                 else:
#                     st.error("Nombre inválido. No usar espacios o caracteres especiales")


#     def get_unread_counts(self):
#         resume = st.session_state.client.db.get_unseen_resume(st.session_state.username)
#         return {user: count for user, count in resume} if resume else {}

#     def update_contacts(self):
#         unread_counts = self.get_unread_counts()
#         all_contacts = set(st.session_state.client.db.get_all_contacts(st.session_state.username))
#         all_contacts.update(unread_counts.keys())
#         st.session_state.contacts = sorted(all_contacts)

#     def display_chat(self, contact):
#         messages = st.session_state.client.load_chat(contact)
#         st.session_state.client.db.set_messages_as_seen(st.session_state.username, contact)
        
#         for msg in messages:
#             sender = msg[1]
#             with st.chat_message("human" if sender != st.session_state.username else "user"):
#                 st.markdown(f"**{sender}**" if sender != st.session_state.username else "**Tú**")
#                 st.write(msg[3])
#                 st.caption(f"{msg[4]} • ID: {msg[0]}")

#     def send_message(self, contact):
#         if prompt := st.chat_input(f"Escribe un mensaje para {contact}"):
#             message = f"MESSAGE {st.session_state.username} {prompt}"
#             if not st.session_state.client.send_message(contact, message):
#                 st.session_state.client.add_to_pending_list(contact, message)
#             st.rerun()

#     def main_interface(self):
#         self.update_contacts()
#         unread_counts = self.get_unread_counts()

#         # Sidebar
#         with st.sidebar:
#             st.header("Chats")
#             for contact in st.session_state.contacts:
#                 unread = unread_counts.get(contact, 0)
#                 badge = f" • {unread} ✉️" if unread > 0 else ""
#                 if st.button(f"{contact}{badge}", key=f"btn_{contact}"):
#                     st.session_state.selected_contact = contact
#                     st.rerun()
            
#             if st.button("🔄 Actualizar contactos"):
#                 st.rerun()
                
#             if st.button("🚪 Salir"):
#                 st.session_state.clear()
#                 st.rerun()

#         # Área principal
#         if 'selected_contact' in st.session_state and st.session_state.selected_contact:
#             st.header(f"💬 Chat con {st.session_state.selected_contact}")
#             self.display_chat(st.session_state.selected_contact)
#             self.send_message(st.session_state.selected_contact)
#         else:
#             st.info("👈 Selecciona un contacto para comenzar a chatear")

#         # Actualización automática
#         if time.time() - st.session_state.get('last_update', 0) > 2:
#             st.session_state.last_update = time.time()
#             st.rerun()

#     def run(self):
#         if not st.session_state.server_connected:
#             st.title("✨ Spark Chat - Conexión al servidor")
#             self.discover_servers()
        
#         elif not st.session_state.logged_in:
#             st.title("✨ Spark Chat - Registro de usuario")
#             self.login_form()
        
#         else:
#             self.main_interface()

# if __name__ == "__main__":
#     app = StreamlitApp()
#     app.run()









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
        # servers = st.session_state.chat_client.discover_servers()
        servers = st.session_state.chat_client.discover_servers()
        return servers
    except Exception as e:
        st.error(f"Error discovering servers: {e}")
        return []

def register_user(username):
    return st.session_state.chat_client.register_user(username)

def render_server_selection():
    st.title("✨ Spark Chat - Server Selection")
    
    if not st.session_state.chat_client.auto_connect():
        st.warning("No servers found. Retrying...")
        time.sleep(2)
        st.experimental_rerun()
        
    else:
        st.session_state.current_view = 'registration'
        st.experimental_rerun()
    
    # for i, (name, ip) in enumerate(servers):
    #     if st.button(f"{name} ({ip})", key=f"server_{i}"):
    #         st.session_state.chat_client.connect_to_server((name, ip))
    #         st.experimental_rerun()

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
    
    # if 'last_refresh' not in st.session_state:
    #     st.session_state.last_refresh = time.time()
    
    # if time.time() - st.session_state.last_refresh >= 3:
    #     st.session_state.last_refresh = time.time()
    #     st.experimental_rerun()

    # Obtener vistas previas de chats y mensajes no leídos
    chat_previews = st.session_state.chat_client.db.get_chat_previews(st.session_state.username)
    unread_resume = st.session_state.chat_client.db.get_unseen_resume(st.session_state.username)
    unread_dict = {user: count for user, count in unread_resume}
    
    if not chat_previews:
        st.markdown("---")
        st.subheader("No chats yet")
        st.info("Start a new chat by entering a username below")
    else:
        st.subheader("Your Chats")
        st.markdown("---")
        
        # Mostrar cada chat como una tarjeta clickeable
        for chat_partner, last_message in chat_previews:
            unread_count = unread_dict.get(chat_partner, 0)
            unread_badge = f"🔴 {unread_count}" if unread_count else ""
            
            # Usar columnas para el layout
            col1, col2 = st.columns([2, 5])
            with col1:
                st.markdown(f"**{chat_partner}** {unread_badge}")
            with col2:
                st.caption(last_message)
            
            # Botón invisible para hacer toda la tarjeta clickeable
            btn_key = f"chat_btn_{chat_partner}"
            if st.button(" ", key=btn_key, help="Click to open chat"):
                st.session_state.interlocutor = chat_partner
                st.session_state.current_view = 'private_chat'
                st.experimental_rerun()
            
            st.markdown("---")
    
    # Campo para nuevo chat
    with st.form("new_chat"):
        new_user = st.text_input("Start new chat with user:", placeholder="@username")
        if st.form_submit_button("Start Chat") and new_user:
            st.session_state.interlocutor = new_user.lstrip('@')
            st.session_state.current_view = 'private_chat'
            st.experimental_rerun()
    
    st.markdown("---")
    if st.button("🚪 Exit"):
        st.session_state.current_view = 'exit'
        st.experimental_rerun()

    time.sleep(1)
    st.experimental_rerun()

# def render_main_menu():
#     st.title(f"✨ Spark Chat - Welcome {st.session_state.username}")
    
#     # Configurar auto-rerun cada 3 segundos
#     if 'last_refresh' not in st.session_state:
#         st.session_state.last_refresh = time.time()
    
#     # Verificar si necesita actualizar
#     if (time.time() - st.session_state.last_refresh) > 3:  # 3 segundos
#         st.session_state.last_refresh = time.time()
#         st.experimental_rerun()
    
#     # Obtener datos actualizados
#     chat_previews = st.session_state.chat_client.db.get_chat_previews(st.session_state.username)
#     unread_resume = st.session_state.chat_client.db.get_unseen_resume(st.session_state.username)
#     unread_dict = {user: count for user, count in unread_resume}
    
#     # Lista de chats
#     if not chat_previews:
#         st.markdown("---")
#         st.subheader("No chats yet")
#         st.info("Start a new chat by entering a username below")
#     else:
#         st.subheader("Your Chats")
#         st.markdown("---")
        
#         # Mostrar cada chat con efecto de actualización
#         for chat_partner, last_message in chat_previews:
#             unread_count = unread_dict.get(chat_partner, 0)
            
#             # Crear contenedor clickeable
#             container = st.container()
#             col1, col2 = container.columns([1, 4])
            
#             with col1:
#                 st.markdown(f"**{chat_partner}** {'🔴' * min(unread_count, 3)}{'➕' if unread_count > 3 else ''}")
#             with col2:
#                 st.caption(last_message[:50] + "..." if len(last_message) > 50 else last_message)
            
#             # Hacer todo el contenedor clickeable
#             if container.button(" ", key=f"chat_{chat_partner}", help="Click to open chat"):
#                 st.session_state.interlocutor = chat_partner
#                 st.session_state.current_view = 'private_chat'
#                 st.experimental_rerun()
            
#             st.markdown("---")
    
#     # Nuevo chat con form para mejor UX
#     with st.form("new_chat_form"):
#         new_user = st.text_input("Start new chat:", placeholder="Username (without @)", key="new_chat_input")
#         if st.form_submit_button("Start New Chat") and new_user:
#             if new_user == st.session_state.username:
#                 st.error("You can't chat with yourself!")
#             else:
#                 st.session_state.interlocutor = new_user
#                 st.session_state.current_view = 'private_chat'
#                 st.experimental_rerun()
    
#     # Botón de salida con confirmación
#     if st.button("🚪 Exit"):
#         st.session_state.current_view = 'exit'
#         st.experimental_rerun()
    
#     # Añadir pequeño indicador de última actualización
#     st.markdown(f"<div style='text-align: center; color: #666; font-size: 0.8em;'>Last updated: {time.strftime('%H:%M:%S')}</div>", 
#                 unsafe_allow_html=True)


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