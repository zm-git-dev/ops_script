## 部署状态监控小程序到BGISEQ-50和BGISEQ-500机器

该部分内容主要是指导如何部署小程序到BGISEQ-50和BGISEQ-500机器，来实现BGISEQ-50和
BGISEQ-500在ZLIMS系统上的饱和度统计功能。

### * 前提条件
* python（安装并将安装路径添加到系统环境变量）

### * 安装小程序
1. [下载ZLIMS安装包](http://192.168.20.72:8189/view/Formal%20Build/job/zlims-formal-release-build(zlims-isw-01)/)，并解压。
2. 将解压后的zlims-dist_MGI.xx.xx.xx.xx\windows\sequencer_monitor_program 文件夹复制到C盘下。
3. 进入到C:\sequencer_monitor_program目录，右键install.bat以管理员身份运行。
4. 打开控制软件，连接上ZLIMS（仪器首次连接ZLIMS，需要执行测序才会连上ZLIMS），在ZLIMS页面观察，如果仪器5分钟内不会离线，即部署成功。