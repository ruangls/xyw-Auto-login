"""
校园网自动登录 — 通用模板版
  修改下方 ==== 配置区 ==== 的参数即可使用
  依赖: pip install requests
"""
import sys
import time
import json
import signal
import subprocess
import logging

try:
    import requests
except ImportError:
    print("❌ 缺少依赖，请先执行: pip install requests")
    input("按回车退出...")
    sys.exit(1)

# ═══════════════════════════════════════════════════
#                   配  置  区
#             改这里就行，代码不用动~
# ═══════════════════════════════════════════════════

STUDENT_ID = ""      # 学号 / 上网账号
PASSWORD   = ""            # 上网密码
ISP        = ""              # 运营商: 校园网 / 联通 / 电信 / 移动

HOST       = ""        # 认证服务器 IP（必改！）
CHECK_URL  = "http://www.baidu.com"  # 检测网络连通性的地址

LOGIN_PATH    = "/drcom/login"   # 登录接口路径，一般是 /drcom/login
LOGIN_PORTS   = [80, 801]        # 尝试的端口，一般不用改
LOGIN_METHODS = ["POST", "GET"]  # 请求方式，一般不用改
CALLBACK      = "dr1003"         # JSONP 回调名，一般不用改

# 登录表单额外字段（一般不用改，除非你们学校有特殊字段）
EXTRA_FORM = {
    "0MKKey": "123456",
    "R1": "0",
    "R2": "",
    "R3": "0",
    "R6": "0",
    "para": "00",
    "v6ip": "",
    "terminal_type": "1",
    "lang": "zh-cn",
    "jsVersion": "4.2.1",
    "v": "6273",
}

CHECK_INTERVAL = 300   # 守护模式检测间隔（秒），默认 5 分钟
ENABLE_NOTIFY  = True  # 是否弹 Windows 通知弹窗

# ═══════════════════════════════════════════════════
#               以下代码无需修改
# ═══════════════════════════════════════════════════

ISP_MAP = {
    "校园网": "", "联通": "@unicom",
    "电信": "@telecom", "移动": "@cmcc",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("校园网")

_shutdown = False

def _on_signal(signum, frame):
    global _shutdown
    log.info("收到退出信号，正在关闭...")
    _shutdown = True

signal.signal(signal.SIGINT, _on_signal)
signal.signal(signal.SIGTERM, _on_signal)


def notify(title: str, msg: str):
    """跨平台通知"""
    if not ENABLE_NOTIFY:
        return
    msg_one_line = msg.replace("\n", " · ").replace('"', "'")
    ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$t = $tpl.GetElementsByTagName("text")
$t[0].AppendChild($tpl.CreateTextNode("{title}")) | Out-Null
$t[1].AppendChild($tpl.CreateTextNode("{msg_one_line}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("校园网自动登录").Show($toast)
'''
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                capture_output=True, timeout=5,
            )
        else:
            log.info(f"[通知] {title}: {msg}")
    except Exception:
        pass


def need_login() -> bool:
    """访问检测地址，看是否被 Portal 重定向"""
    try:
        r = requests.get(CHECK_URL, timeout=5, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            if HOST in r.headers.get("Location", ""):
                return True
        return r.status_code != 200
    except Exception:
        return True


def do_login() -> bool:
    """执行登录"""
    s = requests.Session()
    acc = STUDENT_ID + ISP_MAP.get(ISP, "")
    now = time.strftime("%H:%M:%S")

    data = {
        "callback": CALLBACK,
        "DDDDD": acc,
        "upass": PASSWORD,
        **EXTRA_FORM,
    }

    h = {
        **HEADERS,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"http://{HOST}:801/",
        "Origin": f"http://{HOST}:801",
        "X-Requested-With": "XMLHttpRequest",
    }

    # 触发 Portal 重定向 / 拿 Cookie
    for url in (CHECK_URL, f"http://{HOST}:801/"):
        try:
            s.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        except Exception:
            pass

    for port in LOGIN_PORTS:
        url = f"http://{HOST}:{port}{LOGIN_PATH}"
        for method in LOGIN_METHODS:
            try:
                if method.upper() == "POST":
                    r = s.post(url, data=data, headers=h, timeout=30, allow_redirects=False)
                else:
                    r = s.get(url, params=data, headers=h, timeout=30, allow_redirects=False)

                text = r.text[:300]

                if CALLBACK in text:
                    try:
                        j = json.loads(text.replace(f"{CALLBACK}(", "").rstrip(");"))
                        if j.get("result", "") in ("0", "1", 0, 1):
                            time.sleep(2)
                            if not need_login():
                                notify("校园网 ✅", f"登录成功！\n账号: {acc}\n时间: {now}")
                                log.info(f"✅ 登录成功 → {acc}")
                                return True
                    except json.JSONDecodeError:
                        pass

                time.sleep(2)
                if not need_login():
                    notify("校园网 ✅", f"登录成功！\n账号: {acc}\n时间: {now}")
                    log.info(f"✅ 登录成功 → {acc}")
                    return True

            except Exception as e:
                log.debug(f"尝试 {method} {url} 失败: {e}")
                continue

    notify("校园网 ❌", f"登录失败！\n账号: {acc}\n时间: {now}\n请检查配置或网络~")
    log.error(f"❌ 登录失败 → {acc}")
    return False


def main():
    log.info(f"启动 — {STUDENT_ID}{ISP_MAP.get(ISP, '')}  @ {HOST}")
    do_login()

    log.info(f"进入守护模式，每 {CHECK_INTERVAL}s 检测一次 (Ctrl+C 退出)")
    while not _shutdown:
        try:
            if need_login():
                log.info("检测到断网，尝试重新登录...")
                do_login()
        except Exception as e:
            log.warning(f"检测异常: {e}")
        for _ in range(CHECK_INTERVAL):
            if _shutdown:
                break
            time.sleep(1)

    log.info("已退出")


if __name__ == "__main__":
    main()
