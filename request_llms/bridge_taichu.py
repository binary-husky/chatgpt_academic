import time
import os
from toolbox import update_ui, get_conf, update_ui_latest_msg, log_chat
from toolbox import check_packages, report_exception, have_any_recent_upload_image_files
from toolbox import ChatBotWithCookies

# model_name = 'Taichu-2.0'
# taichu_default_model = 'taichu_llm'

def validate_key():
    TAICHU_API_KEY = get_conf("TAICHU_API_KEY")
    if TAICHU_API_KEY == '': return False
    return True

def predict_no_ui_long_connection(inputs:str, llm_kwargs:dict, history:list=[], sys_prompt:str="",
                                  observe_window:list=[], console_silence:bool=False):
    """
        ⭐多线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    watch_dog_patience = 5
    response = ""

    # if llm_kwargs["llm_model"] == "taichu":
    #     llm_kwargs["llm_model"] = "taichu"

    if validate_key() is False:
        raise RuntimeError('请配置 TAICHU_API_KEY')

    # 开始接收回复
    from .com_taichu import TaichuChatInit
    zhipu_bro_init = TaichuChatInit()
    for chunk, response in zhipu_bro_init.generate_chat(inputs, llm_kwargs, history, sys_prompt):
        if len(observe_window) >= 1:
            observe_window[0] = response
        if len(observe_window) >= 2:
            if (time.time() - observe_window[1]) > watch_dog_patience:
                raise RuntimeError("程序终止。")
    return response


def predict(inputs:str, llm_kwargs:dict, plugin_kwargs:dict, chatbot:ChatBotWithCookies,
            history:list=[], system_prompt:str='', stream:bool=True, additional_fn:str=None):
    """
        ⭐单线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    chatbot.append([inputs, ""])
    yield from update_ui(chatbot=chatbot, history=history)

    if validate_key() is False:
        yield from update_ui_latest_msg(lastmsg="[Local Message] 请配置ZHIPUAI_API_KEY", chatbot=chatbot, history=history, delay=0)
        return

    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)
        chatbot[-1] = [inputs, ""]
        yield from update_ui(chatbot=chatbot, history=history)

    # if llm_kwargs["llm_model"] == "taichu":
    #     llm_kwargs["llm_model"] = taichu_default_model

    # 开始接收回复
    from .com_taichu import TaichuChatInit
    zhipu_bro_init = TaichuChatInit()
    for chunk, response in zhipu_bro_init.generate_chat(inputs, llm_kwargs, history, system_prompt):
        chatbot[-1] = [inputs, response]
        yield from update_ui(chatbot=chatbot, history=history)
    history.extend([inputs, response])
    log_chat(llm_model=llm_kwargs["llm_model"], input_str=inputs, output_str=response)
    yield from update_ui(chatbot=chatbot, history=history)