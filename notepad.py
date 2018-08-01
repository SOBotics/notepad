#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import logging
import logging.handlers
import os
import pickle
import re
import requests
import json as js
from datetime import datetime, timedelta
from subprocess import call
from threading import Timer

import chatexchange.client
import chatexchange.events

hostID = 'stackoverflow.com'
roomID = '111347'
filename = ',notepad'
timersFilename = 'notepadTimers'
apiUrl = 'https://reports.sobotics.org/api/v2/report/create'
durationRegex = re.compile('^(?:(?P<weeks>\d+)w)?(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m?)?$', re.VERBOSE)
timers = []

helpmessage = \
        '    add `message`:        Add `message` to your notepad\n' + \
        '    rm  `idx`:            Delete the message at `idx`\n' + \
        '    rma:                  Clear your notepad\n' + \
        '    show:                 Show your messages\n' + \
        '    remindme `m` [...]:   Reminds you of this message in `m` minutes\n' + \
        '    reboot notepad:       Reboot this bot'

def _parseMessage(msg):
    temp = msg.split()
    return ' '.join(temp[1:])

def buildReport(notepad):
    ret = {'appName' : 'Notepad',
            'appURL' : 'https://github.com/SOBotics/notepad'}
    posts = []
    for i, v in enumerate(notepad, start=1):
        posts.append([{'id':'idx', 'name':'Message Index', 'value':i},
            {'id':'msg', 'name':'Message', 'value':v}])
    ret['fields'] = posts
    return ret

def reminder(msg):
    msg.reply('Reminder for this message is due.')

def handleCommand(message, command, uID):
    words = command.split()
    try:
        with open(str(uID) + filename, 'rb') as f:
            currNotepad = pickle.load(f)
    except:
        currNotepad = []

    if words[0] == 'remindme':
        if len(words) < 2:
            message.room.send_message('Missing duration argument.')
            return

        res = durationRegex.match(words[1])
        if not res:
            message.room.send_message(words[1] + ' could not be parsed as duration.')
            return

        spec = {key:int(val) if val else 0 for key,val in res.groupdict().items()}
        delta = timedelta(**spec)
        time = delta.total_seconds()

        if not time > 0:
            message.room.send_message('Duration must be positive.')
            return
        
        timers.append({'time': datetime.utcnow() + delta, 'messageId': message.message.id})
        t = Timer(time, reminder, args=(message.message,))
        t.start()
        message.room.send_message('I will remind you of this message in %s.'%delta)

        # Write the new updated timer list to the file
        with open(timersFilename, 'wb') as f:
            pickle.dump(timers, f)
        return
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
        r = requests.post(apiUrl, json=report)
        r.raise_for_status()
        js = r.json()
        message.room.send_message('Opened your notepad [here](%s).'%js['reportURL'])
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
        if message.target_user_id != client.get_me().id:
            return
        userID = message.user.id
        command = _parseMessage(message.content)
        # Empty command
        if not command.split():
            return
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
    
    try:
        handleCommand(message, command, userID)
    except Exception as e:
        message.room.send_message('Error occurred: ' + str(e) + ' (cc @Baum)')


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

# Load timers
try:
    with open(timersFilename, 'rb') as f:
        timersToLoad = pickle.load(f)
    
    if not isinstance(timersToLoad, list):
        raise Exception('Timers are not a valid list.')
except FileNotFoundError:
    timersToLoad = []
except Exception as e:
    print('Exception loading timers from {}: {}'.format(timersFilename, e))
    timersToLoad = []

for item in timersToLoad:
    try:
        diff = item['time'] - datetime.utcnow()

        # Filter out expired timers
        if diff < timedelta(0):
            continue
        
        timers.append(item)

        msg = client.get_message(item['messageId'])

        t = Timer(diff.total_seconds(), reminder, args=(msg,))
        t.start()
    except Exception as e:
        print('Error intializing timer ({}): {}'.format(item, e))

while True:
    watcher = room.watch_socket(onMessage)
    watcher.thread.join()


client.logout()

