#!/bin/sh

# Habilitar el reenvío de IP
echo "Habilitando el reenvío de IP..."
sysctl -w net.ipv4.ip_forward=1

# Limpiar reglas existentes de iptables
echo "Limpiando reglas existentes de iptables..."
iptables -F
iptables -t nat -F
iptables -X
iptables -t nat -X

# Determinar las interfaces asociadas con las redes internas
echo "Determinando interfaces de red..."
SERVER_INTERFACE=$(ip route | grep "192.168.3.0/24" | awk '{print $3}')
CLIENT_INTERFACE=$(ip route | grep "192.168.2.0/24" | awk '{print $3}')

echo "Interfaz del servidor: $SERVER_INTERFACE"
echo "Interfaz del cliente: $CLIENT_INTERFACE"

if [ -z "$SERVER_INTERFACE" ] || [ -z "$CLIENT_INTERFACE" ]; then
  echo "Error: No se pudieron determinar las interfaces de red. Saliendo."
  exit 1
fi

# Configurar reglas de reenvío entre las redes internas
echo "Configurando reglas de reenvío..."
iptables -A FORWARD -i "$CLIENT_INTERFACE" -o "$SERVER_INTERFACE" -s 192.168.2.0/24 -d 192.168.3.0/24 -j ACCEPT
iptables -A FORWARD -i "$SERVER_INTERFACE" -o "$CLIENT_INTERFACE" -s 192.168.3.0/24 -d 192.168.2.0/24 -j ACCEPT
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

# Identificar la interfaz de Internet
echo "Identificando la interfaz de Internet..."
INTERNET_INTERFACE=$(ip route | grep default | awk '{print $5}')
echo "Interfaz de Internet: $INTERNET_INTERFACE"

if [ -z "$INTERNET_INTERFACE" ]; then
  echo "Error: No se pudo determinar la interfaz de Internet. Saliendo."
  exit 1
fi

# Configurar NAT
echo "Configurando NAT para diferenciar tráfico interno e Internet..."

# --- Excluir tráfico interno de NAT ---
# Excluir tráfico multicast en puerto 10003
iptables -t nat -I POSTROUTING 1 -s 192.168.3.0/24 -p udp --dport 10003 -j RETURN
iptables -t nat -I POSTROUTING 1 -s 192.168.2.0/24 -p udp --dport 10003 -j RETURN

# Excluir tráfico interno entre las dos redes
iptables -t nat -I POSTROUTING 1 -s 192.168.3.0/24 -d 192.168.2.0/24 -j RETURN
iptables -t nat -I POSTROUTING 1 -s 192.168.2.0/24 -d 192.168.3.0/24 -j RETURN

# --- Aplicar MASQUERADE únicamente para tráfico hacia Internet ---
iptables -t nat -A POSTROUTING -o "$INTERNET_INTERFACE" -j MASQUERADE

# (Opcional) Permitir tráfico ICMP para pruebas de conectividad
echo "Permitiendo tráfico ICMP (ping)..."
iptables -A FORWARD -i "$CLIENT_INTERFACE" -o "$SERVER_INTERFACE" -p icmp -j ACCEPT
iptables -A FORWARD -i "$SERVER_INTERFACE" -o "$CLIENT_INTERFACE" -p icmp -j ACCEPT

# Mostrar reglas para depuración
echo "Reglas actuales de iptables (FILTER):"
iptables -L -v -n
echo "Reglas actuales de iptables (NAT):"
iptables -t nat -L -v -n

# Agregar ruta multicast y ejecutar proxy (ajusta según corresponda)
sleep 5
ip route add 224.0.0.0/4 dev "$SERVER_INTERFACE"
python multicast_proxy.py

# Mantener el contenedor en ejecución
echo "Configuración del router completada. Manteniendo el contenedor en ejecución..."
tail -f /dev/null