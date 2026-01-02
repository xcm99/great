import os
import time
import traceback
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ================= 基础配置 =================
LOGIN_URL = "https://greathost.es/login"
SERVER_URL = "https://greathost.es/contracts/{server_id}"

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# ================= 工具函数 =================
def mask_email(email: str) -> str:
    try:
        name, domain = email.split("@", 1)
        if len(name) <= 3:
            masked_name = name + "*"
        else:
            masked_name = name[:3] + "*" * (len(name) - 3)
        return f"{masked_name}@{domain}"
    except Exception:
        return "***@***"

def tg_notify(msg: str):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass

# ================= 解析账号 =================
GH_ACCOUNTS_RAW = os.getenv("GH_ACCOUNTS")
if not GH_ACCOUNTS_RAW:
    raise RuntimeError("❌ 未检测到 GH_ACCOUNTS 环境变量")

ACCOUNTS = []
for idx, line in enumerate(GH_ACCOUNTS_RAW.strip().splitlines(), 1):
    line = line.strip()
    if not line or line.startswith("#"):
        continue

    parts = [x.strip() for x in line.split("|")]
    if len(parts) != 3:
        raise RuntimeError(f"❌ GH_ACCOUNTS 第 {idx} 行格式错误")

    email, password, server_id = parts
    ACCOUNTS.append({
        "email": email,
        "password": password,
        "server_id": server_id,
    })

# ================= 核心逻辑 =================
def renew_account(p, acc):
    email = acc["email"]
    password = acc["password"]
    server_id = acc["server_id"]

    masked = mask_email(email)
    print(f"\n👤 账号：{masked}")

    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("🔐 打开登录页")
        page.goto(LOGIN_URL, timeout=60000)

        page.fill("input[name='email']", email)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")

        page.wait_for_load_state("networkidle", timeout=30000)
        print("✅ 登录成功")

        print("🖥 打开 VPS 详情页")
        page.goto(SERVER_URL.format(server_id=server_id), timeout=60000)
        page.wait_for_timeout(3000)

        renew_btn = page.locator(
            "button:has-text('Renew'), a:has-text('Renew')"
        ).first

        renew_btn.wait_for(state="visible", timeout=20000)
        renew_btn.click()

        page.wait_for_timeout(5000)

        print("🎉 续期已触发")
        tg_notify(f"✅ VPS 续期成功\n账号：{masked}")
        return True

    except PlaywrightTimeoutError:
        print("⏱ 页面超时")
        tg_notify(f"❌ VPS 续期失败（超时）\n账号：{masked}")
        return False

    except Exception:
        print("❌ 执行异常")
        traceback.print_exc()
        tg_notify(f"❌ VPS 续期失败（异常）\n账号：{masked}")
        return False

    finally:
        context.close()
        browser.close()

# ================= 主入口 =================
def main():
    success = fail = 0

    with sync_playwright() as p:
        for acc in ACCOUNTS:
            if renew_account(p, acc):
                success += 1
            else:
                fail += 1
            time.sleep(8)  # 防风控

    print("\n========== 执行完成 ==========")
    print(f"✅ 成功：{success}")
    print(f"❌ 失败：{fail}")

    # 防 Action 停跑心跳
    with open("time.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
