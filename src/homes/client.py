import socket
 
HOST = "localhost"
PORT = 1515
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))
    m = input("message> ")
    while len(m):
        client_socket.sendall(m.encode())
        data = client_socket.recv(1024)
        print("echo> ", data.decode())
        m = input("message> ")