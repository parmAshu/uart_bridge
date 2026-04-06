#!/usr/bin/env python3
import argparse
import sys
import socket
import threading
import time

def connect_to_uart(port, baudrate):
    """
    Initializes a connection to the specified UART port.
    """
    try:
        import serial
    except ImportError:
        print("Error: The 'pyserial' library is not installed. Install it with: pip install pyserial")
        sys.exit(1)

    print(f"Connecting to UART Port: {port} at {baudrate} baud...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=0.1)
        if ser.is_open:
            print(f"Successfully connected to {port}")
            return ser
    except serial.SerialException as e:
        print(f"Failed to connect to UART: {e}")
        sys.exit(1)

def clear_uart_buffers(uart_connection):
    """
    Clears the input and output buffers of the UART connection.
    """
    print("Clearing UART buffers...")
    uart_connection.reset_input_buffer()
    uart_connection.reset_output_buffer()

def start_udp_server(network_address, uart_connection):
    """
    Starts a UDP server and bridges data between the network and UART.
    """
    host = "0.0.0.0"
    port = int(network_address)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        server_socket.bind((host, port))
        print(f"UDP server listening on {host}:{port}")
    except Exception as e:
        print(f"Failed to bind UDP server: {e}")
        sys.exit(1)

    last_client_address = None
    lock = threading.Lock()

    def uart_to_network():
        nonlocal last_client_address
        try:
            while True:
                if uart_connection.in_waiting > 0:
                    data = uart_connection.read(uart_connection.in_waiting)
                    if data:
                        with lock:
                            if last_client_address:
                                server_socket.sendto(data, last_client_address)
                else:
                    time.sleep(0.01) # Small sleep to prevent CPU hogging
        except Exception as e:
            print(f"UART to Network error: {e}")

    def network_to_uart():
        nonlocal last_client_address
        try:
            while True:
                data, addr = server_socket.recvfrom(4096)
                with lock:
                    if addr != last_client_address:
                        print(f"Receiving data from new client: {addr}")
                        last_client_address = addr
                uart_connection.write(data)
        except Exception as e:
            print(f"Network to UART error: {e}")

    # Start bridging threads
    t1 = threading.Thread(target=uart_to_network, daemon=True)
    t2 = threading.Thread(target=network_to_uart, daemon=True)
    
    t1.start()
    t2.start()

    print("Bridging data. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

def main():
    parser = argparse.ArgumentParser(description="UART to UDP Network Bridge")
    
    parser.add_argument("uart_port", help="UART port description (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("baudrate", type=int, help="Baudrate for the UART connection (e.g., 115200)")
    parser.add_argument("network_address", help="Network port address (e.g., 8080)")

    args = parser.parse_args()

    # 1. Connect to UART
    uart_connection = connect_to_uart(args.uart_port, args.baudrate)

    # 2. Start UDP Server and Bridge
    start_udp_server(args.network_address, uart_connection)

if __name__ == "__main__":
    main()
