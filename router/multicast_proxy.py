import socket
import struct
import ipaddress
from subprocess import check_output
from multiprocessing import Process

LOCAL_ADDRS = [x for x in check_output(["hostname", "-i"]).decode().strip().split(" ")]
IP_RECVORIGDSTADDR = 20
RESERVED_ADDRS = ["127.0.0.1", "192.168.2.254", "192.168.3.254"]
MIN_PORT = 10000
PROCESS_AMOUNT = 5


def proxy(port: int, read_buffer: int = 4196) -> None:
    """
    Starts a UDP proxy that listens for incoming datagrams on the specified port,
    retrieves the original destination address from ancillary data, and forwards
    multicast packets appropriately.

    This function creates a UDP socket with options enabled for address reuse
    and transparent proxying. It binds to all interfaces on the provided port and
    continuously listens for messages. Upon receiving a datagram, the function:
        - Filters out messages from reserved or local addresses and avoids duplication.
        - Extracts the original destination address from the ancillary data.
        - If the destination is a multicast address, it creates a new UDP socket with
            specific multicast options (e.g., disabling loopback, setting TTL, and specifying
            the outgoing interface) to send a discovery message based on the original datagram.

    Parameters:
            port (int): The port number on which the proxy will listen for incoming UDP datagrams.
            read_buffer (int, optional): The size of the buffer used to read data from the socket.
                                                                     Defaults to 4196 bytes.

    Raises:
            TypeError: If the extracted destination address does not belong to the IPv4 family.

    Notes:
            - The function uses system-specific socket options such as IP_RECVORIGDSTADDR and
                IP_TRANSPARENT, which may require root permissions or special system configuration.
            - The CURRENT design assumes that constants such as LOCAL_ADDRS, RESERVED_ADDRS,
                and IP_RECVORIGDSTADDR are defined in the module scope.
            - Adjust the IP used in IP_MULTICAST_IF option ("192.168.1.100") to match your network setup.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ("", port)
    sock.bind(server_address)

    # kernel support for reaching destintation addr
    sock.setsockopt(socket.IPPROTO_IP, IP_RECVORIGDSTADDR, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)

    print(f"Listening on {server_address}")

    while True:
        data, ancdata, _, address = sock.recvmsg(read_buffer, socket.MSG_CMSG_CLOEXEC)
        client_net = address[0].split(".")[2]
        primary_net = LOCAL_ADDRS[1].split(".")[2]
        # Avoid addr loops and pck duplicates
        if (
            address[0] in RESERVED_ADDRS
            or address[0] in LOCAL_ADDRS
            or client_net != primary_net
        ):
            continue

        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if data.startswith(b"DISCOVER_SERVER:"):
                continue
            if cmsg_level == socket.IPPROTO_IP and cmsg_type == IP_RECVORIGDSTADDR:
                family, port = struct.unpack("=HH", cmsg_data[0:4])
                port = socket.htons(port)

                if family != socket.AF_INET:
                    raise TypeError(f"Unsupported socket type '{family}'")

                ip = socket.inet_ntop(family, cmsg_data[4:8])
                print(
                    f"Received data {data} from {address}, original destination: {(ip, port)}"
                )
                ip_object = ipaddress.ip_address(ip)

                if ip_object.is_multicast:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)
                        # Desactivar el loopback multicast para que el paquete no se reciba de nuevo en este host
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
                        # Indica por cuál interfaz enviar el multicast (ajusta la IP según tu entorno)
                        s.setsockopt(
                            socket.IPPROTO_IP,
                            socket.IP_MULTICAST_IF,
                            socket.inet_aton("192.168.3.254"),
                        )
                        # Bindear el socket a la IP original para preservar la dirección de origen
                        try:
                            s.bind((address[0], 0))
                        except Exception as e:
                            print(f"Error al bindear a {address[0]}: {e}")
                        s.sendto(
                            (
                                "DISCOVER_SERVER"
                                + ":"
                                + str(address[0])
                                + ":"
                                + str(address[1])
                            ).encode(),
                            (ip, port),
                        )
                        print(f"Data sent to {(ip, port)}")


processes = []

for i in range(PROCESS_AMOUNT):
    p = Process(target=proxy, args=(MIN_PORT + i,))
    p.start()
    processes.append(p)

for p in processes:
    p.join()