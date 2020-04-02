#!/usr/bin/env python3

from __future__ import print_function, unicode_literals
import asyncio
import json
import os
import requests
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
        'type': 'input',
        'name': 'password',
        'message': 'Password'
    },
]

tool_select = [
    {
        'type': 'list',
        'name': 'tool',
        'message': 'What do you want to do?',
        'choices': ['Quit', 'Plumb ircnet', 'Leave rooms'],
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

class MxTool:
    def __init__(self, server, user, token):
        self.matrix_server = server
        self.matrix_user = user
        self.access_token = token
        self.quit = False

    async def run_tool(self):
        if self.access_token:
            self.client.access_token = self.access_token
            self.client = AsyncClient(self.matrix_server, self.matrix_user)

        while not self.access_token:
            answers = prompt(login_questions)
            self.matrix_server = answers['server']
            self.matrix_user = answers['user']
            self.client = AsyncClient(self.matrix_server, self.matrix_user)
            res = await self.client.login(answers['password'])
            if type(res) == LoginResponse:
                self.access_token = self.client.access_token
            else:
                print(res)

        while not self.quit:
            await self.client.sync()
            print('\nWelcome, ', self.matrix_user, '\n\n')
            answers = prompt(tool_select)
            if(answers['tool']=='quit'):
                self.quit = True
            if(answers['tool']=='plumb ircnet'):
                await self.plumb_ircnet()
            if(answers['tool']=='leave rooms'):
                await self.leave_rooms()

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

        for croomid in self.client.rooms:
            roomobj = self.client.rooms[croomid]
            choice = {'value': croomid, 'name': roomobj.display_name}
            room_select[0]['choices'].append(choice)
        print('Choose a room to plumb:\n')
        answers = prompt(room_select)
        plumbroom = answers['room']
        bot = '@ircnet:irc.snt.utwente.nl'
        print('Inviting', bot, 'to', plumbroom)
        rir = await self.client.room_invite(plumbroom, bot)
        if type(rir) != RoomInviteResponse:
            print('Room invite seemed to fail - press ctrl-c to abort if you want to do so now: ', rir)
            input("Press Enter to continue...")
        await self.wait_until_user_joined(bot, plumbroom)
        print('Bot joined, please give it PL100 in the Matrix room')

        input("Press Enter to continue...")

        # self.client.room_put_state(plumbroom, ) # TODO: figure out how to set PL

        url = 'https://matrix-irc.snt.utwente.nl/ircnet/provision/link'
        post_data = {
            "remote_room_server": "irc.snt.utwente.nl",
            "remote_room_channel": channel,
            "matrix_room_id": plumbroom,
            "op_nick": opnick,
            "user_id": self.matrix_user
        }
        print('POST', json.dumps(post_data))
        res = requests.post(url, data = json.dumps(post_data))
        if res.status_code != 200:
            print('Plumbing failed:', res.text)
        else:
            print('Plumbing succeeded, IRC user', opnick, 'must now reply to the bot')
        input("Press Enter to continue...")

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

mxtool = MxTool(matrix_server, matrix_user, access_token)
asyncio.run(mxtool.run_tool())
