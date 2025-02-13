
from transformers import AutoModel, AutoTokenizer
import time
import threading
import importlib
from toolbox import update_ui, get_conf
from multiprocessing import Process, Pipe

load_message = "jittorllms尚未加载，加载需要一段时间。注意，请避免混用多种jittor模型，否则可能导致显存溢出而造成卡顿，取决于`config.py`的配置，jittorllms消耗大量的内存（CPU）或显存（GPU），也许会导致低配计算机卡死 ……"

#################################################################################
class GetGLMHandle(Process):
    def __init__(self):
        super().__init__(daemon=True)
        self.parent, self.child = Pipe()
        self.jittorllms_model = None
        self.info = ""
        self.local_history = []
        self.success = True
        self.check_dependency()
        self.start()
        self.threadLock = threading.Lock()

    def check_dependency(self):
        try:
            import pandas
            self.info = "依赖检测通过"
            self.success = True
        except:
            from toolbox import trimmed_format_exc
            self.info = r"缺少jittorllms的依赖，如果要使用jittorllms，除了基础的pip依赖以外，您还需要运行`pip install -r request_llms/requirements_jittorllms.txt -i https://pypi.jittor.org/simple -I`"+\
                        r"和`git clone https://gitlink.org.cn/jittor/JittorLLMs.git --depth 1 request_llms/jittorllms`两个指令来安装jittorllms的依赖（在项目根目录运行这两个指令）。" +\
                        r"警告：安装jittorllms依赖后将完全破坏现有的pytorch环境，建议使用docker环境！" + trimmed_format_exc()
            self.success = False

    def ready(self):
        return self.jittorllms_model is not None

    def run(self):
        # 子进程执行
        # 第一次运行，加载参数
        def validate_path():
            import os, sys
            dir_name = os.path.dirname(__file__)
            env = os.environ.get("PATH", "")
            os.environ["PATH"] = env.replace('/cuda/bin', '/x/bin')
            root_dir_assume = os.path.abspath(os.path.dirname(__file__) +  '/..')
            os.chdir(root_dir_assume + '/request_llms/jittorllms')
            sys.path.append(root_dir_assume + '/request_llms/jittorllms')
        validate_path() # validate path so you can run from base directory

        def load_model():
            import types
            try:
                if self.jittorllms_model is None:
                    device = get_conf('LOCAL_MODEL_DEVICE')
                    from .jittorllms.models import get_model
                    # available_models = ["chatglm", "pangualpha", "llama", "chatrwkv"]
                    args_dict = {'model': 'chatrwkv'}
                    print('self.jittorllms_model = get_model(types.SimpleNamespace(**args_dict))')
                    self.jittorllms_model = get_model(types.SimpleNamespace(**args_dict))
                    print('done get model')
            except:
                self.child.send('[Local Message] Call jittorllms fail 不能正常加载jittorllms的参数。')
                raise RuntimeError("不能正常加载jittorllms的参数！")
        print('load_model')
        load_model()

        # 进入任务等待状态
        print('进入任务等待状态')
        while True:
            # 进入任务等待状态
            kwargs = self.child.recv()
            query = kwargs['query']
            history = kwargs['history']
            # 是否重置
            if len(self.local_history) > 0 and len(history)==0:
                print('触发重置')
                self.jittorllms_model.reset()
            self.local_history.append(query)

            print('收到消息，开始请求')
            try:
                for response in self.jittorllms_model.stream_chat(query, history):
                    print(response)
                    self.child.send(response)
            except:
                from toolbox import trimmed_format_exc
                print(trimmed_format_exc())
                self.child.send('[Local Message] Call jittorllms fail.')
            # 请求处理结束，开始下一个循环
            self.child.send('[Finish]')

    def stream_chat(self, **kwargs):
        # 主进程执行
        self.threadLock.acquire()
        self.parent.send(kwargs)
        while True:
            res = self.parent.recv()
            if res != '[Finish]':
                yield res
            else:
                break
        self.threadLock.release()

global rwkv_glm_handle
rwkv_glm_handle = None
#################################################################################
def predict_no_ui_long_connection(inputs:str, llm_kwargs:dict, history:list=[], sys_prompt:str="",
                                  observe_window:list=[], console_silence:bool=False):
    """
        多线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    global rwkv_glm_handle
    if rwkv_glm_handle is None:
        rwkv_glm_handle = GetGLMHandle()
        if len(observe_window) >= 1: observe_window[0] = load_message + "\n\n" + rwkv_glm_handle.info
        if not rwkv_glm_handle.success:
            error = rwkv_glm_handle.info
            rwkv_glm_handle = None
            raise RuntimeError(error)

    # jittorllms 没有 sys_prompt 接口，因此把prompt加入 history
    history_feedin = []
    for i in range(len(history)//2):
        history_feedin.append([history[2*i], history[2*i+1]] )

    watch_dog_patience = 5 # 看门狗 (watchdog) 的耐心, 设置5秒即可
    response = ""
    for response in rwkv_glm_handle.stream_chat(query=inputs, history=history_feedin, system_prompt=sys_prompt, max_length=llm_kwargs['max_length'], top_p=llm_kwargs['top_p'], temperature=llm_kwargs['temperature']):
        print(response)
        if len(observe_window) >= 1:  observe_window[0] = response
        if len(observe_window) >= 2:
            if (time.time()-observe_window[1]) > watch_dog_patience:
                raise RuntimeError("程序终止。")
    return response



def predict(inputs, llm_kwargs, plugin_kwargs, chatbot, history=[], system_prompt='', stream = True, additional_fn=None):
    """
        单线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    chatbot.append((inputs, ""))

    global rwkv_glm_handle
    if rwkv_glm_handle is None:
        rwkv_glm_handle = GetGLMHandle()
        chatbot[-1] = (inputs, load_message + "\n\n" + rwkv_glm_handle.info)
        yield from update_ui(chatbot=chatbot, history=[])
        if not rwkv_glm_handle.success:
            rwkv_glm_handle = None
            return

    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    # 处理历史信息
    history_feedin = []
    for i in range(len(history)//2):
        history_feedin.append([history[2*i], history[2*i+1]] )

    # 开始接收jittorllms的回复
    response = "[Local Message] 等待jittorllms响应中 ..."
    for response in rwkv_glm_handle.stream_chat(query=inputs, history=history_feedin, system_prompt=system_prompt, max_length=llm_kwargs['max_length'], top_p=llm_kwargs['top_p'], temperature=llm_kwargs['temperature']):
        chatbot[-1] = (inputs, response)
        yield from update_ui(chatbot=chatbot, history=history)

    # 总结输出
    if response == "[Local Message] 等待jittorllms响应中 ...":
        response = "[Local Message] jittorllms响应异常 ..."
    history.extend([inputs, response])
    yield from update_ui(chatbot=chatbot, history=history)
