#!/usr/bin/env python3

from __future__ import print_function, unicode_literals
import asyncio
import json
import os
import requests
import re

from easysettings import EasySettings
from nio import AsyncClient, InviteEvent, JoinError, RoomMessageText, MatrixRoom, LoginError, LoginResponse, RoomMemberEvent, RoomVisibility, RoomPreset, RoomCreateError, RoomInviteResponse, RoomLeaveResponse
from PyInquirer import prompt
from pprint import pprint

matrix_user = os.getenv('MATRIX_USER')
matrix_server = os.getenv('MATRIX_SERVER')
access_token = os.getenv('MATRIX_ACCESS_TOKEN')

login_questions = [
    {
        'type': 'input',
        'name': 'user',
        'message': 'Matrix user (example: @user:matrix.org)'
    },
    {
        'type': 'input',
        'name': 'server',
        'message': 'Matrix homeserver (example: https://matrix.org)'
    },
    {
        'type': 'password',
        'name': 'password',
        'message': 'Password'
    },
]

tool_select = [
    {
        'type': 'list',
        'name': 'tool',
        'message': 'What do you want to do?',
        'choices': ['Quit', 'Plumb ircnet', 'Leave rooms', 'IRC channel tools'],
        'filter': lambda val: val.lower()
    }
]

irc_channel_tool_select = [
    {
        'type': 'list',
        'name': 'tool',
        'message': 'What do you want to do?',
        'choices': ['Main menu', 'Change room', 'Op', 'Deop'],
        'filter': lambda val: val.lower()
    }
]

room_select = [
    {
        'type': 'list',
        'name': 'room',
        'message': 'Choose room',
        'choices': [],
    }
]

users_select = [
    {
        'type': 'checkbox',
        'qmark': 'x',
        'message': 'Select users',
        'name': 'users',
        'choices': [ ],
    }
]

plumb_questions = [
    {
        'type': 'input',
        'name': 'channel',
        'message': 'Enter IRC channel name',
     },
    {
        'type': 'input',
        'name': 'opnick',
        'message': 'Nick of a op on the IRC channel',
     }
]

leave_questions = [
    {
        'type': 'checkbox',
        'qmark': 'x',
        'message': 'Select rooms to leave',
        'name': 'rooms',
        'choices': [ ],
    }
]

irc_networks = [
    {
        'name': 'IRCNet',
        'bot': '@ircnet:irc.snt.utwente.nl',
        'provision_url': 'https://matrix-irc.snt.utwente.nl/ircnet/provision/link',
        'server': 'irc.snt.utwente.nl',
        'mxid2nick': '@_ircnet_(.*):irc\.snt\.utwente\.nl'
    }
]

class MxTool:
    def __init__(self, server, user, token):
        self.matrix_server = server
        self.matrix_user = user
        self.access_token = token
        self.quit = False
        self.settings = EasySettings("matrixtool.conf")

    async def run_tool(self):
        if not self.matrix_user: # Not read from env, try settings..
            self.access_token = self.settings.get('MATRIX_ACCESS_TOKEN')
            self.matrix_server = self.settings.get('MATRIX_SERVER')
            self.matrix_user = self.settings.get('MATRIX_USER')

        if self.access_token:
            print('\nUsing access token to authenticate..')
            self.client = AsyncClient(self.matrix_server, self.matrix_user)
            self.client.access_token = self.access_token

        while not self.access_token:
            print('\nLogin to your matrix account\n')
            answers = prompt(login_questions)
            self.matrix_server = answers['server']
            self.matrix_user = answers['user']
            self.client = AsyncClient(self.matrix_server, self.matrix_user)
            print('\nLogging in..')
            res = await self.client.login(answers['password'])
            if type(res) == LoginResponse:
                self.access_token = self.client.access_token
                self.settings.set('MATRIX_USER', self.matrix_user)
                self.settings.set('MATRIX_SERVER', self.matrix_server)
                self.settings.set('MATRIX_ACCESS_TOKEN', self.access_token)
                self.settings.save()
            else:
                print(res)

        while not self.quit:
            await self.client.sync()
            print('\nWelcome, ', self.matrix_user, '\n\n')
            answers = prompt(tool_select)
            if 'tool' in answers:
                if(answers['tool']=='quit'):
                    self.quit = True
                if(answers['tool']=='plumb ircnet'):
                    await self.plumb_ircnet()
                if(answers['tool']=='leave rooms'):
                    await self.leave_rooms()
                if(answers['tool']=='irc channel tools'):
                    await self.irc_channel_tools()

        await self.close()

    async def close(self):
        await self.client.close()

    async def wait_until_user_joined(self, user, room):
        while True:
            await self.client.sync()
            for croomid in self.client.rooms:
                if croomid == room:
                    print('Checking if', user, 'is in', room)
                    roomobj = self.client.rooms[croomid]
                    for roomuser in roomobj.users:
                        if roomuser == user:
                            print('Yes!')
                            return
    
    async def plumb_ircnet(self):
        answers = prompt(plumb_questions)
        channel = answers['channel']
        opnick = answers['opnick']

        room_select[0]['choices'] = []
        network = irc_networks[0]

        for croomid in self.client.rooms:
            roomobj = self.client.rooms[croomid]
            choice = {'value': croomid, 'name': roomobj.display_name}
            room_select[0]['choices'].append(choice)
        print('Choose a room to plumb:\n')
        answers = prompt(room_select)
        plumbroom = answers['room']
        bot = network['bot']
        print('Inviting', bot, 'to', plumbroom)
        rir = await self.client.room_invite(plumbroom, bot)
        if type(rir) != RoomInviteResponse:
            print('Room invite seemed to fail - press ctrl-c to abort if you want to do so now: ', rir)
            input("Press Enter to continue...")
        await self.wait_until_user_joined(bot, plumbroom)
        print('Bot joined, please give it PL100 in the Matrix room')

        input("Press Enter to continue...")

        # self.client.room_put_state(plumbroom, ) # TODO: figure out how to set PL

        url = network['provision_url']
        post_data = {
            "remote_room_server": network['server'],
            "remote_room_channel": channel,
            "matrix_room_id": plumbroom,
            "op_nick": opnick,
            "user_id": self.matrix_user
        }
        headers = {'content-type': 'application/json'}
        print('POST', json.dumps(post_data))
        res = requests.post(url, data = json.dumps(post_data), headers = headers)
        if res.status_code != 200:
            print('Plumbing failed:', res.text)
        else:
            print('Almost finished! IRC user', opnick, 'must now reply to the bot to finish plumbing.')
        input("Press Enter")

    async def leave_rooms(self):
        leave_questions[0]['choices'] = []
        for croomid in self.client.rooms:
            roomobj = self.client.rooms[croomid]
            choice = {'value': croomid, 'name': roomobj.display_name}
            leave_questions[0]['choices'].append(choice)
        answers = prompt(leave_questions)
        for roomid in answers['rooms']:
            roomname = self.client.rooms[roomid].display_name
            print('Leaving room', roomname, '..')
            rlr = await self.client.room_leave(roomid)
            if type(rlr) != RoomLeaveResponse:
                print(rlr)
        print('\nNote: due to bug #46 in nio library, the rooms do not appear to be left until you restart the tool.\n')

    def pick_room(self):
        room_select[0]['choices'] = []
        for croomid in self.client.rooms:
            roomobj = self.client.rooms[croomid]
            choice = {'value': croomid, 'name': roomobj.display_name}
            room_select[0]['choices'].append(choice)
        answer = prompt(room_select)
        return answer['room'], self.client.rooms[answer['room']]

    async def irc_channel_tools(self):
        network = irc_networks[0] # Hardcoded ..

        botroomid = self.find_chat_with(network['bot'])
        if not botroomid:
            print('Please start chat with', network['bot'], 'first!')
            return

        roomid, roomobj = self.pick_room()
        print('Chose room', roomobj.display_name)
        if not self.user_is_in_room(network['bot'], roomid):
            print(network['bot'],'is not in this room - is it really a IRC room?')
            return


        print('Bot room:', botroomid, self.client.rooms[botroomid].display_name, network['name'])

        print('TODO: Figure out how to read this automatrically.\n')
        ircchannel = input('Enter IRC channel name of this room (example: #example): ')

        if len(ircchannel) == 0:
            return

        answer = prompt(irc_channel_tool_select)
        if(answer['tool']=='main menu'):
            return

        if(answer['tool']=='op' or answer['tool']=='deop'):
            users = self.select_users_in_room(roomobj)
            for user in users:
                res = re.compile(network['mxid2nick']).search(user)
                if res:
                    nick = res.group(1)
                    if len(nick) > 0:
                        print('Opping', user, '..')
                        cmd = f'!cmd MODE {ircchannel} +o {nick}'
                        if answer['tool']=='deop':
                            cmd = f'!cmd MODE {ircchannel} -o {nick}'
                        print(cmd)
                        await self.send_text(botroomid, cmd)
                else:
                    print('Cannot figure out irc nick for', user)

    def find_chat_with(self, mxid):
        for croomid in self.client.rooms:
            roomobj = self.client.rooms[croomid]
            if len(roomobj.users) == 2:
                for user in roomobj.users:
                    if user == mxid:
                        return croomid
        return None
    
    def user_is_in_room(self, mxid, roomid):
        roomobj = self.client.rooms[roomid]
        for user in roomobj.users:
            if user == mxid:
                return True
        return False
    
    def select_users_in_room(self, roomobj):
        users_select[0]['choices'] = []
        for user in roomobj.users:
            choice = {'value': user, 'name': roomobj.user_name(user) }
            users_select[0]['choices'].append(choice)
        answers = prompt(users_select)
        return answers['users']

    async def send_text(self, roomid, body):
        msg = {
            "body": body,
            "msgtype": "m.text",
        }
        await self.client.room_send(roomid, 'm.room.message', msg)


mxtool = MxTool(matrix_server, matrix_user, access_token)
asyncio.run(mxtool.run_tool())
