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
from threading import Timer
from textwrap import dedent,indent

import chatexchange.client
import chatexchange.events

hostID = 'stackoverflow.com'
roomID = '111347'
selfID = 7829893
filename = ',notepad'
apiUrl = 'http://reports.socvr.org/api/create-report'

helpmessage = indent(dedent("""\
                            add `message`:        Add `message` to your notepad
                            rm  `idx`:            Delete the message at `idx`
                            rma:                  Clear your notepad
                            show:                 Show your messages
                            remindme `m` [...]:   Reminds you of this message in `m` minutes
                            reboot notepad:       Reboot this bot
                            """), ' '*4)


def _parseMessage(msg):
    _,*tail = msg.split()
    return ' '.join(tail)

def buildReport(notepad):
    ret = {'botName' : 'Notepad'}
    posts = []
    for i, v in enumerate(notepad, start=1):
        posts.append([{'id':'idx', 'name':'Message Index', 'value':i},
            {'id':'msg', 'name':'Message', 'value':v}])
    ret['posts'] = posts
    return ret

def reminder(msg):
    msg.message.reply('Reminder for this message is due.')

def handleCommand(message, command, uID):
    word,*rest = command.split()
    try:
        with open(str(uID) + filename, 'rb') as f:
            currNotepad = pickle.load(f)
    except:
        currNotepad = []
    if word == 'remindme':
        if len(rest) < 1:
            message.room.send_message('Missing duration argument.')
            return
        try:
            time = float(rest[0])
        except:
            message.room.send_message('Number expected as first argument, got {}.'.format(rest[0]))
            return
        if not time > 0:
            message.room.send_message('Duration must be positive.')
            return
        t = Timer(60*time, reminder, args=(message,))
        t.start()
        message.room.send_message('I will remind you of this message in {} minutes.'.format(time))
        return
    elif word == 'add':
        currNotepad.append(' '.join(rest))
        message.room.send_message('Added message to your notepad.')
    elif word == 'rm':
        try:
            which = int(rest[0])
            if which > len(currNotepad):
                message.room.send_message('Item does not exist.')
            del currNotepad[which - 1]
            message.room.send_message('Message deleted.')
        except:
            return
    elif word == 'rma':
        currNotepad = []
        message.room.send_message('All messages deleted.')
    elif word == 'show':
        if not currNotepad:
            message.room.send_message('You have no saved messages.')
            return
        report = buildReport(currNotepad)
        r = requests.post(apiUrl, data=js.dumps(report))
        r.raise_for_status()
        message.room.send_message('Opened your notepad [here]({}).'.format(r.text))
        return
    with open(str(uID) + filename, 'wb') as f:
        pickle.dump(currNotepad, f)
        
def onMessage(message, client):
    if str(message.room.id) != roomID:
        return
    if isinstance(message, chatexchange.events.MessagePosted) and message.content in ['🚂', '🚆', '🚄']:
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
        elif icommand == 'update notepad':
            call(['git', 'pull'])
            os._exit(1)
        elif icommand == 'help':
            message.room.send_message('Try `commands <botname>`, e.g. `commands notepad`.')
        elif icommand in ['a', 'alive']:
            message.room.send_message('[notepad] Yes.')
            return
        elif icommand == 'commands':
            message.room.send_message('[notepad] Try `commands notepad`')
            return
        elif icommand == 'commands notepad':
            message.room.send_message(helpmessage)
            return
    except:
        return
    
    try:
        handleCommand(message, command, userID)
    except Exception as e:
        message.room.send_message('Error occurred: {} (cc @Baum)'.format(e))


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

while True:
    watcher = room.watch_socket(onMessage)
    watcher.thread.join()


client.logout()

