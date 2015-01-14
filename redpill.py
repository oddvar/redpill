# -*- coding: utf-8 -*-

import json
import time
import datetime
import curses
from matrix_client.client import MatrixClient


def loadCredentials(filename):
    global password, username, server
    json_data = open(filename)
    data = json.load(json_data)
    json_data.close()

    username = data["username"]
    password = data["password"]
    server = data["server"]


def processBackFill(backFill):
    global data

    if "rooms" in backFill:
        for r in backFill["rooms"]:
            room = r.get("room_id", "unknown")
            if "messages" in r:
                newMessages = r.get("messages")
                test = newMessages.get("end")
                if "chunk" in newMessages:
                    for thing in newMessages.get("chunk"):
                        if True:
                            registerRoom(room)
                            temp = data[room]["messages"]["chunk"]
                            temp.append(thing)
                            data[room]["messages"]["chunk"] = temp
                            data[room]["endTime"] = test
    for event in backFill:
        if "room_id" in event:
            room = event["room_id"]
            registerRoom(room)
            data[room]["messages"]["chunk"].append(event)


def processMessage(obj):
    global data, room, endTime, stdscr

    didWeProcessSomethingSuccessfully = None

    if 'chunk' in obj:
        for thing in obj.get("chunk"):
            if "room_id" in thing:
                room = thing["room_id"]
                if room not in data:
                    registerRoom(room)
                temp = data[room]["messages"]["chunk"]
                temp.append(thing)
                data[room]["messages"]["chunk"] = temp
                endTime = obj.get("end")
                didWeProcessSomethingSuccessfully = room
    return didWeProcessSomethingSuccessfully


def registerRoom(roomid):
    global data, rooms

    if roomid not in data:
        #rooms.append(roomid)
        data[roomid] = {}
        data[roomid]["messages"] = {}
        data[roomid]["messages"]["chunk"] = []


def incrementalText(string):
    global incrementalTextOffset, stdscr

    stdscr.addstr(0, incrementalTextOffset, string)
    stdscr.refresh()
    incrementalTextOffset += len(string)


def main(stdsc):
    global size, room, data, stdscr, rooms, access_token, endTime, incrementalTextOffset

    stdscr = stdsc

    curses.curs_set(0)
    curses.use_default_colors()
    size = stdscr.getmaxyx()

    incrementalTextOffset = 0
    incrementalText("loading")
    loadCredentials("./credentials.json")

    incrementalText(".")
    client = MatrixClient(server)
    incrementalText(".")
    access_token = client.login_with_password(
        username,
        password,
        size[0])

    incrementalText(".")

    rooms = client.get_rooms()
    roomkeys = rooms.keys()

    data = {}

    room = "foo"
    try:
        for room in rooms:
            incrementalText(".")
            backFill = rooms[room].get_events()
            processBackFill(backFill)

    except KeyError:
        pass

    incrementalText(".")

    endTime = client.end

    room = roomkeys[0]
    nextRoom = 1

    curses.halfdelay(10)
    maxDisplayName = 24
    displayNamestartingPos = 20
    pause = False

    client.add_listener(processMessage)

    while(True):
        size = stdscr.getmaxyx()

        client.listen_for_events(100)
        stdscr.clear()
        stdscr.addstr(
            0, 0, (
                "redpill v0.4 · screen size: " + str(size) + " · chat size: "
                + str(len(data[room]["messages"]["chunk"])) + " · room: " +
                str(room) + " · " + str(endTime)
            ), curses.A_UNDERLINE
        )

        current = len(data[room]["messages"]["chunk"]) - 1

        if True:
            y = 1
            if current >= 0:

                # TODO: something when the first event is a typing event

                for event in reversed(data[room]["messages"]["chunk"]):
                    if event["type"] == "m.typing":
                        pass  # do something clever
                    else:
                        currentLine = size[0] - y

                        if currentLine < 2:  # how many lines we want to reserve
                            break
                        y += 1
                        if "origin_server_ts" in event:
                            convertedDate = datetime.datetime.fromtimestamp(
                                int(
                                    event["origin_server_ts"] / 1000)
                                ).strftime('%Y-%m-%d %H:%M:%S')

                            stdscr.addstr(currentLine, 0, convertedDate)
                        # assumption: body == normal message
                        length = 0
                        if "user_id" in event:
                            length = len(
                                event["user_id"]
                            )
                        if "body" in event["content"]:
                            if length > maxDisplayName:
                                stdscr.addstr(
                                    currentLine, displayNamestartingPos, "<" +
                                    str(event["user_id"][:maxDisplayName])
                                )
                                stdscr.addstr(
                                    currentLine, displayNamestartingPos +
                                    maxDisplayName - 2, "...> "
                                )  # 3 minus the "<" char=2
                            else:
                                stdscr.addstr(
                                    currentLine, displayNamestartingPos +
                                    maxDisplayName - length, "<" +
                                    str(event["user_id"]) + "> "
                                )

                            rawText = event["content"]["body"]
                            with open('debug.log', 'a') as the_file:
                                the_file.write(rawText + "\n")

                            buf = ""
                            for line in rawText:
                                for char in line:
                                    if char == '\n':
                                        pass
                                    #elif char == ' ':   # skip all whitespace
                                    #    self.X += 1
                                    else:
                                        buf += char

                            stdscr.addstr(
                                currentLine, displayNamestartingPos +
                                maxDisplayName + 3, buf[:size[1] -
                                (displayNamestartingPos + maxDisplayName + 4)],
                                curses.A_BOLD
                            )

                        # membership == join/leave events
                        elif "membership" in event["content"]:
                            buf = " invited someone"
                            if event["content"]["membership"] == "invite":
                                if "state_key" in event:
                                    buf = " invited " + event["state_key"]
                            elif event["content"]["membership"] == "join":
                                buf = " has joined"
                            elif event["content"]["membership"] == "leave":
                                buf = " has left"

                            if length > maxDisplayName:
                                stdscr.addstr(
                                    currentLine,
                                    displayNamestartingPos + 1,
                                    str(event["user_id"]),
                                    curses.A_DIM
                                )
                                stdscr.addstr(
                                    currentLine,
                                    displayNamestartingPos + length + 1,
                                    buf,
                                    curses.A_DIM
                            )
                            else:
                                stdscr.addstr(
                                    currentLine,
                                    displayNamestartingPos + 1 +
                                    maxDisplayName - length,
                                    str(event["user_id"]),
                                    curses.A_DIM
                                )
                                stdscr.addstr(
                                    currentLine,
                                    displayNamestartingPos + maxDisplayName + 1,
                                    buf,
                                    curses.A_DIM
                                )

                    current -= 1
        if pause:
            stdscr.addstr(
                int(size[0] / 2) - 1,
                int(size[1] / 2),
                "          ",
                curses.A_REVERSE
            )
            stdscr.addstr(
                int(size[0] / 2),
                int(size[1] / 2),
                "  PAUSED  ",
                curses.A_REVERSE
            )
            stdscr.addstr(
                int(size[0] / 2) + 1,
                int(size[1] / 2),
                "          ",
                curses.A_REVERSE
            )

        stdscr.refresh()

        try:
            c = stdscr.getch()
            if c == -1:
                stdscr.addstr(1, 0, "timeout")
            elif c == 9:
                stdscr.addstr(1, 0, "%s was pressed\n" % c)
                room = roomkeys[nextRoom]
                nextRoom = (nextRoom + 1) % len(rooms)
            elif c == ord("p"):
                pause = not(pause)
                if pause:
                    curses.nocbreak()
                    curses.cbreak()
                    stdscr.timeout(-1)
                    stdscr.addstr(
                        int(size[0] / 2) - 1,
                        int(size[1] / 2),
                        "          ",
                        curses.A_REVERSE
                    )
                    stdscr.addstr(
                        int(size[0] / 2),
                        int(size[1] / 2),
                        " PAUSING  ",
                        curses.A_REVERSE
                    )
                    stdscr.addstr(
                        int(size[0] / 2) + 1,
                        int(size[1] / 2),
                        "          ",
                        curses.A_REVERSE
                    )
                    stdscr.refresh()
                else:
                    stdscr.addstr(
                        int(size[0] / 2) - 1,
                        int(size[1] / 2),
                        "          ",
                        curses.A_REVERSE
                    )
                    stdscr.addstr(
                        int(size[0] / 2),
                        int(size[1] / 2),
                        " RESUMING ",
                        curses.A_REVERSE
                    )
                    stdscr.addstr(
                        int(size[0] / 2) + 1,
                        int(size[1] / 2),
                        "          ",
                        curses.A_REVERSE
                    )
                    stdscr.refresh()
                    curses.halfdelay(10)
                    stdscr.timeout(1)
            elif c == ord("q"):
                curses.endwin()
                quit()

            stdscr.addstr(2, 0, "time() == %s\n" % time.time())

        finally:
            do_nothing = True

curses.wrapper(main)