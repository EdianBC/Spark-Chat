# Arquitectura
- Chord
- Cliente y Server
- ???

# Procesos
- ### Procesos del cliente:
- listen_for_messages
- send_pending_messages

- ### Procesos del server:
- listen_for_messages

Todos son threads

# Comunicacion
- Sockets

# Coordinacion
- A traves de una etiqueta last_update se pueden resolver conflictos, ademas se pueden usar locks para evitar que varios procesos accedan al mismo recurso a la vez

# Nombrado y localizacion
- Cada usuario tiene un username que va a ser el identificador de sus datos
- Chord con hash polinomial

# Consistencia y replicacion
- Los servers crean backups de sus datos en otros servers y les envian actualizaciones segun sea necesario

# Tolerancia a fallos
- Si hay un error con los datos se pueden restaurar gracias a los backups
- Si se envian copias a 3 o mas nodos de la red se logra el nivel de tolerancia a fallos de 2
- Chord

# Seguridad
- Ahora mismo el sistema no implementa ni autenticacion con contrasenha ni codificacion de los datos de ningun tipo, en futuras versiones si lo voy a implementar. Por lo demas como es P2P la informacion de las conversaciones se queda solo entre los usuarios implicados