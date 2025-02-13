model_name = "LLaMA"
cmd_to_install = "`pip install -r request_llms/requirements_chatglm.txt`"


from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from toolbox import update_ui, get_conf, ProxyNetworkActivate
from multiprocessing import Process, Pipe
from .local_llm_class import LocalLLMHandle, get_local_llm_predict_fns
from threading import Thread


# ------------------------------------------------------------------------------------------------------------------------
# 🔌💻 Local Model
# ------------------------------------------------------------------------------------------------------------------------
class GetLlamaHandle(LocalLLMHandle):

    def load_model_info(self):
        # 🏃‍♂️🏃‍♂️🏃‍♂️ 子进程执行
        self.model_name = model_name
        self.cmd_to_install = cmd_to_install

    def load_model_and_tokenizer(self):
        # 🏃‍♂️🏃‍♂️🏃‍♂️ 子进程执行
        import os, glob
        import os
        import platform
        huggingface_token, device = get_conf('HUGGINGFACE_ACCESS_TOKEN', 'LOCAL_MODEL_DEVICE')
        assert len(huggingface_token) != 0, "没有填写 HUGGINGFACE_ACCESS_TOKEN"
        with open(os.path.expanduser('~/.cache/huggingface/token'), 'w', encoding='utf8') as f:
            f.write(huggingface_token)
        model_id = 'meta-llama/Llama-2-7b-chat-hf'
        with ProxyNetworkActivate('Download_LLM'):
            self._tokenizer = AutoTokenizer.from_pretrained(model_id, use_auth_token=huggingface_token)
            # use fp16
            model = AutoModelForCausalLM.from_pretrained(model_id, use_auth_token=huggingface_token).eval()
            if device.startswith('cuda'): model = model.half().to(device)
            self._model = model

            return self._model, self._tokenizer

    def llm_stream_generator(self, **kwargs):
        # 🏃‍♂️🏃‍♂️🏃‍♂️ 子进程执行
        def adaptor(kwargs):
            query = kwargs['query']
            max_length = kwargs['max_length']
            top_p = kwargs['top_p']
            temperature = kwargs['temperature']
            history = kwargs['history']
            console_silence = kwargs.get('console_silence', True)
            return query, max_length, top_p, temperature, history, console_silence

        def convert_messages_to_prompt(query, history):
            prompt = ""
            for a, b in history:
                prompt += f"\n[INST]{a}[/INST]"
                prompt += "\n{b}" + b
            prompt += f"\n[INST]{query}[/INST]"
            return prompt

        query, max_length, top_p, temperature, history, console_silence = adaptor(kwargs)
        prompt = convert_messages_to_prompt(query, history)
        # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=--=-=-
        # code from transformers.llama
        streamer = TextIteratorStreamer(self._tokenizer)
        # Run the generation in a separate thread, so that we can fetch the generated text in a non-blocking way.
        inputs = self._tokenizer([prompt], return_tensors="pt")
        prompt_tk_back = self._tokenizer.batch_decode(inputs['input_ids'])[0]

        generation_kwargs = dict(inputs.to(self._model.device), streamer=streamer, max_new_tokens=max_length)
        thread = Thread(target=self._model.generate, kwargs=generation_kwargs)
        thread.start()
        generated_text = ""
        for new_text in streamer:
            generated_text += new_text
            if not console_silence: print(new_text, end='')
            yield generated_text.lstrip(prompt_tk_back).rstrip("</s>")
        if not console_silence: print()
        # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=--=-=-

    def try_to_import_special_deps(self, **kwargs):
        # import something that will raise error if the user does not install requirement_*.txt
        # 🏃‍♂️🏃‍♂️🏃‍♂️ 主进程执行
        import importlib
        importlib.import_module('transformers')


# ------------------------------------------------------------------------------------------------------------------------
# 🔌💻 GPT-Academic Interface
# ------------------------------------------------------------------------------------------------------------------------
predict_no_ui_long_connection, predict = get_local_llm_predict_fns(GetLlamaHandle, model_name)