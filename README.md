# APRStoot
Python script for sending messages from the amateur radio Automatic Packet Reporting System (APRS) network to Mastodon.

## A brief history (because nobody really cares)
Several years ago, I created a PHP script that was able to retrieve direct messages from APRS-IS and post them to a guestbook on my website. Between 2020 and 2023, about three dozen such messages arrived, and then two things happened:
* I wanted to rewrite the script from PHP to Python.
* Because guestbooks are way too 1990s, I decided to target messages to the federated Mastodon social network.

So I considered everything I learned during that time about APRS-IS and APRStoot came into being.

## What does it do?
APRStoot connects to the selected APRS-IS server and receives all APRS messages, which are then processed according to the type:
* Direct messages to a specified HAM CALL are posted to the Mastodon account.
* Server messages are printed to stdout.
* All other messages are ignored.

## What does it also do?
The first thing I learned with the original script was that messages need to be ACKed back if the original message states so. So whenever there is an APRS message ID filled in, the script sends back an ACK.

The second thing I learned with the original script was that ACK is sometimes not enough. If the original message has been sent from a transceiver in a poor coverage area, ACK may never reach it, and then the transceiver sends the message again. And again. So ARPStoot stores all messages posted to Mastodon in a SQLite database and never toots anything from the same HAM CALL with the same message content again.

## What does it not do?
* My original script sent APRS beacons about its own existence every couple of hours, so it could be found on APRS.fi and so that I could check if it still runs. I didn't implement such functionality here (yet?).
* 2FA authentication on Mastodon is not implemented; the target account must have username/password authentication only set in preferences.

## What does it depend on?
* `socket`, `re` - no 3rd party APRS library is used because everything can be managed using one socket and one regular expression
* `sqlite3` - message storage
* `datetime` - basic date/time operations
* `hashlib` - creating message digests for deduplication
* `Mastodon.py` - posting messages to Mastodon
* `os` - checking the existence of Mastodon secret files
* `sys` - for sys.exit()
* `atexit` - cleaning up connections at the exit

## Configuration
Everything is configured directly in the script via a set of variables. All such variables have descriptions in a comment directly in the source code.
* `appname="APRSTOOT-PY"` - app name
* `appvers="1.0"` - app version
* `msgdb="./messages.db"` - sqlite3 database file for storage
* `msgtbl="APRSMSG"` - message table name
* `mycall="URCAL"` - your HAM call
* `myssid="15"` - the suffix on which the app listens for APRS message
* `mypass="URPAS"` - your APRS-IS password
* `aprsserver="euro.aprs2.net"`- APRS-IS server
* `aprsport=14580` - APRS-IS server port
* `fediserver="https://some.instance"` - your Mastodon instance
* `fediacc="some@email.address"`- your Mastodon login e-mail
* `fedipass="URFEDIPAS"` - your Mastodon password
* `fediclisec="./fedicli.secret"` - here will be the client secret stored
* `fediaccsec="./fediacc.secret"` - here will be the user secret stored
