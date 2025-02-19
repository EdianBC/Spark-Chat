#!/bin/sh

# Cargar la configuración del kernel (IP forwarding)
sysctl -p

# Configurar iptables para NAT en ambas interfaces:
# Se asume que:
# - eth1 es la interfaz conectada a client_network
# - eth2 es la interfaz conectada a server_network

iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE
iptables -t nat -A POSTROUTING -o eth2 -j MASQUERADE

# Permitir el forwarding entre las dos interfaces
iptables -A FORWARD -i eth1 -o eth2 -j ACCEPT
iptables -A FORWARD -i eth2 -o eth1 -j ACCEPT

# Iniciar el script de Python en segundo plano (que reenvía broadcast UDP)
python routerplus.py &

# Mantener el contenedor en ejecución
tail -f /dev/null
