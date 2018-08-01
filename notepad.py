#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import logging
import logging.handlers
import traceback
import os
import pickle
import re
import requests
import json as js
from exceptions import DurationException, CommandException
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

def addReminder(delta, message):
    timers.append({'time': datetime.utcnow() + delta, 'messageId': message.id})
    t = Timer(delta.total_seconds(), reminder, args=(message,))
    t.start()

    # Write the new updated timer list to the file
    with open(timersFilename, 'wb') as f:
        pickle.dump(timers, f)
    return

def parseDuration(duration):
    res = durationRegex.match(duration)
    if not res:
        raise DurationException('{} could not be parsed as duration.'.format(duration))
        return

    spec = {key:int(val) if val else 0 for key,val in res.groupdict().items()}

    delta = timedelta(**spec)

    if not delta > timedelta(0):
        raise DurationException('Duration must be positive.')

    return delta

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

def handleMessage(message, uID):
    _, command, *args = message.content.split()
    try:
        with open(str(uID) + filename, 'rb') as f:
            currNotepad = pickle.load(f)
    except:
        currNotepad = []

    if command == 'remindme':
        if len(args) < 1:
            raise CommandException('Missing duration argument.')

        delta = parseDuration(args[0])

        addReminder(delta, message.message)
        message.room.send_message('I will remind you of this message in {0}.'.format(delta))
    if command == 'snooze':
        if len(args) < 1:
            delta = timedelta(minutes=5)
        else:
            delta = parseDuration(args[0])

        myMessage = message.message.parent

        if not myMessage:
            raise CommandException('Snooze requires a reply to my reminder "Reminder for this message is due." message.')

        reminderMessage = myMessage.parent

        if not reminderMessage:
            raise CommandException('Snooze requires a reply to my reminder "Reminder for this message is due." message.')


        if reminderMessage.owner.id != message.message.owner.id:
            raise CommandException('You cannot snooze a message that doesn\'t belong to you.')

        addReminder(delta, reminderMessage)

        message.room.send_message('Your message has been snoozed for {0}.'.format(delta))

    if command == 'add':
        currNotepad.append(' '.join(args))
        message.room.send_message('Added message to your notepad.')
    if command == 'rm':
        try:
            which = int(args[0])
            if which > len(currNotepad):
                raise CommandException('Item does not exist.')
            del currNotepad[which - 1]
            message.room.send_message('Message deleted.')
        except:
            return
    if command == 'rma':
        currNotepad = []
        message.room.send_message('All messages deleted.')
    if command == 'show':
        if not currNotepad:
            raise CommandException('You have no saved messages.')
        report = buildReport(currNotepad)
        r = requests.post(apiUrl, json=report)
        r.raise_for_status()
        js = r.json()
        message.room.send_message('Opened your notepad [here]({}).'.format(js['reportURL']))
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
        handleMessage(message, userID)
    except CommandException as e:
        message.room.send_message(str(e))
    except Exception as e:
        print(traceback.format_exc())
        message.room.send_message('Error occurred: {} (cc @Baum @FrankerZ)'.format(e))

if 'ChatExchangeR' in os.environ:
    roomID = os.environ['ChatExchangeR']

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
print('Joined room {}'.format(room.name))
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
