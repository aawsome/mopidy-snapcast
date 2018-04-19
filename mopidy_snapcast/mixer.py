"""Mixer that controls snapcast volume."""

from __future__ import unicode_literals

from mopidy import mixer

import pykka

from snapcast_socket import snapcast

VOLUME_METHODS = [
"Client.OnConnect",
"Client.OnDisconnect",
"Client.OnVolumeChanged",
"Server.OnUpdate",
]

MUTE_METHODS = [
"Group.OnMute",
"Server.OnUpdate",
]

class SnapcastMixer(pykka.ThreadingActor, mixer.Mixer):

    name = 'snapcast'

    def __init__(self, config):
        super(SnapcastMixer, self).__init__(config)

        self.host = config['snapcast']['host']
        self.port = config['snapcast']['port']
        
        self.group = config['snapcast']['group_id']
        if not self.group:
          import re
          m = re.search(r'location=(\S+)', config['audio']['output']) 
          if m:
            self.path = m.group(1)

        self._volume_cache = 0
        self._snap = None

    def get_volume(self):
        return self._snap.GetGroupVolume(self.group)

    def set_volume(self, volume):
        return self._snap.SetGroupVolume(self.group, volume)

    def get_mute(self):
        return self._snap.GetGroupMute(self.group)

    def set_mute(self, mute):
        if mute:
          self._snap.MuteGroup(self.group)
        else:
          self._snap.UnmuteGroup(self.group)

    def message_handler(self, method, jsonrpc, params):
        if method in VOLUME_METHODS:
	  self.trigger_volume_changed(self.get_volume())
        
	if method in MUTE_METHODS:
	  self.trigger_mute_changed(self.get_mute())

    def on_start(self):
        self._snap = snapcast(self.host, self.port, self.message_handler)
        if not self.group:
           # Get group from audio path 
           self.group = self._snap.GroupFromPath(self.path)

    def on_stop(self):
        self._snap.stop()
        self._snap = None
