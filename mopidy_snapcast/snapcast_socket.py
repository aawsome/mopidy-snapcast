from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)
import socket, select, json
import threading 
from operator import itemgetter

CLIENT_CONNECT_CHANGES = [
"Client.OnConnect",
"Client.OnDisconnect",
]
CLIENT_VOLUME_CHANGES = [
"Client.OnVolumeChanged", 
]
CLIENT_CHANGES = [
"Client.OnLatencyChanged",
"Client.OnNameChanged",
]
GROUP_CHANGES = [
"Group.OnMutet",
"Group.OnStreamChanged",
]
SERVER_CHANGES = [
"Server.OnUpdate",
]

def distribute_volume(clients, sum_to_distribute):
    """ Helper function to distribute volume changes to clients.
        sum_to_distribute may be positive or negative """

    client_count = len(clients)
    client_sum = sum([client['old_volume'] for client in clients])
    clients.sort(key = itemgetter('old_volume'), reverse=(True if sum_to_distribute > 0 else False) )

    for client in clients:
      if client_sum == 0:
        value = sum_to_distribute // client_count
      else:
        value = sum_to_distribute * client['old_volume'] // client_sum

      if client['old_volume'] + value >= 100:
        sum_to_distribute += client['old_volume'] - 100
        client['new_volume'] = 100
      elif client['old_volume'] + value <= 0:
        sum_to_distribute += client['old_volume']
        client['new_volume'] = 0
      else:
        sum_to_distribute -= value
        client['new_volume'] = client['old_volume'] + value

      client_count -= 1
      client_sum -= client['old_volume']


class snapcast(object):
  def __init__(self, host, port, message_handler=None):
    # connect to remote host
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect((host, port))

    self.message_handler = message_handler
    self.socket = s
    self.msgid = 1
    self.message = {}
    self.gotmessage = threading.Event()
    thread = threading.Thread(target=self.getmessage)
    thread.setDaemon(True)
    thread.start()

    self.server = self.sendmessage('Server.GetStatus')['server']
 
  def stop(self):
    self.socket.close()
     
  def sendmessage(self, method, params=None):
    msg = { "id":self.msgid,"jsonrpc":"2.0","method": method }
    if params:
      msg['params'] = params
    socketmsg = json.dumps(msg) + "\r\n"
    select.select([],[self.socket],[])
    self.socket.send(socketmsg)
    self.gotmessage.wait()

    self.msgid += 1
    return self.message['result']

  def getmessage(self):
    while True:
      self.gotmessage.clear()
      select.select([self.socket],[],[])
      data = ''
      while len(data) == 0 or data[-1] != "\n":
        data += self.socket.recv(1)

      try:
        my_data = json.loads(data)
      except ValueError:
        raise ValueError(data)

      if 'id' in my_data:
	if my_data['id'] == self.msgid:
	   self.message = my_data 
           self.gotmessage.set()
	else:
           raise ValueError(my_data)
      else:
           self.handle_message(**my_data)

  def handle_message(self, method, jsonrpc, params):
    if method in CLIENT_VOLUME_CHANGES:
      client = self._GetClient(params['id'])
      if client:
         client['config']['volume'].update(params['volume'])
    elif method in CLIENT_CONNECT_CHANGES:
      client = self._GetClient(params['id'])
      if client:
         client['config'].update(params['client'])
    elif method in CLIENT_CHANGES:
      client = self._GetClient(params['id'])
      if client:
         client.update(params)
    elif method in GROUP_CHANGES:
      group = self._GetGroup(params['id'])
      if group:
         group.update(params)
      else:
         self.server['groups'].append(params)
    elif method in SERVER_CHANGES:
      self.server = params['server']

    if self.message_handler:
      self.message_handler(method, jsonrpc, params)
  
  def _GetClient(self, client_id):
    for group in self.server['groups']:
      for client in group['clients']:
        if client['id'] == client_id:
           return client

  def _SetClientVolume(self, client_id, key, value):
    client = self._GetClient(client_id)
    if client['config']['volume'][key] == value:
        return True
    else:
        client['config']['volume'][key] = value
        return self.sendmessage('Client.SetVolume', {'id': client_id, 'volume': {key : value}})
    
  def MuteClient(self, client_id):
    return self._SetClientVolume(client_id, 'muted', True)

  def UnmuteClient(self, client_id):
    return self._SetClientVolume(client_id, 'muted', False)
  
  def SetClientVolume(self, client_id, volume):
    return self._SetClientVolume(client_id, 'percent', volume)
  
  def _GetGroup(self, group_id):
    for group in self.server['groups']:
      if group['id'] == group_id:
         return group

  def GetGroupMute(self, group_id):
    mygroup = self._GetGroup(group_id)
    return mygroup['muted']
  
  def _MuteGroup(self, group_id, value):
    mygroup = self._GetGroup(group_id)
    if mygroup['mute'] == value:
       return True
    else: 
       mygroup['mute'] = value
       return self.sendmessage('Group.SetMute', {'id': group_id, 'mute': value})
  
  def MuteGroup(self, group_id):
    return self._MuteGroup(group_id, True)

  def UnmuteGroup(self, group_id):
    return self._MuteGroup(group_id, False)

  def GroupFromPath(self, path):
    for stream in self.server['streams']:
      if stream['uri']['path'] == path :
        for group in self.server['groups']:
          if group['stream_id'] ==  stream['id']:
            return group['id']

  def ActiveClientsFromGroup(self, GroupID):
    group = self._GetGroup(GroupID)
    ClientIDs = []
    for client in group['clients']:
      if client['connected'] and not client['config']['volume']['muted']:
        ClientIDs.append(client['id'])

  def MuteClientsInGroup(self, GroupID):
    for ClientID in self.ActiveClientsFromGroup(GroupID):
      self.MuteClient(ClientID)

  def ExclusiveClientInGroup(self, my_client, GroupID):
    self.UnmuteGroup(GroupID)
    ActiveClients = self.ActiveClientsFromGroup(GroupID)
    if ActiveClients:
      for client in ActiveClients:
        if client != my_client:
          self.MuteClient(client)
    self.UnmuteClient(my_client)

  def GetGroupVolume(self, GroupID):
    group = self._GetGroup(GroupID)
    volume_sum = 0
    num_clients = 0
    for client in group['clients']:
      if client['connected'] and not client['config']['volume']['muted']:
        volume_sum += client['config']['volume']['percent']
        num_clients += 1
    if num_clients > 0:
      return int(volume_sum / num_clients)
    else:
      return 0
  
  def SetGroupVolume(self, GroupID, volume):
    group = self._GetGroup(GroupID)
    clients = []
    sum_to_distribute = 0
    for client in group['clients']:
      if client['connected'] and not client['config']['volume']['muted']:
        old_volume = client['config']['volume']['percent']
        clients.append({'old_volume': old_volume,
                        'id': client['id']})
        sum_to_distribute += volume - old_volume

    if clients:
      distribute_volume(clients, sum_to_distribute)
      for client in clients:
        if client['new_volume'] != client['old_volume']:
          self.SetClientVolume(client['id'], client['new_volume'])
      return True    
    else:
      return False
