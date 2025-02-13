import os

"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
接驳void-terminal:
    - set_conf:                     在运行过程中动态地修改配置
    - set_multi_conf:               在运行过程中动态地修改多个配置
    - get_plugin_handle:            获取插件的句柄
    - get_plugin_default_kwargs:    获取插件的默认参数
    - get_chat_handle:              获取简单聊天的句柄
    - get_chat_default_kwargs:      获取简单聊天的默认参数
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""


def get_plugin_handle(plugin_name):
    """
    e.g. plugin_name = 'crazy_functions.Markdown_Translate->Markdown翻译指定语言'
    """
    import importlib

    assert (
        "->" in plugin_name
    ), "Example of plugin_name: crazy_functions.Markdown_Translate->Markdown翻译指定语言"
    module, fn_name = plugin_name.split("->")
    f_hot_reload = getattr(importlib.import_module(module, fn_name), fn_name)
    return f_hot_reload


def get_chat_handle():
    """
    Get chat function
    """
    from request_llms.bridge_all import predict_no_ui_long_connection

    return predict_no_ui_long_connection


def get_plugin_default_kwargs():
    """
    Get Plugin Default Arguments
    """
    from toolbox import ChatBotWithCookies, load_chat_cookies

    cookies = load_chat_cookies()
    llm_kwargs = {
        "api_key": cookies["api_key"],
        "llm_model": cookies["llm_model"],
        "top_p": 1.0,
        "max_length": None,
        "temperature": 1.0,
    }
    chatbot = ChatBotWithCookies(llm_kwargs)

    # txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request
    DEFAULT_FN_GROUPS_kwargs = {
        "main_input": "./README.md",
        "llm_kwargs": llm_kwargs,
        "plugin_kwargs": {},
        "chatbot_with_cookie": chatbot,
        "history": [],
        "system_prompt": "You are a good AI.",
        "user_request": None,
    }
    return DEFAULT_FN_GROUPS_kwargs


def get_chat_default_kwargs():
    """
    Get Chat Default Arguments
    """
    from toolbox import load_chat_cookies

    cookies = load_chat_cookies()
    llm_kwargs = {
        "api_key": cookies["api_key"],
        "llm_model": cookies["llm_model"],
        "top_p": 1.0,
        "max_length": None,
        "temperature": 1.0,
    }
    default_chat_kwargs = {
        "inputs": "Hello there, are you ready?",
        "llm_kwargs": llm_kwargs,
        "history": [],
        "sys_prompt": "You are AI assistant",
        "observe_window": None,
        "console_silence": False,
    }

    return default_chat_kwargs
