# 借鉴自同目录下的bridge_chatgpt.py

"""
    该文件中主要包含三个函数

    不具备多线程能力的函数：
    1. predict: 正常对话时使用，具备完备的交互功能，不可多线程

    具备多线程调用能力的函数
    2. predict_no_ui_long_connection：支持多线程
"""

import json
import time
import gradio as gr
import traceback
import requests
import importlib
import random
from loguru import logger

# config_private.py放自己的秘密如API和代理网址
# 读取时首先看是否存在私密的config_private配置文件（不受git管控），如果有，则覆盖原config文件
from toolbox import get_conf, update_ui, trimmed_format_exc, is_the_upload_folder, read_one_api_model_name
proxies, TIMEOUT_SECONDS, MAX_RETRY = get_conf(
    "proxies", "TIMEOUT_SECONDS", "MAX_RETRY"
)

timeout_bot_msg = '[Local Message] Request timeout. Network error. Please check proxy settings in config.py.' + \
                  '网络错误，检查代理服务器是否可用，以及代理设置的格式是否正确，格式须是[协议]://[地址]:[端口]，缺一不可。'

def get_full_error(chunk, stream_response):
    """
        获取完整的从Openai返回的报错
    """
    while True:
        try:
            chunk += next(stream_response)
        except:
            break
    return chunk

def decode_chunk(chunk):
    # 提前读取一些信息（用于判断异常）
    chunk_decoded = chunk.decode()
    chunkjson = None
    is_last_chunk = False
    try:
        chunkjson = json.loads(chunk_decoded)
        is_last_chunk = chunkjson.get("done", False)
    except:
        pass
    return chunk_decoded, chunkjson, is_last_chunk

def predict_no_ui_long_connection(inputs, llm_kwargs, history=[], sys_prompt="", observe_window=None, console_silence=False):
    """
    发送至chatGPT，等待回复，一次性完成，不显示中间过程。但内部用stream的方法避免中途网线被掐。
    inputs：
        是本次问询的输入
    sys_prompt:
        系统静默prompt
    llm_kwargs：
        chatGPT的内部调优参数
    history：
        是之前的对话列表
    observe_window = None：
        用于负责跨越线程传递已经输出的部分，大部分时候仅仅为了fancy的视觉效果，留空即可。observe_window[0]：观测窗。observe_window[1]：看门狗
    """
    watch_dog_patience = 5 # 看门狗的耐心, 设置5秒即可
    if inputs == "":     inputs = "空空如也的输入栏"
    headers, payload = generate_payload(inputs, llm_kwargs, history, system_prompt=sys_prompt, stream=True)
    retry = 0
    while True:
        try:
            # make a POST request to the API endpoint, stream=False
            from .bridge_all import model_info
            endpoint = model_info[llm_kwargs['llm_model']]['endpoint']
            response = requests.post(endpoint, headers=headers, proxies=None,
                                    json=payload, stream=True, timeout=TIMEOUT_SECONDS); break
        except requests.exceptions.ReadTimeout as e:
            retry += 1
            traceback.print_exc()
            if retry > MAX_RETRY: raise TimeoutError
            if MAX_RETRY!=0: logger.error(f'请求超时，正在重试 ({retry}/{MAX_RETRY}) ……')

    stream_response = response.iter_lines()
    result = ''
    while True:
        try: chunk = next(stream_response)
        except StopIteration:
            break
        except requests.exceptions.ConnectionError:
            chunk = next(stream_response) # 失败了，重试一次？再失败就没办法了。
        chunk_decoded, chunkjson, is_last_chunk = decode_chunk(chunk)
        if chunk:
            try:
                if is_last_chunk:
                    # 判定为数据流的结束，gpt_replying_buffer也写完了
                    logger.info(f'[response] {result}')
                    break
                result += chunkjson['message']["content"]
                if not console_silence: print(chunkjson['message']["content"], end='')
                if observe_window is not None:
                    # 观测窗，把已经获取的数据显示出去
                    if len(observe_window) >= 1:
                        observe_window[0] += chunkjson['message']["content"]
                    # 看门狗，如果超过期限没有喂狗，则终止
                    if len(observe_window) >= 2:
                        if (time.time()-observe_window[1]) > watch_dog_patience:
                            raise RuntimeError("用户取消了程序。")
            except Exception as e:
                chunk = get_full_error(chunk, stream_response)
                chunk_decoded = chunk.decode()
                error_msg = chunk_decoded
                logger.error(error_msg)
                raise RuntimeError("Json解析不合常规")
    return result


def predict(inputs, llm_kwargs, plugin_kwargs, chatbot, history=[], system_prompt='', stream = True, additional_fn=None):
    """
    发送至chatGPT，流式获取输出。
    用于基础的对话功能。
    inputs 是本次问询的输入
    top_p, temperature是chatGPT的内部调优参数
    history 是之前的对话列表（注意无论是inputs还是history，内容太长了都会触发token数量溢出的错误）
    chatbot 为WebUI中显示的对话列表，修改它，然后yield出去，可以直接修改对话界面内容
    additional_fn代表点击的哪个按钮，按钮见functional.py
    """
    if inputs == "":     inputs = "空空如也的输入栏"
    user_input = inputs
    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    raw_input = inputs
    logger.info(f'[raw_input] {raw_input}')
    chatbot.append((inputs, ""))
    yield from update_ui(chatbot=chatbot, history=history, msg="等待响应") # 刷新界面

    # check mis-behavior
    if is_the_upload_folder(user_input):
        chatbot[-1] = (inputs, f"[Local Message] 检测到操作错误！当您上传文档之后，需点击“**函数插件区**”按钮进行处理，请勿点击“提交”按钮或者“基础功能区”按钮。")
        yield from update_ui(chatbot=chatbot, history=history, msg="正常") # 刷新界面
        time.sleep(2)

    headers, payload = generate_payload(inputs, llm_kwargs, history, system_prompt, stream)

    from .bridge_all import model_info
    endpoint = model_info[llm_kwargs['llm_model']]['endpoint']

    history.append(inputs); history.append("")

    retry = 0
    if proxies is not None:
        logger.error("Ollama不会使用代理服务器, 忽略了proxies的设置。")
    while True:
        try:
            # make a POST request to the API endpoint, stream=True
            response = requests.post(endpoint, headers=headers, proxies=None,
                                    json=payload, stream=True, timeout=TIMEOUT_SECONDS);break
        except:
            retry += 1
            chatbot[-1] = ((chatbot[-1][0], timeout_bot_msg))
            retry_msg = f"，正在重试 ({retry}/{MAX_RETRY}) ……" if MAX_RETRY > 0 else ""
            yield from update_ui(chatbot=chatbot, history=history, msg="请求超时"+retry_msg) # 刷新界面
            if retry > MAX_RETRY: raise TimeoutError

    gpt_replying_buffer = ""

    if stream:
        stream_response =  response.iter_lines()
        while True:
            try:
                chunk = next(stream_response)
            except StopIteration:
                break
            except requests.exceptions.ConnectionError:
                chunk = next(stream_response) # 失败了，重试一次？再失败就没办法了。

            # 提前读取一些信息 （用于判断异常）
            chunk_decoded, chunkjson, is_last_chunk = decode_chunk(chunk)

            if chunk:
                try:
                    if is_last_chunk:
                        # 判定为数据流的结束，gpt_replying_buffer也写完了
                        logger.info(f'[response] {gpt_replying_buffer}')
                        break
                    # 处理数据流的主体
                    try:
                        status_text = f"finish_reason: {chunkjson['error'].get('message', 'null')}"
                    except:
                        status_text = "finish_reason: null"
                    gpt_replying_buffer = gpt_replying_buffer + chunkjson['message']["content"]
                    # 如果这里抛出异常，一般是文本过长，详情见get_full_error的输出
                    history[-1] = gpt_replying_buffer
                    chatbot[-1] = (history[-2], history[-1])
                    yield from update_ui(chatbot=chatbot, history=history, msg=status_text) # 刷新界面
                except Exception as e:
                    yield from update_ui(chatbot=chatbot, history=history, msg="Json解析不合常规") # 刷新界面
                    chunk = get_full_error(chunk, stream_response)
                    chunk_decoded = chunk.decode()
                    error_msg = chunk_decoded
                    chatbot, history = handle_error(inputs, llm_kwargs, chatbot, history, chunk_decoded, error_msg)
                    yield from update_ui(chatbot=chatbot, history=history, msg="Json异常" + error_msg) # 刷新界面
                    logger.error(error_msg)
                    return

def handle_error(inputs, llm_kwargs, chatbot, history, chunk_decoded, error_msg):
    from .bridge_all import model_info
    if "bad_request" in error_msg:
        chatbot[-1] = (chatbot[-1][0], "[Local Message] 已经超过了模型的最大上下文或是模型格式错误,请尝试削减单次输入的文本量。")
    elif "authentication_error" in error_msg:
        chatbot[-1] = (chatbot[-1][0], "[Local Message] Incorrect API key. 请确保API key有效。")
    elif "not_found" in error_msg:
        chatbot[-1] = (chatbot[-1][0], f"[Local Message] {llm_kwargs['llm_model']} 无效，请确保使用小写的模型名称。")
    elif "rate_limit" in error_msg:
        chatbot[-1] = (chatbot[-1][0], "[Local Message] 遇到了控制请求速率限制，请一分钟后重试。")
    elif "system_busy" in error_msg:
        chatbot[-1] = (chatbot[-1][0], "[Local Message] 系统繁忙，请一分钟后重试。")
    else:
        from toolbox import regular_txt_to_markdown
        tb_str = '```\n' + trimmed_format_exc() + '```'
        chatbot[-1] = (chatbot[-1][0], f"[Local Message] 异常 \n\n{tb_str} \n\n{regular_txt_to_markdown(chunk_decoded)}")
    return chatbot, history

def generate_payload(inputs, llm_kwargs, history, system_prompt, stream):
    """
    整合所有信息，选择LLM模型，生成http请求，为发送请求做准备
    """

    headers = {
        "Content-Type": "application/json",
    }

    conversation_cnt = len(history) // 2

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_cnt:
        for index in range(0, 2*conversation_cnt, 2):
            what_i_have_asked = {}
            what_i_have_asked["role"] = "user"
            what_i_have_asked["content"] = history[index]
            what_gpt_answer = {}
            what_gpt_answer["role"] = "assistant"
            what_gpt_answer["content"] = history[index+1]
            if what_i_have_asked["content"] != "":
                if what_gpt_answer["content"] == "": continue
                if what_gpt_answer["content"] == timeout_bot_msg: continue
                messages.append(what_i_have_asked)
                messages.append(what_gpt_answer)
            else:
                messages[-1]['content'] = what_gpt_answer['content']

    what_i_ask_now = {}
    what_i_ask_now["role"] = "user"
    what_i_ask_now["content"] = inputs
    messages.append(what_i_ask_now)
    model = llm_kwargs['llm_model']
    if llm_kwargs['llm_model'].startswith('ollama-'):
        model = llm_kwargs['llm_model'][len('ollama-'):]
        model, _ = read_one_api_model_name(model)
    options = {"temperature": llm_kwargs['temperature']}
    payload = {
        "model": model,
        "messages": messages,
        "options": options,
    }

    return headers,payload
