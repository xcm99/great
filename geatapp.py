import os
import sys
import time
import traceback
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests

# ===================== 基础配置 =====================
LOGIN_URL = "https://greathost.es/login"
SERVER_DETAIL_URL = "https://greathost.es/clientarea.php?action=productdetails&id={server_id}"

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# ===================== 工具函数 =====================
def mask_email(email: str) -> str:
    try:
        name, domain = email.split("@", 1)
        if len(name) <= 1:
            masked = "*"
        else:
            masked = name[0] + "*" * (len(name) - 1)
        return f"{masked}@{domain}"
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

# ===================== 解析账号 =====================
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

if not ACCOUNTS:
    raise RuntimeError("❌ 未解析到任何账号")

# ===================== 核心逻辑 =====================
def renew_single_account(playwright, account: dict):
    email = account["email"]
    password = account["password"]
    server_id = account["server_id"]
    masked_email = mask_email(email)

    print(f"\n👤 账号：{masked_email}")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        # ---------- 登录 ----------
        print("🔐 打开登录页")
        page.goto(LOGIN_URL, timeout=60000)

        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')

        page.wait_for_load_state("networkidle", timeout=30000)
        print("✅ 登录成功")

        # ---------- 打开 VPS ----------
        detail_url = SERVER_DETAIL_URL.format(server_id=server_id)
        print("🖥 打开 VPS 详情页")
        page.goto(detail_url, timeout=60000)

        # 允许页面差异，不强依赖文案
        page.wait_for_timeout(3000)

        # ---------- 点击 Renew ----------
        print("🔁 查找续期按钮")
        renew_btn = page.locator(
            'a:has-text("Renew"), button:has-text("Renew"), a:has-text("续期"), button:has-text("续期")'
        ).first

        renew_btn.wait_for(state="visible", timeout=20000)
        renew_btn.click()

        page.wait_for_load_state("networkidle", timeout=30000)

        print("🎉 续期流程已触发")
        tg_notify(f"✅ VPS 续期成功\n账号：{masked_email}")

        return True

    except PlaywrightTimeoutError as e:
        print("⏱ 页面超时")
        tg_notify(f"❌ VPS 续期失败（超时）\n账号：{masked_email}")
        return False

    except Exception as e:
        print("❌ 执行异常")
        traceback.print_exc()
        tg_notify(f"❌ VPS 续期失败（异常）\n账号：{masked_email}")
        return False

    finally:
        context.close()
        browser.close()

# ===================== 主入口 =====================
def main():
    success = 0
    fail = 0

    with sync_playwright() as p:
        for account in ACCOUNTS:
            ok = False
            try:
                ok = renew_single_account(p, account)
            except Exception:
                fail += 1
            else:
                if ok:
                    success += 1
                else:
                    fail += 1

            # 防止触发风控
            time.sleep(8)

    print("\n========== 运行结果 ==========")
    print(f"✅ 成功：{success}")
    print(f"❌ 失败：{fail}")

    # 防 Action 停跑心跳
    with open("time.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
