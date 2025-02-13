
from transformers import AutoModel, AutoTokenizer
from loguru import logger
from toolbox import update_ui, get_conf
from multiprocessing import Process, Pipe
import time
import os
import json
import threading
import importlib

load_message = "ChatGLMFT尚未加载，加载需要一段时间。注意，取决于`config.py`的配置，ChatGLMFT消耗大量的内存（CPU）或显存（GPU），也许会导致低配计算机卡死 ……"

def string_to_options(arguments):
    import argparse
    import shlex
    # Create an argparse.ArgumentParser instance
    parser = argparse.ArgumentParser()
    # Add command-line arguments
    parser.add_argument("--llm_to_learn", type=str, help="LLM model to learn", default="gpt-3.5-turbo")
    parser.add_argument("--prompt_prefix", type=str, help="Prompt prefix", default='')
    parser.add_argument("--system_prompt", type=str, help="System prompt", default='')
    parser.add_argument("--batch", type=int, help="System prompt", default=50)
    # Parse the arguments
    args = parser.parse_args(shlex.split(arguments))
    return args


#################################################################################
class GetGLMFTHandle(Process):
    def __init__(self):
        super().__init__(daemon=True)
        self.parent, self.child = Pipe()
        self.chatglmft_model = None
        self.chatglmft_tokenizer = None
        self.info = ""
        self.success = True
        self.check_dependency()
        self.start()
        self.threadLock = threading.Lock()

    def check_dependency(self):
        try:
            import sentencepiece
            self.info = "依赖检测通过"
            self.success = True
        except:
            self.info = "缺少ChatGLMFT的依赖，如果要使用ChatGLMFT，除了基础的pip依赖以外，您还需要运行`pip install -r request_llms/requirements_chatglm.txt`安装ChatGLM的依赖。"
            self.success = False

    def ready(self):
        return self.chatglmft_model is not None

    def run(self):
        # 子进程执行
        # 第一次运行，加载参数
        retry = 0
        while True:
            try:
                if self.chatglmft_model is None:
                    from transformers import AutoConfig
                    import torch
                    # conf = 'request_llms/current_ptune_model.json'
                    # if not os.path.exists(conf): raise RuntimeError('找不到微调模型信息')
                    # with open(conf, 'r', encoding='utf8') as f:
                    #     model_args = json.loads(f.read())
                    CHATGLM_PTUNING_CHECKPOINT = get_conf('CHATGLM_PTUNING_CHECKPOINT')
                    assert os.path.exists(CHATGLM_PTUNING_CHECKPOINT), "找不到微调模型检查点"
                    conf = os.path.join(CHATGLM_PTUNING_CHECKPOINT, "config.json")
                    with open(conf, 'r', encoding='utf8') as f:
                        model_args = json.loads(f.read())
                    if 'model_name_or_path' not in model_args:
                        model_args['model_name_or_path'] = model_args['_name_or_path']
                    self.chatglmft_tokenizer = AutoTokenizer.from_pretrained(
                        model_args['model_name_or_path'], trust_remote_code=True)
                    config = AutoConfig.from_pretrained(
                        model_args['model_name_or_path'], trust_remote_code=True)

                    config.pre_seq_len = model_args['pre_seq_len']
                    config.prefix_projection = model_args['prefix_projection']

                    logger.info(f"Loading prefix_encoder weight from {CHATGLM_PTUNING_CHECKPOINT}")
                    model = AutoModel.from_pretrained(model_args['model_name_or_path'], config=config, trust_remote_code=True)
                    prefix_state_dict = torch.load(os.path.join(CHATGLM_PTUNING_CHECKPOINT, "pytorch_model.bin"))
                    new_prefix_state_dict = {}
                    for k, v in prefix_state_dict.items():
                        if k.startswith("transformer.prefix_encoder."):
                            new_prefix_state_dict[k[len("transformer.prefix_encoder."):]] = v
                    model.transformer.prefix_encoder.load_state_dict(new_prefix_state_dict)

                    if model_args['quantization_bit'] is not None and model_args['quantization_bit'] != 0:
                        logger.info(f"Quantized to {model_args['quantization_bit']} bit")
                        model = model.quantize(model_args['quantization_bit'])
                    model = model.cuda()
                    if model_args['pre_seq_len'] is not None:
                        # P-tuning v2
                        model.transformer.prefix_encoder.float()
                    self.chatglmft_model = model.eval()

                    break
                else:
                    break
            except Exception as e:
                retry += 1
                if retry > 3:
                    self.child.send('[Local Message] Call ChatGLMFT fail 不能正常加载ChatGLMFT的参数。')
                    raise RuntimeError("不能正常加载ChatGLMFT的参数！")

        while True:
            # 进入任务等待状态
            kwargs = self.child.recv()
            # 收到消息，开始请求
            try:
                for response, history in self.chatglmft_model.stream_chat(self.chatglmft_tokenizer, **kwargs):
                    self.child.send(response)
                    # # 中途接收可能的终止指令（如果有的话）
                    # if self.child.poll():
                    #     command = self.child.recv()
                    #     if command == '[Terminate]': break
            except:
                from toolbox import trimmed_format_exc
                self.child.send('[Local Message] Call ChatGLMFT fail.' + '\n```\n' + trimmed_format_exc() + '\n```\n')
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

global glmft_handle
glmft_handle = None
#################################################################################
def predict_no_ui_long_connection(inputs:str, llm_kwargs:dict, history:list=[], sys_prompt:str="",
                                  observe_window:list=[], console_silence:bool=False):
    """
        多线程方法
        函数的说明请见 request_llms/bridge_all.py
    """
    global glmft_handle
    if glmft_handle is None:
        glmft_handle = GetGLMFTHandle()
        if len(observe_window) >= 1: observe_window[0] = load_message + "\n\n" + glmft_handle.info
        if not glmft_handle.success:
            error = glmft_handle.info
            glmft_handle = None
            raise RuntimeError(error)

    # chatglmft 没有 sys_prompt 接口，因此把prompt加入 history
    history_feedin = []
    history_feedin.append(["What can I do?", sys_prompt])
    for i in range(len(history)//2):
        history_feedin.append([history[2*i], history[2*i+1]] )

    watch_dog_patience = 5 # 看门狗 (watchdog) 的耐心, 设置5秒即可
    response = ""
    for response in glmft_handle.stream_chat(query=inputs, history=history_feedin, max_length=llm_kwargs['max_length'], top_p=llm_kwargs['top_p'], temperature=llm_kwargs['temperature']):
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

    global glmft_handle
    if glmft_handle is None:
        glmft_handle = GetGLMFTHandle()
        chatbot[-1] = (inputs, load_message + "\n\n" + glmft_handle.info)
        yield from update_ui(chatbot=chatbot, history=[])
        if not glmft_handle.success:
            glmft_handle = None
            return

    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)

    # 处理历史信息
    history_feedin = []
    history_feedin.append(["What can I do?", system_prompt] )
    for i in range(len(history)//2):
        history_feedin.append([history[2*i], history[2*i+1]] )

    # 开始接收chatglmft的回复
    response = "[Local Message] 等待ChatGLMFT响应中 ..."
    for response in glmft_handle.stream_chat(query=inputs, history=history_feedin, max_length=llm_kwargs['max_length'], top_p=llm_kwargs['top_p'], temperature=llm_kwargs['temperature']):
        chatbot[-1] = (inputs, response)
        yield from update_ui(chatbot=chatbot, history=history)

    # 总结输出
    if response == "[Local Message] 等待ChatGLMFT响应中 ...":
        response = "[Local Message] ChatGLMFT响应异常 ..."
    history.extend([inputs, response])
    yield from update_ui(chatbot=chatbot, history=history)
