import json
import redis

r = redis.Redis(host='172.27.152.174', port=6379, decode_responses=True)


def safe_loads(json_str):
    if not json_str:  # 检查字符串是否为空
        return {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}  # 如果解析失败，也返回空字典

# bilibili


def add_to_bilibili_login_list(id):
    r.sadd('bilibili_login', id)


def register_bilibili_login(id: str, value: str):
    r.set(id, value)


def remove_from_bilibili_login_list(id):
    r.srem('bilibili_login', id)


def get_bilibili_login(id) -> dict:
    return json.loads(r.get(id))


def remove_bilibili_login(id):
    r.delete(id)


def get_all_bilibili_login_ids():
    return r.smembers('bilibili_login')


def clear_bilibili_login_list():
    r.delete('bilibili_login')


# xiaohongshu
def add_to_xiaohongshu_login_list(id):
    r.sadd('xiaohongshu_login', id)


def register_xiaohongshu_login(id: str, value: str):
    r.set(id, value)


def remove_from_xiaohongshu_login_list(id):
    r.srem('xiaohongshu_login', id)


def get_xiaohongshu_login(id) -> dict:
    return json.loads(r.get(id))


def remove_xiaohongshu_login(id):
    r.delete(id)


def get_all_xiaohongshu_login_ids():
    return r.smembers('xiaohongshu_login')


def clear_xiaohongshu_login_list():
    r.delete('xiaohongshu_login')

# tencent


def add_to_tencent_login_list(id: str):
    r.sadd('tencent_login', id)


def register_tencent_login(id: str, value: str):
    r.set(id, value)


def remove_from_tencent_login_list(id: str):
    r.srem('tencent_login', id)


def get_tencent_login(id: str) -> dict:
    return json.loads(r.get(id))


def remove_tencent_login(id: str):
    r.delete(id)


def get_all_tencent_login_ids():
    return r.smembers('tencent_login')


def clear_tencent_login_list():
    r.delete('tencent_login')


# douyin
def add_to_douyin_login_list(id: str):
    r.sadd('douyin_login', id)


def register_douyin_login(id: str, value: str):
    r.set(id, value)


def remove_from_douyin_login_list(id: str):
    r.srem('douyin_login', id)


def get_douyin_login(id: str) -> dict:
    return safe_loads(r.get(id))


def remove_douyin_login(id: str):
    r.delete(id)


def get_all_douyin_login_ids():
    return r.smembers('douyin_login')


def clear_douyin_login_list():
    r.delete('douyin_login')

# kuaishou


def add_to_ks_login_list(id: str):
    r.sadd('ks_login', id)


def register_ks_login(id: str, value: str):
    r.set(id, value)


def remove_from_ks_login_list(id: str):
    r.srem('ks_login', id)


def get_ks_login(id: str) -> dict:
    return safe_loads(r.get(id))


def remove_ks_login(id: str):
    r.delete(id)


def get_all_ks_login_ids():
    return r.smembers('ks_login')


def clear_ks_login_list():
    r.delete('ks_login')
