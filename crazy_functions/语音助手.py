from toolbox import update_ui
from toolbox import CatchException, get_conf, markdown_convertion
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.crazy_utils import input_clipping
from crazy_functions.agent_fns.watchdog import WatchDog
from crazy_functions.live_audio.aliyunASR import AliyunASR
from loguru import logger

import threading, time
import numpy as np
import json
import re


def chatbot2history(chatbot):
    history = []
    for c in chatbot:
        for q in c:
            if q in ["[ 请讲话 ]", "[ 等待GPT响应 ]", "[ 正在等您说完问题 ]"]:
                continue
            elif q.startswith("[ 正在等您说完问题 ]"):
                continue
            else:
                history.append(q.strip('<div class="markdown-body">').strip('</div>').strip('<p>').strip('</p>'))
    return history

def visualize_audio(chatbot, audio_shape):
    if len(chatbot) == 0: chatbot.append(["[ 请讲话 ]", "[ 正在等您说完问题 ]"])
    chatbot[-1] = list(chatbot[-1])
    p1 = '「'
    p2 = '」'
    chatbot[-1][-1] = re.sub(p1+r'(.*)'+p2, '', chatbot[-1][-1])
    chatbot[-1][-1] += (p1+f"`{audio_shape}`"+p2)

class AsyncGptTask():
    def __init__(self) -> None:
        self.observe_future = []
        self.observe_future_chatbot_index = []

    def gpt_thread_worker(self, i_say, llm_kwargs, history, sys_prompt, observe_window, index):
        try:
            MAX_TOKEN_ALLO = 2560
            i_say, history = input_clipping(i_say, history, max_token_limit=MAX_TOKEN_ALLO)
            gpt_say_partial = predict_no_ui_long_connection(inputs=i_say, llm_kwargs=llm_kwargs, history=history, sys_prompt=sys_prompt,
                                                            observe_window=observe_window[index], console_silence=True)
        except ConnectionAbortedError as token_exceed_err:
            logger.error('至少一个线程任务Token溢出而失败', e)
        except Exception as e:
            logger.error('至少一个线程任务意外失败', e)

    def add_async_gpt_task(self, i_say, chatbot_index, llm_kwargs, history, system_prompt):
        self.observe_future.append([""])
        self.observe_future_chatbot_index.append(chatbot_index)
        cur_index = len(self.observe_future)-1
        th_new = threading.Thread(target=self.gpt_thread_worker, args=(i_say, llm_kwargs, history, system_prompt, self.observe_future, cur_index))
        th_new.daemon = True
        th_new.start()

    def update_chatbot(self, chatbot):
        for of, ofci in zip(self.observe_future, self.observe_future_chatbot_index):
            try:
                chatbot[ofci] = list(chatbot[ofci])
                chatbot[ofci][1] = markdown_convertion(of[0])
            except:
                self.observe_future = []
                self.observe_future_chatbot_index = []
        return chatbot

class InterviewAssistant(AliyunASR):
    def __init__(self):
        self.capture_interval = 0.5 # second
        self.stop = False
        self.parsed_text = ""   # 下个句子中已经说完的部分, 由 test_on_result_chg() 写入
        self.parsed_sentence = ""   # 某段话的整个句子, 由 test_on_sentence_end() 写入
        self.buffered_sentence = ""    #
        self.audio_shape = ""   # 音频的可视化表现, 由 audio_convertion_thread() 写入
        self.event_on_result_chg = threading.Event()
        self.event_on_entence_end = threading.Event()
        self.event_on_commit_question = threading.Event()

    def __del__(self):
        self.stop = True
        self.stop_msg = ""
        self.commit_wd.kill_dog = True
        self.plugin_wd.kill_dog = True

    def init(self, chatbot):
        # 初始化音频采集线程
        self.captured_audio = np.array([])
        self.keep_latest_n_second = 10
        self.commit_after_pause_n_second = 2.0
        self.ready_audio_flagment = None
        self.stop = False
        self.plugin_wd = WatchDog(timeout=5, bark_fn=self.__del__, msg="程序终止")
        self.aut = threading.Thread(target=self.audio_convertion_thread, args=(chatbot._cookies['uuid'],))
        self.aut.daemon = True
        self.aut.start()
        # th2 = threading.Thread(target=self.audio2txt_thread, args=(chatbot._cookies['uuid'],))
        # th2.daemon = True
        # th2.start()

    def no_audio_for_a_while(self):
        if len(self.buffered_sentence) < 7: # 如果一句话小于7个字，暂不提交
            self.commit_wd.begin_watch()
        else:
            self.event_on_commit_question.set()

    def begin(self, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt):
        # main plugin function
        self.init(chatbot)
        chatbot.append(["[ 请讲话 ]", "[ 正在等您说完问题 ]"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        self.plugin_wd.begin_watch()
        self.agt = AsyncGptTask()
        self.commit_wd = WatchDog(timeout=self.commit_after_pause_n_second, bark_fn=self.no_audio_for_a_while, interval=0.2)
        self.commit_wd.begin_watch()

        while not self.stop:
            self.event_on_result_chg.wait(timeout=0.25)  # run once every 0.25 second
            chatbot = self.agt.update_chatbot(chatbot)   # 将子线程的gpt结果写入chatbot
            history = chatbot2history(chatbot)
            yield from update_ui(chatbot=chatbot, history=history)      # 刷新界面
            self.plugin_wd.feed()

            if self.event_on_result_chg.is_set():
                # called when some words have finished
                self.event_on_result_chg.clear()
                chatbot[-1] = list(chatbot[-1])
                chatbot[-1][0] = self.buffered_sentence + self.parsed_text
                history = chatbot2history(chatbot)
                yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
                self.commit_wd.feed()

            if self.event_on_entence_end.is_set():
                # called when a sentence has ended
                self.event_on_entence_end.clear()
                self.parsed_text = self.parsed_sentence
                self.buffered_sentence += self.parsed_text
                chatbot[-1] = list(chatbot[-1])
                chatbot[-1][0] = self.buffered_sentence
                history = chatbot2history(chatbot)
                yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面

            if self.event_on_commit_question.is_set():
                # called when a question should be commited
                self.event_on_commit_question.clear()
                if len(self.buffered_sentence) == 0: raise RuntimeError

                self.commit_wd.begin_watch()
                chatbot[-1] = list(chatbot[-1])
                chatbot[-1] = [self.buffered_sentence, "[ 等待GPT响应 ]"]
                yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
                # add gpt task 创建子线程请求gpt，避免线程阻塞
                history = chatbot2history(chatbot)
                self.agt.add_async_gpt_task(self.buffered_sentence, len(chatbot)-1, llm_kwargs, history, system_prompt)

                self.buffered_sentence = ""
                chatbot.append(["[ 请讲话 ]", "[ 正在等您说完问题 ]"])
                yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

            if not self.event_on_result_chg.is_set() and not self.event_on_entence_end.is_set() and not self.event_on_commit_question.is_set():
                visualize_audio(chatbot, self.audio_shape)
                yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

        if len(self.stop_msg) != 0:
            raise RuntimeError(self.stop_msg)



@CatchException
def 语音助手(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    # pip install -U openai-whisper
    chatbot.append(["对话助手函数插件：使用时，双手离开鼠标键盘吧", "音频助手, 正在听您讲话（点击“停止”键可终止程序）..."])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖，如果缺少依赖，则给出安装建议
    try:
        import nls
        from scipy import io
    except:
        chatbot.append(["导入依赖失败", "使用该模块需要额外依赖, 安装方法:```pip install --upgrade aliyun-python-sdk-core==2.13.3 pyOpenSSL webrtcvad scipy git+https://github.com/aliyun/alibabacloud-nls-python-sdk.git```"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    APPKEY = get_conf('ALIYUN_APPKEY')
    if APPKEY == "":
        chatbot.append(["导入依赖失败", "没有阿里云语音识别APPKEY和TOKEN, 详情见https://help.aliyun.com/document_detail/450255.html"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return

    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    ia = InterviewAssistant()
    yield from ia.begin(llm_kwargs, plugin_kwargs, chatbot, history, system_prompt)

