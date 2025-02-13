import time
import asyncio
import threading
import importlib

from .bridge_newbingfree import preprocess_newbing_out, preprocess_newbing_out_simple
from multiprocessing import Process, Pipe
from toolbox import update_ui, get_conf, trimmed_format_exc
from loguru import logger as logging
from toolbox import get_conf

load_message = "正在加载Claude组件，请稍候..."

try:
    """
    =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    第一部分：Slack API Client
    https://github.com/yokonsan/claude-in-slack-api
    =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
    """

    from slack_sdk.errors import SlackApiError
    from slack_sdk.web.async_client import AsyncWebClient

    class SlackClient(AsyncWebClient):
        """SlackClient类用于与Slack API进行交互，实现消息发送、接收等功能。

        属性：
        - CHANNEL_ID：str类型，表示频道ID。

        方法：
        - open_channel()：异步方法。通过调用conversations_open方法打开一个频道，并将返回的频道ID保存在属性CHANNEL_ID中。
        - chat(text: str)：异步方法。向已打开的频道发送一条文本消息。
        - get_slack_messages()：异步方法。获取已打开频道的最新消息并返回消息列表，目前不支持历史消息查询。
        - get_reply()：异步方法。循环监听已打开频道的消息，如果收到"Typing…_"结尾的消息说明Claude还在继续输出，否则结束循环。

        """

        CHANNEL_ID = None

        async def open_channel(self):
            response = await self.conversations_open(
                users=get_conf("SLACK_CLAUDE_BOT_ID")
            )
            self.CHANNEL_ID = response["channel"]["id"]

        async def chat(self, text):
            if not self.CHANNEL_ID:
                raise Exception("Channel not found.")

            resp = await self.chat_postMessage(channel=self.CHANNEL_ID, text=text)
            self.LAST_TS = resp["ts"]

        async def get_slack_messages(self):
            try:
                # TODO：暂时不支持历史消息，因为在同一个频道里存在多人使用时历史消息渗透问题
                resp = await self.conversations_history(
                    channel=self.CHANNEL_ID, oldest=self.LAST_TS, limit=1
                )
                msg = [
                    msg
                    for msg in resp["messages"]
                    if msg.get("user") == get_conf("SLACK_CLAUDE_BOT_ID")
                ]
                return msg
            except (SlackApiError, KeyError) as e:
                raise RuntimeError(f"获取Slack消息失败。")

        async def get_reply(self):
            while True:
                slack_msgs = await self.get_slack_messages()
                if len(slack_msgs) == 0:
                    await asyncio.sleep(0.5)
                    continue

                msg = slack_msgs[-1]
                if msg["text"].endswith("Typing…_"):
                    yield False, msg["text"]
                else:
                    yield True, msg["text"]
                    break

except:
    pass

"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
第二部分：子进程Worker（调用主体）
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""


class ClaudeHandle(Process):
    def __init__(self):
        super().__init__(daemon=True)
        self.parent, self.child = Pipe()
        self.claude_model = None
        self.info = ""
        self.success = True
        self.local_history = []
        self.check_dependency()
        if self.success:
            self.start()
            self.threadLock = threading.Lock()

    def check_dependency(self):
        try:
            self.success = False
            import slack_sdk

            self.info = "依赖检测通过，等待Claude响应。注意目前不能多人同时调用Claude接口（有线程锁），否则将导致每个人的Claude问询历史互相渗透。调用Claude时，会自动使用已配置的代理。"
            self.success = True
        except:
            self.info = "缺少的依赖，如果要使用Claude，除了基础的pip依赖以外，您还需要运行`pip install -r request_llms/requirements_slackclaude.txt`安装Claude的依赖，然后重启程序。"
            self.success = False

    def ready(self):
        return self.claude_model is not None

    async def async_run(self):
        await self.claude_model.open_channel()
        while True:
            # 等待
            kwargs = self.child.recv()
            question = kwargs["query"]
            history = kwargs["history"]

            # 开始问问题
            prompt = ""

            # 问题
            prompt += question
            print("question:", prompt)

            # 提交
            await self.claude_model.chat(prompt)

            # 获取回复
            async for final, response in self.claude_model.get_reply():
                if not final:
                    print(response)
                    self.child.send(str(response))
                else:
                    # 防止丢失最后一条消息
                    slack_msgs = await self.claude_model.get_slack_messages()
                    last_msg = (
                        slack_msgs[-1]["text"]
                        if slack_msgs and len(slack_msgs) > 0
                        else ""
                    )
                    if last_msg:
                        self.child.send(last_msg)
                    print("-------- receive final ---------")
                    self.child.send("[Finish]")

    def run(self):
        """
        这个函数运行在子进程
        """
        # 第一次运行，加载参数
        self.success = False
        self.local_history = []
        if (self.claude_model is None) or (not self.success):
            # 代理设置
            proxies = get_conf("proxies")
            if proxies is None:
                self.proxies_https = None
            else:
                self.proxies_https = proxies["https"]

            try:
                SLACK_CLAUDE_USER_TOKEN = get_conf("SLACK_CLAUDE_USER_TOKEN")
                self.claude_model = SlackClient(
                    token=SLACK_CLAUDE_USER_TOKEN, proxy=self.proxies_https
                )
                print("Claude组件初始化成功。")
            except:
                self.success = False
                tb_str = "\n```\n" + trimmed_format_exc() + "\n```\n"
                self.child.send(f"[Local Message] 不能加载Claude组件。{tb_str}")
                self.child.send("[Fail]")
                self.child.send("[Finish]")
                raise RuntimeError(f"不能加载Claude组件。")

        self.success = True
        try:
            # 进入任务等待状态
            asyncio.run(self.async_run())
        except Exception:
            tb_str = "\n```\n" + trimmed_format_exc() + "\n```\n"
            self.child.send(f"[Local Message] Claude失败 {tb_str}.")
            self.child.send("[Fail]")
            self.child.send("[Finish]")

    def stream_chat(self, **kwargs):
        """
        这个函数运行在主进程
        """
        self.threadLock.acquire()
        self.parent.send(kwargs)  # 发送请求到子进程
        while True:
            res = self.parent.recv()  # 等待Claude回复的片段
            if res == "[Finish]":
                break  # 结束
            elif res == "[Fail]":
                self.success = False
                break
            else:
                yield res  # Claude回复的片段
        self.threadLock.release()


"""
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
第三部分：主进程统一调用函数接口
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"""
global claude_handle
claude_handle = None


def predict_no_ui_long_connection(
    inputs,
    llm_kwargs,
    history=[],
    sys_prompt="",
    observe_window=None,
    console_silence=False,
):
    """
    多线程方法
    函数的说明请见 request_llms/bridge_all.py
    """
    global claude_handle
    if (claude_handle is None) or (not claude_handle.success):
        claude_handle = ClaudeHandle()
        observe_window[0] = load_message + "\n\n" + claude_handle.info
        if not claude_handle.success:
            error = claude_handle.info
            claude_handle = None
            raise RuntimeError(error)

    # 没有 sys_prompt 接口，因此把prompt加入 history
    history_feedin = []
    for i in range(len(history) // 2):
        history_feedin.append([history[2 * i], history[2 * i + 1]])

    watch_dog_patience = 5  # 看门狗 (watchdog) 的耐心, 设置5秒即可
    response = ""
    observe_window[0] = "[Local Message] 等待Claude响应中 ..."
    for response in claude_handle.stream_chat(
        query=inputs,
        history=history_feedin,
        system_prompt=sys_prompt,
        max_length=llm_kwargs["max_length"],
        top_p=llm_kwargs["top_p"],
        temperature=llm_kwargs["temperature"],
    ):
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
    chatbot.append((inputs, "[Local Message] 等待Claude响应中 ..."))

    global claude_handle
    if (claude_handle is None) or (not claude_handle.success):
        claude_handle = ClaudeHandle()
        chatbot[-1] = (inputs, load_message + "\n\n" + claude_handle.info)
        yield from update_ui(chatbot=chatbot, history=[])
        if not claude_handle.success:
            claude_handle = None
            return

    if additional_fn is not None:
        from core_functional import handle_core_functionality

        inputs, history = handle_core_functionality(
            additional_fn, inputs, history, chatbot
        )

    history_feedin = []
    for i in range(len(history) // 2):
        history_feedin.append([history[2 * i], history[2 * i + 1]])

    chatbot[-1] = (inputs, "[Local Message] 等待Claude响应中 ...")
    response = "[Local Message] 等待Claude响应中 ..."
    yield from update_ui(
        chatbot=chatbot, history=history, msg="Claude响应缓慢，尚未完成全部响应，请耐心完成后再提交新问题。"
    )
    for response in claude_handle.stream_chat(
        query=inputs, history=history_feedin, system_prompt=system_prompt
    ):
        chatbot[-1] = (inputs, preprocess_newbing_out(response))
        yield from update_ui(
            chatbot=chatbot, history=history, msg="Claude响应缓慢，尚未完成全部响应，请耐心完成后再提交新问题。"
        )
    if response == "[Local Message] 等待Claude响应中 ...":
        response = "[Local Message] Claude响应异常，请刷新界面重试 ..."
    history.extend([inputs, response])
    logging.info(f"[raw_input] {inputs}")
    logging.info(f"[response] {response}")
    yield from update_ui(chatbot=chatbot, history=history, msg="完成全部响应，请提交新问题。")
