import socket
import sys
import threading
import os

CREDENTIALS_FILE = "credentials.txt"
BUFFER_SIZE = 4096
UDP_SEGMENT_SIZE = 65535
logged_in_users = set()
threads = {}
lock = threading.Lock()
SERVER_PORT = None

def load_credentials():
    credentials = {}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            for line in f:
                if line.strip():
                    username, password = line.strip().split()
                    credentials[username] = password
    return credentials

def append_credentials(username, password):
    with open(CREDENTIALS_FILE, "a") as f:
        f.write(f"{username} {password}\n")

def list_threads():
    return list(threads.keys())

def create_thread(username, title):
    with lock:
        if title in threads:
            return "Error. Thread already exists"
        with open(title, "w") as f:
            f.write(username + "\n")
        threads[title] = 0
    return "Thread created"

def post_message(username, title, message):
    with lock:
        if title not in threads:
            return "Error, thread does not exist"
        threads[title] += 1
        msg_num = threads[title]
        with open(title, "a") as f:
            f.write(f"{msg_num} {username}: {message}\n")
    return "Message posted"

def delete_message(username, title, msg_num):
    if title not in threads:
        return "Error. Thread does not exist"
    
    lines = []
    deleted = False
    with lock:
        with open(title, "r") as f:
            lines = f.readlines()

        owner_line = lines[0]
        message_lines = lines[1:]

        new_messages = []
        current_index = 1

        for line in message_lines:
            if line.startswith(f"{msg_num} {username}:") and not deleted:
                deleted = True
                continue
            elif line.strip() and line.split(' ', 1)[0].isdigit():
                parts = line.split(' ', 1)
                if len(parts) == 2 and ':' in parts[1]:
                    new_messages.append(f"{current_index} {parts[1]}")
                    current_index += 1
                else:
                    new_messages.append(line)
            else:
                new_messages.append(line)

        if not deleted:
            return "Error. Message not found or not owned by user"

        with open(title, "w") as f:
            f.write(owner_line)
            f.writelines(new_messages)

        threads[title] = len(new_messages)

    return "Message deleted"


def edit_message(username, title, msg_num, new_msg):
    if title not in threads:
        return "Error. Thread does not exist"
    
    lines = []
    edited = False
    with lock:
        with open(title, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if line.startswith(f"{msg_num} {username}:"):
                lines[i] = f"{msg_num} {username}: {new_msg}\n"
                edited = True
                break

        if not edited:
            return "Error. Message not found or not owned by user"

        with open(title, "w") as f:
            f.writelines(lines)

    return "Message edited"

def handle_client(udp_sock, addr, msg, credentials):
    global logged_in_users
    parts = msg.strip().split()
    if not parts:
        udp_sock.sendto("INVALID".encode(), addr)
        return

    command = parts[0]

    if command == "USERNAME" and len(parts) == 2:
        username = parts[1]
        with lock:
            if username in logged_in_users:
                udp_sock.sendto("IN_USE".encode(), addr)
                return
        if username in credentials:
            print(f"Login attempt from {username}")
            udp_sock.sendto("EXISTS".encode(), addr)
        else:
            print(f"Sign-up request from {username}")
            udp_sock.sendto("NEW".encode(), addr)

    elif command == "PASSWORD" and len(parts) == 3:
        username, password = parts[1], parts[2]
        if credentials.get(username) == password:
            with lock:
                logged_in_users.add(username)
            udp_sock.sendto("SUCCESS".encode(), addr)
            print(f"Logged in {username}")
        else:
            print(f"Rejected login attempt from {username}")
            udp_sock.sendto("FAIL".encode(), addr)

    elif command == "NEWUSER" and len(parts) == 3:
        username, password = parts[1], parts[2]
        with lock:
            credentials[username] = password
            logged_in_users.add(username)
        append_credentials(username, password)
        udp_sock.sendto("CREATED".encode(), addr)
        print(f"Signed up {username}")

    elif command == "XIT" and len(parts) == 2:
        username = parts[1]
        with lock:
            logged_in_users.discard(username)
        udp_sock.sendto("LOGOUT".encode(), addr)
        print(f"{username} logged out")

    elif command == "CRT" and len(parts) == 3:
        username, title = parts[1], parts[2]
        print(f"Request to create thread {title} from {username}")
        response = create_thread(username, title)
        udp_sock.sendto(response.encode(), addr)

    elif command == "LST":
        print(f"Request to list threads")
        thread_list = list_threads()
        if not thread_list:
            udp_sock.sendto("No threads exist".encode(), addr)
        else:
            print(f"Threads listed")
            udp_sock.sendto("\n".join(thread_list).encode(), addr)

    elif command == "MSG":
        username = parts[1]
        title = parts[2]
        print(f"Request to message in {title} from {username}")
        message = ' '.join(parts[3:])
        response = post_message(username, title, message)
        udp_sock.sendto(response.encode(), addr)

    elif command == "DLT":
        username, title, msg_num = parts[1], parts[2], parts[3]
        print(f"Request to delete message {msg_num} in {title} from {username}")
        response = delete_message(username, title, msg_num)
        udp_sock.sendto(response.encode(), addr)

    elif command == "EDT":
        username, title, msg_num = parts[1], parts[2], parts[3]
        print(f"Request to edit message {msg_num} in {title} from {username}")
        new_msg = ' '.join(parts[4:])
        response = edit_message(username, title, msg_num, new_msg)
        udp_sock.sendto(response.encode(), addr)

    elif command == "RDT":
        title = parts[1]
        if title not in threads:
            print(f"Error reading {title}")
            udp_sock.sendto("Error. Thread does not exist".encode(), addr)
        else:
            try:
                with lock:
                    with open(title, "r") as f:
                        lines = f.readlines()
                    content = ''.join(lines[1:]).strip()
                if not content:
                    udp_sock.sendto("Thread is empty.".encode(), addr)
                else:
                    udp_sock.sendto(content.encode(), addr)
                    print(f"{title} read")
            except Exception as e:
                print(f"Error reading {title}")
                udp_sock.sendto(f"Error reading thread: {e}".encode(), addr)

    elif command == "RMV":
        username, title = parts[1], parts[2]
        if title not in threads:
            print(f"Error removing {title}")
            udp_sock.sendto("Error. Thread does not exist".encode(), addr)
        else:
            try:
                with lock:
                    with open(title, "r") as f:
                        lines = f.readlines()
                if not lines or lines[0].strip() != username:
                    print(f"Error removing {title}")
                    udp_sock.sendto("Error. Only thread creator can remove thread".encode(), addr)
                else:
                    os.remove(title)
                    with lock:
                        del threads[title]
                        for filename in os.listdir():
                            if filename.startswith(f"{title}-"):
                                os.remove(filename)
                    udp_sock.sendto("Thread removed".encode(), addr)
                    print(f"{title} removed")
            except Exception as e:
                print(f"Error removing {title}")
                udp_sock.sendto(f"Error removing thread: {e}".encode(), addr)

    elif command == "UPD":
        username, title, filename = parts[1], parts[2], parts[3]
        thread_file = f"{title}-{filename}"

        if title not in threads:
            udp_sock.sendto("Error. Thread does not exist".encode(), addr)
            return
        if os.path.exists(thread_file):
            udp_sock.sendto("Error. File already exists".encode(), addr)
            return

        udp_sock.sendto("READY".encode(), addr)

        def receive_tcp_file(filename):
            try:
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_sock.bind(('', SERVER_PORT))
                tcp_sock.listen(1)

                conn, _ = tcp_sock.accept()
                with open(thread_file, "wb") as f:
                    while True:
                        data = conn.recv(BUFFER_SIZE)
                        if not data:
                            break
                        f.write(data)
                conn.close()
                tcp_sock.close()

                with open(title, "a") as f:
                    f.write(f"{username} uploaded {filename}\n")

                udp_sock.sendto("File uploaded successfully.".encode(), addr)
                print(f"{thread_file} uploaded from {username}")
            except Exception as e:
                print(f"Error uploading {thread_file} from {username}")
                udp_sock.sendto(f"Error receiving file: {e}".encode(), addr)
        
        threading.Thread(target=receive_tcp_file, args=(filename,)).start()

    elif command == "DWN":
        username, title, filename = parts[1], parts[2], parts[3]
        thread_file = f"{title}-{filename}"

        if title not in threads:
            udp_sock.sendto("Error. Thread does not exist".encode(), addr)
            return
        if not os.path.exists(thread_file):
            udp_sock.sendto("Error. File does not exist".encode(), addr)
            return

        udp_sock.sendto("READY".encode(), addr)

        def send_tcp_file(filename):
            try:
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tcp_sock.bind(('', SERVER_PORT)) 
                tcp_sock.listen(1)

                conn, _ = tcp_sock.accept()
                with open(thread_file, "rb") as f:
                    while True:
                        data = f.read(BUFFER_SIZE)
                        if not data:
                            break
                        conn.sendall(data)
                conn.close()
                tcp_sock.close()
                udp_sock.sendto("File downloaded successfully.".encode(), addr)
                print(f"{thread_file} downloaded to {username}")
            except Exception as e:
                print(f"Error downloading {thread_file} to {username}")
                udp_sock.sendto(f"Error sending file: {e}".encode(), addr)
            
        threading.Thread(target=send_tcp_file, args=(filename,)).start()        

    else:
        udp_sock.sendto("INVALID COMMAND".encode(), addr)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 server.py <server_port>")
        sys.exit(1)

    server_port = int(sys.argv[1])
    global SERVER_PORT
    SERVER_PORT = server_port
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("", server_port))
    print(f"Server listening on UDP port {server_port}")

    credentials = load_credentials()

    while True:
        try:
            msg, addr = udp_sock.recvfrom(UDP_SEGMENT_SIZE)
            threading.Thread(target=handle_client, args=(udp_sock, addr, msg.decode(), credentials)).start()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            break

    udp_sock.close()

if __name__ == '__main__':
    main()
