
import asyncio
import json
import re
import uuid
from fastapi import BackgroundTasks, Response
from playwright.async_api import async_playwright, Browser

from utils.base_social_media import set_init_script
from utils.redis import add_to_ks_login_list, get_ks_login, register_ks_login


def convert_storage_state(storage_state):
    for cookie in storage_state.get('cookies', []):
        if 'expires' in cookie:
            cookie['expires'] = int(cookie['expires'])
    return storage_state


async def ks_login(background_tasks: BackgroundTasks, browser: Browser):
    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as playwright:
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}  # 设置视口宽度和高度
        )
        context = await set_init_script(context)
        page = await context.new_page()
        await page.context.clear_cookies()
        await page.goto("https://cp.kuaishou.com")
        await page.get_by_role("link", name="立即登录").click()
        qrcode_login_div = page.locator('.platform-switch-pc')

        await qrcode_login_div.click()

        # 创建一个 Future 对象来存放响应的结果
        future = asyncio.get_event_loop().create_future()

        # 定义拦截器函数
        async def handle_response(response: Response, future):
            if r"https://id.kuaishou.com/rest/c/infra/ks/qr/start" in response.url and response.status == 200:
                body = await response.json()
                qrcode = body['imageData']
                future.set_result(qrcode)  # 将结果存入 Future 对象

        # 侦听响应事件
        page.on("response", lambda response: handle_response(response, future))
        src = await future
        print(f"二维码链接: {src}")

        async def ks_login_callback():
            try:
                for i in range(0, 180):
                    await asyncio.sleep(1)  # 一秒检测一次，最多三分钟

                    # 检查是否成功登录
                    id_span = page.get_by_text('快手号：')
                    if await id_span.is_visible():
                        print('登录成功')
                        account_id_text = await id_span.inner_text()
                        pattern = r'\d+'
                        account_id = re.search(
                            pattern, account_id_text).group()

                        # 打印调试信息
                        print(f"Account ID: {account_id} Iteration: {i}")
                        if account_id is not None:
                            cookies = await context.storage_state()  # 获取登录后的cookie
                            converted_state = convert_storage_state(cookies)
                            cookies_json = json.dumps(
                                converted_state)  # 将cookie转换为json格式

                            login_info = {
                                'ks_id': account_id,
                                'client_cookie': cookies_json,
                                'login_status': 'success',
                            }
                            register_ks_login(
                                generated_login_uuid_str, json.dumps(login_info))
                            add_to_ks_login_list(generated_login_uuid_str)
                            break
                    if i == 180:
                        raise Exception("Login timeout")
            except Exception as e:
                print(f"Error during login: {e}")
            finally:
                await page.close()
                await page.context.clear_cookies()
                await context.close()

        background_tasks.add_task(ks_login_callback)

        # 返回二维码图片的URL
        if src:
            return {"blob": src, "id": generated_login_uuid_str}
        else:
            return {"error": "Failed to get QR code URL"}
