#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import logging
import logging.handlers
import os
import pickle
import requests
import json as js
from subprocess import call

import chatexchange.client
import chatexchange.events

hostID = 'stackoverflow.com'
roomID = '111347'
selfID = 7829893
filename = ',notepad'
apiUrl = 'http://reports.socvr.org/api/create-report'

helpmessage = \
        '    add `message`:    Add `message` to your notepad\n' + \
        '    rm  `idx`:        Delete the message at `idx`\n' + \
        '    rma:              Clear your notepad\n' + \
        '    show:             Show your messages\n' + \
        '    reboot notepad:   Reboot this bot'

def _parseMessage(msg):
    temp = msg.split()
    return ' '.join(temp[1:])

def buildReport(notepad):
    ret = {'botName' : 'Notepad'}
    posts = []
    for i, v in enumerate(notepad, start=1):
        posts.append([{'id':'idx', 'name':'Message Index', 'value':i},
            {'id':'msg', 'name':'Message', 'value':v}])
    ret['posts'] = posts
    return ret

def handleCommand(message, command, uID):
    words = command.split()
    try:
        f = open(str(uID) + filename, 'rb')
        currNotepad = pickle.load(f)
    except:
        currNotepad = []
    if words[0] == 'add':
        currNotepad.append(' '.join(words[1:]))
        message.room.send_message('Added message to your notepad.')
    if words[0] == 'rm':
        try:
            which = int(words[1])
            if which > len(currNotepad):
                message.room.send_message('Item does not exist.')
            del currNotepad[which - 1]
            message.room.send_message('Message deleted.')
        except:
            return
    if words[0] == 'rma':
        currNotepad = []
        message.room.send_message('All messages deleted.')
    if words[0] == 'show':
        if not currNotepad:
            message.room.send_message('You have no saved messages.')
            return
        report = buildReport(currNotepad)
        r = requests.post(apiUrl, data=js.dumps(report))
        r.raise_for_status()
        message.room.send_message('Opened your notepad [here](%s).'%r.text)
        return
    f = open(str(uID) + filename, 'wb')
    pickle.dump(currNotepad, f)
        
def onMessage(message, client):
    if isinstance(message, chatexchange.events.MessagePosted) and message.content in ['🚂', '🚆']:
        message.room.send_message('[🚃](https://github.com/SOBotics/notepad)')
        return

    amount = None
    fromTheBack = False
    try:
        if message.target_user_id != selfID:
            return
        userID = message.user.id
        command = _parseMessage(message.content)
        icommand = command.lower()
        if icommand == 'reboot notepad':
            os._exit(1)
        if icommand == 'update notepad':
            call(['git', 'pull'])
            os._exit(1)
        if icommand == 'help':
            message.room.send_message('Try `commands <botname>`, e.g. `commands notepad`.')
        if icommand in ['a', 'alive']:
            message.room.send_message('[notepad] Yes.')
            return
        if icommand == 'commands':
            message.room.send_message('[notepad] Try `commands notepad`')
            return
        if icommand == 'commands notepad':
            message.room.send_message(helpmessage)
            return
    except:
        return
    
    handleCommand(message, command, userID)

if 'ChatExchangeU' in os.environ:
    email = os.environ['ChatExchangeU']
else:
    email = input("Email: ")
if 'ChatExchangeP' in os.environ:
    password = os.environ['ChatExchangeP']
else:
    password = input("Password: ")

client = chatexchange.client.Client(hostID)
client.login(email, password)
print('Logged in')

room = client.get_room(roomID)
room.join()
print('Joined room')
room.send_message('[notepad] Hi o/')

watcher = room.watch(onMessage)
watcher.thread.join()


client.logout()

