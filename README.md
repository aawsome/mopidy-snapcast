Snapcast Mopidy Extension
=========================

This [Mopdidy](https://www.mopidy.com) Extension adds support for [Snapcast](https://github.com/badaix/snapcast/).

Currently a mixer 'snapcast' is implemented which uses the Snapcast JSON-RPC to control volume of a snapcast group.

The group may be configured in the configuration file or automatically detected by the pipe used as 'location=' in the audio output, see Configuration example below.

Installation
------------
To install:

    git clone https://github.com/aawsome/mopidy-snapcast.git
    sudo pip install .

PyPi distribution is coming soon...

Configuration
-------------
The extension is enabled by default.
Snapcast Server hostname/port and group ID can be given as config options.

Examples:
### Use snapcast group with ID 'abc' of snapcastserver 'snapserver.local' on port 1234:
    
    [audio]
    mixer = snapcast
    
    [snapcast]
    enabled = true
    host = snapserver.local
    port = 1234
    group_id = abc

### Use snapcast server on localhost:1705 and automatically detect group from stream connected to output:
   
    [audio]
    mixer = snapcast
    output = audioresample ! audio/x-raw,rate=48000,channels=2,format=S16LE ! audioconvert ! wavenc ! filesink location=/tmp/snapfifo
    
(-> Group linked to stream which is connected to /tmp/snapfifo is used!)

Technical Details
-----------------
The connection to the snapcast server is established in snapcast_socket.py. Here a simple implementation using socket is used and all non-answer message from the server are ignored. Should be changed in future by using [python-snapcast](https://github.com/happyleavesaoc/python-snapcast), see Roadmap

To get group volume, the relevant clients' volume is used and the mean value is calculated, as snapcast supports no group volume. Accordingly, to set the group volume, client volumes are changed in a suitable way.

In the group only activated and unmuted clients are taken into account. 


Roadmap
-------
- [ ] **PyPI distribution** Spread the module on PyPI
- [ ] **tests and error handling** Do more tests and implement better error handling
- [ ] **Clients in group** Make decission of clients (activated / muted) a config option
- [ ] **Python 3** Use as soon as Mopidy runs on Python 3, use [python-snapcast](https://github.com/happyleavesaoc/python-snapcast)
- [ ] **Snapcast group volume** Maybe use a snapcast group volume if it is supported in future, see [snapcast issue 376](https://github.com/badaix/snapcast/issues/376)

Changelog
---------
### v0.1 (2018-04-02):
- Initial release

