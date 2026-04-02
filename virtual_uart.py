#!/usr/bin/env python3
import os
import sys
import argparse
import select
import socket
import termios

def main():
    parser = argparse.ArgumentParser(description="Virtual UART to Network Bridge (Client)")
    parser.add_argument("ip_address", help="Target TCP server IP address")
    parser.add_argument("port", type=int, help="Target TCP server port")

    args = parser.parse_args()

    # 1. Create a virtual UART (PTY)
    master, slave = os.openpty()
    slave_name = os.ttyname(slave)

    # Set slave side to raw mode
    try:
        mode = termios.tcgetattr(slave)
        mode[0] = 0 # iflag
        mode[1] = 0 # oflag
        mode[2] &= ~(termios.CSIZE | termios.PARENB | termios.CSTOPB)
        mode[2] |= (termios.CS8 | termios.CLOCAL | termios.CREAD)
        mode[3] = 0 # lflag
        termios.tcsetattr(slave, termios.TCSANOW, mode)
    except Exception as e:
        print(f"Warning: Could not configure slave terminal: {e}")

    print(f"Virtual UART created: {slave_name}")
    print(f"Connect your terminal (e.g., minicom) to {slave_name}")

    # 2. Connect to the TCP Server
    print(f"Connecting to {args.ip_address}:{args.port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((args.ip_address, args.port))
        print("Connected to network server.")
    except Exception as e:
        print(f"Failed to connect to network: {e}")
        os.close(master)
        os.close(slave)
        sys.exit(1)

    print("Bridging data. Press Ctrl+C to stop.")

    try:
        while True:
            # Monitor both the PTY master and the network socket
            r, _, _ = select.select([master, sock], [], [])

            for source in r:
                if source is master:
                    # Data from Virtual UART -> Send to Network
                    data = os.read(master, 4096)
                    if not data:
                        print("PTY closed.")
                        return
                    sock.sendall(data)
                
                elif source is sock:
                    # Data from Network -> Send to Virtual UART
                    data = sock.recv(4096)
                    if not data:
                        print("Network connection closed by server.")
                        return
                    os.write(master, data)

    except KeyboardInterrupt:
        print("\nStopping bridge...")
    finally:
        sock.close()
        os.close(master)
        os.close(slave)

if __name__ == "__main__":
    main()
