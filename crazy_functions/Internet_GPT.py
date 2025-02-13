import requests
import random
import time
import re
import json
from bs4 import BeautifulSoup
from functools import lru_cache
from itertools import zip_longest
from check_proxy import check_proxy
from toolbox import CatchException, update_ui, get_conf, update_ui_latest_msg
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive, input_clipping
from request_llms.bridge_all import model_info
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.prompts.internet import SearchOptimizerPrompt, SearchAcademicOptimizerPrompt

def search_optimizer(
    query,
    proxies,
    history,
    llm_kwargs,
    optimizer=1,
    categories="general",
    searxng_url=None,
    engines=None,
):
    # ------------- < 第1步：尝试进行搜索优化 > -------------
    # * 增强优化，会尝试结合历史记录进行搜索优化
    if optimizer == 2:
        his = " "
        if len(history) == 0:
            pass
        else:
            for i, h in enumerate(history):
                if i % 2 == 0:
                    his += f"Q: {h}\n"
                else:
                    his += f"A: {h}\n"
        if categories == "general":
            sys_prompt = SearchOptimizerPrompt.format(query=query, history=his, num=4)
        elif categories == "science":
            sys_prompt = SearchAcademicOptimizerPrompt.format(query=query, history=his, num=4)
    else:
        his = " "
        if categories == "general":
            sys_prompt = SearchOptimizerPrompt.format(query=query, history=his, num=3)
        elif categories == "science":
            sys_prompt = SearchAcademicOptimizerPrompt.format(query=query, history=his, num=3)
    
    mutable = ["", time.time(), ""]
    llm_kwargs["temperature"] = 0.8
    try:
        queries_json = predict_no_ui_long_connection(
            inputs=query,
            llm_kwargs=llm_kwargs,
            history=[],
            sys_prompt=sys_prompt,
            observe_window=mutable,
        )
    except Exception:
        queries_json = "1234"
    #* 尝试解码优化后的搜索结果
    queries_json = re.sub(r"```json|```", "", queries_json)
    try:
        queries = json.loads(queries_json)
    except Exception:
        #* 如果解码失败,降低温度再试一次
        try:
            llm_kwargs["temperature"] = 0.4
            queries_json = predict_no_ui_long_connection(
                inputs=query,
                llm_kwargs=llm_kwargs,
                history=[],
                sys_prompt=sys_prompt,
                observe_window=mutable,
            )
            queries_json = re.sub(r"```json|```", "", queries_json)
            queries = json.loads(queries_json)
        except Exception:
            #* 如果再次失败，直接返回原始问题
            queries = [query]
    links = []
    success = 0
    Exceptions = ""
    for q in queries:
        try:
            link = searxng_request(q, proxies, categories, searxng_url, engines=engines)
            if len(link) > 0:
                links.append(link[:-5])
                success += 1
        except Exception:
            Exceptions = Exception
            pass
    if success == 0:
        raise ValueError(f"在线搜索失败！\n{Exceptions}")
    # * 清洗搜索结果，依次放入每组第一，第二个搜索结果，并清洗重复的搜索结果
    seen_links = set()
    result = []
    for tuple in zip_longest(*links, fillvalue=None):
        for item in tuple:
            if item is not None:
                link = item["link"]
                if link not in seen_links:
                    seen_links.add(link)
                    result.append(item)
    return result


@lru_cache
def get_auth_ip():
    ip = check_proxy(None, return_ip=True)
    if ip is None:
        return '114.114.114.' + str(random.randint(1, 10))
    return ip


def searxng_request(query, proxies, categories='general', searxng_url=None, engines=None):
    if searxng_url is None:
        urls = get_conf("SEARXNG_URLS")
        url = random.choice(urls)
    else:
        url = searxng_url

    if engines == "Mixed":
        engines = None

    if categories == 'general':
        params = {
            'q': query,         # 搜索查询
            'format': 'json',   # 输出格式为JSON
            'language': 'zh',   # 搜索语言
            'engines': engines,
        }
    elif categories == 'science':
        params = {
            'q': query,         # 搜索查询
            'format': 'json',   # 输出格式为JSON
            'language': 'zh',   # 搜索语言
            'categories': 'science'
        }
    else:
        raise ValueError('不支持的检索类型')

    headers = {
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'X-Forwarded-For': get_auth_ip(),
        'X-Real-IP': get_auth_ip()
    }
    results = []
    response = requests.post(url, params=params, headers=headers, proxies=proxies, timeout=30)
    if response.status_code == 200:
        json_result = response.json()
        for result in json_result['results']:
            item = {
                "title": result.get("title", ""),
                "source": result.get("engines", "unknown"),
                "content": result.get("content", ""),
                "link": result["url"],
            }
            results.append(item)
        return results
    else:
        if response.status_code == 429:
            raise ValueError("Searxng（在线搜索服务）当前使用人数太多，请稍后。")
        else:
            raise ValueError("在线搜索失败，状态码: " + str(response.status_code) + '\t' + response.content.decode('utf-8'))


def scrape_text(url, proxies) -> str:
    """Scrape text from a webpage

    Args:
        url (str): The URL to scrape text from

    Returns:
        str: The scraped text
    """
    from loguru import logger
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Content-Type': 'text/plain',
    }

    # 首先采用Jina进行文本提取
    if get_conf("JINA_API_KEY"):
        try: return jina_scrape_text(url)
        except: logger.debug("Jina API 请求失败，回到旧方法")

    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=8)
        if response.encoding == "ISO-8859-1": response.encoding = response.apparent_encoding
    except:
        return "无法连接到该网页"
    soup = BeautifulSoup(response.text, "html.parser")
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    return text


def jina_scrape_text(url) -> str:
    "jina_39727421c8fa4e4fa9bd698e5211feaaDyGeVFESNrRaepWiLT0wmHYJSh-d"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Content-Type': 'text/plain',
        "X-Retain-Images": "none",
        "Authorization": f'Bearer {get_conf("JINA_API_KEY")}'
    }
    response = requests.get("https://r.jina.ai/" + url, headers=headers, proxies=None, timeout=8)
    if response.status_code != 200:
        raise ValueError("Jina API 请求失败，开始尝试旧方法！" + response.text)
    if response.encoding == "ISO-8859-1": response.encoding = response.apparent_encoding
    result = response.text
    result = result.replace("\\[", "[").replace("\\]", "]").replace("\\(", "(").replace("\\)", ")")
    return response.text


def internet_search_with_analysis_prompt(prompt, analysis_prompt, llm_kwargs, chatbot):
    from toolbox import get_conf
    proxies = get_conf('proxies')
    categories = 'general'
    searxng_url = None  # 使用默认的searxng_url
    engines = None  # 使用默认的搜索引擎
    yield from update_ui_latest_msg(lastmsg=f"检索中: {prompt} ...", chatbot=chatbot, history=[], delay=1)
    urls = searxng_request(prompt, proxies, categories, searxng_url, engines=engines)
    yield from update_ui_latest_msg(lastmsg=f"依次访问搜索到的网站 ...", chatbot=chatbot, history=[], delay=1)
    if len(urls) == 0:
        return None
    max_search_result = 5   # 最多收纳多少个网页的结果
    history = []
    for index, url in enumerate(urls[:max_search_result]):
        yield from update_ui_latest_msg(lastmsg=f"依次访问搜索到的网站: {url['link']} ...", chatbot=chatbot, history=[], delay=1)
        res = scrape_text(url['link'], proxies)
        prefix = f"第{index}份搜索结果 [源自{url['source'][0]}搜索] （{url['title'][:25]}）："
        history.extend([prefix, res])
    i_say = f"从以上搜索结果中抽取信息，然后回答问题：{prompt} {analysis_prompt}"
    i_say, history = input_clipping( # 裁剪输入，从最长的条目开始裁剪，防止爆token
        inputs=i_say,
        history=history,
        max_token_limit=8192
    )
    gpt_say = predict_no_ui_long_connection(
        inputs=i_say,
        llm_kwargs=llm_kwargs,
        history=history,
        sys_prompt="请从搜索结果中抽取信息，对最相关的两个搜索结果进行总结，然后回答问题。",
        console_silence=False,
    )
    return gpt_say

@CatchException
def 连接网络回答问题(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    optimizer_history = history[:-8]
    history = []    # 清空历史，以免输入溢出
    chatbot.append((f"请结合互联网信息回答以下问题：{txt}", "检索中..."))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # ------------- < 第1步：爬取搜索引擎的结果 > -------------
    from toolbox import get_conf
    proxies = get_conf('proxies')
    categories = plugin_kwargs.get('categories', 'general')
    searxng_url = plugin_kwargs.get('searxng_url', None)
    engines = plugin_kwargs.get('engine', None)
    optimizer = plugin_kwargs.get('optimizer', "关闭")
    if optimizer == "关闭":
        urls = searxng_request(txt, proxies, categories, searxng_url, engines=engines)
    else:
        urls = search_optimizer(txt, proxies, optimizer_history, llm_kwargs, optimizer, categories, searxng_url, engines)
    history = []
    if len(urls) == 0:
        chatbot.append((f"结论：{txt}", "[Local Message] 受到限制，无法从searxng获取信息！请尝试更换搜索引擎。"))
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # ------------- < 第2步：依次访问网页 > -------------
    from concurrent.futures import ThreadPoolExecutor
    from textwrap import dedent
    max_search_result = 5   # 最多收纳多少个网页的结果
    if optimizer == "开启(增强)":
        max_search_result = 8
    template = dedent("""
        <details>
        <summary>{TITLE}</summary>
        <div class="search_result">{URL}</div>
        <div class="search_result">{CONTENT}</div>
        </details>
    """)

    buffer = ""

    # 创建线程池
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交任务到线程池
        futures = []
        for index, url in enumerate(urls[:max_search_result]):
            future = executor.submit(scrape_text, url['link'], proxies)
            futures.append((index, future, url))

        # 处理完成的任务
        for index, future, url in futures:
            # 开始
            prefix = f"正在加载 第{index+1}份搜索结果 [源自{url['source'][0]}搜索] （{url['title'][:25]}）："
            string_structure = template.format(TITLE=prefix, URL=url['link'], CONTENT="正在加载，请稍后 ......")
            yield from update_ui_lastest_msg(lastmsg=(buffer + string_structure), chatbot=chatbot, history=history, delay=0.1)  # 刷新界面

            # 获取结果
            res = future.result()

            # 显示结果
            prefix = f"第{index+1}份搜索结果 [源自{url['source'][0]}搜索] （{url['title'][:25]}）："
            string_structure = template.format(TITLE=prefix, URL=url['link'], CONTENT=res[:1000] + "......")
            buffer += string_structure

            # 更新历史
            history.extend([prefix, res])
            yield from update_ui_lastest_msg(lastmsg=buffer, chatbot=chatbot, history=history, delay=0.1)  # 刷新界面

    # ------------- < 第3步：ChatGPT综合 > -------------
    if (optimizer != "开启(增强)"):
        i_say = f"从以上搜索结果中抽取信息，然后回答问题：{txt}"
        i_say, history = input_clipping(    # 裁剪输入，从最长的条目开始裁剪，防止爆token
            inputs=i_say,
            history=history,
            max_token_limit=min(model_info[llm_kwargs['llm_model']]['max_token']*3//4, 8192)
        )
        gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
            inputs=i_say, inputs_show_user=i_say,
            llm_kwargs=llm_kwargs, chatbot=chatbot, history=history,
            sys_prompt="请从给定的若干条搜索结果中抽取信息，对最相关的两个搜索结果进行总结，然后回答问题。"
        )
        chatbot[-1] = (i_say, gpt_say)
        history.append(i_say);history.append(gpt_say)
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新

    #* 或者使用搜索优化器，这样可以保证后续问答能读取到有效的历史记录
    else:
        i_say = f"从以上搜索结果中抽取与问题：{txt} 相关的信息:"
        i_say, history = input_clipping(    # 裁剪输入，从最长的条目开始裁剪，防止爆token
            inputs=i_say,
            history=history,
            max_token_limit=min(model_info[llm_kwargs['llm_model']]['max_token']*3//4, 8192)
        )
        gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
            inputs=i_say, inputs_show_user=i_say,
            llm_kwargs=llm_kwargs, chatbot=chatbot, history=history,
            sys_prompt="请从给定的若干条搜索结果中抽取信息，对最相关的三个搜索结果进行总结"
        )
        chatbot[-1] = (i_say, gpt_say)
        history = []
        history.append(i_say);history.append(gpt_say)
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新

        # ------------- < 第4步：根据综合回答问题 > -------------
        i_say = f"请根据以上搜索结果回答问题：{txt}"
        gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
            inputs=i_say, inputs_show_user=i_say,
            llm_kwargs=llm_kwargs, chatbot=chatbot, history=history,
            sys_prompt="请根据给定的若干条搜索结果回答问题"
        )
        chatbot[-1] = (i_say, gpt_say)
        history.append(i_say);history.append(gpt_say)
        yield from update_ui(chatbot=chatbot, history=history)