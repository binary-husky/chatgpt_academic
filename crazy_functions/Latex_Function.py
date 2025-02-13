from toolbox import update_ui, trimmed_format_exc, get_conf, get_log_folder, promote_file_to_downloadzone, check_repeat_upload, map_file_to_sha256
from toolbox import CatchException, report_exception, update_ui_latest_msg, zip_result, gen_time_str
from functools import partial
from loguru import logger

import glob, os, requests, time, json, tarfile, threading

pj = os.path.join
ARXIV_CACHE_DIR = get_conf("ARXIV_CACHE_DIR")


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- 工具函数 =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# 专业词汇声明  = 'If the term "agent" is used in this section, it should be translated to "智能体". '
def switch_prompt(pfg, mode, more_requirement):
    """
    Generate prompts and system prompts based on the mode for proofreading or translating.
    Args:
    - pfg: Proofreader or Translator instance.
    - mode: A string specifying the mode, either 'proofread' or 'translate_zh'.

    Returns:
    - inputs_array: A list of strings containing prompts for users to respond to.
    - sys_prompt_array: A list of strings containing prompts for system prompts.
    """
    n_split = len(pfg.sp_file_contents)
    if mode == 'proofread_en':
        inputs_array = [r"Below is a section from an academic paper, proofread this section." +
                        r"Do not modify any latex command such as \section, \cite, \begin, \item and equations. " + more_requirement +
                        r"Answer me only with the revised text:" +
                        f"\n\n{frag}" for frag in pfg.sp_file_contents]
        sys_prompt_array = ["You are a professional academic paper writer." for _ in range(n_split)]
    elif mode == 'translate_zh':
        inputs_array = [
            r"Below is a section from an English academic paper, translate it into Chinese. " + more_requirement +
            r"Do not modify any latex command such as \section, \cite, \begin, \item and equations. " +
            r"Answer me only with the translated text:" +
            f"\n\n{frag}" for frag in pfg.sp_file_contents]
        sys_prompt_array = ["You are a professional translator." for _ in range(n_split)]
    else:
        assert False, "未知指令"
    return inputs_array, sys_prompt_array


def descend_to_extracted_folder_if_exist(project_folder):
    """
    Descend into the extracted folder if it exists, otherwise return the original folder.

    Args:
    - project_folder: A string specifying the folder path.

    Returns:
    - A string specifying the path to the extracted folder, or the original folder if there is no extracted folder.
    """
    maybe_dir = [f for f in glob.glob(f'{project_folder}/*') if os.path.isdir(f)]
    if len(maybe_dir) == 0: return project_folder
    if maybe_dir[0].endswith('.extract'): return maybe_dir[0]
    return project_folder


def move_project(project_folder, arxiv_id=None):
    """
    Create a new work folder and copy the project folder to it.

    Args:
    - project_folder: A string specifying the folder path of the project.

    Returns:
    - A string specifying the path to the new work folder.
    """
    import shutil, time
    time.sleep(2)  # avoid time string conflict
    if arxiv_id is not None:
        new_workfolder = pj(ARXIV_CACHE_DIR, arxiv_id, 'workfolder')
    else:
        new_workfolder = f'{get_log_folder()}/{gen_time_str()}'
    try:
        shutil.rmtree(new_workfolder)
    except:
        pass

    # align subfolder if there is a folder wrapper
    items = glob.glob(pj(project_folder, '*'))
    items = [item for item in items if os.path.basename(item) != '__MACOSX']
    if len(glob.glob(pj(project_folder, '*.tex'))) == 0 and len(items) == 1:
        if os.path.isdir(items[0]): project_folder = items[0]

    shutil.copytree(src=project_folder, dst=new_workfolder)
    return new_workfolder


def arxiv_download(chatbot, history, txt, allow_cache=True):
    def check_cached_translation_pdf(arxiv_id):
        translation_dir = pj(ARXIV_CACHE_DIR, arxiv_id, 'translation')
        if not os.path.exists(translation_dir):
            os.makedirs(translation_dir)
        target_file = pj(translation_dir, 'translate_zh.pdf')
        if os.path.exists(target_file):
            promote_file_to_downloadzone(target_file, rename_file=None, chatbot=chatbot)
            target_file_compare = pj(translation_dir, 'comparison.pdf')
            if os.path.exists(target_file_compare):
                promote_file_to_downloadzone(target_file_compare, rename_file=None, chatbot=chatbot)
            return target_file
        return False

    def is_float(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    if txt.startswith('https://arxiv.org/pdf/'):
        arxiv_id = txt.split('/')[-1]   # 2402.14207v2.pdf
        txt = arxiv_id.split('v')[0]  # 2402.14207

    if ('.' in txt) and ('/' not in txt) and is_float(txt):  # is arxiv ID
        txt = 'https://arxiv.org/abs/' + txt.strip()
    if ('.' in txt) and ('/' not in txt) and is_float(txt[:10]):  # is arxiv ID
        txt = 'https://arxiv.org/abs/' + txt[:10]

    if not txt.startswith('https://arxiv.org'):
        return txt, None    # 是本地文件，跳过下载

    # <-------------- inspect format ------------->
    chatbot.append([f"检测到arxiv文档连接", '尝试下载 ...'])
    yield from update_ui(chatbot=chatbot, history=history)
    time.sleep(1)  # 刷新界面

    url_ = txt  # https://arxiv.org/abs/1707.06690

    if not txt.startswith('https://arxiv.org/abs/'):
        msg = f"解析arxiv网址失败, 期望格式例如: https://arxiv.org/abs/1707.06690。实际得到格式: {url_}。"
        yield from update_ui_latest_msg(msg, chatbot=chatbot, history=history)  # 刷新界面
        return msg, None
    # <-------------- set format ------------->
    arxiv_id = url_.split('/abs/')[-1]
    if 'v' in arxiv_id: arxiv_id = arxiv_id[:10]
    cached_translation_pdf = check_cached_translation_pdf(arxiv_id)
    if cached_translation_pdf and allow_cache: return cached_translation_pdf, arxiv_id

    extract_dst = pj(ARXIV_CACHE_DIR, arxiv_id, 'extract')
    translation_dir = pj(ARXIV_CACHE_DIR, arxiv_id, 'e-print')
    dst = pj(translation_dir, arxiv_id + '.tar')
    os.makedirs(translation_dir, exist_ok=True)
    # <-------------- download arxiv source file ------------->

    def fix_url_and_download():
        # for url_tar in [url_.replace('/abs/', '/e-print/'), url_.replace('/abs/', '/src/')]:
        for url_tar in [url_.replace('/abs/', '/src/'), url_.replace('/abs/', '/e-print/')]:
            proxies = get_conf('proxies')
            r = requests.get(url_tar, proxies=proxies)
            if r.status_code == 200:
                with open(dst, 'wb+') as f:
                    f.write(r.content)
                return True
        return False

    if os.path.exists(dst) and allow_cache:
        yield from update_ui_latest_msg(f"调用缓存 {arxiv_id}", chatbot=chatbot, history=history)  # 刷新界面
        success = True
    else:
        yield from update_ui_latest_msg(f"开始下载 {arxiv_id}", chatbot=chatbot, history=history)  # 刷新界面
        success = fix_url_and_download()
        yield from update_ui_latest_msg(f"下载完成 {arxiv_id}", chatbot=chatbot, history=history)  # 刷新界面


    if not success:
        yield from update_ui_latest_msg(f"下载失败 {arxiv_id}", chatbot=chatbot, history=history)
        raise tarfile.ReadError(f"论文下载失败 {arxiv_id}")

    # <-------------- extract file ------------->
    from toolbox import extract_archive
    try:
        extract_archive(file_path=dst, dest_dir=extract_dst)
    except tarfile.ReadError:
        os.remove(dst)
        raise tarfile.ReadError(f"论文下载失败")
    return extract_dst, arxiv_id


def pdf2tex_project(pdf_file_path, plugin_kwargs):
    if plugin_kwargs["method"] == "MATHPIX":
        # Mathpix API credentials
        app_id, app_key = get_conf('MATHPIX_APPID', 'MATHPIX_APPKEY')
        headers = {"app_id": app_id, "app_key": app_key}

        # Step 1: Send PDF file for processing
        options = {
            "conversion_formats": {"tex.zip": True},
            "math_inline_delimiters": ["$", "$"],
            "rm_spaces": True
        }

        response = requests.post(url="https://api.mathpix.com/v3/pdf",
                                headers=headers,
                                data={"options_json": json.dumps(options)},
                                files={"file": open(pdf_file_path, "rb")})

        if response.ok:
            pdf_id = response.json()["pdf_id"]
            logger.info(f"PDF processing initiated. PDF ID: {pdf_id}")

            # Step 2: Check processing status
            while True:
                conversion_response = requests.get(f"https://api.mathpix.com/v3/pdf/{pdf_id}", headers=headers)
                conversion_data = conversion_response.json()

                if conversion_data["status"] == "completed":
                    logger.info("PDF processing completed.")
                    break
                elif conversion_data["status"] == "error":
                    logger.info("Error occurred during processing.")
                else:
                    logger.info(f"Processing status: {conversion_data['status']}")
                    time.sleep(5)  # wait for a few seconds before checking again

            # Step 3: Save results to local files
            output_dir = os.path.join(os.path.dirname(pdf_file_path), 'mathpix_output')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            url = f"https://api.mathpix.com/v3/pdf/{pdf_id}.tex"
            response = requests.get(url, headers=headers)
            file_name_wo_dot = '_'.join(os.path.basename(pdf_file_path).split('.')[:-1])
            output_name = f"{file_name_wo_dot}.tex.zip"
            output_path = os.path.join(output_dir, output_name)
            with open(output_path, "wb") as output_file:
                output_file.write(response.content)
            logger.info(f"tex.zip file saved at: {output_path}")

            import zipfile
            unzip_dir = os.path.join(output_dir, file_name_wo_dot)
            with zipfile.ZipFile(output_path, 'r') as zip_ref:
                zip_ref.extractall(unzip_dir)

            return unzip_dir

        else:
            logger.error(f"Error sending PDF for processing. Status code: {response.status_code}")
            return None
    else:
        from crazy_functions.pdf_fns.parse_pdf_via_doc2x import 解析PDF_DOC2X_转Latex
        unzip_dir = 解析PDF_DOC2X_转Latex(pdf_file_path)
        return unzip_dir




# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= 插件主程序1 =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


@CatchException
def Latex英文纠错加PDF对比(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    # <-------------- information about this plugin ------------->
    chatbot.append(["函数插件功能？",
                    "对整个Latex项目进行纠错, 用latex编译为PDF对修正处做高亮。函数插件贡献者: Binary-Husky。注意事项: 目前对机器学习类文献转化效果最好，其他类型文献转化效果未知。仅在Windows系统进行了测试，其他操作系统表现未知。"])
    yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面

    # <-------------- more requirements ------------->
    if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop("advanced_arg")
    more_req = plugin_kwargs.get("advanced_arg", "")
    _switch_prompt_ = partial(switch_prompt, more_requirement=more_req)

    # <-------------- check deps ------------->
    try:
        import glob, os, time, subprocess
        subprocess.Popen(['pdflatex', '-version'])
        from .latex_fns.latex_actions import Latex精细分解与转化, 编译Latex
    except Exception as e:
        chatbot.append([f"解析项目: {txt}",
                        f"尝试执行Latex指令失败。Latex没有安装, 或者不在环境变量PATH中。安装方法https://tug.org/texlive/。报错信息\n\n```\n\n{trimmed_format_exc()}\n\n```\n\n"])
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- clear history and read input ------------->
    history = []
    if os.path.exists(txt):
        project_folder = txt
    else:
        if txt == "": txt = '空空如也的输入栏'
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到本地项目或无权访问: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return
    file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.tex', recursive=True)]
    if len(file_manifest) == 0:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到任何.tex文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- if is a zip/tar file ------------->
    project_folder = descend_to_extracted_folder_if_exist(project_folder)

    # <-------------- move latex project away from temp folder ------------->
    from shared_utils.fastapi_server import validate_path_safety
    validate_path_safety(project_folder, chatbot.get_user())
    project_folder = move_project(project_folder, arxiv_id=None)

    # <-------------- if merge_translate_zh is already generated, skip gpt req ------------->
    if not os.path.exists(project_folder + '/merge_proofread_en.tex'):
        yield from Latex精细分解与转化(file_manifest, project_folder, llm_kwargs, plugin_kwargs,
                                       chatbot, history, system_prompt, mode='proofread_en',
                                       switch_prompt=_switch_prompt_)

    # <-------------- compile PDF ------------->
    success = yield from 编译Latex(chatbot, history, main_file_original='merge',
                                   main_file_modified='merge_proofread_en',
                                   work_folder_original=project_folder, work_folder_modified=project_folder,
                                   work_folder=project_folder)

    # <-------------- zip PDF ------------->
    zip_res = zip_result(project_folder)
    if success:
        chatbot.append((f"成功啦", '请查收结果（压缩包）...'))
        yield from update_ui(chatbot=chatbot, history=history);
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)
    else:
        chatbot.append((f"失败了",
                        '虽然PDF生成失败了, 但请查收结果（压缩包）, 内含已经翻译的Tex文档, 也是可读的, 您可以到Github Issue区, 用该压缩包+Conversation_To_File进行反馈 ...'))
        yield from update_ui(chatbot=chatbot, history=history);
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)

    # <-------------- we are done ------------->
    return success


# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= 插件主程序2 =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@CatchException
def Latex翻译中文并重新编译PDF(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    # <-------------- information about this plugin ------------->
    chatbot.append([
        "函数插件功能？",
        "对整个Latex项目进行翻译, 生成中文PDF。函数插件贡献者: Binary-Husky。注意事项: 此插件Windows支持最佳，Linux下必须使用Docker安装，详见项目主README.md。目前对机器学习类文献转化效果最好，其他类型文献转化效果未知。"])
    yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面

    # <-------------- more requirements ------------->
    if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop("advanced_arg")
    more_req = plugin_kwargs.get("advanced_arg", "")

    no_cache = ("--no-cache" in more_req)
    if no_cache: more_req = more_req.replace("--no-cache", "").strip()

    allow_gptac_cloud_io = ("--allow-cloudio" in more_req)  # 从云端下载翻译结果，以及上传翻译结果到云端
    if allow_gptac_cloud_io: more_req = more_req.replace("--allow-cloudio", "").strip()

    allow_cache = not no_cache
    _switch_prompt_ = partial(switch_prompt, more_requirement=more_req)


    # <-------------- check deps ------------->
    try:
        import glob, os, time, subprocess
        subprocess.Popen(['pdflatex', '-version'])
        from .latex_fns.latex_actions import Latex精细分解与转化, 编译Latex
    except Exception as e:
        chatbot.append([f"解析项目: {txt}",
                        f"尝试执行Latex指令失败。Latex没有安装, 或者不在环境变量PATH中。安装方法https://tug.org/texlive/。报错信息\n\n```\n\n{trimmed_format_exc()}\n\n```\n\n"])
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- clear history and read input ------------->
    history = []
    try:
        txt, arxiv_id = yield from arxiv_download(chatbot, history, txt, allow_cache)
    except tarfile.ReadError as e:
        yield from update_ui_latest_msg(
            "无法自动下载该论文的Latex源码，请前往arxiv打开此论文下载页面，点other Formats，然后download source手动下载latex源码包。接下来调用本地Latex翻译插件即可。",
            chatbot=chatbot, history=history)
        return

    if txt.endswith('.pdf'):
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"发现已经存在翻译好的PDF文档")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # #################################################################
    if allow_gptac_cloud_io and arxiv_id:
        # 访问 GPTAC学术云，查询云端是否存在该论文的翻译版本
        from crazy_functions.latex_fns.latex_actions import check_gptac_cloud
        success, downloaded = check_gptac_cloud(arxiv_id, chatbot)
        if success:
            chatbot.append([
                f"检测到GPTAC云端存在翻译版本, 如果不满意翻译结果, 请禁用云端分享, 然后重新执行。", 
                None
            ])
            yield from update_ui(chatbot=chatbot, history=history)
            return
    #################################################################

    if os.path.exists(txt):
        project_folder = txt
    else:
        if txt == "": txt = '空空如也的输入栏'
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到本地项目或无法处理: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.tex', recursive=True)]
    if len(file_manifest) == 0:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到任何.tex文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- if is a zip/tar file ------------->
    project_folder = descend_to_extracted_folder_if_exist(project_folder)

    # <-------------- move latex project away from temp folder ------------->
    from shared_utils.fastapi_server import validate_path_safety
    validate_path_safety(project_folder, chatbot.get_user())
    project_folder = move_project(project_folder, arxiv_id)

    # <-------------- if merge_translate_zh is already generated, skip gpt req ------------->
    if not os.path.exists(project_folder + '/merge_translate_zh.tex'):
        yield from Latex精细分解与转化(file_manifest, project_folder, llm_kwargs, plugin_kwargs,
                                       chatbot, history, system_prompt, mode='translate_zh',
                                       switch_prompt=_switch_prompt_)

    # <-------------- compile PDF ------------->
    success = yield from 编译Latex(chatbot, history, main_file_original='merge',
                                   main_file_modified='merge_translate_zh', mode='translate_zh',
                                   work_folder_original=project_folder, work_folder_modified=project_folder,
                                   work_folder=project_folder)

    # <-------------- zip PDF ------------->
    zip_res = zip_result(project_folder)
    if success:
        if allow_gptac_cloud_io and arxiv_id:
            # 如果用户允许，我们将翻译好的arxiv论文PDF上传到GPTAC学术云
            from crazy_functions.latex_fns.latex_actions import upload_to_gptac_cloud_if_user_allow
            threading.Thread(target=upload_to_gptac_cloud_if_user_allow, 
                args=(chatbot, arxiv_id), daemon=True).start()

        chatbot.append((f"成功啦", '请查收结果（压缩包）...'))
        yield from update_ui(chatbot=chatbot, history=history)
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)

    else:
        chatbot.append((f"失败了",
                        '虽然PDF生成失败了, 但请查收结果（压缩包）, 内含已经翻译的Tex文档, 您可以到Github Issue区, 用该压缩包进行反馈。如系统是Linux，请检查系统字体（见Github wiki） ...'))
        yield from update_ui(chatbot=chatbot, history=history)
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)

    # <-------------- we are done ------------->
    return success


#  =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- 插件主程序3  =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

@CatchException
def PDF翻译中文并重新编译PDF(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port):
    # <-------------- information about this plugin ------------->
    chatbot.append([
        "函数插件功能？",
        "将PDF转换为Latex项目，翻译为中文后重新编译为PDF。函数插件贡献者: Marroh。注意事项: 此插件Windows支持最佳，Linux下必须使用Docker安装，详见项目主README.md。目前对机器学习类文献转化效果最好，其他类型文献转化效果未知。"])
    yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面

    # <-------------- more requirements ------------->
    if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop("advanced_arg")
    more_req = plugin_kwargs.get("advanced_arg", "")
    no_cache = more_req.startswith("--no-cache")
    if no_cache: more_req.lstrip("--no-cache")
    allow_cache = not no_cache
    _switch_prompt_ = partial(switch_prompt, more_requirement=more_req)

    # <-------------- check deps ------------->
    try:
        import glob, os, time, subprocess
        subprocess.Popen(['pdflatex', '-version'])
        from .latex_fns.latex_actions import Latex精细分解与转化, 编译Latex
    except Exception as e:
        chatbot.append([f"解析项目: {txt}",
                        f"尝试执行Latex指令失败。Latex没有安装, 或者不在环境变量PATH中。安装方法https://tug.org/texlive/。报错信息\n\n```\n\n{trimmed_format_exc()}\n\n```\n\n"])
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- clear history and read input ------------->
    if os.path.exists(txt):
        project_folder = txt
    else:
        if txt == "": txt = '空空如也的输入栏'
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到本地项目或无法处理: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.pdf', recursive=True)]
    if len(file_manifest) == 0:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到任何.pdf文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return
    if len(file_manifest) != 1:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"不支持同时处理多个pdf文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    if plugin_kwargs.get("method", "") == 'MATHPIX':
        app_id, app_key = get_conf('MATHPIX_APPID', 'MATHPIX_APPKEY')
        if len(app_id) == 0 or len(app_key) == 0:
            report_exception(chatbot, history, a="缺失 MATHPIX_APPID 和 MATHPIX_APPKEY。", b=f"请配置 MATHPIX_APPID 和 MATHPIX_APPKEY")
            yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
            return
    if plugin_kwargs.get("method", "") == 'DOC2X':
        app_id, app_key = "", ""
        DOC2X_API_KEY = get_conf('DOC2X_API_KEY')
        if len(DOC2X_API_KEY) == 0:
            report_exception(chatbot, history, a="缺失 DOC2X_API_KEY。", b=f"请配置 DOC2X_API_KEY")
            yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
            return

    hash_tag = map_file_to_sha256(file_manifest[0])

    # # <-------------- check repeated pdf ------------->
    # chatbot.append([f"检查PDF是否被重复上传", "正在检查..."])
    # yield from update_ui(chatbot=chatbot, history=history)
    # repeat, project_folder = check_repeat_upload(file_manifest[0], hash_tag)

    # if repeat:
    #     yield from update_ui_latest_msg(f"发现重复上传，请查收结果（压缩包）...", chatbot=chatbot, history=history)
    #     try:
    #         translate_pdf = [f for f in glob.glob(f'{project_folder}/**/merge_translate_zh.pdf', recursive=True)][0]
    #         promote_file_to_downloadzone(translate_pdf, rename_file=None, chatbot=chatbot)
    #         comparison_pdf = [f for f in glob.glob(f'{project_folder}/**/comparison.pdf', recursive=True)][0]
    #         promote_file_to_downloadzone(comparison_pdf, rename_file=None, chatbot=chatbot)
    #         zip_res = zip_result(project_folder)
    #         promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)
    #         return
    #     except:
    #         report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"发现重复上传，但是无法找到相关文件")
    #         yield from update_ui(chatbot=chatbot, history=history)
    # else:
    #     yield from update_ui_latest_msg(f"未发现重复上传", chatbot=chatbot, history=history)

    # <-------------- convert pdf into tex ------------->
    chatbot.append([f"解析项目: {txt}", "正在将PDF转换为tex项目，请耐心等待..."])
    yield from update_ui(chatbot=chatbot, history=history)
    project_folder = pdf2tex_project(file_manifest[0], plugin_kwargs)
    if project_folder is None:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"PDF转换为tex项目失败")
        yield from update_ui(chatbot=chatbot, history=history)
        return False

    # <-------------- translate latex file into Chinese ------------->
    yield from update_ui_latest_msg("正在tex项目将翻译为中文...", chatbot=chatbot, history=history)
    file_manifest = [f for f in glob.glob(f'{project_folder}/**/*.tex', recursive=True)]
    if len(file_manifest) == 0:
        report_exception(chatbot, history, a=f"解析项目: {txt}", b=f"找不到任何.tex文件: {txt}")
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        return

    # <-------------- if is a zip/tar file ------------->
    project_folder = descend_to_extracted_folder_if_exist(project_folder)

    # <-------------- move latex project away from temp folder ------------->
    from shared_utils.fastapi_server import validate_path_safety
    validate_path_safety(project_folder, chatbot.get_user())
    project_folder = move_project(project_folder)

    # <-------------- set a hash tag for repeat-checking ------------->
    with open(pj(project_folder, hash_tag + '.tag'), 'w', encoding='utf8') as f:
        f.write(hash_tag)
        f.close()


    # <-------------- if merge_translate_zh is already generated, skip gpt req ------------->
    if not os.path.exists(project_folder + '/merge_translate_zh.tex'):
        yield from Latex精细分解与转化(file_manifest, project_folder, llm_kwargs, plugin_kwargs,
                                    chatbot, history, system_prompt, mode='translate_zh',
                                    switch_prompt=_switch_prompt_)

    # <-------------- compile PDF ------------->
    yield from update_ui_latest_msg("正在将翻译好的项目tex项目编译为PDF...", chatbot=chatbot, history=history)
    success = yield from 编译Latex(chatbot, history, main_file_original='merge',
                                main_file_modified='merge_translate_zh', mode='translate_zh',
                                work_folder_original=project_folder, work_folder_modified=project_folder,
                                work_folder=project_folder)

    # <-------------- zip PDF ------------->
    zip_res = zip_result(project_folder)
    if success:
        chatbot.append((f"成功啦", '请查收结果（压缩包）...'))
        yield from update_ui(chatbot=chatbot, history=history);
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)
    else:
        chatbot.append((f"失败了",
                        '虽然PDF生成失败了, 但请查收结果（压缩包）, 内含已经翻译的Tex文档, 您可以到Github Issue区, 用该压缩包进行反馈。如系统是Linux，请检查系统字体（见Github wiki） ...'))
        yield from update_ui(chatbot=chatbot, history=history);
        time.sleep(1)  # 刷新界面
        promote_file_to_downloadzone(file=zip_res, chatbot=chatbot)

    # <-------------- we are done ------------->
    return success