import youtube_dl
from bypy import ByPy
import requests, time, json
import os, sys, logging
import nonebot

pathExport = 'D:/hanayori.paryi.xyz/OneDrive - paryi/Others/'
path = 'D:/dl/Others/'
googleAPIKey = 'AIzaSyCGjl5IedVCHJYKWVdYVbmJnflgiP_GrA4'
uploader = 'D:/BaiduService/BaiduPCS-Go-v3.6-windows-x64/BaiduPCS-Go-v3.6-windows-x64/BaiduPCS-Go.exe'

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
    file = open('D:/dl/started.json', 'r')
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = True
    with open('D:/dl/started.json', 'w+') as f:
        json.dump(statusDict, f, indent=4)

def registerFalse():
    file = open('D:/dl/started.json', 'r')
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = False
    with open('D:/dl/started.json', 'w+') as f:
        json.dump(statusDict, f, indent=4)

def getStatus():
    file = open('D:/dl/started.json', 'r')
    statusDict = json.loads(str(file.read()))
    return statusDict['status']

def getConfig() -> dict:
    file = open('E:/Python/qqBot/config/downloader.json', 'r+')
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
            if len(videoTitle_temp) > 20:
                videoTitle = videoTitle_temp[0 : 19]
            else:
                videoTitle = videoTitle_temp
            videoTitle = videoTitle.replace('|', '').replace(' ', '-').replace('/', '~')

    except youtube_dl.utils.ExtractorError:
        logger.warning('Current Video is not available yet')
        registerTrue()
        return

    realPath3 = pathExport + name + '/' + videoTitle + '.mp4'
    logger.warning('Downloading in %s' % realPath)

    if not os.path.exists(path + name + '/'):
        os.makedirs(path + name + '/')

    if not os.path.exists(pathExport + name + '/'):
        os.makedirs(pathExport + name + '/')

    if not (os.path.exists(realPath) or os.path.exists(realPath2) or os.path.exists(realPath3)):

        print("Missing %s" % realPath3)
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
                    'format': 'bestaudio[ext=m4a]/bestaudio',
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
        logger.warning('Download has already finished.\nVideo Title: %s' % videoTitle)
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
            "%s%s/%s.mp4" % (pathExport, name, videoTitle),
            "-err_detect",
            "explode"
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
            "%s%s/%s.mp4" % (pathExport, name, videoTitle),
            "-err_detect",
            "explode"
        ])

        os.remove("%s%s/temp_bulk.mp4" % (path, name))
        os.remove("%s%s/tempAudio_bulk.m4a" % (path, name))

    registerTrue()

def uploadStuff(videoName : str, groupID, retcode=-1):
    """
    command = [uploader, "upload", filePath, targetPath]
    import subprocess
    subprocess.run(command)

    import requests
    from qcloud_cos import CosConfig
    from qcloud_cos import CosS3Client

    ak = "2019186476261361582082806"
    sk = "70CE2219972D8AE950C7D4CB18128E6857FBD36E"
    bucket_id = "505920095592120329406"
    region = "ap-chengdu"
    Doname = "http://mos.api.maoyuncloud.cn/"
    tokenPath = "/api/user/getToken"
    bucketUploadToken = "/api/mos/bucket/uploadToken"
    token = ""
    tokenUrl = Doname + tokenPath
    json_data = {"appid": ak, "appkey": sk}
    req = requests.post(tokenUrl, json=json_data)
    retdata = req.json()
    if retdata["code"] == 0:
        token = retdata["token"]
    if token != "":
        headers = {'Authorization': token}
        json_data = {"bucket_id": bucket_id, "url": "/qiyu/" + name, "is_block": True}
        req = requests.post(Doname + bucketUploadToken, json=json_data, headers=headers)
        retdata = req.json()
        secret_id = retdata["secret_id"]
        secret_key = retdata["secret_key"]
        token = retdata["token"]
        savekey = "/qiyu/" + name
        scheme = 'https'
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)
        response = client.upload_file(
            Bucket=bucket_id + "-1258813047",
            LocalFilePath=path,
            MAXThread=4,
            Key=savekey,
        )
        download_url = "http://dl.hanayori.cn/qiyu/" + name
        print(download_url)
    """
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
