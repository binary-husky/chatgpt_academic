from toolbox import CatchException, update_ui, ProxyNetworkActivate, update_ui_latest_msg, get_log_folder, get_user
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive, get_files_from_everything
from loguru import logger
install_msg ="""

1. python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

2. python -m pip install transformers protobuf langchain sentence-transformers  faiss-cpu nltk beautifulsoup4 bitsandbytes tabulate icetk --upgrade

3. python -m pip install unstructured[all-docs] --upgrade

4. python -c 'import nltk; nltk.download("punkt")'
"""

@CatchException
def 知识库文件注入(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    """
    txt             输入栏用户输入的文本，例如需要翻译的一段话，再例如一个包含了待处理文件的路径
    llm_kwargs      gpt模型参数, 如温度和top_p等, 一般原样传递下去就行
    plugin_kwargs   插件模型的参数，暂时没有用武之地
    chatbot         聊天显示框的句柄，用于显示给用户
    history         聊天历史，前情提要
    system_prompt   给gpt的静默提醒
    user_request    当前用户的请求信息（IP地址等）
    """
    history = []    # 清空历史，以免输入溢出

    # < --------------------读取参数--------------- >
    if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop("advanced_arg")
    kai_id = plugin_kwargs.get("advanced_arg", 'default')

    chatbot.append((f"向`{kai_id}`知识库中添加文件。", "[Local Message] 从一批文件(txt, md, tex)中读取数据构建知识库, 然后进行问答。"))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # resolve deps
    try:
        # from zh_langchain import construct_vector_store
        # from langchain.embeddings.huggingface import HuggingFaceEmbeddings
        from crazy_functions.vector_fns.vector_database import knowledge_archive_interface
    except Exception as e:
        chatbot.append(["依赖不足", f"{str(e)}\n\n导入依赖失败。请用以下命令安装" + install_msg])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        # from crazy_functions.crazy_utils import try_install_deps
        # try_install_deps(['zh_langchain==0.2.1', 'pypinyin'], reload_m=['pypinyin', 'zh_langchain'])
        # yield from update_ui_latest_msg("安装完成，您可以再次重试。", chatbot, history)
        return

    # < --------------------读取文件--------------- >
    file_manifest = []
    spl = ["txt", "doc", "docx", "email", "epub", "html", "json", "md", "msg", "pdf", "ppt", "pptx", "rtf"]
    for sp in spl:
        _, file_manifest_tmp, _ = get_files_from_everything(txt, type=f'.{sp}')
        file_manifest += file_manifest_tmp

    if len(file_manifest) == 0:
        chatbot.append(["没有找到任何可读取文件", "当前支持的格式包括: txt, md, docx, pptx, pdf, json等"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    # < -------------------预热文本向量化模组--------------- >
    chatbot.append(['<br/>'.join(file_manifest), "正在预热文本向量化模组, 如果是第一次运行, 将消耗较长时间下载中文向量化模型..."])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    logger.info('Checking Text2vec ...')
    from langchain.embeddings.huggingface import HuggingFaceEmbeddings
    with ProxyNetworkActivate('Download_LLM'):    # 临时地激活代理网络
        HuggingFaceEmbeddings(model_name="GanymedeNil/text2vec-large-chinese")

    # < -------------------构建知识库--------------- >
    chatbot.append(['<br/>'.join(file_manifest), "正在构建知识库..."])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    logger.info('Establishing knowledge archive ...')
    with ProxyNetworkActivate('Download_LLM'):    # 临时地激活代理网络
        kai = knowledge_archive_interface()
        vs_path = get_log_folder(user=get_user(chatbot), plugin_name='vec_store')
        kai.feed_archive(file_manifest=file_manifest, vs_path=vs_path, id=kai_id)
    kai_files = kai.get_loaded_file(vs_path=vs_path)
    kai_files = '<br/>'.join(kai_files)
    # chatbot.append(['知识库构建成功', "正在将知识库存储至cookie中"])
    # yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    # chatbot._cookies['langchain_plugin_embedding'] = kai.get_current_archive_id()
    # chatbot._cookies['lock_plugin'] = 'crazy_functions.知识库文件注入->读取知识库作答'
    # chatbot.append(['完成', "“根据知识库作答”函数插件已经接管问答系统, 提问吧! 但注意, 您接下来不能再使用其他插件了，刷新页面即可以退出知识库问答模式。"])
    chatbot.append(['构建完成', f"当前知识库内的有效文件：\n\n---\n\n{kai_files}\n\n---\n\n请切换至“知识库问答”插件进行知识库访问, 或者使用此插件继续上传更多文件。"])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 由于请求gpt需要一段时间，我们先及时地做一次界面更新

@CatchException
def 读取知识库作答(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request=-1):
    # resolve deps
    try:
        # from zh_langchain import construct_vector_store
        # from langchain.embeddings.huggingface import HuggingFaceEmbeddings
        from crazy_functions.vector_fns.vector_database import knowledge_archive_interface
    except Exception as e:
        chatbot.append(["依赖不足", f"{str(e)}\n\n导入依赖失败。请用以下命令安装" + install_msg])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        # from crazy_functions.crazy_utils import try_install_deps
        # try_install_deps(['zh_langchain==0.2.1', 'pypinyin'], reload_m=['pypinyin', 'zh_langchain'])
        # yield from update_ui_latest_msg("安装完成，您可以再次重试。", chatbot, history)
        return

    # < -------------------  --------------- >
    kai = knowledge_archive_interface()

    if ("advanced_arg" in plugin_kwargs) and (plugin_kwargs["advanced_arg"] == ""): plugin_kwargs.pop("advanced_arg")
    kai_id = plugin_kwargs.get("advanced_arg", 'default')
    vs_path = get_log_folder(user=get_user(chatbot), plugin_name='vec_store')
    resp, prompt = kai.answer_with_archive_by_id(txt, kai_id, vs_path)

    chatbot.append((txt, f'[知识库 {kai_id}] ' + prompt))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 由于请求gpt需要一段时间，我们先及时地做一次界面更新
    gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=prompt, inputs_show_user=txt,
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=[],
        sys_prompt=system_prompt
    )
    history.extend((prompt, gpt_say))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 由于请求gpt需要一段时间，我们先及时地做一次界面更新
