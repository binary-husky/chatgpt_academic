from toolbox import CatchException, check_packages, get_conf
from toolbox import update_ui, update_ui_latest_msg, disable_auto_promotion
from toolbox import trimmed_format_exc_markdown
from crazy_functions.crazy_utils import get_files_from_everything
from crazy_functions.pdf_fns.parse_pdf import get_avail_grobid_url
from crazy_functions.pdf_fns.parse_pdf_via_doc2x import 解析PDF_基于DOC2X
from crazy_functions.pdf_fns.parse_pdf_legacy import 解析PDF_简单拆解
from crazy_functions.pdf_fns.parse_pdf_grobid import 解析PDF_基于GROBID
from shared_utils.colorful import *

@CatchException
def 批量翻译PDF文档(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):

    disable_auto_promotion(chatbot)
    # 基本信息：功能、贡献者
    chatbot.append([None, "插件功能：批量翻译PDF文档。函数插件贡献者: Binary-Husky"])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖，如果缺少依赖，则给出安装建议
    try:
        check_packages(["fitz", "tiktoken", "scipdf"])
    except:
        chatbot.append([None, f"导入软件依赖失败。使用该模块需要额外依赖，安装方法```pip install --upgrade pymupdf tiktoken scipdf_parser```。"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # 清空历史，以免输入溢出
    history = []
    success, file_manifest, project_folder = get_files_from_everything(txt, type='.pdf')

    # 检测输入参数，如没有给定输入参数，直接退出
    if (not success) and txt == "": txt = '空空如也的输入栏。提示：请先上传文件（把PDF文件拖入对话）。'

    # 如果没找到任何文件
    if len(file_manifest) == 0:
        chatbot.append([None, f"找不到任何.pdf拓展名的文件: {txt}"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # 开始正式执行任务
    method = plugin_kwargs.get("pdf_parse_method", None)
    if method == "DOC2X":
        # ------- 第一种方法，效果最好，但是需要DOC2X服务 -------
        DOC2X_API_KEY = get_conf("DOC2X_API_KEY")
        if len(DOC2X_API_KEY) != 0:
            try:
                yield from 解析PDF_基于DOC2X(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, DOC2X_API_KEY, user_request)
                return
            except:
                chatbot.append([None, f"DOC2X服务不可用，请检查报错详细。{trimmed_format_exc_markdown()}"])
                yield from update_ui(chatbot=chatbot, history=history)

    if method == "GROBID":
        # ------- 第二种方法，效果次优 -------
        grobid_url = get_avail_grobid_url()
        if grobid_url is not None:
            yield from 解析PDF_基于GROBID(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, grobid_url)
            return

    if method == "Classic":
        # ------- 第三种方法，早期代码，效果不理想 -------
        yield from update_ui_latest_msg("GROBID服务不可用，请检查config中的GROBID_URL。作为替代，现在将执行效果稍差的旧版代码。", chatbot, history, delay=3)
        yield from 解析PDF_简单拆解(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt)
        return

    if method is None:
        # ------- 以上三种方法都试一遍 -------
        DOC2X_API_KEY = get_conf("DOC2X_API_KEY")
        if len(DOC2X_API_KEY) != 0:
            try:
                yield from 解析PDF_基于DOC2X(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, DOC2X_API_KEY, user_request)
                return
            except:
                chatbot.append([None, f"DOC2X服务不可用，正在尝试GROBID。{trimmed_format_exc_markdown()}"])
                yield from update_ui(chatbot=chatbot, history=history)
        grobid_url = get_avail_grobid_url()
        if grobid_url is not None:
            yield from 解析PDF_基于GROBID(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, grobid_url)
            return
        yield from update_ui_latest_msg("GROBID服务不可用，请检查config中的GROBID_URL。作为替代，现在将执行效果稍差的旧版代码。", chatbot, history, delay=3)
        yield from 解析PDF_简单拆解(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt)
        return

