import youtube_dl
from bypy import ByPy
import requests, time, json
import os, sys, logging
import nonebot

pathExport = ''   #oneDrive path
path = ''   #a temp path
googleAPIKey = ''     #google api key

def main():
    if not getStatus():
        logging.warning('There is one task running.')
        return

    var = sys.argv
    print(var)
    setting = var[1]

    try:
        if setting == 'single':
            videoID = var[2]
            groupID = var[3]
            downloadVideo(videoID, 'others', groupID)

        else:
            userInDict = getConfig()
            if not userInDict:
                logging.warning('Init failed when trying to download videos.')
                exit(-1)

            for elements in userInDict:
                getFirstVideo(userInDict[elements]['channel'], elements, userInDict[elements]['qqGroup'])
                time.sleep(10)

    except Exception as e:
        logging.warning('Unknown error occurred. %s' % e)
        registerTrue()

def registerTrue():
    file = open('', 'r')
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = True
    with open('', 'w+') as f:
        json.dump(statusDict, f, indent=4)

def registerFalse():
    file = open('', 'r')
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = False
    with open('', 'w+') as f:
        json.dump(statusDict, f, indent=4)

def getStatus():
    file = open('', 'r')
    statusDict = json.loads(str(file.read()))
    return statusDict['status']

def getConfig() -> dict:
    file = open('', 'r+')     #config file path
    fl = file.read()
    import json
    try:
        downloadDict = json.loads(str(fl))
    except Exception as e:
        logging.warning('Something went wrong when getting download config. %s' % e)
        return {}

    return downloadDict

def getFirstVideo(ID : str, name : str, groupID):
    logger = logging.getLogger('getFirstVideo')
    baseURL = 'https://www.googleapis.com/youtube/v3/activities' \
              '?key=%s&channelId=%s&part=contentDetails&order=date&maxResults=5' % (googleAPIKey, ID)

    json_data = None
    try:
        json_data = requests.get(baseURL, timeout=10).json()

    except Exception as e:
        logger.warning('Something went wrong when fetching data from youtube. %s' % e)
        registerTrue()

    if json_data is not None:
        try:
            videoID = json_data['items'][0]['contentDetails']['upload']['videoId']
        except KeyError:
            logger.warning('Quota exceeded..')
            registerTrue()
            return

        logger.warning('Current Video ID is: %s' % videoID)

        downloadVideo(videoID, name, groupID)

def downloadVideo(videoID : str, name : str, groupID):
    merge = True
    registerFalse()
    youtubeLink = "https://www.youtube.com/watch?v=%s" % videoID
    logger = logging.getLogger('downloadVideo')
    realPath = path + name + '/' + 'temp.mp4'
    realPath2 = path + name + '/' + 'temp_bulk.mp4'

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]/bestvideo',
        'outtmpl': '%s' % realPath if name == 'others' else realPath2,
        'noplaylist': True
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            videoTitle_temp = ydl.extract_info(youtubeLink, download=False).get('title')
            videoTitle = videoTitle_temp[0: len(videoTitle_temp) // 3 - 1]
            videoTitle = videoTitle.replace('|', '').replace(' ', '-').replace('/', '~')

    except youtube_dl.utils.ExtractorError:
        logger.warning('Current Video is not available yet')
        registerTrue()
        return

    realPath3 = pathExport + name + '/' + '%s.mp4' % videoTitle
    logger.warning('Downloading in %s' % realPath)

    if not os.path.exists(path + name + '/'):
        os.makedirs(path + name + '/')

    if not os.path.exists(pathExport + name + '/'):
        os.makedirs(pathExport + name + '/')

    if not (os.path.exists(realPath) or os.path.exists(realPath2) or os.path.exists(realPath3)):
        logger.warning('Download will be starting shortly.\nVideo ID: %s' % videoID)
        registerFalse()
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtubeLink])

            logger.warning('Download is completed.\nVideo title: %s' % videoTitle)

            if merge:
                logger.warning('Now downloading audio for %s...' % videoTitle)
                audioName = 'tempAudio' if name == 'others' else 'tempAudio_bulk'

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': '%s%s/%s.m4a' % (path, name, audioName),
                    'noplaylist': True
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtubeLink])

                logger.warning('audio download completed. Trying to merge video %s...' % videoTitle)
                mergeVideos(videoTitle, name)

            try:
                uploadStuff(videoTitle_temp, groupID, retcode=0)
            except Exception as e:
                logger.warning('Something went wrong when uploading file. %s' % e)
                registerTrue()

        except Exception as e:
            logger.warning("Something went wrong when trying to download. %s" % e)
            registerTrue()

    else:
        logger.warning('Download has already finished.')
        registerTrue()

def mergeVideos(videoTitle, name):
    from subprocess import run
    if name == 'others':
        run ([
            "D:/youtube/ffmpeg/bin/ffmpeg",
            "-i",
            "%s%s/temp.mp4" % (path, name),
            "-i",
            "%s%s/tempAudio.m4a" % (path, name),
            "-acodec",
            "copy",
            "-c:a",
            "aac",
            "-vcodec",
            "copy",
            "%s%s/%s.mp4" % (pathExport, name, videoTitle)
        ])

        os.remove("%s%s/temp.mp4" % (path, name))
        os.remove("%s%s/tempAudio.m4a" % (path, name))

    else:
        run([
            "D:/youtube/ffmpeg/bin/ffmpeg",
            "-i",
            "%s%s/temp_bulk.mp4" % (path, name),
            "-i",
            "%s%s/tempAudio_bulk.m4a" % (path, name),
            "-acodec",
            "copy",
            "-c:a",
            "aac",
            "-vcodec",
            "copy",
            "%s%s/%s.mp4" % (pathExport, name, videoTitle)
        ])

        os.remove("%s%s/temp_bulk.mp4" % (path, name))
        os.remove("%s%s/tempAudio_bulk.m4a" % (path, name))

    registerTrue()

def uploadStuff(videoName : str, groupID, retcode=-1):
    
    file = open('E:/Python/qqBot/config/YouTubeNotify.json', 'r')
    fl = file.read()
    downloadedDict = json.loads(str(fl))
    downloadedDict[videoName] = {
        "status" : False,
        "group_id" : groupID,
        "retcode" : retcode
    }

    with open('E:/Python/qqBot/config/YouTubeNotify.json', 'w+') as f:
        json.dump(downloadedDict, f, indent=4)

if __name__ == '__main__':
    main()
