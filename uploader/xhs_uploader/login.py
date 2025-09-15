import asyncio
import json
import re
import uuid
from fastapi import BackgroundTasks
from playwright.async_api import async_playwright, Browser

import base64

from utils.base_social_media import set_init_script
from utils.redis import (
    add_to_xiaohongshu_login_list,
    add_to_xiaohongshu_sms_list,
    get_all_xiaohongshu_login_ids,
    get_all_xiaohongshu_sms_numbers,
    get_xiaohongshu_login,
    register_xiaohongshu_login,
    remove_from_xiaohongshu_sms_list,
    remove_xiaohongshu_login,
)


def save_blob_as_image(blob_string, output_image_path):
    # 假设 blob_string 中包含的是 base64 编码的图片数据
    # 去掉data:image/png;base64,之类的前缀（如果有的话）
    if "," in blob_string:
        blob_string = blob_string.split(",", 1)[1]

    # 解码 base64 数据
    image_data = base64.b64decode(blob_string)

    # 将二进制数据写入文件
    with open(output_image_path, "wb") as image_file:
        image_file.write(image_data)


async def xhs_login_client(background_tasks: BackgroundTasks, browser: Browser):

    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as p:

        try:
            # 启动浏览器并打开新的页面
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720}  # 设置视口宽度和高度
            )
            page = await context.new_page()
            await page.context.clear_cookies()

            # 导航到目标网页
            await page.goto("https://www.xiaohongshu.com/explore")

            # 等待2s
            await page.wait_for_timeout(2000)

            # 获取二维码图像的 src 属性
            qr_code_image = page.locator(".qrcode-img")
            qr_code_image_src = await qr_code_image.get_attribute("src")

            login_info = {"login_status": "logging_in"}
            register_xiaohongshu_login(generated_login_uuid_str, json.dumps(login_info))

            async def get_cookie():
                try:
                    for i in range(0, 180):
                        await asyncio.sleep(1)  # 一秒检测一次，最多三分钟
                        # 检查是否成功登录
                        user_link = page.get_by_role("link", name="我", exact=True)
                        if await user_link.is_visible():
                            break
                        try:
                            selector = "div.red-captcha-container"
                            await page.wait_for_selector(
                                selector=selector,
                                timeout=1000,
                            )
                            login_info = {"login_status": "captcha_required"}
                            register_xiaohongshu_login(
                                generated_login_uuid_str, json.dumps(login_info)
                            )
                            return
                        except:
                            pass
                        if i == 180:
                            raise Exception("Login timeout")

                    # 成功登录
                    account_page_path = await page.get_attribute(
                        "li.user div.link-wrapper a.link-wrapper", "href"
                    )
                    parts = account_page_path.split("/")
                    user_id = parts[-1]  # 获取最后一个部分
                    if user_id is not None and user_id != "":
                        await page.get_by_role("link", name="我", exact=True).click()
                        await asyncio.sleep(5)  # 等待页面加载
                        redId_text = await page.inner_text("span.user-redId")
                        redId = redId_text.split("：")[
                            -1
                        ].strip()  # 提取冒号后面的内容并去除空白字符

                        # 跳转创作者页面
                        await page.get_by_role("link", name="发布").click()
                        await asyncio.sleep(10)
                        cookies = await context.cookies()
                        cookies_json = json.dumps(cookies)

                        login_info = {"redId": redId, "client_cookie": cookies_json}
                        register_xiaohongshu_login(
                            generated_login_uuid_str, json.dumps(login_info)
                        )
                        add_to_xiaohongshu_login_list(generated_login_uuid_str)
                        return
                    else:
                        raise Exception("Login failed, user_id is None or empty")
                except Exception as e:
                    print("Login failed:", str(e))
                finally:
                    await page.context.clear_cookies()
                    await page.close()
                    await context.close()

            background_tasks.add_task(get_cookie)

            return {
                "id": generated_login_uuid_str,
                "qr_code_image_src": qr_code_image_src,
            }
        except Exception as e:
            print("An error occurred:", str(e))
            if page:
                await page.context.clear_cookies()
                await page.close()


async def xhs_login_creator(
    background_tasks: BackgroundTasks, browser: Browser, id: str
):
    async with async_playwright() as p:
        try:
            client_cookie_json = get_xiaohongshu_login(id)["client_cookie"]
            client_cookies = json.loads(client_cookie_json)

            # 启动浏览器并打开新的页面
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720}  # 设置视口宽度和高度
            )
            await context.add_cookies(client_cookies)  # 写入小红书 Web 客户端的 Cookie
            page1 = await context.new_page()

            current_cookie = await page1.context.cookies()
            print("current_cookie", current_cookie)

            print("goto xiaohongshu")
            # 导航到目标网页
            await page1.goto("https://www.xiaohongshu.com")
            print("load success")

            # 等待2s
            await page1.wait_for_timeout(1000)

            await page1.get_by_role("button", name="创作中心").click()
            page_coro = page1.wait_for_event("popup")  # 等待新标签页弹出
            await page1.get_by_role("link", name="创作服务").click()
            page = await page_coro
            # 等待页面加载完成
            await page.wait_for_load_state("networkidle", timeout=2000)

            # 获取二维码图像的 src 属性
            await page.locator("img").click()
            qr_code_image_element = page.get_by_role("img").nth(2)
            qr_code_image_src = await qr_code_image_element.get_attribute("src")

            async def get_cookie():
                try:
                    for i in range(0, 180):
                        await asyncio.sleep(1)  # 一秒检测一次，最多三分钟
                        # 检查是否成功登录
                        redId = page.get_by_text("小红书账号:")
                        if await redId.is_visible():
                            break
                        if i == 180:
                            raise Exception("Login timeout")

                    # 成功登录
                    await asyncio.sleep(5)
                    redId_text_element = page.get_by_text("小红书账号:")
                    redId_text = await redId_text_element.inner_text()
                    redId = redId_text.split(": ")[
                        -1
                    ].strip()  # 提取冒号后面的内容并去除空白字符
                    cookies = await context.cookies()
                    cookies_json = json.dumps(cookies)

                    login_info = {
                        "redId": redId,
                        "client_cookie": client_cookie_json,
                        "creator_cookie": cookies_json,
                    }
                    register_xiaohongshu_login(id, json.dumps(login_info))
                    add_to_xiaohongshu_login_list(id)
                    return
                except Exception as e:
                    print("Login failed:", str(e))
                finally:
                    await page.context.clear_cookies()
                    await page.close()

            background_tasks.add_task(get_cookie)

            return {"id": id, "qr_code_image_src": qr_code_image_src}
        except Exception as e:
            print("An error occurred:", str(e))
            if page:
                await page.context.clear_cookies()
                await page.close()


def xhs_save_cookie(cookies: str):
    try:
        generated_login_uuid = uuid.uuid4()
        generated_login_uuid_str = str(generated_login_uuid)

        login_info = {
            "str_cookies": cookies,
        }
        register_xiaohongshu_login(generated_login_uuid_str, json.dumps(login_info))
        add_to_xiaohongshu_login_list(generated_login_uuid_str)

        return generated_login_uuid_str
    except Exception as e:
        print("An error occurred:", str(e))
        return None


async def xhs_login_by_sms(
    background_tasks: BackgroundTasks, browser: Browser, phone_number: str
):
    # 检测是否该手机号码已经在验证登录
    numbers = get_all_xiaohongshu_sms_numbers()
    if phone_number in numbers:
        raise Exception("该手机号码已经在验证登录")

    generated_login_uuid = uuid.uuid4()
    generated_login_uuid_str = str(generated_login_uuid)
    async with async_playwright() as playwright:
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720}  # 设置视口宽度和高度
            )
            context = await set_init_script(context)
            page = await context.new_page()
            await page.context.clear_cookies()
            await page.goto("https://www.xiaohongshu.com/explore")
            await page.get_by_placeholder("输入手机号").click()
            await page.get_by_placeholder("输入手机号").fill(phone_number)
            await page.get_by_text("获取验证码").click()
            try:
                selector = "div.reds-toast.center"
                await page.wait_for_selector(
                    selector=selector,
                    timeout=5000,
                )
                element = await page.query_selector(selector)
                text = await element.inner_text()
                if text == "验证码已发送":
                    raise Exception("验证码已发送")
                return {"error": text}
            except:
                pass

            login_info = {
                "login_status": "send_sms_verify_code",
                "phone_number": phone_number,
            }
            register_xiaohongshu_login(generated_login_uuid_str, json.dumps(login_info))
            add_to_xiaohongshu_sms_list(phone_number)

            async def xhs_login_callback():
                try:
                    for i in range(0, 180):
                        await asyncio.sleep(1)
                        login_status = get_xiaohongshu_login(
                            generated_login_uuid_str
                        ).get("login_status")
                        sms_verify_code = get_xiaohongshu_login(
                            generated_login_uuid_str
                        ).get("sms_verify_code")
                        if (
                            login_status == "send_sms_verify_code"
                            and sms_verify_code is not None
                        ):
                            # 输入短信验证码
                            await page.get_by_placeholder("输入验证码").click()
                            await page.get_by_placeholder("输入验证码").fill(
                                get_xiaohongshu_login(generated_login_uuid_str)[
                                    "sms_verify_code"
                                ]
                            )
                            await page.locator("form").get_by_role(
                                "button", name="登录"
                            ).click()
                            await page.get_by_text("同意并继续").click()
                            try:
                                selector = "div.red-captcha-container"
                                await page.wait_for_selector(
                                    selector=selector,
                                    timeout=1000,
                                )
                                login_info = {"login_status": "captcha_required"}
                                register_xiaohongshu_login(
                                    generated_login_uuid_str, json.dumps(login_info)
                                )
                                return
                            except:
                                pass
                            login_info = {"login_status": "verified_sms_verify_code"}
                            register_xiaohongshu_login(
                                generated_login_uuid_str, json.dumps(login_info)
                            )

                        # 检查是否成功登录
                        if login_status == "verified_sms_verify_code":
                            account_page_path = await page.get_attribute(
                                "li.user div.link-wrapper a.link-wrapper", "href"
                            )
                            parts = account_page_path.split("/")
                            user_id = parts[-1]  # 获取最后一个部分
                            if user_id is not None and user_id != "":
                                await page.get_by_role(
                                    "link", name="我", exact=True
                                ).click()
                                await asyncio.sleep(5)  # 等待页面加载
                                redId_text = await page.inner_text("span.user-redId")
                                redId = redId_text.split("：")[
                                    -1
                                ].strip()  # 提取冒号后面的内容并去除空白字符

                                # 跳转创作者页面
                                await page.get_by_role("link", name="发布").click()
                                await asyncio.sleep(10)
                                cookies = await context.cookies()
                                cookies_json = json.dumps(cookies)

                                login_info = {
                                    "redId": redId,
                                    "client_cookie": cookies_json,
                                }
                                register_xiaohongshu_login(
                                    generated_login_uuid_str, json.dumps(login_info)
                                )
                                add_to_xiaohongshu_login_list(generated_login_uuid_str)
                                return
                        if i == 180:
                            return
                except Exception as e:
                    print(f"Error during login: {e}")
                finally:
                    remove_from_xiaohongshu_sms_list(phone_number)
                    await page.close()
                    await page.context.clear_cookies()
                    await context.close()

            background_tasks.add_task(xhs_login_callback)

            return {"id": generated_login_uuid_str}
        except Exception as e:
            raise Exception(f"发生验证码失败: {e}")


def xhs_login_verify_sms(id: str, code: str):
    try:
        login_info = get_xiaohongshu_login(id)
        if login_info.get("login_status") != "send_sms_verify_code":
            raise Exception("请先发送验证码")
        elif login_info is None:
            raise Exception("登录信息不存在")
        login_info["sms_verify_code"] = code
        register_xiaohongshu_login(id, json.dumps(login_info))
    except Exception as e:
        raise Exception(f"验证验证码失败: {e}")


def xhs_login_get_status(account_id: str):
    try:
        login_info = get_xiaohongshu_login(account_id)
        if login_info is None:
            return {"error": "Account not found"}
        return {"login_status": login_info.get("login_status", "unknown")}
    except TypeError:
        raise Exception("无法获取到相关ID登录状态")
    except Exception as e:
        raise Exception(f"获取登录状态失败: {e}")
