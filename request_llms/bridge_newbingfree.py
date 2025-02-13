"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
第一部分：来自EdgeGPT.py
https://github.com/acheong08/EdgeGPT
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""
from .edge_gpt_free import Chatbot as NewbingChatbot

load_message = "等待NewBing响应。"

"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
第二部分：子进程Worker（调用主体）
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""
import time
import json
import re
import logging
import asyncio
import importlib
import threading
from toolbox import update_ui, get_conf, trimmed_format_exc
from multiprocessing import Process, Pipe


def preprocess_newbing_out(s):
    pattern = r"\^(\d+)\^"  # 匹配^数字^
    sub = lambda m: "(" + m.group(1) + ")"  # 将匹配到的数字作为替换值
    result = re.sub(pattern, sub, s)  # 替换操作
    if "[1]" in result:
        result += (
            "\n\n```reference\n"
            + "\n".join([r for r in result.split("\n") if r.startswith("[")])
            + "\n```\n"
        )
    return result


def preprocess_newbing_out_simple(result):
    if "[1]" in result:
        result += (
            "\n\n```reference\n"
            + "\n".join([r for r in result.split("\n") if r.startswith("[")])
            + "\n```\n"
        )
    return result


class NewBingHandle(Process):
    def __init__(self):
        super().__init__(daemon=True)
        self.parent, self.child = Pipe()
        self.newbing_model = None
        self.info = ""
        self.success = True
        self.local_history = []
        self.check_dependency()
        self.start()
        self.threadLock = threading.Lock()

    def check_dependency(self):
        try:
            self.success = False
            import certifi, httpx, rich

            self.info = "依赖检测通过，等待NewBing响应。注意目前不能多人同时调用NewBing接口（有线程锁），否则将导致每个人的NewBing问询历史互相渗透。调用NewBing时，会自动使用已配置的代理。"
            self.success = True
        except:
            self.info = "缺少的依赖，如果要使用Newbing，除了基础的pip依赖以外，您还需要运行`pip install -r request_llms/requirements_newbing.txt`安装Newbing的依赖。"
            self.success = False

    def ready(self):
        return self.newbing_model is not None

    async def async_run(self):
        # 读取配置
        NEWBING_STYLE = get_conf("NEWBING_STYLE")
        from request_llms.bridge_all import model_info

        endpoint = model_info["newbing"]["endpoint"]
        while True:
            # 等待
            kwargs = self.child.recv()
            question = kwargs["query"]
            history = kwargs["history"]
            system_prompt = kwargs["system_prompt"]

            # 是否重置
            if len(self.local_history) > 0 and len(history) == 0:
                await self.newbing_model.reset()
                self.local_history = []

            # 开始问问题
            prompt = ""
            if system_prompt not in self.local_history:
                self.local_history.append(system_prompt)
                prompt += system_prompt + "\n"

            # 追加历史
            for ab in history:
                a, b = ab
                if a not in self.local_history:
                    self.local_history.append(a)
                    prompt += a + "\n"

            # 问题
            prompt += question
            self.local_history.append(question)
            print("question:", prompt)
            # 提交
            async for final, response in self.newbing_model.ask_stream(
                prompt=question,
                conversation_style=NEWBING_STYLE,  # ["creative", "balanced", "precise"]
                wss_link=endpoint,  # "wss://sydney.bing.com/sydney/ChatHub"
            ):
                if not final:
                    print(response)
                    self.child.send(str(response))
                else:
                    print("-------- receive final ---------")
                    self.child.send("[Finish]")
                    # self.local_history.append(response)

    def run(self):
        """
        这个函数运行在子进程
        """
        # 第一次运行，加载参数
        self.success = False
        self.local_history = []
        if (self.newbing_model is None) or (not self.success):
            # 代理设置
            proxies, NEWBING_COOKIES = get_conf("proxies", "NEWBING_COOKIES")
            if proxies is None:
                self.proxies_https = None
            else:
                self.proxies_https = proxies["https"]

            if (NEWBING_COOKIES is not None) and len(NEWBING_COOKIES) > 100:
                try:
                    cookies = json.loads(NEWBING_COOKIES)
                except:
                    self.success = False
                    tb_str = "\n```\n" + trimmed_format_exc() + "\n```\n"
                    self.child.send(f"[Local Message] NEWBING_COOKIES未填写或有格式错误。")
                    self.child.send("[Fail]")
                    self.child.send("[Finish]")
                    raise RuntimeError(f"NEWBING_COOKIES未填写或有格式错误。")
            else:
                cookies = None

            try:
                self.newbing_model = NewbingChatbot(
                    proxy=self.proxies_https, cookies=cookies
                )
            except:
                self.success = False
                tb_str = "\n```\n" + trimmed_format_exc() + "\n```\n"
                self.child.send(
                    f"[Local Message] 不能加载Newbing组件，请注意Newbing组件已不再维护。{tb_str}"
                )
                self.child.send("[Fail]")
                self.child.send("[Finish]")
                raise RuntimeError(f"不能加载Newbing组件，请注意Newbing组件已不再维护。")

        self.success = True
        try:
            # 进入任务等待状态
            asyncio.run(self.async_run())
        except Exception:
            tb_str = "\n```\n" + trimmed_format_exc() + "\n```\n"
            self.child.send(
                f"[Local Message] Newbing 请求失败，报错信息如下. 如果是与网络相关的问题，建议更换代理协议（推荐http）或代理节点 {tb_str}."
            )
            self.child.send("[Fail]")
            self.child.send("[Finish]")

    def stream_chat(self, **kwargs):
        """
        这个函数运行在主进程
        """
        self.threadLock.acquire()  # 获取线程锁
        self.parent.send(kwargs)  # 请求子进程
        while True:
            res = self.parent.recv()  # 等待newbing回复的片段
            if res == "[Finish]":
                break  # 结束
            elif res == "[Fail]":
                self.success = False
                break  # 失败
            else:
                yield res  # newbing回复的片段
        self.threadLock.release()  # 释放线程锁


"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
第三部分：主进程统一调用函数接口
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""
global newbingfree_handle
newbingfree_handle = None


def predict_no_ui_long_connection(
    inputs,
    llm_kwargs,
    history=[],
    sys_prompt="",
    observe_window=[],
    console_silence=False,
):
    """
    多线程方法
    函数的说明请见 request_llms/bridge_all.py
    """
    global newbingfree_handle
    if (newbingfree_handle is None) or (not newbingfree_handle.success):
        newbingfree_handle = NewBingHandle()
        if len(observe_window) >= 1:
            observe_window[0] = load_message + "\n\n" + newbingfree_handle.info
        if not newbingfree_handle.success:
            error = newbingfree_handle.info
            newbingfree_handle = None
            raise RuntimeError(error)

    # 没有 sys_prompt 接口，因此把prompt加入 history
    history_feedin = []
    for i in range(len(history) // 2):
        history_feedin.append([history[2 * i], history[2 * i + 1]])

    watch_dog_patience = 5  # 看门狗 (watchdog) 的耐心, 设置5秒即可
    response = ""
    if len(observe_window) >= 1:
        observe_window[0] = "[Local Message] 等待NewBing响应中 ..."
    for response in newbingfree_handle.stream_chat(
        query=inputs,
        history=history_feedin,
        system_prompt=sys_prompt,
        max_length=llm_kwargs["max_length"],
        top_p=llm_kwargs["top_p"],
        temperature=llm_kwargs["temperature"],
    ):
        if len(observe_window) >= 1:
            observe_window[0] = preprocess_newbing_out_simple(response)
        if len(observe_window) >= 2:
            if (time.time() - observe_window[1]) > watch_dog_patience:
                raise RuntimeError("程序终止。")
    return preprocess_newbing_out_simple(response)


def predict(
    inputs,
    llm_kwargs,
    plugin_kwargs,
    chatbot,
    history=[],
    system_prompt="",
    stream=True,
    additional_fn=None,
):
    """
    单线程方法
    函数的说明请见 request_llms/bridge_all.py
    """
    chatbot.append((inputs, "[Local Message] 等待NewBing响应中 ..."))

    global newbingfree_handle
    if (newbingfree_handle is None) or (not newbingfree_handle.success):
        newbingfree_handle = NewBingHandle()
        chatbot[-1] = (inputs, load_message + "\n\n" + newbingfree_handle.info)
        yield from update_ui(chatbot=chatbot, history=[])
        if not newbingfree_handle.success:
            newbingfree_handle = None
            return

    if additional_fn is not None:
        from core_functional import handle_core_functionality

        inputs, history = handle_core_functionality(
            additional_fn, inputs, history, chatbot
        )

    history_feedin = []
    for i in range(len(history) // 2):
        history_feedin.append([history[2 * i], history[2 * i + 1]])

    chatbot[-1] = (inputs, "[Local Message] 等待NewBing响应中 ...")
    response = "[Local Message] 等待NewBing响应中 ..."
    yield from update_ui(
        chatbot=chatbot, history=history, msg="NewBing响应缓慢，尚未完成全部响应，请耐心完成后再提交新问题。"
    )
    for response in newbingfree_handle.stream_chat(
        query=inputs,
        history=history_feedin,
        system_prompt=system_prompt,
        max_length=llm_kwargs["max_length"],
        top_p=llm_kwargs["top_p"],
        temperature=llm_kwargs["temperature"],
    ):
        chatbot[-1] = (inputs, preprocess_newbing_out(response))
        yield from update_ui(
            chatbot=chatbot, history=history, msg="NewBing响应缓慢，尚未完成全部响应，请耐心完成后再提交新问题。"
        )
    if response == "[Local Message] 等待NewBing响应中 ...":
        response = "[Local Message] NewBing响应异常，请刷新界面重试 ..."
    history.extend([inputs, response])
    logging.info(f"[raw_input] {inputs}")
    logging.info(f"[response] {response}")
    yield from update_ui(chatbot=chatbot, history=history, msg="完成全部响应，请提交新问题。")
