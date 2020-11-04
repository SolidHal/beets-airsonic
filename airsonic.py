# This file is part of beets-airsonic.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

from beets import plugins
from beets import util
from beets import ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from beets.ui.commands import _do_query
import libsonic
import datetime
import time
import logging

date = datetime.datetime.now()

# could have sync called on the items returned by the item_moved event, but that would result in an multiple api called to the airsonic server for every song and would have to wait for the airsonic server to rescan media files after every song
# instead, after import, do a media rescan, then do a beet query for all songs imported today

class airsonic(BeetsPlugin):
    def __init__(self):
        super(airsonic, self).__init__()

        self.config['password'].redact = True

        log = self.config['log'].get()


        # Have everything that goes to the console, also print to the log
        logFormatter = logging.Formatter("%(asctime)s [ %(levelname)-5.5s]  %(message)s")
        rootLogger = self._log
        fileHandler = logging.FileHandler(log)
        fileHandler.setFormatter(logFormatter)
        rootLogger.addHandler(fileHandler)

    def commands(self):
        airsonicsync = Subcommand('airsonicsync', help='sync new imports to the airsonic monthly playlist')
        airsonicsync.func = self.sync

        airsonictest = Subcommand('airsonictest', help='ping the airsonic server defined in the config')
        airsonictest.func = self.test


        airsonicscan = Subcommand('airsonicscan', help='run a scan on the airsonic server')
        airsonicscan.func = self.scan
        return [airsonicsync, airsonictest, airsonicscan]

    def sync(self, lib, opts, args):
        self._log.info(u'~~~~~Syncing new imports to monthly playlist~~~~~')
        conn = self.connect()

        self.scanMediaFolders(conn)
        newSongIds = self.getNewSongs(lib, conn)
        if not newSongIds:
            self._log.info(u'No new songs to sync, leaving')
            return
        playlistId = self.getCurPlaylist(conn)
        self.addSongsToPlaylist(conn, newSongIds, playlistId)

    # connect to the specified server, returns a libsonic.Connection
    def connect(self):
            baseUrl = self.config['baseurl'].get()
            apiPath = self.config['apipath'].get()
            apiVersion = self.config['apiversion'].get()
            user = self.config['user'].get()
            password = self.config['password'].get()
            port = self.config['port'].get()
            # We pass in the base url, path, the username, password, port number and api version
            # Be sure to use https:// if this is an ssl connection!
            conn = libsonic.Connection(
                baseUrl=baseUrl,
                port=port,
                serverPath=apiPath,
                apiVersion=apiVersion,
                username=user,
                password=password
            )
            return conn

    # run a scan on the airsonic server
    def scan(self, lib, opts, args):
        conn = self.connect()
        self.scanMediaFolders(conn)
        print("scan complete")

    # try to get, and print two random songs to ensure we can contact the server
    def test(self, lib, opts, args):
        conn = self.connect()
        reply = conn.ping()

        if reply:
            print("Successfully connected to server")
        else:
            print("Could not contact server, ensure the information in the config is correct and the server includes http:// or https://")

    # to get the playlist, get all playlists, get the playlist id of the playlist with the current year and month in the name
    # returns None if the playlist doesn't exist
    def getCurPlaylist(self, conn):
        playlistId = None
        currName = date.strftime("%Y") + " " + date.strftime("%m") + " " + date.strftime("%B")
        reply = conn.getPlaylists()
        replylist = reply.get("playlists")
        playlists = replylist.get("playlist")
        for playlist in playlists:
            if (playlist.get("name") == currName):
                playlistId = playlist.get("id")
                return playlistId

        return playlistId

    # prompts a scan of the media folder, waits for the scan to complete to return
    def scanMediaFolders(self, conn):
        conn.startScan()
        status = conn.getScanStatus()
        scanStatus = status.get("scanStatus")
        scanning = scanStatus.get("scanning")
        while(scanning):
            time.sleep(5)
            status = conn.getScanStatus()
            scanStatus = status.get("scanStatus")
            scanning = scanStatus.get("scanning")


    # to get the songs, do a beets query for songs added on this date, get the song title and artist/album artist ID3 tag, then do a api search for said songs
    def getNewSongs(self, lib, conn):
        newSongIds = []
        query = "added:" + str(date.year) + "-" + str(date.month) + "-" + str(date.day)
        try:
            items = _do_query(lib, query, False, False)
        except:
            return []
        #get the songs list from the tuple
        songs = items[0]
        self._log.info(u'----Locating:-----')
        for item in songs:
            if not item: # skip empty lists
                continue
            self._log.info(u'{0.title} by {0.artist} on album {0.album} in beets is:', item)
            searchQuery = item.title + " " + item.artist
            reply = conn.search3(searchQuery, artistCount=1, albumCount=1, songCount=1)
            #peel back the artist and album layers to get the song id
            searchResult = reply.get("searchResult3")
            song = searchResult.get("song")
            song = song[0] #peel back the list
            self._log.info(u'{} by {} on album {} in airsonic', song.get("title"), song.get("artist"), song.get("album"))
            songId = song.get("id")
            newSongIds.append(songId)

        return newSongIds

    def addSongsToPlaylist(self, conn, newSongIds, playlistId):
        # if playlistId is none, aka the playlist was not found, this createPlaylist will create the playlist with currName
        # if the name is set to None, then it will use the ID to update the playlist with the provided list of song ids
        if(playlistId == None):
            # make the playlist, add the songs
            self._log.info(u'----Playlist doesnt exist, creating-----')
            currName = date.strftime("%Y") + " " + date.strftime("%m") + " " + date.strftime("%B")
            conn.createPlaylist(None, currName, newSongIds)
            #print the playlist contents after modification
            newPlaylistId = self.getCurPlaylist(conn)
            self.logSongsInPlaylist(conn, newPlaylistId)
        else:
            # Get all the songs currently in the playlist, then append the new song ids.
            currentSongIds = [] # the songs currently in the playlist
            reply = conn.getPlaylist(playlistId)
            playlist = reply.get("playlist")
            name = playlist.get("name")
            songs = playlist.get("entry")
            if (playlist.get("songCount") == 0):
                self._log.info(u'----Playlist {} exists, and is empty before addition:----', name)
            else:
                self._log.info(u'----Playlist {} before addition:----', name)
                for song in songs:
                    self._log.info(u'{}', song.get("title"))
                    currentSongIds.append(song.get("id"))

            allIds = currentSongIds + newSongIds
            conn.createPlaylist(playlistId, None, allIds)
            #print the playlist contents after modification
            self.logSongsInPlaylist(conn, playlistId)

    def logSongsInPlaylist(self, conn, playlistId):
        reply = conn.getPlaylist(playlistId)
        playlist = reply.get("playlist")
        name = playlist.get("name")
        songs = playlist.get("entry")
        self._log.info(u'----Playlist {} has the following songs:----', name)
        for song in songs:
            self._log.info(u'{}', song.get("title"))
