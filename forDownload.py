import youtube_dl
import requests, time, json
import os, sys, logging, re

pathExport = ''  # 源所在onedrive路径
googleAPIKey = ''  # 自申请谷歌KEY

"""
程序入口
"""
def main():
    if not getStatus():
        logging.warning('There is one task running.')
        return

    var = sys.argv  # subprocess.run()调用
    print(var)
    setting = var[1]

    try:
        # 单个扒源
        if setting == 'single':
            videoID = var[2]
            groupID = var[3]
            downloadVideo(videoID, 'others', groupID)

        # 自动扒源
        else:
            userInDict = getConfig()  # config示例请见./downloader.json
            if not userInDict:
                logging.warning('Init failed when trying to download videos.')
                exit(-1)

            for elements in userInDict:
                getFirstVideo(userInDict[elements]['channel'], elements, userInDict[elements]['qqGroup'], userInDict)
                time.sleep(10)

    except Exception as e:
        logging.warning('Unknown error occurred. %s' % e)
        registerTrue()


"""
注册“机器人正忙”状态
"""
def registerTrue():
    file = open('started.json', 'r')  # 异步处理检查用，会注册为“机器人正忙”
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = True
    with open('D:/dl/started.json', 'w+') as f:
        json.dump(statusDict, f, indent=4)

"""
注册“机器人扒源完毕，或闲置”状态
"""
def registerFalse():
    file = open('started.json', 'r')  # 异步处理检查用，会注册为“机器人扒源完毕，或闲置”
    statusDict = json.loads(str(file.read()))
    statusDict['status'] = False
    with open('D:/dl/started.json', 'w+') as f:
        json.dump(statusDict, f, indent=4)

"""
获得目前机器人的情况
:return: bool
"""
def getStatus() -> bool:
    file = open('started.json', 'r')  # 异步处理检查用，返回目前机器人的状态——闲置或正忙。 True -> 闲置， False -> 忙
    statusDict = json.loads(str(file.read()))
    return statusDict['status']

"""
获得自动扒源设置
:return: dict
"""
def getConfig() -> dict:
    file = open('downloader.json', 'r+')
    fl = file.read()
    import json
    try:
        downloadDict = json.loads(str(fl))
    except Exception as e:
        logging.warning('Something went wrong when getting download config. %s' % e)
        return {}

    return downloadDict

def getFirstVideo(ID: str, name: str, groupID, userDict: dict):
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
            # 获取最新视频videoID
            videoID = json_data['items'][0]['contentDetails']['upload']['videoId']
        except Exception as e:
            logger.warning('Something has happened with %s... Error Message: %s' % (name, e))
            registerTrue()
            return

        videoID_temp = userDict[name]["videoID"] if 'videoID' in userDict[name] else ''
        # 从downloader.json检查是否是最新视频以减少googleAPI请求次数
        if videoID == videoID_temp:
            logger.warning('Download is already finished. This is the test from videoID test.')
            return

        logger.warning('Current Video ID is: %s' % videoID)
        enabled = userDict[name]['enabled']
        # 按人名批量下载最新视频
        downloadVideo(videoID, name, groupID, enabled)


def downloadVideo(videoID: str, name: str, groupID, enable: bool):
    restart = False
    registerFalse()
    youtubeLink = "https://www.youtube.com/watch?v=%s" % videoID
    logger = logging.getLogger('downloadVideo')

    url = 'https://www.googleapis.com/youtube/v3/videos?part=status&key=%s&id=%s' % (googleAPIKey, videoID)
    status = requests.get(url).json()
    stat = status['items'][0]['status']['uploadStatus']
    if stat != 'processed':
        logger.warning("Video is still processing...")
        return

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]/bestvideo',       #扒取视频的最好清晰度
        'noplaylist': True
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            videoTitle_temp = ydl.extract_info(youtubeLink, download=False).get('title')
            videoTitle = videoTitle_temp.replace('|', '').replace(' ', '-').replace('/', '~')

    except youtube_dl.utils.ExtractorError:
        logger.warning('Current Video is not available yet')
        registerTrue()
        return

    realPath3 = pathExport + name + '/' + videoTitle + '.mp4'
    realPath = pathExport + name + '/'
    logger.warning('Downloading in %s' % realPath3)

    if not os.path.exists(pathExport + name + '/'):
        os.makedirs(pathExport + name + '/')

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': '%s' % realPath3,                    #下载地址
        'noplaylist': True,
        'ffmpeg_location': 'D:/youtube/ffmpeg-4.2.1-win64-static/bin'   #ffmpeg.exe路径

    }

    removeList = []
    # 查看是否视频已经被下载
    if not os.path.exists(realPath3) and enable:  # (os.path.exists(realPath) or os.path.exists(realPath2) or :

        print("Missing %s" % realPath3)
        logger.warning('Download will be starting shortly.\nVideo ID: %s' % videoID)
        registerFalse()
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtubeLink])

            logger.warning('Download is completed.\nVideo title: %s' % videoTitle)

            try:
                fileList = os.listdir(realPath)
                for files in fileList:
                    #检查是否有文件碎片
                    if re.match(r'.*?\.mp4\.part.*?\.ytdl', files) \
                            or re.match(r'.*?\.f\d+\.mp4\.part', files) \
                            or re.match(r'.*?\.f\d+\.mp4\.ytdl', files):
                        logging.warning('Something went wrong when downloading the file. We will retry it')
                        if files not in removeList:
                            removeList.append(realPath + files)
                        #如果有，代表视频下载失败，重试。
                        restart = True

                if restart:
                    for elements in removeList:
                        os.remove(elements)

                    registerTrue()
                    os.remove(realPath3)
                    uploadStuff(name, videoTitle_temp, '', groupID, retcode=-1)
                    return

                uploadStuff(name, videoTitle_temp, videoID, groupID, retcode=0)
            except Exception as e:
                logger.warning('Something went wrong when uploading file. %s' % e)
                registerTrue()

        except Exception as e:
            logger.warning("Something went wrong when trying to download. %s" % e)
            registerTrue()

    # 如果只是提醒，则返回一个retcode=1，这个retcode在我的机器人中意味着未下载，只提醒。
    # retcode=0代表着已下载，并需要提醒
    # retcode=-1代表下载出错，需要重试

    elif not enable:
        uploadStuff(name, videoTitle_temp, videoID, groupID, retcode=1)
    else:
        logger.warning('Download has already finished.\nVideo Title: %s' % videoTitle)
        registerTrue()


def uploadStuff(name: str, videoName: str, videoID: str, groupID, retcode=-1):
    # 注册YouTubeNotify.json
    file = open('YouTubeNotify.json', 'r')
    fl = file.read()
    downloadedDict = json.loads(str(fl))
    downloadedDict[videoName] = {
        "status": False,
        "group_id": groupID,        #组号，这里的组号应该是int，如果是str的话要记得在nonebot里call的时候加一个int(groupID)
        "retcode": retcode
    }

    if name != 'others':
        userDict = getConfig()
        userDict[name]['videoID'] = videoID

        with open('downloader.json', 'w+') as f:
            json.dump(userDict, f, indent=4)

    with open('YouTubeNotify.json', 'w+') as f:
        json.dump(downloadedDict, f, indent=4)

    registerTrue()

if __name__ == '__main__':
    main()
