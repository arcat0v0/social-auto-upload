import json
import os
import traceback
from typing import List, Optional
import uuid
from type.upload_video_by_url_request import Platforms
from uploader.bilibili_uploader.extra import upload_video_to_bilibili
from uploader.douyin_uploader.extra import upload_video_to_douyin
from uploader.ks_uploader.extra import upload_video_to_ks
from uploader.tencent_uploader.extra import upload_video_to_tencent
from uploader.xhs_uploader.extra import upload_video_to_xiaohongshu
from utils.redis import record_task_result
from utils.video_file_manager import download_file, remove_file

current_working_directory = os.getcwd()


def run_upload_task(task_id: str, description: str, platforms: Platforms, tags: List[str],
                    title: str, video_url: str, video_file_name: str, category: Optional[str] = None, tid: Optional[str] = None,
                    timestamp: Optional[str] = None):
    try:
        download_file_path = download_file(video_url, save_folder=f'{
                                           current_working_directory}/cache/', filename=video_file_name)
        print(f'下载视频成功，文件路径：{download_file_path}')
        try:
            dict_platforms = platforms.model_dump()
            upload_task_dict = {"status": 'uploading'}
            record_task_result(task_id,
                               json.dumps(upload_task_dict))
            print(dict_platforms)
            for platform in dict_platforms.keys():
                if dict_platforms[platform] == []:
                    print(f'{platform} 没有配置账号，跳过该平台')
                if platform == 'bilibili':
                    upload_task_dict['bilibili'] = {}
                    for id in dict_platforms[platform]:
                        try:
                            upload_video_to_bilibili(id=id, video_path=download_file_path, title=title,
                                                     description=description, tags=tags, tid=int(tid), timestamp=timestamp)
                            upload_task_dict['bilibili'][id] = {
                                'status': 'success'}
                        except Exception as e:
                            upload_task_dict['bilibili'][id] = {
                                'status': 'failed', 'error': str(e)}
                elif platform == 'xiaohongshu':
                    upload_task_dict['xiaohongshu'] = {}
                    for id in dict_platforms[platform]:
                        try:
                            upload_video_to_xiaohongshu(
                                id=id, video_path=download_file_path, title=title, tags=tags, timestamp=timestamp)
                            upload_task_dict['xiaohongshu'][id] = {
                                'status': 'success'}
                        except Exception as e:
                            upload_task_dict['xiaohongshu'][id] = {
                                'status': 'failed', 'error': str(e)}
                elif platform == 'tencent':
                    upload_task_dict['tencent'] = {}
                    for id in dict_platforms[platform]:
                        try:
                            upload_video_to_tencent(
                                id=id, video_path=download_file_path, title=title, tags=tags, timestamp=timestamp, category=category)
                            upload_task_dict['tencent'][id] = {
                                'status': 'success'}
                        except Exception as e:
                            upload_task_dict['tencent'][id] = {
                                'status': 'failed', 'error': str(e)}
                elif platform == 'douyin':
                    upload_task_dict['douyin'] = {}
                    for id in dict_platforms[platform]:
                        try:
                            upload_video_to_douyin(
                                id=id, video_path=download_file_path, title=title, tags=tags, timestamp=timestamp)
                            upload_task_dict['douyin'][id] = {
                                'status': 'success'}
                        except Exception as e:
                            upload_task_dict['douyin'][id] = {
                                'status': 'failed', 'error': str(e)}

                elif platform == 'kuaishou':
                    upload_task_dict['kuaishou'] = {}
                    for id in dict_platforms[platform]:
                        try:
                            upload_video_to_ks(
                                id=id, video_path=download_file_path, title=title, tags=tags, timestamp=timestamp)
                            upload_task_dict['kuaishou'][id] = {
                                'status': 'success'}
                        except Exception as e:
                            upload_task_dict['kuaishou'][id] = {
                                'status': 'failed', 'error': str(e)}

                else:
                    print(f'不支持的平台：{platform}')
        except Exception as e:
            print(f'上传视频失败，错误信息：{str(e)}')
            traceback.print_exc()
        finally:
            # remove_file(download_file_path)
            record_task_result(task_id,
                               json.dumps(upload_task_dict))

    except Exception as e:
        print(f'内部出错，错误信息：{str(e)}')
        traceback.print_exc()
