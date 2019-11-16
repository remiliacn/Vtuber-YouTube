# 自动扒源脚本
自动下源Python脚本

与nonebot机器人兼容进行定时查询YouTube更新：

```python3
@nonebot.scheduler_scheduled_job('interval', seconds=3600)
async def downloadVideo():
  downloadPath = ''     #这里请输入forDownload.py部署的路径
  subprocess.Popen('py %s bulk' % downloadPath)  
```
