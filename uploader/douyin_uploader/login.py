
import asyncio
import json
import re
import uuid
from fastapi import BackgroundTasks, Response
from playwright.async_api import async_playwright, Browser

from utils.base_social_media import set_init_script
from utils.redis import add_to_douyin_login_list, get_douyin_login, register_douyin_login


def convert_storage_state(storage_state):
    for cookie in storage_state.get('cookies', []):
        if 'expires' in cookie:
            cookie['expires'] = int(cookie['expires'])
    return storage_state


async def douyin_login(background_tasks: BackgroundTasks, browser: Browser):
    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as playwright:
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}  # 设置视口宽度和高度
        )
        context = await set_init_script(context)
        page = await context.new_page()
        await page.context.clear_cookies()
        await page.goto("https://creator.douyin.com/")

        # 创建一个 Future 对象来存放响应的结果
        future = asyncio.get_event_loop().create_future()

        # 定义拦截器函数
        async def handle_response(response: Response, future):
            if r"https://sso.douyin.com/get_qrcode" in response.url and response.status == 200:
                body = await response.json()
                qrcode = body['data']['qrcode']
                future.set_result(qrcode)  # 将结果存入 Future 对象

        # 侦听响应事件
        page.on("response", lambda response: handle_response(response, future))
        src = await future
        print(f"二维码链接: {src}")

        async def douyin_login_callback():
            try:
                for i in range(0, 180):
                    await asyncio.sleep(1)  # 一秒检测一次，最多三分钟
                    # 检测是否需要二次验证
                    verify_card = page.locator('div').filter(
                        has_text='身份验证为保证帐号安全，请完成身份验证接收短信验证发送短信验证').nth(2)
                    if await verify_card.is_visible():
                        print("需要二次验证")
                        login_info = {
                            'login_status': 'send_sms_verify_code',
                        }
                        register_douyin_login(
                            generated_login_uuid_str, json.dumps(login_info))
                        await page.get_by_text('接收短信验证').click()
                        await page.get_by_text('获取验证码').click()
                    login_status = get_douyin_login(
                        generated_login_uuid_str).get('login_status')
                    sms_verify_code = get_douyin_login(generated_login_uuid_str).get(
                        'sms_verify_code')
                    if login_status == 'send_sms_verify_code' and sms_verify_code is not None:
                        # 输入短信验证码
                        await page.get_by_role('spinbutton').click()
                        await page.get_by_role('spinbutton').fill(get_douyin_login(generated_login_uuid_str)['sms_verify_code'])
                        await page.get_by_text('验证', exact=True).click()
                        login_info = {
                            'login_status': 'verified_sms_verify_code'
                        }
                        register_douyin_login(
                            generated_login_uuid_str, json.dumps(login_info))

                    # 检查是否成功登录
                    id_span = page.get_by_text('抖音号：')
                    if await id_span.is_visible():
                        print('登录成功')
                        account_id_text = await id_span.inner_text()
                        pattern = r'\d+'
                        account_id = re.search(
                            pattern, account_id_text).group()

                        print(f"Account ID: {account_id}  Login Status: {
                            login_status}  SMS Verify Code: {sms_verify_code}  Iteration: {i}")  # 打印调试信息
                        if account_id is not None:
                            cookies = await context.storage_state()  # 获取登录后的cookie
                            converted_state = convert_storage_state(cookies)
                            cookies_json = json.dumps(
                                converted_state)  # 将cookie转换为json格式

                            login_info = {
                                'douyin_id': account_id,
                                'client_cookie': cookies_json,
                                'login_status': 'success',
                            }
                            register_douyin_login(
                                generated_login_uuid_str, json.dumps(login_info))
                            add_to_douyin_login_list(generated_login_uuid_str)
                            break
                    if i == 180:
                        raise Exception("Login timeout")
            except Exception as e:
                print(f"Error during login: {e}")
            finally:
                await page.close()
                await page.context.clear_cookies()
                await context.close()

        background_tasks.add_task(douyin_login_callback)

        # 返回二维码图片的URL
        if src:
            return {"blob": src, "id": generated_login_uuid_str}
        else:
            return {"error": "Failed to get QR code URL"}


def douyin_login_verify_sms_code(account_id: str, code: str):
    try:
        login_info = get_douyin_login(account_id)
        login_info['sms_verify_code'] = code

        print(login_info)
        register_douyin_login(account_id, json.dumps(login_info))
    except Exception as e:
        raise {"message": e}


def douyin_login_get_status(account_id: str):
    login_info = get_douyin_login(account_id)
    if login_info is None:
        return {"error": "Account not found"}
    return {"login_status": login_info.get('login_status', 'unknown')}
