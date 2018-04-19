Snapcast Mopidy Extension
=========================

This [Mopidy] (https://www.mopidy.com) Extension adds support for [Snapcast] (https://github.com/badaix/snapcast/).

Currently a mixer 'snapcast' is implemented which uses the Snapcast JSON-RPC to control volume of a snapcast group.
In the group only activated and unmuted clients are taken into account.
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
Snapcast Server 

Examples:
- Use snapcast group with ID 'abc' of snapcastserver 'snapserver.local' on port 1234:

    [audio]
    mixer = snapcast

    [snapcast]
    enabled = true
    host = snapserver.local
    port = 1234

- Use snapcast server on localhost:1705 and automatically detect group from stream connected to output:
   
    [audio]
    mixer = snapcast
    output = audioresample ! audio/x-raw,rate=48000,channels=2,format=S16LE ! audioconvert ! wavenc ! filesink location=/tmp/snapfifo

(-> Group linked to stream which is connected to /tmp/snapfifo is used!)


Changelog
---------
v0.2 (2018-04-19):
- fixed pip problem
- changed logic in snapcast-socket.py, now also events are considered;
- changes in snapcast are now distributed as Mopidy events, e.g. volume changes

v0.1 (2018-04-02):
- Initial release

