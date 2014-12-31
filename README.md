TiVoToGo.bundle
================

This Plex plugin uses the TiVo To Go API to watch a stream off a TiVo
or to download a recorded program from the TiVo.  It requires a Series
2 or newer TiVo with an ethernet connection.  The Plex Server needs to
have a high speed connection between itself and the TiVo.

Q: What would I use this channel for?

A: You browse to a show on your TiVo and watch it without downloading
   it to the Plex Server.

Q: Can I download something from the TiVo it to the Plex Server using
   this channel?

A: Yes!  If you enable the TiVoToGo service, and fill in a folder
   name, the channel will have extra entries to allow you to download
   the content.

   NOTE: You should create a library on your Plex server which points
   to the same directory which you are downloading the file into.  If
   you name the Plex library "TiVo To Go" it will automatically get
   refreshed when downloads are initiated and when they complete.  If
   you decide to name the Plex library something different simply add
   that name in the TiVoToGo preferences.

Requires:
- Linux, OSX or Windows Plex Server (No ARM Processor NAS support)
- On Linux, OSX or X86 NAS requires curl be installed

To Do:
- Use the urllib instead of curl
- Stop using /tmp/cookies.txt
- Use dynamic sockets and a fixed URL for the live stream video
- If the community support for the MPEG-TS improves, add MPEG-TS
  support, for now it only works with MPEG-PS

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

