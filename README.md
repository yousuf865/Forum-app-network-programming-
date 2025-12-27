# Forum App

## Overview
The program implements a **command-line forum application** using a combination of **TCP and UDP sockets** for communication between a client and server.

The forum supports:
- User authentication
- Thread creation
- Message posting
- Message removal and editing
- Uploading and downloading files to threads
- Listing threads
- Reading threads
- Logging out

The client sends commands (acceptable commands are displayed to the user) to the server, and the server responds appropriately.

The server can also handle **multiple concurrent client requests**, which is achieved through **multithreading**.

---

## Usage

| Command | Description |
|------|------------|
| `CRT <thread_title>` | Create a new thread |
| `MSG <thread_title> <message>` | Post a message to a thread |
| `DLT <thread_title> <msg_number>` | Delete a message |
| `EDT <thread_title> <msg_number> <new_msg>` | Edit a message |
| `UPD <thread_title> <filename>` | Upload a file to a thread |
| `DWN <thread_title> <filename>` | Download a file from a thread |
| `LST` | List all threads |
| `RDT <thread_title>` | Read a thread |
| `RMV <thread_title>` | Remove a thread |
| `XIT` | Logout |
