from playwright.sync_api import sync_playwright, TimeoutError
import time
import os

EMAIL = os.environ.get("GH_EMAIL")
PASSWORD = os.environ.get("GH_PASSWORD")

if not EMAIL or not PASSWORD:
    raise RuntimeError("❌ 未设置 GitHub Secrets：GH_EMAIL / GH_PASSWORD")

# ========= 配置区 =========
LOGIN_URL = "https://greathost.es/login"
SERVER_ID = "9ad3a329-4a2f-497a-8ae7-63e5e2bfda07"
SERVER_URL = f"https://greathost.es/contracts/{SERVER_ID}"



HEADLESS = True  # 本地调试可改 False
# ==========================


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        page = context.new_page()

        # ========== 1️⃣ 打开登录页 ==========
        print("🔐 打开登录页面")
        page.goto(LOGIN_URL, timeout=60_000)
        page.wait_for_timeout(3000)

        # ========== 2️⃣ 填写账号密码 ==========
        print("✍️ 输入邮箱")
        page.fill("input[placeholder='Enter your email']", EMAIL)

        print("✍️ 输入密码")
        page.fill("input[placeholder='Enter your password']", PASSWORD)

        # ========== 3️⃣ 点击登录 ==========
        print("➡️ 点击 Sign In")
        page.click("button:has-text('Sign In')")

        # ========== 4️⃣ 等待登录成功 ==========
        print("⏳ 等待登录完成")
        page.wait_for_timeout(8000)

        if "login" in page.url:
            raise RuntimeError("❌ 登录失败，请检查账号密码或验证码")

        print("✅ 登录成功")

        # ========== 5️⃣ 打开 VPS 详情页 ==========
        print("🖥 打开 VPS 详情页")
        page.goto(SERVER_URL, timeout=60_000)
        page.wait_for_timeout(5000)

        # 校验是否真到了续期页面
        page.wait_for_selector(
            "text=Renewal Information",
            timeout=20_000
        )

        print("🔍 找到续期按钮")

        # ========== 6️⃣ 点击续期 ==========
        renew_btn = page.wait_for_selector(
            "button:has-text('Renew +12 hours')",
            timeout=20_000
        )

        renew_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)

        print("🟢 点击 Renew +12 hours")
        renew_btn.click()

        # ========== 7️⃣ 等待前端处理 ==========
        page.wait_for_timeout(8000)

        # ========== 8️⃣ 结果判断 ==========
        if page.locator("text=Maximum").count() > 0:
            print("⚠️ 已达到最大续期时间（120h）")
        else:
            print("🎉 已尝试续期，请人工确认时间是否增加")

        browser.close()


if __name__ == "__main__":
    main()
