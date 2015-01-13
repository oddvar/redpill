# -*- coding: utf-8 -*-

import urlparse
import urllib
import re
import requests
import json
import time
import datetime
import curses
#sys.path.append("/home/oddvar/src/matrix/matrix-python-sdk/")
from matrix_client.client import MatrixClient
#from pprint import pprint


def loadCredentials(filename):
    global password, username, server
    json_data = open(filename)
    data = json.load(json_data)
    #pprint(data)
    json_data.close()

    username = data["username"]
    password = data["password"]
    server = data["server"]


def login():
    global access_token
    # TODO: should do a GET first to find access methods

    url = server + '/_matrix/client/api/v1/login'  # lint:ok
    values = {
        "type": "m.login.password", "user": username,   # lint:ok
        "password": password  # lint:ok
    }

    params = json.dumps(values).encode('utf8')
    #print(str(params))
    req = urllib.request.Request(
        url, data=params,
        headers={'content-type': 'application/json'}
    )

    response = urllib.request.urlopen(req)

    #obj = json.load(response)
    str_response = response.readall().decode('utf-8')
    obj = json.loads(str_response)
    #print(obj)
    access_token = obj["access_token"]


def initialRoomSync(roomId):
    url = (
        server + '/_matrix/client/api/v1/rooms/' + roomId +   # lint:ok
        '/initialSync'
    )

    #values = {"type":"m.login.password", "user":username, "password":password }
    values = {"access_token": access_token, "limit": 1}   # lint:ok
    url_values = urllib.parse.urlencode(values)
    #print(url_values)
    url += "?" + url_values
    #print(url)
    #params = json.dumps(values).encode('utf8')
    #print(str(params))
    req = urllib.request.Request(
        url, headers={'content-type': 'application/json'}
    )
    response = urllib.request.urlopen(req)

    str_response = response.readall().decode('utf-8')
    obj = json.loads(str_response)
    #print(json.dumps(obj, indent=4))
    test = obj["messages"]["end"]

    if 'end' in obj:
        test = obj["end"]
    return test


def initialSync(maxMessages):

    url = server + '/_matrix/client/api/v1/initialSync'   # lint:ok
    #values = {"type":"m.login.password", "user":username, "password":password }
    values = {"access_token": access_token, "limit": maxMessages}   # lint:ok
    url_values = urllib.parse.urlencode(values)
    #print(url_values)
    url += "?" + url_values
    #print(url)
    #params = json.dumps(values).encode('utf8')
    #print(str(params))
    req = urllib.request.Request(
        url, headers={'content-type': 'application/json'}
        )

    response = urllib.request.urlopen(req)

    str_response = response.readall().decode('utf-8')
    obj = json.loads(str_response)
    #print(json.dumps(obj, indent=4))
    #test = obj["messages"]["end"]
    return obj


def listenForEvent(room, end):
    url = server + '/_matrix/client/api/v1/events'   # lint:ok
    values = {"access_token": access_token, "from": end}   # lint:ok
    url_values = urllib.parse.urlencode(values)
    #print(url_values)
    url += "?" + url_values
    req = urllib.request.Request(
        url, headers={'content-type': 'application/json'}
    )
    response = urllib.request.urlopen(req)

    str_response = response.readall().decode('utf-8')
    obj = json.loads(str_response)
    #print(json.dumps(obj, indent=4))
    test = end
    if 'end' in obj:
        test = obj["end"]
    return test

def listenForMessage(room):
    global endTime

    url = (
        server + '/_matrix/client/api/v1/rooms/' + room +  # lint:ok
        "/messages"
    )
    query_params = {}
    query_params["access_token"] = access_token
    query_params["from"] = endTime

    return _send("GET", url, None, query_params)


def _send(method, path, content=None, query_params={}, headers={}):
    method = method.upper()
    if method not in ["GET", "PUT", "DELETE", "POST"]:
        raise MatrixError("Unsupported HTTP method: %s" % method)

    headers["Content-Type"] = "application/json"
    #query_params["access_token"] = access_token
    #query_params["from"] =  data[room]["endTime"]
    endpoint = path

    response = requests.request(
        method, endpoint, params=query_params,
        data=json.dumps(content), headers=headers
        , verify=False
    )

    if response.status_code < 200 or response.status_code >= 300:
        raise MatrixRequestError(
            code=response.status_code, content=response.text
        )

    return response.json()

def listenForMessage2(room):
    global data, stdscr, endTime
    url = (
        server + '/_matrix/client/api/v1/rooms/' + room +  # lint:ok
        "/messages"
    )

    values = {
        "access_token": access_token, "from": endTime   # lint:ok
    }
    url_values = urllib.parse.urlencode(values)
    #print(url_values)
    url += "?" + url_values
    stdscr.addstr(1, 0, "checking messages for " + room)
    stdscr.refresh()
    #c = stdscr.getch()

    req = urllib.request.Request(
        url, headers={'content-type': 'application/json'}
    )
    response = urllib.request.urlopen(req)

    str_response = response.readall().decode('utf-8')
    obj = json.loads(str_response)
    #print(json.dumps(obj, indent=4))
    test = data[room]["endTime"]   # lint:ok
    if 'end' in obj:
        test = obj["end"]

    return obj


def processBackFill(backFill):
    global data

    if "rooms" in backFill:
        for r in backFill["rooms"]:
            room = r.get("room_id", "unknown")
            #print(room)
            if "messages" in r:
                newMessages = r.get("messages")
                test = newMessages.get("end")
                if "chunk" in newMessages:
                    for thing in newMessages.get("chunk"):
                        #if "content" in thing and "body" in thing["content"]:  #can also be join msgs
                        if True:
                            registerRoom(room)
                            temp = data[room]["messages"]["chunk"]
                            temp.append(thing)
                            data[room]["messages"]["chunk"] = temp
                            data[room]["endTime"] = test


def processMessage(obj):
    global data

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
                #data[room]["endTime"] = test
                didWeProcessSomethingSuccessfully = room
    return didWeProcessSomethingSuccessfully


def registerRoom(roomid):
    global data, rooms

    if roomid not in data:
        rooms.append(roomid)
        data[roomid] = {}
        data[roomid]["messages"] = {}
        data[roomid]["messages"]["chunk"] = []
        #end = initialRoomSync(roomid)
        #data[roomid]["endTime"] = end  # do this in the function above


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

    incrementalTextOffset = 0
    incrementalText("loading")
    loadCredentials("credentials")

    incrementalText(".")
    client = MatrixClient(server)
    incrementalText(".")
    access_token = client.login_with_password(username=username, password=password)
    incrementalText(".")

#room = client.create_room("myroom")
    #room.send_image(file_like_object)

    #Usage (logged in):
    #    client = MatrixClient("https://matrix.org", token="foobar")
    #rooms = client.get_rooms()  # NB: From initial sync
    #client.add_listener(func)  # NB: event stream callback
    #rooms[0].add_listener(func)  # NB: callbacks just for this room.
    #room = client.join_room("#matrix:matrix.org")
    #response = room.send_text("Hello!")
    #response = room.kick("@bob:matrix.org")


    rooms = []
    #"!cURbafjkfsMDVwdRDQ:matrix.org",  # main
   #     "!HqyIHODmvZcSvOGJqw:matrix.org",  # odd
   #     "!XqBunHwQIXUiqCaoxq:matrix.org",  # dev
   #     "!zOmsiVucpWbRRDjSwe:matrix.org",  # internal
   #     "!vfFxDRtZSSdspfTSEr:matrix.org",  # test
   #     "!pDoZaoxgqWkenMFAyE:matrix.org",  #testing123
   #     "!BbbQBRcbpgRhtyAead:matrix.org"   # oddvar-oddvar.org 1-1 chat
    #]
    data = {}

    size = stdscr.getmaxyx()

    #print(client)
    #print(access_token)

    #backFill = initialSync(1) #size[0])
    #print(backFill)
    #backFill = client.initial_sync(size[0])
    backFill = client.api.initial_sync(size[0])
    try:
        for room in backFill["rooms"]:
            incrementalText(".")
            client._mkroom(room["room_id"])
            client.end = backFill["end"]
    except KeyError:
        pass

    incrementalText(".")
    #print("-----")
    #print(backFill)
    #print("----")
    #print(client.rooms)
    #print("---")
    #rooms = []

    #for r in client.rooms:
    #    registerRoom(str(r))
    #    incrementalText(".")

    endTime = client.end
    processBackFill(backFill)
    incrementalText(".")

    nextRoom = 0
    room = rooms[len(rooms) - 1]


    curses.halfdelay(10)
    maxDisplayName = 24
    displayNamestartingPos = 20
    pause = False

    #room = "!HqyIHODmvZcSvOGJqw:matrix.org" ## delete

    while(True):
        size = stdscr.getmaxyx()

        obj = None
#        stdscr.addstr(5, 0, "H: " + endTime)
#        stdscr.refresh()
        obj = client.listen_for_events(endTime, 100)
        response = processMessage(obj)
        if response is not None:
            room = response

 #       stdscr.addstr(8, 0, "Ha: " + str(obj))
 #       stdscr.refresh()
        #time.sleep(10)

        #for r in rooms:
  #      if False:
   #         obj = listenForMessage(str(r))

    #        stdscr.addstr(1, 0, "checking messages for " + r + " from " +
     #           endTime)
      #      stdscr.addstr(2, 0, str(obj))


       #     stdscr.addstr(3, 0, endTime)
        #    stdscr.refresh()

         #   if processMessage(obj, str(r)):
          #      room = str(r)

        #if 'end'.encode('utf-8') in obj:
        #stdscr.addstr(7, 0, "H: " + endTime)
        key = "end".encode("utf-8")
        #stdscr.addstr(7, 30, "N: " + str(obj.get(key)))
        endTime = obj.get(key)
        #endTime = obj.get("end".encode('utf-8')) #""str(obj["u'end'"])
        #stdscr.refresh()
        #time.sleep(5)
            #time.sleep(5)

        stdscr.clear()
        stdscr.addstr(
            0, 0, ("redpill v0.3 · screen size: " + str(size) +
            " · chat size: " + str(len(data[room]["messages"]["chunk"])) +
            " · room: " + str(room)), curses.A_UNDERLINE
        )

        current = len(data[room]["messages"]["chunk"]) - 1

        #for y in range(1, size[0]):
        if True:
            y = 1
            if current >= 0:

                # TODO: something when the first event is a typing

                for event in reversed(data[room]["messages"]["chunk"]):
                    if event["type"] == "m.typing":
                        pass # do something clever
                    else:
                        currentLine = size[0] - y

                        if currentLine < 3: # how many lines we want to reserve
                            break
                        y += 1
                        if "origin_server_ts" in event:
                            convertedDate = datetime.datetime.fromtimestamp(
                                int(
                                    event["origin_server_ts"] / 1000)
                                ).strftime('%Y-%m-%d %H:%M:%S')

                            stdscr.addstr(currentLine, 0, convertedDate)
                        # find length
                        if "user_id" in event:
                            length = len(
                                event["user_id"]
                            )
                        else:
                            user_id = ""
                        # assumption: body == normal message
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
                                currentLine, displayNamestartingPos + maxDisplayName
                                + 3, buf[:size[1] -
                                (displayNamestartingPos + maxDisplayName + 4)],
                                curses.A_BOLD
                            )

                        # membership == join/leave events
                        elif "membership" in event["content"]:
                            buf = " has left"
                            if event["content"]["membership"] == "join":
                                buf = " has joined"

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
        #time.sleep(1)
        try:
            c = stdscr.getch()
            if c == -1:
                stdscr.addstr(1, 0, "timeout")
            elif c == 9:
                stdscr.addstr(1, 0, "%s was pressed\n" % c)
                room = rooms[nextRoom]
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
                #main.endwin()
                #stdscr.endwin()
                curses.endwin()
                quit()
            stdscr.addstr(2, 0, "time() == %s\n" % time.time())

        finally:
            do_nothing = True

curses.wrapper(main)

#main(False)