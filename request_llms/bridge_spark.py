
import time
import threading
import importlib
from toolbox import update_ui, get_conf, update_ui_latest_msg
from multiprocessing import Process, Pipe

model_name = '星火认知大模型'

def validate_key():
    XFYUN_APPID = get_conf('XFYUN_APPID')
    if XFYUN_APPID == '00000000' or XFYUN_APPID == '':
        return False
    return True

def predict_no_ui_long_connection(inputs:str, llm_kwargs:dict, history:list=[], sys_prompt:str="",
                                  observe_window:list=[], console_silence:bool=False):
    """
        ⭐多线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    watch_dog_patience = 5
    response = ""

    if validate_key() is False:
        raise RuntimeError('请配置讯飞星火大模型的XFYUN_APPID, XFYUN_API_KEY, XFYUN_API_SECRET')

    from .com_sparkapi import SparkRequestInstance
    sri = SparkRequestInstance()
    for response in sri.generate(inputs, llm_kwargs, history, sys_prompt, use_image_api=False):
        if len(observe_window) >= 1:
            observe_window[0] = response
        if len(observe_window) >= 2:
            if (time.time()-observe_window[1]) > watch_dog_patience: raise RuntimeError("程序终止。")
    return response

def predict(inputs, llm_kwargs, plugin_kwargs, chatbot, history=[], system_prompt='', stream = True, additional_fn=None):
    """
        ⭐单线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    chatbot.append((inputs, ""))
    yield from update_ui(chatbot=chatbot, history=history)

    if validate_key() is False:
        yield from update_ui_latest_msg(lastmsg="[Local Message] 请配置讯飞星火大模型的XFYUN_APPID, XFYUN_API_KEY, XFYUN_API_SECRET", chatbot=chatbot, history=history, delay=0)
        return

    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    # 开始接收回复
    from .com_sparkapi import SparkRequestInstance
    sri = SparkRequestInstance()
    response = f"[Local Message] 等待{model_name}响应中 ..."
    for response in sri.generate(inputs, llm_kwargs, history, system_prompt, use_image_api=True):
        chatbot[-1] = (inputs, response)
        yield from update_ui(chatbot=chatbot, history=history)

    # 总结输出
    if response == f"[Local Message] 等待{model_name}响应中 ...":
        response = f"[Local Message] {model_name}响应异常 ..."
    history.extend([inputs, response])
    yield from update_ui(chatbot=chatbot, history=history)