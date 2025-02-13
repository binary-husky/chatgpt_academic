import requests
import random
import time
import re
import json
from bs4 import BeautifulSoup
from functools import lru_cache
from itertools import zip_longest
from check_proxy import check_proxy
from toolbox import CatchException, update_ui, get_conf, promote_file_to_downloadzone, update_ui_latest_msg, generate_file_link
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive, input_clipping
from request_llms.bridge_all import model_info
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.prompts.internet import SearchOptimizerPrompt, SearchAcademicOptimizerPrompt
from crazy_functions.json_fns.pydantic_io import GptJsonIO, JsonStringError
from textwrap import dedent
from loguru import logger
from pydantic import BaseModel, Field

class Query(BaseModel):
    search_keyword: str = Field(description="search query for video resource")


class VideoResource(BaseModel):
    thought: str = Field(description="analysis of the search results based on the user's query")
    title: str = Field(description="title of the video")
    author: str = Field(description="author/uploader of the video") 
    bvid: str = Field(description="unique ID of the video")
    another_failsafe_bvid: str = Field(description="provide another bvid, the other one is not working")


def get_video_resource(search_keyword):
    from crazy_functions.media_fns.get_media import search_videos

    # Search for videos and return the first result
    videos = search_videos(
        search_keyword
    )

    # Return the first video if results exist, otherwise return None
    return videos

def download_video(bvid, user_name, chatbot, history):
    # from experimental_mods.get_bilibili_resource import download_bilibili
    from crazy_functions.media_fns.get_media import download_video
    # pause a while
    tic_time = 8
    for i in range(tic_time):
        yield from update_ui_latest_msg(
            lastmsg=f"即将下载音频。等待{tic_time-i}秒后自动继续, 点击“停止”键取消此操作。", 
            chatbot=chatbot, history=[], delay=1)

    # download audio
    chatbot.append((None, "下载音频, 请稍等...")); yield from update_ui(chatbot=chatbot, history=history)
    downloaded_files = yield from download_video(bvid, only_audio=True, user_name=user_name, chatbot=chatbot, history=history)

    if len(downloaded_files) == 0:
        # failed to download audio
        return []

    # preview
    preview_list = [promote_file_to_downloadzone(fp) for fp in downloaded_files]
    file_links = generate_file_link(preview_list)
    yield from update_ui_latest_msg(f"已完成的文件: <br/>" + file_links, chatbot=chatbot, history=history, delay=0)
    chatbot.append((None, f"即将下载视频。"))

    # pause a while
    tic_time = 16
    for i in range(tic_time):
        yield from update_ui_latest_msg(
            lastmsg=f"即将下载视频。等待{tic_time-i}秒后自动继续, 点击“停止”键取消此操作。", 
            chatbot=chatbot, history=[], delay=1)

    # download video
    chatbot.append((None, "下载视频, 请稍等...")); yield from update_ui(chatbot=chatbot, history=history)
    downloaded_files_part2 = yield from download_video(bvid, only_audio=False, user_name=user_name, chatbot=chatbot, history=history)

    # preview
    preview_list = [promote_file_to_downloadzone(fp) for fp in downloaded_files_part2]
    file_links = generate_file_link(preview_list)
    yield from update_ui_latest_msg(f"已完成的文件: <br/>" + file_links, chatbot=chatbot, history=history, delay=0)

    # return
    return downloaded_files + downloaded_files_part2


class Strategy(BaseModel):
    thought: str = Field(description="analysis of the user's wish, for example, can you recall the name of the resource?")
    which_methods: str = Field(description="Which method to use to find the necessary information? choose from 'method_1' and 'method_2'.")
    method_1_search_keywords: str = Field(description="Generate keywords to search the internet if you choose method 1, otherwise empty.")
    method_2_generate_keywords: str = Field(description="Generate keywords for video download engine if you choose method 2, otherwise empty.")


@CatchException
def 多媒体任务(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    user_wish: str = txt
    # query demos: 
    #   - "我想找一首歌，里面有句歌词是“turn your face towards the sun”"
    #   - "一首歌，第一句是红豆生南国"
    #   - "一首音乐，中国航天任务专用的那首"
    #   - "戴森球计划在熔岩星球的音乐"
    #   - "hanser的百变什么精"
    #   - "打大圣残躯时的bgm"
    #   - "渊下宫战斗音乐"

    # 搜索
    chatbot.append((txt, "检索中, 请稍等..."))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    if "跳过联网搜索" not in user_wish:
        # 结构化生成
        internet_search_keyword = user_wish

        yield from update_ui_latest_msg(lastmsg=f"发起互联网检索: {internet_search_keyword} ...", chatbot=chatbot, history=[], delay=1)
        from crazy_functions.Internet_GPT import internet_search_with_analysis_prompt
        result = yield from internet_search_with_analysis_prompt(
            prompt=internet_search_keyword,
            analysis_prompt="请根据搜索结果分析，获取用户需要找的资源的名称、作者、出处等信息。",
            llm_kwargs=llm_kwargs,
            chatbot=chatbot
        )

        yield from update_ui_latest_msg(lastmsg=f"互联网检索结论: {result} \n\n 正在生成进一步检索方案 ...", chatbot=chatbot, history=[], delay=1)
        rf_req = dedent(f"""
        The user wish to get the following resource:
            {user_wish}
        Meanwhile, you can access another expert's opinion on the user's wish:
            {result}
        Generate search keywords (less than 5 keywords) for video download engine accordingly.
        """)
    else:
        user_wish = user_wish.replace("跳过联网搜索", "").strip()
        rf_req = dedent(f"""
        The user wish to get the following resource:
            {user_wish}
        Generate research keywords (less than 5 keywords) accordingly.
        """)
    gpt_json_io = GptJsonIO(Query)
    inputs = rf_req + gpt_json_io.format_instructions
    run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
    analyze_res = run_gpt_fn(inputs, "")
    logger.info(analyze_res)
    query: Query = gpt_json_io.generate_output_auto_repair(analyze_res, run_gpt_fn)
    video_engine_keywords = query.search_keyword
    # 关键词展示
    chatbot.append((None, f"检索关键词已确认: {video_engine_keywords}。筛选中, 请稍等..."))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 获取候选资源
    candidate_dictionary: dict =  get_video_resource(video_engine_keywords)
    candidate_dictionary_as_str = json.dumps(candidate_dictionary, ensure_ascii=False, indent=4)

    # 展示候选资源
    candidate_display = "\n".join([f"{i+1}. {it['title']}" for i, it in enumerate(candidate_dictionary)])
    chatbot.append((None, f"候选:\n\n{candidate_display}"))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 结构化生成
    rf_req_2 = dedent(f"""
    The user wish to get the following resource:
        {user_wish}

    Select the most relevant and suitable video resource from the following search results:
        {candidate_dictionary_as_str}

    Note:
        1. The first several search video results are more likely to satisfy the user's wish.
        2. The time duration of the video should be less than 10 minutes.
        3. You should analyze the search results first, before giving your answer.
        4. Use Chinese if possible.
        5. Beside the primary video selection, give a backup video resource `bvid`.
    """)
    gpt_json_io = GptJsonIO(VideoResource)
    inputs = rf_req_2 + gpt_json_io.format_instructions
    run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
    analyze_res = run_gpt_fn(inputs, "")
    logger.info(analyze_res)
    video_resource: VideoResource = gpt_json_io.generate_output_auto_repair(analyze_res, run_gpt_fn)

    # Display
    chatbot.append(
        (None, 
            f"分析：{video_resource.thought}" "<br/>"
            f"选择: `{video_resource.title}`。" "<br/>" 
            f"作者：{video_resource.author}"
        )
    )
    chatbot.append((None, f"下载中, 请稍等..."))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    if video_resource and video_resource.bvid:
        logger.info(video_resource)
        downloaded = yield from download_video(video_resource.bvid, chatbot.get_user(), chatbot, history)
        if not downloaded:
            chatbot.append((None, f"下载失败, 尝试备选 ..."))
            yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
            downloaded = yield from download_video(video_resource.another_failsafe_bvid, chatbot.get_user(), chatbot, history)




        
@CatchException
def debug(bvid, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    yield from download_video(bvid, chatbot.get_user(), chatbot, history)