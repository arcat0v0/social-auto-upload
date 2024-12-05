import asyncio
from decimal import Decimal
import json
import uuid
from playwright.async_api import Playwright, async_playwright
from utils.base_social_media import set_init_script
from fastapi import BackgroundTasks
from playwright.async_api import async_playwright, Browser

from utils.redis import add_to_tencent_login_list, register_tencent_login


def convert_storage_state(storage_state):
    for cookie in storage_state.get('cookies', []):
        if 'expires' in cookie:
            cookie['expires'] = int(cookie['expires'])
    return storage_state


async def tencent_login(background_tasks: BackgroundTasks, browser: Browser):
    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as playwright:
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}  # 设置视口宽度和高度
        )
        context = await set_init_script(context)
        page = await context.new_page()
        await page.context.clear_cookies()
        await page.goto("https://channels.weixin.qq.com")

        # 获取登录二维码
        await page.screenshot(path="example.png")
        qrcode_img = page.locator('iframe').content_frame.locator('img.qrcode')
        src = await qrcode_img.get_attribute("src")

        async def tencent_login_callback():
            try:
                for i in range(0, 180):
                    await asyncio.sleep(1)  # 一秒检测一次，最多三分钟
                    # 检查是否成功登录
                    id_span = page.locator("#finder-uid-copy")
                    account_id = await id_span.text_content()
                    if account_id is not None:
                        cookies = await context.storage_state()  # 获取登录后的cookie
                        converted_state = convert_storage_state(cookies)
                        cookies_json = json.dumps(
                            converted_state)  # 将cookie转换为json格式

                        login_info = {
                            'tencent_id': account_id,
                            'client_cookie': cookies_json
                        }
                        register_tencent_login(
                            generated_login_uuid_str, json.dumps(login_info))
                        add_to_tencent_login_list(generated_login_uuid_str)
                        break
                    if i == 180:
                        raise Exception("Login timeout")
            except Exception as e:
                print(f"Error during login: {e}")
            finally:
                await page.close()
                await page.context.clear_cookies()
                await context.close()

        background_tasks.add_task(tencent_login_callback)

        # 返回二维码图片的URL
        if src and src.startswith("data:image"):
            return {"blob": src, "id": generated_login_uuid_str}
        else:
            return {"error": "Failed to get QR code URL"}
