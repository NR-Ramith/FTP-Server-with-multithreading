# Import libraries
import socket   # For network communication
import sys  # For system-related functions
import time # For timing operations
import os   # For file and directory operations
import struct   # For packing and unpacking binary data
import threading    # For threading

print("\nWelcome to the FTP server.\n\nWaiting for a connection")

# Initialize socket details
TCP_PORT = 1456 # Just a random choice | It can be anything in between 0-65535 except reserved ones
BUFFER_SIZE = 1024 # Standard size 1024 bytes | If more data is to be sent or recieved, it will be done in chunks of 1024 bytes
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # IPv4 , TCP
s.bind((socket.gethostname(), TCP_PORT))    # Binds socket to a specific port
s.listen() # Listens to 1 client connection
# conn, addr = s.accept()
clientconn = threading.local()  # Creating local variable for each thread
clientconn.conn = None
clientconn.addr = None
# print("\nConnected to by address: {}".format(addr))

users=[[b"RAMITH",b"RAM"],[b"PRANAV",b"PRA"],[b"KISHAN",b"KIS"]]  # Username, Password

def upld():
    # Send message once server is ready to recieve file details
    clientconn.conn.send(b"1")
    # Recieve file name length, then file name
    file_name_size = struct.unpack("h", clientconn.conn.recv(2))[0]
    file_name = clientconn.conn.recv(file_name_size)
    # Send message to let client know server is ready for document content
    clientconn.conn.send(b"1")
    # Recieve file size
    file_size = struct.unpack("i", clientconn.conn.recv(4))[0]
    # Initialise and enter loop to recive file content
    start_time = time.time()
    output_file = open(file_name, "wb")
    # This keeps track of how many bytes we have recieved, so we know when to stop the loop
    bytes_recieved = 0
    print("\nRecieving...")
    while bytes_recieved < file_size:
        l = clientconn.conn.recv(BUFFER_SIZE)
        output_file.write(l)
        bytes_recieved += BUFFER_SIZE
    output_file.close()
    print("\nRecieved file: {}".format(file_name))
    # Send upload performance details
    clientconn.conn.send(struct.pack("f", time.time() - start_time))
    clientconn.conn.send(struct.pack("i", file_size))
    return

def list_files():
    print("Listing files...")
    # Get list of files in directory
    listing = os.listdir(os.getcwd())
    # Send over the number of files, so the client knows what to expect (and avoid some errors)
    clientconn.conn.send(struct.pack("i", len(listing)))
    total_directory_size = 0
    # Send over the file names and sizes whilst totaling the directory size
    for i in listing:
        # File name size
        clientconn.conn.send(struct.pack("i", sys.getsizeof(i)))
        # File name
        clientconn.conn.send(bytes(i, encoding='ascii'))
        # File content size
        clientconn.conn.send(struct.pack("i", os.path.getsize(i)))
        total_directory_size += os.path.getsize(i)
        # Make sure that the client and server are syncronised
        clientconn.conn.recv(BUFFER_SIZE)
    # Sum of file sizes in directory
    clientconn.conn.send(struct.pack("i", total_directory_size))
    #Final check
    clientconn.conn.recv(BUFFER_SIZE)
    print("Successfully sent file listing")
    return

def dwld():
    clientconn.conn.send(b"1")
    file_name_length = struct.unpack("h", clientconn.conn.recv(2))[0]
    print (file_name_length)
    file_name = clientconn.conn.recv(file_name_length)
    print (file_name)
    if os.path.isfile(file_name):
        # Then the file exists, and send file size
        clientconn.conn.send(struct.pack("i", os.path.getsize(file_name)))
    else:
        # Then the file doesn't exist, and send error code
        print("File name not valid")
        clientconn.conn.send(struct.pack("i", -1))
        return
    # Wait for ok to send file
    clientconn.conn.recv(BUFFER_SIZE)
    # Enter loop to send file
    start_time = time.time()
    print("Sending file...")
    content = open(file_name, "rb")
    # Again, break into chunks defined by BUFFER_SIZE
    l = content.read(BUFFER_SIZE)
    while l:
        clientconn.conn.send(l)
        l = content.read(BUFFER_SIZE)
    content.close()
    # Get client go-ahead, then send download details
    clientconn.conn.recv(BUFFER_SIZE)
    clientconn.conn.send(struct.pack("f", time.time() - start_time))
    return


def delf():
    # Send go-ahead
    clientconn.conn.send(b"1")
    # Get file details
    file_name_length = struct.unpack("h", clientconn.conn.recv(2))[0]
    file_name = clientconn.conn.recv(file_name_length)
    # Check file exists
    if os.path.isfile(file_name):
        clientconn.conn.send(struct.pack("i", 1))
    else:
        # Then the file doesn't exist
        clientconn.conn.send(struct.pack("i", -1))
    # Wait for deletion conformation
    confirm_delete = clientconn.conn.recv(BUFFER_SIZE)
    if confirm_delete == (b"Y"):
        try:
            # Delete file
            os.remove(file_name)
            clientconn.conn.send(struct.pack("i", 1))
        except:
            # Unable to delete file
            print("Failed to delete {}".format(file_name))
            clientconn.conn.send(struct.pack("i", -1))
    else:
        # User abandoned deletion
        # The server probably recieved "N", but else used as a safety catch-all
        print("Delete abandoned by client!")
        return

def user_authentication():
    # Send message once server is ready to recieve user details
    clientconn.conn.send(b"1")
    # Recieve user name
    user_name_size = struct.unpack("h", clientconn.conn.recv(2))[0]
    user_name = clientconn.conn.recv(user_name_size)
    # Send message to let client know username received
    clientconn.conn.send(b"1")
    passwd_size = struct.unpack("h", clientconn.conn.recv(2))[0]
    passwd = clientconn.conn.recv(passwd_size)
    # Send message to let client know password received
    clientconn.conn.send(b"1")
    #Check if user name exsits
    num=0
    for user in users:
        if(user_name==user[0] and passwd==user[1]):
            num=1
            clientconn.conn.send(struct.pack("i", num))
            break
    if num==0:
        clientconn.conn.send(struct.pack("i", num))

def quit():
    # Send quit conformation
    clientconn.conn.send(b"1")
    # Close and restart the server
    clientconn.conn.close()
    # os.execl(sys.executable, sys.executable, *sys.argv)

def handle_client(conn, addr):
    clientconn.conn=conn
    clientconn.addr=addr
    while True:
        # Enter into a while loop to recieve commands from client
        print("\n\nWaiting for instruction from address: {}".format(clientconn.addr))
        data = conn.recv(BUFFER_SIZE)
        print("\nRecieved instruction: {} from address: {}".format(data, clientconn.addr))
        # Check the command and respond correctly
        if data == b"UPLD":
            upld()
        elif data == b"LIST":
            list_files()
        elif data == b"DWLD":
            dwld()
        elif data == b"DELF":
            delf()
        elif data == b"USER":
            user_authentication()
        elif data == b"QUIT":
            quit()
            break
        # Reset the data to loop
        data = None

def start_server():
    try:
        while True:
            # Accept incoming connections
            conn, addr = s.accept()
            print("\nConnected to by address: {}".format(addr))

            # Create a new thread for each client connection
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

            # Check if the client is done and join the thread
            # if not client_thread.is_alive():
            #     client_thread.join()
    finally:
        s.close()

start_server()