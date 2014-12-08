TiVoToGo.bundle
================

This Plex plugin uses the TiVo To Go API to watch a stream off a TiVo
or to download a recorded program from the TiVo.  It requires a Series
2 or newer TiVo with an ethernet connection.  The Plex Server needs to
have a high speed connection between itself and the TiVo.

Requires:
- Linux, OSX or Windows Plex Server (No direct NAS support)
- On Linux and OSX requires curl be installed

To Do:
- Probably build a statically linked tivodecode for linux
- Use the urllib instead of curl
- Stop using /tmp/cookies.txt
- Use dynamic sockets and a fixed URL for the live stream video

Installation Instructions
-------------------------
1.  Install curl if you don't already have it
2.  Copy TiVoToGo.bundle to your plugin directory
    * Mac: ~/Library/Application Support/Plex Media Server/Plug-ins
    * Windows: C:\Users\\[user]\AppData\Local\Plex Media Server\Plug-ins
    * Linux: /var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins
3.  Make sure to update the plugins settings
    * Enter your Media Access Key from the TiVo
    * Enter a IP address for the TiVo if the Plex Server is on a
      different subnet and then exit the channel and enter it again.
    * If you want enable the To Go offline download check the box and
      fill in a directory that is writable by the plex user.

Contribute to the project if you like! :-)

https://github.com/tivoguy/TiVoToGo.bundle

