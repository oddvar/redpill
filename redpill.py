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


def processMessage(obj):
    global room

    if "room_id" in obj:
        room = obj["room_id"]


def main(stdscr):
    global size, room, data, rooms, access_token, endTime, incrementalTextOffset

    curses.curs_set(0)
    curses.use_default_colors()
    size = stdscr.getmaxyx()

    stdscr.addstr(0, 0, "loading...")
    stdscr.refresh()
    loadCredentials("./credentials.json")

    client = MatrixClient(server)
    access_token = client.login_with_password(
        username,
        password,
        size[0])

    rooms = client.get_rooms()
    roomkeys = list(rooms.keys())
    room = roomkeys[0]
    nextRoom = 1
    endTime = client.end

    curses.halfdelay(10)
    maxDisplayName = 24
    displayNamestartingPos = 20
    pause = False

    client.add_listener(processMessage)
    client.start_listener_thread()

    while(True):
        size = stdscr.getmaxyx()

        stdscr.clear()
        stdscr.addstr(
            0, 0, (
                "redpill v0.5 · screen size: " + str(size) + " · chat size: "
                + str(len(rooms[room].events)) + " · room: " +
                str(room) + " · " + str(endTime)
            ), curses.A_UNDERLINE
        )

        current = len(rooms[room].events) - 1

        if True:
            y = 1
            if current >= 0:

                # TODO: something when the first event is a typing event
#reversed
                for event in reversed(rooms[room].events):
                    #stdscr.clear()
                    #stdscr.addstr(1, 0, str(event))
                    #stdscr.refresh()
                    if event["type"] == "m.typing":
                    #if True:
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
            elif c == ord("r"):
                rooms = client.get_rooms()

            stdscr.addstr(2, 0, "time() == %s\n" % time.time())

        finally:
            do_nothing = True

curses.wrapper(main)