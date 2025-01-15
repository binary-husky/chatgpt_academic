from toolbox import CatchException, report_exception, get_log_folder, gen_time_str
from toolbox import update_ui, promote_file_to_downloadzone, update_ui_lastest_msg, disable_auto_promotion
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from crazy_functions.crazy_utils import request_gpt_model_multi_threads_with_very_awesome_ui_and_high_efficiency
from crazy_functions.crazy_utils import read_and_clean_pdf_text
from .pdf_fns.parse_pdf import parse_pdf, get_avail_grobid_url, translate_pdf
from shared_utils.colorful import *
import copy
import os
import math
import logging
import time


@CatchException
def 解析PDF文档(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    disable_auto_promotion(chatbot)
    # 基本信息：功能、贡献者
    chatbot.append([
        "函数插件功能？",
        "使用`MinerU`解析PDF文档到Markdown。(支持版本-1.0.1)\n\n"
        "由于MinerU环境与gpt_academic冲突，需要事先创建好名字为`MinerU`的Conda环境。\n\n"
        "安装命令如下：\n\n"
        "```sh\n"
        "conda create -n MinerU python=3.10\n"
        "conda activate MinerU\n"
        "pip install -U 'magic-pdf[full]' --extra-index-url https://wheels.myhloli.com\n```\n\n"
        "默认使用CPU，使用GPU加速至少需要8GB显存，需要修改 `~/magic-pdf.json` 中的 `device-mode` 为 `cuda`\n\n"
        "函数插件贡献者: Xunge-Jiang"])
    yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面

    # 清空历史，以免输入溢出
    history = []

    from crazy_functions.crazy_utils import get_files_from_everything
    success, file_manifest, project_folder = get_files_from_everything(txt, type='.pdf')

    # success_md, file_manifest_md, _ = get_files_from_everything(txt, type='.md')
    # success = success or success_md
    # file_manifest += file_manifest_md
    chatbot.append(["文件列表：", ", ".join([e.split('/')[-1] for e in file_manifest])])
    yield from update_ui(chatbot=chatbot, history=history)
    # 检测输入参数，如没有给定输入参数，直接退出
    if not success:
        if txt == "": txt = '空空如也的输入栏'

    # 如果没找到任何文件
    if len(file_manifest) == 0:
        report_exception(chatbot, history,
                         a=f"解析项目: {txt}", b=f"找不到任何.pdf拓展名的文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # 开始正式执行任务
    yield from 解析PDF_基于MinerU(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history,
                                  system_prompt)


def 解析PDF_基于MinerU(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt):
    from crazy_functions.crazy_utils import mineru_interface
    mineru_handle = mineru_interface()
    for index, fp in enumerate(file_manifest):
        if fp.endswith('pdf'):
            chatbot.append(["当前进度：", f"正在解析论文，请稍候。"])
            yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
            if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop(
                "advanced_arg")
            conda_env = plugin_kwargs.get("advanced_arg", 'MinerU')
            md_path, zip_path = yield from mineru_handle.mineru_parse_pdf(fp, chatbot, history, conda_env)
            chatbot.append((f"成功啦", '请查收结果...'))
            yield from update_ui(chatbot=chatbot, history=history)
            time.sleep(1)  # 刷新界面
            promote_file_to_downloadzone(md_path, rename_file=None, chatbot=chatbot)
            promote_file_to_downloadzone(zip_path, rename_file=None, chatbot=chatbot)
        else:
            chatbot.append(["当前论文无法解析：", fp]);
            yield from update_ui(chatbot=chatbot, history=history)

    yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
