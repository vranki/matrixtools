#!/usr/bin/env python3

from __future__ import print_function, unicode_literals
import asyncio
import json
import os
import requests
from nio import AsyncClient, InviteEvent, JoinError, RoomMessageText, MatrixRoom, LoginError, RoomMemberEvent, RoomVisibility, RoomPreset, RoomCreateError, RoomInviteResponse
from PyInquirer import prompt
from pprint import pprint

matrix_user = os.getenv('MATRIX_USER')
matrix_server = os.getenv('MATRIX_SERVER')
access_token = os.getenv('MATRIX_ACCESS_TOKEN')


tool_select = [
    {
        'type': 'list',
        'name': 'tool',
        'message': 'What do you want to do?',
        'choices': ['Quit', 'Plumb ircnet'],
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

class MxTool:
    def __init__(self, server, user, token):
        self.matrix_server = server
        self.matrix_user = user
        self.access_token = token
        self.client = AsyncClient(self.matrix_server, self.matrix_user)
        self.client.access_token = self.access_token
        self.quit = False

    async def run_tool(self):
        while not self.quit:
            await self.client.sync()
            print('Welcome, ', self.matrix_user, '\n\n')
            answers = prompt(tool_select)
            if(answers['tool']=='quit'):
                self.quit = True
            if(answers['tool']=='plumb ircnet'):
                answers = prompt(plumb_questions)
                channel = answers['channel']
                opnick = answers['opnick']

                room_select[0]['choices'] = []

                for croomid in self.client.rooms:
                    print(croomid)
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
        



if matrix_server and matrix_user and access_token:
    mxtool = MxTool(matrix_server, matrix_user, access_token)
    asyncio.run(mxtool.run_tool())

