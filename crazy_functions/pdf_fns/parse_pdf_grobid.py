import os
from toolbox import CatchException, report_exception, get_log_folder, gen_time_str, check_packages
from toolbox import update_ui, promote_file_to_downloadzone, update_ui_latest_msg, disable_auto_promotion
from toolbox import write_history_to_file, promote_file_to_downloadzone, get_conf, extract_archive
from crazy_functions.pdf_fns.parse_pdf import parse_pdf, translate_pdf

def 解析PDF_基于GROBID(file_manifest, project_folder, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, grobid_url):
    import copy, json
    TOKEN_LIMIT_PER_FRAGMENT = 1024
    generated_conclusion_files = []
    generated_html_files = []
    DST_LANG = "中文"
    from crazy_functions.pdf_fns.report_gen_html import construct_html
    for index, fp in enumerate(file_manifest):
        chatbot.append(["当前进度：", f"正在连接GROBID服务，请稍候: {grobid_url}\n如果等待时间过长，请修改config中的GROBID_URL，可修改成本地GROBID服务。"]); yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        article_dict = parse_pdf(fp, grobid_url)
        grobid_json_res = os.path.join(get_log_folder(), gen_time_str() + "grobid.json")
        with open(grobid_json_res, 'w+', encoding='utf8') as f:
            f.write(json.dumps(article_dict, indent=4, ensure_ascii=False))
        promote_file_to_downloadzone(grobid_json_res, chatbot=chatbot)
        if article_dict is None: raise RuntimeError("解析PDF失败，请检查PDF是否损坏。")
        yield from translate_pdf(article_dict, llm_kwargs, chatbot, fp, generated_conclusion_files, TOKEN_LIMIT_PER_FRAGMENT, DST_LANG, plugin_kwargs=plugin_kwargs)
    chatbot.append(("给出输出文件清单", str(generated_conclusion_files + generated_html_files)))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面


