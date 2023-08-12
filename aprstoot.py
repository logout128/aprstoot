#!/usr/bin/python3
import  sqlite3, socket, hashlib, os, re, datetime, atexit
from mastodon import Mastodon

# First the constants
appname="APRSTOOT-PY"			# app name 
appvers="1.0"				# app version
msgdb="./messages.db"			# sqlite3 database file for storage
msgtbl="APRSMSG"			# message table name
mycall="URCAL"				# your HAM call
myssid="15"				# suffix on which the app listens for APRS message
mypass="URPAS"				# your APRS-IS password
aprsserver="euro.aprs2.net"		# APRS-IS server
aprsport=14580				# APRS-IS server port
fediserver="https://some.instance"	# your Mastodon instance
fediacc="some@email.address"		# your Mastodon login e-mail
fedipass="URFEDIPAS"			# your Mastodon password
fediclisec="./fedicli.secret"		# here will be client secret stored
fediaccsec="./fediacc.secret"		# here will be user secret stored

# Cleanup procedure
def cleanup():
  print("Closing socket.")
  sock.close()
  print("Closing sqlite3 connection.")
  con.close()
  print("Bye.")
  
# Opening messages database, creating message table if it does not exist
con = sqlite3.connect(msgdb)
con.execute("""CREATE TABLE IF NOT EXISTS """ + msgtbl + """ 
                (ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                TIMESTAMP DATETIME NOT NULL,
                CALLSIGN VARCHAR(16) NOT NULL,
                MESSAGE VARCHAR(256) NOT NULL,
                APRSMSGID VARCHAR(32),
                DIGEST VARCHAR(256) NOT NULL);""")
                               
# If not already registered, register app on Mastodon instance
if os.path.isfile(fediclisec) == False:
  print("App not yet registered on Mastodon instance, registering.")
  Mastodon.create_app(
    appname + ' ' + appvers,
    api_base_url = fediserver,
    to_file = fediclisec)                
else:
  print("App already registered.")

# Now logging Mastodon user account using e-mail + password
print("Logging Mastodon user account.")    
mastodon = Mastodon(client_id = fediclisec)
try:
  mastodon.log_in(
    fediacc,
    fedipass,
    to_file = fediaccsec)
except MastodonIllegalArgumentError:
  print("Incorrect account/password, or 2FA is on. This app needs it off.")
  sys.exit(1)

# New instance using access token, for future tooting
mastodon = Mastodon(access_token = fediaccsec)

# Creating socket
print("Creating socket: ", end="")
try:
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  print("OK")
except socket.error as err:
  print("failed with reason", err)
  sys.exit(1)

# Connecting to APRS-IS server
try:
  ip = socket.gethostbyname(aprsserver)
except socket.gaierror:
  print("ERROR: cannot resolve server hostname")
  sys.exit(1)
  
print("Connecting to APRS-IS server ", aprsserver, " (IP: ", ip, ") on port ", aprsport, ": ", sep="",end="")
try:
  sock.connect((ip, aprsport))
  print("OK")
except socket.timeout:
  print("timed out")
  sys.exit(1)
  
# When connected, authenticating APRS user
print("Identifying as ", mycall,"-",myssid, " with stored password: ", sep="", end="")
message="user "+mycall+"-"+myssid+" pass "+mypass+" vers "+appname+" "+appvers+" filter t/m \r\n"
try:
  sock.sendall(message.encode("Latin1"))
  print("OK")
except InterutedError:
  print("interupted")
  sys.exit(1)

# Hashlib init
hsh = hashlib.md5()

# Register cleanup procedure with atexit
atexit.register(cleanup)

# Reading and parsing APRS-IS stream
rexp = "(.*)\>.*\:\:" + mycall + "\-" + myssid + ".*\:([^\{]*)[\{]*(.*)"	# regexp for message content
print("Reading APRS-IS stream:")
while True:
  data = sock.recv(2048).decode("Latin1")
  if len(data) > 2:
    parts = re.search(rexp, data, flags=re.IGNORECASE)       
    # Message is for our user (matches regexp)
    if parts is not None:
      now = datetime.datetime.utcnow()
      fromcall = parts.group(1)
      aprsmsg = parts.group(2)
      aprsmsgid = parts.group(3)
      
      # If message has ID, then it has to be ACKed
      if aprsmsgid is not None:
        print("Sending ACK to message from " + fromcall + " with ID " + aprsmsgid + "... ", end="")
        recepient = "{:<9}".format(fromcall)
        ackmessage = mycall + "-" + myssid + ">APRS,TCPIP*::" + recepient + ":ack" + aprsmsgid + "\r\n";
        sock.sendall(ackmessage.encode("Latin1"))
        print("\t\t\tOK")
        
      # Create digest of the message           
      hsh.update(fromcall.encode("Latin1")+aprsmsg.encode("Latin1")+aprsmsgid.encode("Latin1"))
      digest = hsh.hexdigest()
     
      # Look for it in the database
      cur = con.execute("SELECT COUNT(ID) FROM " + msgtbl + " WHERE DIGEST='" + digest + "';")
      rows = cur.fetchall()

      # If the message is not in the database, then we'll process it        
      if rows[0][0] == 0:
        print(now.strftime("%Y-%m-%dT%H:%MZ"), end="")
        print(" | Callsign: " + fromcall + " | Message: " + aprsmsg + " | ID: " + aprsmsgid)     
        # Store the message as processed
        con.execute("INSERT INTO " + msgtbl + " (TIMESTAMP, CALLSIGN, MESSAGE, APRSMSGID, DIGEST) VALUES (?,?,?,?,?)", (now, fromcall, aprsmsg, aprsmsgid, digest))
        con.commit()
        # Toot the content
        mastodon.toot(fromcall + ": " + aprsmsg);
        
    # Message from server - usually ping - will be printed, other messages dropped without notice             
    elif data[0 : 1] == "#":
      print("Server message:", data, end="")    

