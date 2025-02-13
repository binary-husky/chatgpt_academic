from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from toolbox import CatchException, report_exception, promote_file_to_downloadzone
from toolbox import update_ui, update_ui_latest_msg, disable_auto_promotion, write_history_to_file
import logging
import requests
import time
import random

ENABLE_ALL_VERSION_SEARCH = True

def get_meta_information(url, chatbot, history):
    import arxiv
    import difflib
    import re
    from bs4 import BeautifulSoup
    from toolbox import get_conf
    from urllib.parse import urlparse
    session = requests.session()

    proxies = get_conf('proxies')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cache-Control':'max-age=0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Connection': 'keep-alive'
    }
    try:
        session.proxies.update(proxies)
    except:
        report_exception(chatbot, history,
                    a=f"获取代理失败 无代理状态下很可能无法访问OpenAI家族的模型及谷歌学术 建议：检查USE_PROXY选项是否修改。",
                    b=f"尝试直接连接")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
    session.headers.update(headers)

    response = session.get(url)
    # 解析网页内容
    soup = BeautifulSoup(response.text, "html.parser")

    def string_similar(s1, s2):
        return difflib.SequenceMatcher(None, s1, s2).quick_ratio()

    if ENABLE_ALL_VERSION_SEARCH:
        def search_all_version(url):
            time.sleep(random.randint(1,5)) # 睡一会防止触发google反爬虫
            response = session.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            for result in soup.select(".gs_ri"):
                try:
                    url = result.select_one(".gs_rt").a['href']
                except:
                    continue
                arxiv_id = extract_arxiv_id(url)
                if not arxiv_id:
                    continue
                search = arxiv.Search(
                    id_list=[arxiv_id],
                    max_results=1,
                    sort_by=arxiv.SortCriterion.Relevance,
                )
                try: paper = next(search.results())
                except: paper = None
                return paper

            return None

        def extract_arxiv_id(url):
            # 返回给定的url解析出的arxiv_id，如url未成功匹配返回None
            pattern = r'arxiv.org/abs/([^/]+)'
            match = re.search(pattern, url)
            if match:
                return match.group(1)
            else:
                return None

    profile = []
    # 获取所有文章的标题和作者
    for result in soup.select(".gs_ri"):
        title = result.a.text.replace('\n', ' ').replace('  ', ' ')
        author = result.select_one(".gs_a").text
        try:
            citation = result.select_one(".gs_fl > a[href*='cites']").text  # 引用次数是链接中的文本，直接取出来
        except:
            citation = 'cited by 0'
        abstract = result.select_one(".gs_rs").text.strip()  # 摘要在 .gs_rs 中的文本，需要清除首尾空格

        # 首先在arxiv上搜索，获取文章摘要
        search = arxiv.Search(
            query = title,
            max_results = 1,
            sort_by = arxiv.SortCriterion.Relevance,
        )
        try: paper = next(search.results())
        except: paper = None

        is_match = paper is not None and string_similar(title, paper.title) > 0.90

        # 如果在Arxiv上匹配失败，检索文章的历史版本的题目
        if not is_match and ENABLE_ALL_VERSION_SEARCH:
            other_versions_page_url = [tag['href'] for tag in result.select_one('.gs_flb').select('.gs_nph') if 'cluster' in tag['href']]
            if len(other_versions_page_url) > 0:
                other_versions_page_url = other_versions_page_url[0]
                paper = search_all_version('http://' + urlparse(url).netloc + other_versions_page_url)
                is_match = paper is not None and string_similar(title, paper.title) > 0.90

        if is_match:
            # same paper
            abstract = paper.summary.replace('\n', ' ')
            is_paper_in_arxiv = True
        else:
            # different paper
            abstract = abstract
            is_paper_in_arxiv = False

        logging.info('[title]:' + title)
        logging.info('[author]:' + author)
        logging.info('[citation]:' + citation)

        profile.append({
            'title': title,
            'author': author,
            'citation': citation,
            'abstract': abstract,
            'is_paper_in_arxiv': is_paper_in_arxiv,
        })

        chatbot[-1] = [chatbot[-1][0], title + f'\n\n是否在arxiv中（不在arxiv中无法获取完整摘要）:{is_paper_in_arxiv}\n\n' + abstract]
        yield from update_ui(chatbot=chatbot, history=[]) # 刷新界面
    return profile

@CatchException
def 谷歌检索小助手(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    disable_auto_promotion(chatbot=chatbot)
    # 基本信息：功能、贡献者
    chatbot.append([
        "函数插件功能？",
        "分析用户提供的谷歌学术（google scholar）搜索页面中，出现的所有文章: binary-husky，插件初始化中..."])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖，如果缺少依赖，则给出安装建议
    try:
        import arxiv
        import math
        from bs4 import BeautifulSoup
    except:
        report_exception(chatbot, history,
            a = f"解析项目: {txt}",
            b = f"导入软件依赖失败。使用该模块需要额外依赖，安装方法```pip install --upgrade beautifulsoup4 arxiv```。")
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # 清空历史，以免输入溢出
    history = []
    meta_paper_info_list = yield from get_meta_information(txt, chatbot, history)
    if len(meta_paper_info_list) == 0:
        yield from update_ui_latest_msg(lastmsg='获取文献失败，可能触发了google反爬虫机制。',chatbot=chatbot, history=history, delay=0)
        return
    batchsize = 5
    for batch in range(math.ceil(len(meta_paper_info_list)/batchsize)):
        if len(meta_paper_info_list[:batchsize]) > 0:
            i_say = "下面是一些学术文献的数据，提取出以下内容：" + \
            "1、英文题目；2、中文题目翻译；3、作者；4、arxiv公开（is_paper_in_arxiv）；4、引用数量（cite）；5、中文摘要翻译。" + \
            f"以下是信息源：{str(meta_paper_info_list[:batchsize])}"

            inputs_show_user = f"请分析此页面中出现的所有文章：{txt}，这是第{batch+1}批"
            gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs=i_say, inputs_show_user=inputs_show_user,
                llm_kwargs=llm_kwargs, chatbot=chatbot, history=[],
                sys_prompt="你是一个学术翻译，请从数据中提取信息。你必须使用Markdown表格。你必须逐个文献进行处理。"
            )

            history.extend([ f"第{batch+1}批", gpt_say ])
            meta_paper_info_list = meta_paper_info_list[batchsize:]

    chatbot.append(["状态？",
        "已经全部完成，您可以试试让AI写一个Related Works，例如您可以继续输入Write a \"Related Works\" section about \"你搜索的研究领域\" for me."])
    msg = '正常'
    yield from update_ui(chatbot=chatbot, history=history, msg=msg) # 刷新界面
    path = write_history_to_file(history)
    promote_file_to_downloadzone(path, chatbot=chatbot)
    chatbot.append(("完成了吗？", path));
    yield from update_ui(chatbot=chatbot, history=history, msg=msg) # 刷新界面
