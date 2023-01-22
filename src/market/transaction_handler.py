import price

def transaction_handler(socket, address):
    with socket as client_socket:
        print("client:", address)
        message_received = ['']
        running = True

        while(message_received[0] != 'end' and running):
            data =  client_socket.recv(1024)
            message_received = data.decode().split()
            print(address, message_received)
            if message_received[0] == 'price?':
                current_price = str(price.price)

                res = 'price '
                res += current_price

                client_socket.sendall(res.encode())

            elif message_received[0] == 'buy':
                current_price = str(price.price)
                quantity_asked = 0
                try:
                    quantity_asked = int(message_received[1])
                    transaction_price = price.price * quantity_asked
                    res = 'ok_buy '
                    res += str(transaction_price)
                    client_socket.sendall(res.encode())
                except Exception:
                    running = False
                    break
            
            elif message_received[0] == 'sell':
                current_price = str(price.price)
                quantity_sold = 0
                try:
                    quantity_sold = int(message_received[1])
                    transaction_price = price.price * quantity_sold
                    res = 'ok_sell '
                    res += str(transaction_price)
                    client_socket.sendall(res.encode())
                except Exception:
                    running = False
                    break
            elif message_received[0] == 'end':
                client_socket.sendall('Ending communication...'.encode())
            else:
                client_socket.sendall('Sorry, invalid command'.encode())

        print("disconnect from client:", address)

    pass