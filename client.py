import socket
import sys
import os
import time

RETRY_LIMIT = 5
TIMEOUT = 2

SERVER_HOST = '127.0.0.1'
UDP_PORT = int(sys.argv[1])
BUFFER_SIZE = 65535
server_address = (SERVER_HOST, UDP_PORT)

def udp_send_receive(sock, msg):
    ## implement reliability for other udp sends
    sock.settimeout(TIMEOUT)
    for attempt in range(RETRY_LIMIT):
        try:
            sock.sendto(msg.encode(), server_address)
            response, _ = sock.recvfrom(BUFFER_SIZE)
            return response.decode()
        except socket.timeout:
            print(f"Timeout, retrying... ({attempt + 1})")
    return "Error. No response from server"

def tcp_upload(filename):
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        for i in range(10):
            try:
                tcp_sock.connect(server_address)
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        else:
            print("Error. Couldn't connect to server")
            return
        
        with open(filename, 'rb') as f:
            while True:
                data = f.read(1024)
                if not data:
                    break
                tcp_sock.sendall(data)
        tcp_sock.close()
        print("File uploaded successfully.")
    except Exception as e:
        print("Error uploading file:", e)

def tcp_download(filename):
    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for i in range(10):
            try:
                tcp_sock.connect(server_address)
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        else:
            print("Error. Couldn't connect to server")
            return

        with open(filename, 'wb') as f:
            while True:
                data = tcp_sock.recv(1024)
                if not data:
                    break
                f.write(data)
        tcp_sock.close()
        print("File downloaded successfully.")
    except Exception as e:
        print("Error downloading file:", e)

def display_menu():
    """
    Display the available commands
    """
    print("\n===== Available Commands =====")
    print("CRT MSG DLT EDT LST RDT UPD DWN RMV XIT \n")

def main():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    username = None

    while not username:
        uname = input("Enter username: ")
        response = udp_send_receive(udp_sock, f"USERNAME {uname}")

        if response == "EXISTS":
            while True:
                pw = input("Enter password: ")
                response = udp_send_receive(udp_sock, f"PASSWORD {uname} {pw}")
                print(response)
                if response == "SUCCESS":
                    username = uname
                    break
                elif response == "FAIL":
                    break

        elif response == "IN_USE":
            print("This username is in use, please try a different username.")

        elif response == "NEW":
            print(response)
            pw = input("Create password: ")
            response = udp_send_receive(udp_sock, f"NEWUSER {uname} {pw}")
            print(response)
            if response == "CREATED":
                username = uname

    display_menu()

    while True:
        cmd = input("Enter command: ")
        if not cmd:
            continue
        parts = cmd.strip().split()
        command = parts[0].upper()

        if command == "XIT":
            if len(parts) != 1:
                print("Invalid Command")
                continue

            print(udp_send_receive(udp_sock, f"XIT {username}"))
            break

        elif command == "UPD":
            if len(parts) != 3 or not parts[1] or not parts[2]:
                print("Invalid Command")
                continue

            thread, filename = parts[1], parts[2]
            if os.path.exists(filename):
                response = udp_send_receive(udp_sock, f"UPD {username} {thread} {filename}")
                print(response)
                if response == "READY":
                    tcp_upload(filename)
            else:
                print("File not found.")

        elif command == "DWN":
            if len(parts) != 3 or not parts[1] or not parts[2]:
                print("Invalid Command")
                continue

            thread, filename = parts[1], parts[2]
            response = udp_send_receive(udp_sock, f"DWN {username} {thread} {filename}")
            print(response)
            if response.startswith("READY"):
                tcp_download(filename)

        elif command == "CRT":
            if len(parts) != 2 or not parts[1]:
                print("Invalid Command")
                continue
            
            print(udp_send_receive(udp_sock, f"CRT {username} {parts[1]}"))

        elif command == "LST":
            if len(parts) != 1:
                print("Invalid Command")
                continue

            response = udp_send_receive(udp_sock, "LST")
            if response.strip() == "":
                print("No active threads.")
            else:
                print("Active threads:")
                for line in response.strip().split('\n'):
                    print(line)

        elif command == "MSG":
            if len(parts) < 3 or not parts[1] or not parts[2]:
                print("Invalid Command")
                continue

            thread_title = parts[1]
            message = ' '.join(parts[2:])
            response = udp_send_receive(udp_sock, f"MSG {username} {thread_title} {message}")
            print(response)

        elif command == "DLT":
            if len(parts) != 3 or not parts[1] or not parts[2]:
                print("Invalid Command")
                continue

            thread_title = parts[1]
            message_number = parts[2]
            response = udp_send_receive(udp_sock, f"DLT {username} {thread_title} {message_number}")
            print(response)

        elif command == "EDT":
            if len(parts) < 4 or not parts[1] or not parts[2] or not parts[3]:
                print("Invalid Command")
                continue

            thread_title = parts[1]
            message_number = parts[2]
            new_message = ' '.join(parts[3:])
            response = udp_send_receive(udp_sock, f"EDT {username} {thread_title} {message_number} {new_message}")
            print(response)

        elif command == "RDT":
            if len(parts) != 2 or not parts[1]:
                print("Invalid Command")
                continue

            thread_title = parts[1]
            response = udp_send_receive(udp_sock, f"RDT {thread_title}")
            print(response)

        elif command == "RMV":
            if len(parts) != 2 or not parts[1]:
                print("Invalid Command")
                continue

            thread_title = parts[1]
            response = udp_send_receive(udp_sock, f"RMV {username} {thread_title}")
            print(response)

        else:
            print("Invalid command")

        display_menu()

    udp_sock.close()

if __name__ == '__main__':
    main()
