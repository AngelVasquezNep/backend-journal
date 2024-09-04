from socket import *


PORT = 3000

def create_server():
    serversocket = socket(AF_INET, SOCK_STREAM)
    try:
        serversocket.bind(('0.0.0.0', PORT))
        serversocket.listen(5)

        while True:
            (clientsocket, address) = serversocket.accept()
            print('-' * 100)
            rd = clientsocket.recv(5000).decode()
            print(rd)
            pieces = rd.split('\n')
            
            data = "HTTP/1.1 200 OK\r\n"
            data += "Content-Type: text/html; charset=utf-8\r\n"
            data += "\r\n"
            data += "<html><body><h1>Hello world</h1><p><a href='/page2'>Page 2</a></p></body></html>\r\n\r\n"

            clientsocket.sendall(data.encode())
            clientsocket.shutdown(SHUT_WR)
            print('-' * 100)

    except KeyboardInterrupt:
        print("\nShutting down...\n")
    except Exception as e:
        print("Error:\n")
        print(e)

    serversocket.close()


print(f"Access http://localhost:{PORT}")
create_server()
