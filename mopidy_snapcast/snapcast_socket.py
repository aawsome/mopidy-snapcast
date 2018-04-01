from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)
import socket, json
from operator import itemgetter

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
  def __init__(self, host, port):
    self.msgid = 1
    
    # connect to remote host
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect((host, port))

    self.socket = s
     
  def sendmessage(self, method, params=None):
    msg = { "id":self.msgid,"jsonrpc":"2.0","method": method }
    if params:
      msg['params'] = params
    socketmsg = json.dumps(msg) + "\r\n"
    self.socket.send(socketmsg)
    while True:
      data = ''
      while len(data) == 0 or data[-1] != "\n":
        data += self.socket.recv(1)
      if data[0] == '[':
        continue

      try:
        my_data = json.loads(data)
      except ValueError:
        raise ValueError(data)

      if 'id' not in my_data or my_data['id'] < self.msgid:
        continue
      if 'result' in my_data:
        break
      else:
        raise ValueError(my_data)
    
    self.msgid += 1
    return my_data['result']

  def MuteClient(self, client_id):
    return self.sendmessage('Client.SetVolume', {'id': client_id, 'volume': {'muted' : True}})

  def UnmuteClient(self, client_id):
    return self.sendmessage('Client.SetVolume', {'id': client_id, 'volume': {'muted' : False}})
  
  def SetClientVolume(self, client_id, volume):
    return self.sendmessage('Client.SetVolume', {'id': client_id, 'volume': {'percent' : volume}})
  
  def GetGroupMute(self, group):
    data = self.sendmessage('Group.GetStatus', {'id': group})
    return data['group']['muted']
  
  def MuteGroup(self, group_id):
    return self.sendmessage('Group.SetMute', {'id': group_id, 'mute': True})

  def UnmuteGroup(self, group_id):
    return self.sendmessage('Group.SetMute', {'id': group_id, 'mute': False})

  def GroupFromPath(self, path):
    data = self.sendmessage('Server.GetStatus')
    for stream in data['server']['streams']:
      if stream['uri']['path'] == path :
        for group in data['server']['groups']:
          if group['stream_id'] ==  stream['id']:
            return group['id']

  def ActiveClientsFromGroup(self, group):
    data = self.sendmessage('Group.GetStatus', {'id': group})
    clients = []
    for client in data['group']['clients']:
      if client['connected'] and not client['config']['volume']['muted']:
        clients.append(client['id'])

  def MuteClientsInGroup(self, group):
    for client in self.ActiveClientsFromGroup(group):
      self.MuteClient(client)

  def ExclusiveClientInGroup(self, my_client, group):
    self.UnmuteGroup(group)
    ActiveClients = self.ActiveClientsFromGroup(group)
    if ActiveClients:
      for client in ActiveClients:
        if client != my_client:
          self.MuteClient(client)
    self.UnmuteClient(my_client)

  def GetGroupVolume(self, group):
    data = self.sendmessage('Group.GetStatus', {'id': group})
    volume_sum = 0
    num_clients = 0
    for client in data['group']['clients']:
      if client['connected'] and not client['config']['volume']['muted']:
        volume_sum += client['config']['volume']['percent']
        num_clients += 1
    if num_clients > 0:
      return int(volume_sum / num_clients)
    else:
      return 0
  
  def SetGroupVolume(self, group, volume):
    data = self.sendmessage('Group.GetStatus', {'id': group})
    clients = []
    sum_to_distribute = 0
    for client in data['group']['clients']:
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
