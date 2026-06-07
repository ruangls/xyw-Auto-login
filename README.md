校园网自动登录
=============================
脚本: xyw.py (单文件，改顶部配置区即可)

依赖安装:
  pip install requests

运行:
  python xyw.py

核心配置项 (改这5个就能用):
  STUDENT_ID = "你的学号"
  PASSWORD   = "上网密码"
  ISP        = "校园网" / "联通" / "电信" / "移动"
  HOST       = "认证服务器IP"
  CHECK_URL  = "http://www.baidu.com"

守护模式:
  登录成功后自动进入，每5分钟检测一次
  断网自动重连，Ctrl+C 退出

支持:
  Windows / Linux / macOS
  Windows 桌面通知弹窗