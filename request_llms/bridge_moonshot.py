# encoding: utf-8
# @Time   : 2024/3/3
# @Author : Spike
# @Descr   :
import json
import os
import time

from toolbox import get_conf, update_ui, log_chat
from toolbox import ChatBotWithCookies

import requests


class MoonShotInit:

    def __init__(self):
        self.llm_model = None
        self.url = 'https://api.moonshot.cn/v1/chat/completions'
        self.api_key = get_conf('MOONSHOT_API_KEY')

    def __converter_file(self, user_input: str):
        what_ask = []
        for f in user_input.splitlines():
            if os.path.exists(f):
                files = []
                if os.path.isdir(f):
                    file_list = os.listdir(f)
                    files.extend([os.path.join(f, file) for file in file_list])
                else:
                    files.append(f)
                for file in files:
                    if file.split('.')[-1] in ['pdf']:
                        with open(file, 'r', encoding='utf8') as fp:
                            from crazy_functions.crazy_utils import read_and_clean_pdf_text
                            file_content, _ = read_and_clean_pdf_text(fp)
                        what_ask.append({"role": "system", "content": file_content})
        return what_ask

    def __converter_user(self, user_input: str):
        what_i_ask_now = {"role": "user", "content": user_input}
        return what_i_ask_now

    def __conversation_history(self, history):
        conversation_cnt = len(history) // 2
        messages = []
        if conversation_cnt:
            for index in range(0, 2 * conversation_cnt, 2):
                what_i_have_asked = {
                    "role": "user",
                    "content": str(history[index])
                }
                what_gpt_answer = {
                    "role": "assistant",
                    "content": str(history[index + 1])
                }
                if what_i_have_asked["content"] != "":
                    if what_gpt_answer["content"] == "": continue
                    messages.append(what_i_have_asked)
                    messages.append(what_gpt_answer)
                else:
                    messages[-1]['content'] = what_gpt_answer['content']
        return messages

    def _analysis_content(self, chuck):
        chunk_decoded = chuck.decode("utf-8")
        chunk_json = {}
        content = ""
        try:
            chunk_json = json.loads(chunk_decoded[6:])
            content = chunk_json['choices'][0]["delta"].get("content", "")
        except:
            pass
        return chunk_decoded, chunk_json, content

    def generate_payload(self, inputs, llm_kwargs, history, system_prompt, stream):
        self.llm_model = llm_kwargs['llm_model']
        llm_kwargs.update({'use-key': self.api_key})
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.__converter_file(inputs))
        for i in history[0::2]:    # 历史文件继续上传
            messages.extend(self.__converter_file(i))
        messages.extend(self.__conversation_history(history))
        messages.append(self.__converter_user(inputs))
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": llm_kwargs.get('temperature', 0.3),  # 1.0,
            "top_p": llm_kwargs.get('top_p', 1.0),  # 1.0,
            "n": llm_kwargs.get('n_choices', 1),
            "stream": stream
        }
        return payload, header

    def generate_messages(self, inputs, llm_kwargs, history, system_prompt, stream):
        payload, headers = self.generate_payload(inputs, llm_kwargs, history, system_prompt, stream)
        response = requests.post(self.url, headers=headers, json=payload, stream=stream)

        chunk_content = ""
        gpt_bro_result = ""
        for chuck in response.iter_lines():
            chunk_decoded, check_json, content = self._analysis_content(chuck)
            chunk_content += chunk_decoded
            if content:
                gpt_bro_result += content
                yield content, gpt_bro_result, ''
            else:
                error_msg = msg_handle_error(llm_kwargs, chunk_decoded)
                if error_msg:
                    yield error_msg, gpt_bro_result, error_msg
                    break


def msg_handle_error(llm_kwargs, chunk_decoded):
    use_ket = llm_kwargs.get('use-key', '')
    api_key_encryption = use_ket[:8] + '****' + use_ket[-5:]
    openai_website = f' 请登录OpenAI查看详情 https://platform.openai.com/signup  api-key: `{api_key_encryption}`'
    error_msg = ''
    if "does not exist" in chunk_decoded:
        error_msg = f"[Local Message] Model {llm_kwargs['llm_model']} does not exist. 模型不存在, 或者您没有获得体验资格."
    elif "Incorrect API key" in chunk_decoded:
        error_msg = f"[Local Message] Incorrect API key. OpenAI以提供了不正确的API_KEY为由, 拒绝服务." + openai_website
    elif "exceeded your current quota" in chunk_decoded:
        error_msg = "[Local Message] You exceeded your current quota. OpenAI以账户额度不足为由, 拒绝服务." + openai_website
    elif "account is not active" in chunk_decoded:
        error_msg = "[Local Message] Your account is not active. OpenAI以账户失效为由, 拒绝服务." + openai_website
    elif "associated with a deactivated account" in chunk_decoded:
        error_msg = "[Local Message] You are associated with a deactivated account. OpenAI以账户失效为由, 拒绝服务." + openai_website
    elif "API key has been deactivated" in chunk_decoded:
        error_msg = "[Local Message] API key has been deactivated. OpenAI以账户失效为由, 拒绝服务." + openai_website
    elif "bad forward key" in chunk_decoded:
        error_msg = "[Local Message] Bad forward key. API2D账户额度不足."
    elif "Not enough point" in chunk_decoded:
        error_msg = "[Local Message] Not enough point. API2D账户点数不足."
    elif 'error' in str(chunk_decoded).lower():
        try:
            error_msg = json.dumps(json.loads(chunk_decoded[:6]), indent=4, ensure_ascii=False)
        except:
            error_msg = chunk_decoded
    return error_msg


def predict(inputs:str, llm_kwargs:dict, plugin_kwargs:dict, chatbot:ChatBotWithCookies,
            history:list=[], system_prompt:str='', stream:bool=True, additional_fn:str=None):
    chatbot.append([inputs, ""])

    if additional_fn is not None:
        from core_functional import handle_core_functionality
        inputs, history = handle_core_functionality(additional_fn, inputs, history, chatbot)
    yield from update_ui(chatbot=chatbot, history=history, msg="等待响应")  # 刷新界面
    gpt_bro_init = MoonShotInit()
    history.extend([inputs, ''])
    stream_response = gpt_bro_init.generate_messages(inputs, llm_kwargs, history, system_prompt, stream)
    for content, gpt_bro_result, error_bro_meg in stream_response:
        chatbot[-1] = [inputs, gpt_bro_result]
        history[-1] = gpt_bro_result
        yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
        if error_bro_meg:
            chatbot[-1] = [inputs, error_bro_meg]
            history = history[:-2]
            yield from update_ui(chatbot=chatbot, history=history)  # 刷新界面
            break
    log_chat(llm_model=llm_kwargs["llm_model"], input_str=inputs, output_str=gpt_bro_result)

def predict_no_ui_long_connection(inputs, llm_kwargs, history=[], sys_prompt="", observe_window=None,
                                  console_silence=False):
    gpt_bro_init = MoonShotInit()
    watch_dog_patience = 60  # 看门狗的耐心, 设置10秒即可
    stream_response = gpt_bro_init.generate_messages(inputs, llm_kwargs, history, sys_prompt, True)
    moonshot_bro_result = ''
    for content, moonshot_bro_result, error_bro_meg in stream_response:
        moonshot_bro_result = moonshot_bro_result
        if error_bro_meg:
            if len(observe_window) >= 3:
                observe_window[2] = error_bro_meg
            return f'{moonshot_bro_result} 对话错误'
            # 观测窗
        if len(observe_window) >= 1:
            observe_window[0] = moonshot_bro_result
        if len(observe_window) >= 2:
            if (time.time() - observe_window[1]) > watch_dog_patience:
                observe_window[2] = "请求超时，程序终止。"
                raise RuntimeError(f"{moonshot_bro_result} 程序终止。")
    return moonshot_bro_result

if __name__ == '__main__':
    moon_ai = MoonShotInit()
    for g in moon_ai.generate_messages('hello', {'llm_model': 'moonshot-v1-8k'},
                                       [], '', True):
        print(g)
