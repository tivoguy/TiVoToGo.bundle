from subprocess import Popen, PIPE
from signal import *
from os import kill, getpid, environ, path, unlink, open, close, write, O_RDWR, O_CREAT
from sys import platform
from time import sleep
import urllib2, cookielib
from lxml import etree
import base64
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import thread
import string
import re
import copy
import socket
from collections import deque
import zeroconf

NAME = "TiVo To Go"
BUNDLE_NAME = "TiVoToGo.bundle"

TIVO_CONTENT_FOLDER     = "x-tivo-container/folder"
TIVO_CONTENT_SHOW_TTS   = "video/x-tivo-raw-tts"
TIVO_CONTENT_SHOW_PES   = "video/x-tivo-raw-pes"

TIVO_PORT            = 49492

TIVO_XML_NAMESPACE   = 'http://www.tivo.com/developer/calypso-protocol-1.6/'
TIVO_LIST_PATH       = "/TiVoConnect?Command=QueryContainer&Recurse=No&Container=%2FNowPlaying"

DownloadThread = None
GL_CURL_PID = 0
DL_QUEUE = deque()

####################################################################################################
def Start():

	ObjectContainer.title1 = NAME
	HTTP.CacheTime = 3600*5

####################################################################################################
def getMyMAC():
	return Prefs['MAC'] or ""


####################################################################################################
def getNameFromXML(show, name, default=""):
	result = show.xpath(name, namespaces={'g': TIVO_XML_NAMESPACE})
	if (len(result) > 0):
		return result[0]
	else:
		return default

####################################################################################################

def getTivoShowsByIPURL(tivoip, url, dir):
	anchoroffset = 0
	offset = 16
	endanchor = 0

	# Loop for all pages of the TiVo Now Playing
	while True:
		qurl = url + "&AnchorOffset=%i" % anchoroffset
		Log("getTivoShowsByIPURL: %s" % qurl)
		try:
			authhandler = urllib2.HTTPDigestAuthHandler()
			authhandler.add_password("TiVo DVR", "https://" + tivoip + ":443/", "tivo", getMyMAC())
			opener = urllib2.build_opener(authhandler)
			pagehandle = opener.open(qurl)
		except IOError, e:
			Log("Got a URLError trying to open %s" % url)
			if hasattr(e, 'code'):
				Log("Failed with code : %s" % e.code)
				if (int(e.code) == 401):
					dir.SetMessage("Couldn't authenticate", "Failed to authenticate to tivo.  Is the Media Access Key correct?")
				else:
					dir.SetMessage("Couldn't connect", "Failed to connect to tivo")
			if hasattr(e, 'reason'):
				Log("Failed with reason : %s" % e.reason)
			return dir
		except:
			Log("Unexpected error trying to open %s" % url)
			return dir

		myetree = etree.parse(pagehandle).getroot()
		page_total_items = getNameFromXML(myetree, "g:Details/g:TotalItems/text()")
		if page_total_items != "":
			endanchor = int(page_total_items)
		if anchoroffset == 0:
			page_item_count = getNameFromXML(myetree, "g:ItemCount/text()")
			if page_item_count != "":
				offset = int(page_item_count)

		for show in myetree.xpath("g:Item", namespaces={'g': TIVO_XML_NAMESPACE}):
			show_name = getNameFromXML(show, "g:Details/g:Title/text()")
			show_content_type = getNameFromXML(show, "g:Details/g:ContentType/text()")
			if (show_content_type == TIVO_CONTENT_FOLDER):
				show_total_items = int(getNameFromXML(show, "g:Details/g:TotalItems/text()"))
				show_folder_url = getNameFromXML(show, "g:Links/g:Content/g:Url/text()")
				show_folder_id = show_folder_url[show_folder_url.rfind("%2F")+3:]
				dir.add(DirectoryObject(key=Callback(getTivoShows, tivoip=tivoip, url=show_folder_url, showName=show_name), title=L("%s (%s)" % (show_name, show_total_items))))

			elif ((show_content_type == TIVO_CONTENT_SHOW_TTS) or
						(show_content_type == TIVO_CONTENT_SHOW_PES)) :
				show_duration = getNameFromXML(show, "g:Details/g:Duration/text()")
				show_episode_name = getNameFromXML(show,"g:Details/g:EpisodeTitle/text()")
				show_episode_num = getNameFromXML(show, "g:Details/g:EpisodeNumber/text()")
				show_desc = getNameFromXML(show, "g:Details/g:Description/text()")
				show_url = getNameFromXML(show, "g:Links/g:Content/g:Url/text()")
				show_in_progress = getNameFromXML(show,"g:Details/g:InProgress/text()")
				show_copyright = getNameFromXML(show, "g:Details/g:CopyProtected/text()")
			
				show_desc = show_desc[:show_desc.rfind("Copyright Tribune Media")]
				show_id  =  show_url[show_url.rfind("&id=")+4:]
				if (show_episode_num != ""):
					show_season_num = show_episode_num[:-2]
					show_season_ep_num = show_episode_num[-2:]

				if show_episode_name != "":
					target_name = show_name + ": " + show_episode_name
				else:
					target_name = show_name
				if show_copyright != "Yes" and show_in_progress != "Yes":
					localurl = "http://127.0.0.1:" + str(TIVO_PORT) + "/" + base64.b64encode(show_url, "-_")
					if Prefs['togo']:
						dir.add(DirectoryObject(key=Callback(getShowContainer, url = localurl,
										     show_url = show_url,
										     title = target_name,
										     summary = show_desc,
										     thumb = R('art-default.jpg'),
										     tagline = show_episode_name,
										     duration = show_duration),
									title=L(target_name)))

					else:
						dir.add(CreateVideoClipObject(url = localurl,
									      title = target_name,
									      summary = show_desc,
									      thumb = R('art-default.jpg'),
									      tagline = show_episode_name,
									      duration = show_duration))
			else:
				Log("Found a different content type: " + show_content_type)
		if endanchor == 0 or anchoroffset + offset >= endanchor:
			break
		else:
			anchoroffset += offset

	return dir

@route('/video/tivotogo/createvideoclipobject', allow_sync = True)
def CreateVideoClipObject(url, title, thumb, container = False, summary="", duration=14400000, tagline=""):
    Log.Debug("Starting a thread")
    thread.start_new_thread(TivoServerThread, ("127.0.0.1", TIVO_PORT))
    Log.Debug("Done Starting a thread")
    vco = VideoClipObject(
        key = Callback(CreateVideoClipObject, url = url, title = title, thumb = thumb,
		       tagline = tagline,
		       summary = summary, container = True,
		       duration = duration),
        url = url,
        title = title,
        thumb = thumb,
	summary = summary,
	tagline = tagline,
	duration = int(duration),
        items = [
            MediaObject(
                parts = [
                    PartObject(
			#key = HTTPLiveStreamURL(Callback(PlayVideo, url=url))
                        key = Callback(PlayVideo, url=url)
                    ),
                ],
                optimized_for_streaming = True
            )
        ]
    )

    if container:
        return ObjectContainer(objects = [vco])
    else:
        return vco
    return vco

####################################################################################################

@indirect
def PlayVideo(url):
	Log("Return PlayVideo: %s" % url)
	return IndirectResponse(VideoClipObject, key=url)

####################################################################################################
def getTvd():
	# Lack of a PMS api for a local path means we find the local
	# plugin resources the hard way duplicating some of Plugin.py
	if platform == "darwin":
		return path.join(environ['HOME'],
				 'Library',
				 'Application Support',
				 'Plex Media Server',
				 'Plug-ins',
				 BUNDLE_NAME,
				 'Contents',
				 'Resources',
				 'tivodecode.osx')

	if 'PLEXLOCALAPPDATA' in environ:
		key = 'PLEXLOCALAPPDATA'
	else:
		key = 'LOCALAPPDATA'

	Log("PLATFORM %s" % platform)
	return path.join(environ[key],
			 'Plex Media Server',
			 'Plug-ins',
			 BUNDLE_NAME,
			 'Contents',
			 'Resources',
			 'tivodecode')

####################################################################################################

class MyVideoHandler(BaseHTTPRequestHandler):

  def do_HEAD(self):
    try:
      self.send_response(200)
      self.send_header('Content-Type', 'video/mpeg2')
      self.end_headers()
      return
    except:
      Log("Got an Error")

  def do_GET(self):
    try:
      url = base64.b64decode(string.split(self.path[1:], "/")[0], "-_")
      Log("GET URL: %s" % url)
      self.send_response(200)
      self.send_header('Content-type', 'video/mpeg2')
      self.end_headers()
      tvd = getTvd()
      Log.Debug("TVD: %s" % tvd)
      Log.Debug("CMD: %s %s %s %s %s %s %s %s" % ("/usr/bin/curl", url, "--digest", "-s", "-u", "tivo:"+getMyMAC(), "-c", "/tmp/cookies.txt"))
      Log.Debug(" PIPED to: %s %s %s %s" % (tvd, "-m", getMyMAC(), "-"))
      if "LD_LIBRARY_PATH" in environ.keys():
        del environ["LD_LIBRARY_PATH"]
      curlp = Popen(["/usr/bin/curl", url, "--digest", "-s", "-u", "tivo:"+getMyMAC(), "-c", "/tmp/cookies.txt"], stdout=PIPE)
      tivodecode = Popen([tvd, "-m", getMyMAC(), "-"],stdin=curlp.stdout, stdout=PIPE)
      Log("Starting decoder")
      while True:
          data = tivodecode.stdout.read(4192)
          if not data:
              break
          self.wfile.write(data)

      #tivodecode.communicate()

    except Exception, e:
      Log("Unexpected error: %s" % e)

    try:
      kill(curlp.pid, SIGTERM)
      kill(tivodecode.pid, SIGTERM)
    except:
      Log("Self-exit of tivodecode/curl")

    Log("tivodecode/curl terminated")
    return

  def do_POST(self):
    Log("Got a Post")

####################################################################################################

def TivoServerThread(ip, port):
  try:
    httpserver = HTTPServer((ip, port), MyVideoHandler)
    Log("Server Starting: %i pid %i" % (port, getpid()))
    httpserver.allow_reuse_address = True
    httpserver.serve_forever()
    Log("Server Ooopsed out %i" % port)
  except :
    Log("Server Already Running or port in use")
  
####################################################################################################


def TivoVideo(count, pathNouns):
  Log("Starting a thread")
  thread.start_new_thread(TivoServerThread, ("127.0.0.1", TIVO_PORT))
  Log("Done Starting a thread")
  #playlist = PLS()
  #playlist.AppendTrack("http://127.0.0.1:" + str(TIVO_PORT) + "/" + pathNouns[1] + "/" + pathNouns[2], base64.b64decode(pathNouns[3], "-_"))
  #Plugin.Response["Content-Type"] = playlist.ContentType
  #return playlist.Content()
  url = "http://127.0.0.1:" + str(TIVO_PORT) + "/" + pathNouns[1] + "/" + pathNouns[2]
  #Log(str(Plugin.Redirect (url))
  Log("TivoVideo: URL %s" % url)
  return Plugin.Redirect (url)


####################################################################################################

def GetVideoURL(url, live = True):
    if url.startswith('rtmp') and Prefs['rtmp']:
        Log.Debug('*' * 80)
        Log.Debug('* url before processing: %s' % url)
        #if url.find(' ') > -1:
        #    playpath = GetAttribute(url, 'playpath', '=', ' ')
        #    swfurl = GetAttribute(url, 'swfurl', '=', ' ')
        #    pageurl = GetAttribute(url, 'pageurl', '=', ' ')
        #    url = url[0:url.find(' ')]
        #    Log.Debug('* url_after: %s' % RTMPVideoURL(url = url, playpath = playpath, swfurl = swfurl, pageurl = pageurl, live = live))
        #    Log.Debug('*' * 80)
        #    return RTMPVideoURL(url = url, playpath = playpath, swfurl = swfurl, pageurl = pageurl, live = live)
        #else:
        #    Log.Debug('* url_after: %s' % RTMPVideoURL(url = url, live = live))
        #    Log.Debug('*' * 80)
        #    return RTMPVideoURL(url = url, live = live)
        Log.Debug('* url after processing: %s' % RTMPVideoURL(url = url, live = live))
        Log.Debug('*' * 80)
        return RTMPVideoURL(url = url, live = live)
    elif url.startswith('mms') and Prefs['mms']:
        return WindowsMediaVideoURL(url = url)
    else:
        return HTTPLiveStreamURL(url = url)

####################################################################################################

@route("/video/tivotogo/showconatiner")
def getShowContainer(url, show_url, title, summary, thumb, tagline, duration):
	oc = ObjectContainer(title2=L(title))
	oc.add(CreateVideoClipObject(url = url,
				     title = title,
				     summary = summary,
				     thumb = R('art-default.jpg'),
				     tagline = tagline,
				     duration = duration))
	oc.add(DirectoryObject(key = Callback(downloadLocal, url=show_url, title=title), title = 'Download Locally'))
	return oc

####################################################################################################

def dlThread():

	global GL_CURL_PID
	global DownloadThread
	global DL_QUEUE

	while True:
		if DL_QUEUE:
			(fileName, url) = DL_QUEUE[0]
		else:
			break
		try:
			tvd = getTvd()
			Log.Debug("CMD: %s \"%s\" %s %s %s %s %s %s" % ("/usr/bin/curl", url, "--digest", "-s", "-u", "tivo:"+getMyMAC(), "-c", "/tmp/cookies.txt"))
			Log.Debug(" PIPED to: \"%s\" %s %s %s \"%s\" %s" % (tvd, "-m", getMyMAC(), "-o", fileName, "-"))
			Log("Downloading: %s From: %s", fileName, url)
			if "LD_LIBRARY_PATH" in environ.keys():
				del environ["LD_LIBRARY_PATH"]
			try:
				unlink("/tmp/cookies.txt")
			except:
				pass
			curlp = Popen(["/usr/bin/curl", url, "--digest", "-s", "-u", "tivo:"+getMyMAC(), "-c", "/tmp/cookies.txt"], stdout=PIPE)
			tivodecode = Popen([getTvd(), "-m", getMyMAC(), "-o", fileName, "-"], stdin=curlp.stdout)
			GL_CURL_PID = curlp.pid
			tivodecode.wait()
			kill(curlp.pid, SIGTERM)
			sleep(1)
		except Exception, e:
			Log("Error in Download Thread: %s" % e)
		DL_QUEUE.popleft()
		Log("Download complete: %s" % fileName)
		GL_CURL_PID = 0
	DownloadThread = None

####################################################################################################

@route("/video/tivotogo/downloadlocal")
def downloadLocal(url, title):
	global DownloadThread
	global DL_QUEUE
	ttgdir = Prefs['togodir']
	if not ttgdir:
		return ObjectContainer(header='Error', message='TiVo To Go Download Directory is not available from the preferences.', title2='ERROR: No TTG Directory')
	try:
		pth = path.join(ttgdir, "tmp.txt")
		f = open(pth, O_CREAT | O_RDWR)
		write(f, "Test123")
		close(f)
		unlink(pth)
	except Exception, e:
		Log("TTG Exception: %s" % e)
		return ObjectContainer(header='Error', message='TiVo To Go Download Directory is not writeable', title2='ERROR: Cannot Write to TTG dir')

	Log("URL: %s" % url)
	Log("Title: %s" % title)

        try:
		fileName = path.join(ttgdir, title + ".mpg")
		jobs = copy.deepcopy(DL_QUEUE)
		do_dl = True
		while jobs:
			(tryName, tryURL) = jobs.popleft()
			if (tryName == fileName):
				do_dl = False
		if do_dl:
			DL_QUEUE.append((fileName, url))
			# Race found on OSX setting the thread where it can
			# exit so fast the global has a data hazard
			if not DownloadThread or len(DL_QUEUE) == 1:
				DownloadThread = Thread.Create(dlThread)
			message = 'Queued download of: %s' % title
			title2 = 'Download Queued'
		else:
			message = 'Already Queued: %s' % title
			title2 = 'Download Queued'
        except Exception, e:
		DownloadThread = None
		Log("Error starting DL thread: %e" % e)
		message = 'Error starting the Download Thread'
		title2 = 'Download Error'

	return ObjectContainer(header=title2, message=message, title2=title2)

####################################################################################################

def discoverTiVo(oc):

    class ZCListener:
        def __init__(self, names):
            self.names = names

        def removeService(self, server, type, name):
            self.names.remove(name)

        def addService(self, server, type, name):
            self.names.append(name)

    REMOTE = '_tivo-videos._tcp.local.'
    tivo_names = []

    # Get the names of TiVos offering network remote control
    try:
        serv = zeroconf.Zeroconf()
        browser = zeroconf.ServiceBrowser(serv, REMOTE, ZCListener(tivo_names))
    except Exception, e:
        Log("Error staring Zero Conf: %s" % e)
        return oc

    # Give them a second to respond
    sleep(0.7)

    # For proxied TiVos, remove the original
    for t in tivo_names[:]:
        if t.startswith('Proxy('):
            try:
                t = t.replace('.' + REMOTE, '')[6:-1] + '.' + REMOTE
                tivo_names.remove(t)
            except:
                pass

    # Now get the addresses -- this is the slow part
    swversion = re.compile('(\d*.\d*)').findall
    for t in tivo_names:
        Log("Found TiVo by Name: %s" % t)
        s = serv.getServiceInfo(REMOTE, t)
        if s:
            tivoName = t.replace('.' + REMOTE, '')
            addr = socket.inet_ntoa(s.getAddress())
            try:
                port = s.getPort()
                url_proto = s.getProperties()['protocol']
                url_path = s.getProperties()['path']
		url = "%s://%s:%s%s" % (url_proto, addr, port, url_path)
		Log("Found TiVo URL %s" % url)
                oc.add(DirectoryObject(key=Callback(getTivoShows, tivoName=tivoName, url=url, tivoip=addr), title=L(tivoName)))
            except Exception, e:
                Log("Error finding Tivo: %s" % e)
                pass

    serv.close()
    return oc

####################################################################################################

@route("/video/tivotogo/shows")
def getTivoShows(tivoName="", url="", tivoip="", showName=""):
	if showName == "":
		oc = ObjectContainer(title2=L(tivoName))
	else:
		oc = ObjectContainer(title2=L(showName))

	if url == "":
		url = "https://" + tivoip + ":443" + TIVO_LIST_PATH
	return getTivoShowsByIPURL(tivoip, url, oc)

####################################################################################################

@route('/video/tivotogo/getStatus')
def getStatus(rand, execkill=0):
	global DownloadThread
	global GL_CURL_PID
	global DL_QUEUE
	oc = ObjectContainer(title2='Downloading')
	if execkill and GL_CURL_PID:
		kill(GL_CURL_PID, SIGTERM)
		sleep(2)
	jobs = copy.deepcopy(DL_QUEUE)
	if DownloadThread and jobs:
		if jobs:
			(fileName, url) = jobs.popleft()
			oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random())), title = 'Running: %s' % fileName))
		while jobs:
			(fileName, url) = jobs.popleft()
			oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random())), title = 'Queued: %s' % fileName))
		oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random()), execkill = 1), title = 'Kill Current Job...'))
	else:
		oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random())), title = 'Job Queue Empty'))
	oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random())), title = 'Refresh'))
	return oc

####################################################################################################

@handler("/video/tivotogo", NAME, thumb="icon-default.jpg", art="art-default.jpg")
def MainMenu():

	myMAC = getMyMAC()

	oc = ObjectContainer()

	if (len(myMAC) == 10):
		tivoName = Prefs['tivoStaticIP'] or ""
		if tivoName == "":
			discoverTiVo(oc)
		else:
			oc.add(DirectoryObject(key=Callback(getTivoShows, tivoName=tivoName, tivoip=tivoName), title=L(tivoName)))
	global DownloadThread
	if DownloadThread:
		oc.add(DirectoryObject(key = Callback(getStatus, rand=str(Util.Random())), title = 'Active Downloads'))
	oc.add(PrefsObject(title=L("Preferences...")))

	return oc
