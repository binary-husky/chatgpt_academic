'''
Contributed by SagsMug. Modified by binary-husky
https://github.com/oobabooga/text-generation-webui/pull/175
'''

import asyncio
import json
import random
import string
import websockets
import time
import threading
import importlib
from toolbox import get_conf, update_ui


def random_hash():
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(9))

async def run(context, max_token, temperature, top_p, addr, port):
    params = {
        'max_new_tokens': max_token,
        'do_sample': True,
        'temperature': temperature,
        'top_p': top_p,
        'typical_p': 1,
        'repetition_penalty': 1.05,
        'encoder_repetition_penalty': 1.0,
        'top_k': 0,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': True,
        'seed': -1,
    }
    session = random_hash()

    async with websockets.connect(f"ws://{addr}:{port}/queue/join") as websocket:
        while content := json.loads(await websocket.recv()):
            #Python3.10 syntax, replace with if elif on older
            if content["msg"] ==  "send_hash":
                await websocket.send(json.dumps({
                    "session_hash": session,
                    "fn_index": 12
                }))
            elif content["msg"] ==  "estimation":
                pass
            elif content["msg"] ==  "send_data":
                await websocket.send(json.dumps({
                    "session_hash": session,
                    "fn_index": 12,
                    "data": [
                        context,
                        params['max_new_tokens'],
                        params['do_sample'],
                        params['temperature'],
                        params['top_p'],
                        params['typical_p'],
                        params['repetition_penalty'],
                        params['encoder_repetition_penalty'],
                        params['top_k'],
                        params['min_length'],
                        params['no_repeat_ngram_size'],
                        params['num_beams'],
                        params['penalty_alpha'],
                        params['length_penalty'],
                        params['early_stopping'],
                        params['seed'],
                    ]
                }))
            elif content["msg"] ==  "process_starts":
                pass
            elif content["msg"] in ["process_generating", "process_completed"]:
                yield content["output"]["data"][0]
                # You can search for your desired end indicator and
                #  stop generation by closing the websocket here
                if (content["msg"] == "process_completed"):
                    break





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
    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    raw_input = "What I would like to say is the following: " + inputs
    history.extend([inputs, ""])
    chatbot.append([inputs, ""])
    yield from update_ui(chatbot=chatbot, history=history, msg="等待响应") # 刷新界面

    prompt = raw_input
    tgui_say = ""

    model_name, addr_port = llm_kwargs['llm_model'].split('@')
    assert ':' in addr_port, "LLM_MODEL 格式不正确！" + llm_kwargs['llm_model']
    addr, port = addr_port.split(':')


    mutable = ["", time.time()]
    def run_coroutine(mutable):
        async def get_result(mutable):
            # "tgui:galactica-1.3b@localhost:7860"

            async for response in run(context=prompt, max_token=llm_kwargs['max_length'],
                                      temperature=llm_kwargs['temperature'],
                                      top_p=llm_kwargs['top_p'], addr=addr, port=port):
                print(response[len(mutable[0]):])
                mutable[0] = response
                if (time.time() - mutable[1]) > 3:
                    print('exit when no listener')
                    break
        asyncio.run(get_result(mutable))

    thread_listen = threading.Thread(target=run_coroutine, args=(mutable,), daemon=True)
    thread_listen.start()

    while thread_listen.is_alive():
        time.sleep(1)
        mutable[1] = time.time()
        # Print intermediate steps
        if tgui_say != mutable[0]:
            tgui_say = mutable[0]
            history[-1] = tgui_say
            chatbot[-1] = (history[-2], history[-1])
            yield from update_ui(chatbot=chatbot, history=history) # 刷新界面




def predict_no_ui_long_connection(inputs, llm_kwargs, history, sys_prompt, observe_window, console_silence=False):
    raw_input = "What I would like to say is the following: " + inputs
    prompt = raw_input
    tgui_say = ""
    model_name, addr_port = llm_kwargs['llm_model'].split('@')
    assert ':' in addr_port, "LLM_MODEL 格式不正确！" + llm_kwargs['llm_model']
    addr, port = addr_port.split(':')


    def run_coroutine(observe_window):
        async def get_result(observe_window):
            async for response in run(context=prompt, max_token=llm_kwargs['max_length'],
                                      temperature=llm_kwargs['temperature'],
                                      top_p=llm_kwargs['top_p'], addr=addr, port=port):
                print(response[len(observe_window[0]):])
                observe_window[0] = response
                if (time.time() - observe_window[1]) > 5:
                    print('exit when no listener')
                    break
        asyncio.run(get_result(observe_window))
    thread_listen = threading.Thread(target=run_coroutine, args=(observe_window,))
    thread_listen.start()
    return observe_window[0]
