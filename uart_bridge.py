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

def start_tcp_server(network_address, uart_connection):
    """
    Starts a TCP server and bridges data between the network and UART.
    """
    host = "0.0.0.0"
    port = int(network_address)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"TCP server listening on {host}:{port}")
    except Exception as e:
        print(f"Failed to bind TCP server: {e}")
        sys.exit(1)

    try:
        while True:
            print("\nWaiting for network connection...")
            client_socket, client_address = server_socket.accept()
            print(f"Connected by {client_address}")

            # Clear UART buffers for the new session
            clear_uart_buffers(uart_connection)

            stop_event = threading.Event()

            def uart_to_network():
                try:
                    while not stop_event.is_set():
                        if uart_connection.in_waiting > 0:
                            data = uart_connection.read(uart_connection.in_waiting)
                            if data:
                                client_socket.sendall(data)
                        else:
                            time.sleep(0.01) # Small sleep to prevent CPU hogging
                except Exception as e:
                    print(f"UART to Network error: {e}")
                finally:
                    stop_event.set()

            def network_to_uart():
                try:
                    while not stop_event.is_set():
                        data = client_socket.recv(4096)
                        if not data:
                            print("Network client disconnected.")
                            break
                        uart_connection.write(data)
                except Exception as e:
                    print(f"Network to UART error: {e}")
                finally:
                    stop_event.set()

            # Start bridging threads
            t1 = threading.Thread(target=uart_to_network, daemon=True)
            t2 = threading.Thread(target=network_to_uart, daemon=True)
            
            t1.start()
            t2.start()

            # Wait for either thread to signal a stop
            try:
                while not stop_event.is_set():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                stop_event.set()
                raise

            client_socket.close()
            print("Connection closed.")

    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

def main():
    parser = argparse.ArgumentParser(description="UART to Network Bridge")
    
    parser.add_argument("uart_port", help="UART port description (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("baudrate", type=int, help="Baudrate for the UART connection (e.g., 115200)")
    parser.add_argument("network_address", help="Network port address (e.g., 8080 or 127.0.0.1:8080)")

    args = parser.parse_args()

    # 1. Connect to UART
    uart_connection = connect_to_uart(args.uart_port, args.baudrate)

    # 2. Start TCP Server and Bridge
    start_tcp_server(args.network_address, uart_connection)

if __name__ == "__main__":
    main()
