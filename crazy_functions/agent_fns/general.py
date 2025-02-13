from toolbox import trimmed_format_exc, get_conf, ProxyNetworkActivate
from crazy_functions.agent_fns.pipe import PluginMultiprocessManager, PipeCom
from request_llms.bridge_all import predict_no_ui_long_connection
import time

def gpt_academic_generate_oai_reply(
    self,
    messages,
    sender,
    config,
):
    llm_config = self.llm_config if config is None else config
    if llm_config is False:
        return False, None
    if messages is None:
        messages = self._oai_messages[sender]

    inputs = messages[-1]['content']
    history = []
    for message in messages[:-1]:
        history.append(message['content'])
    context=messages[-1].pop("context", None)
    assert context is None, "预留参数 context 未实现"

    reply = predict_no_ui_long_connection(
        inputs=inputs,
        llm_kwargs=llm_config,
        history=history,
        sys_prompt=self._oai_system_message[0]['content'],
        console_silence=True
    )
    assumed_done = reply.endswith('\nTERMINATE')
    return True, reply

class AutoGenGeneral(PluginMultiprocessManager):
    def gpt_academic_print_override(self, user_proxy, message, sender):
        # ⭐⭐ run in subprocess
        try:
            print_msg = sender.name + "\n\n---\n\n" + message["content"]
        except:
            print_msg = sender.name + "\n\n---\n\n" + message
        self.child_conn.send(PipeCom("show", print_msg))

    def gpt_academic_get_human_input(self, user_proxy, message):
        # ⭐⭐ run in subprocess
        patience = 300
        begin_waiting_time = time.time()
        self.child_conn.send(PipeCom("interact", message))
        while True:
            time.sleep(0.5)
            if self.child_conn.poll():
                wait_success = True
                break
            if time.time() - begin_waiting_time > patience:
                self.child_conn.send(PipeCom("done", ""))
                wait_success = False
                break
        if wait_success:
            return self.child_conn.recv().content
        else:
            raise TimeoutError("等待用户输入超时")

    def define_agents(self):
        raise NotImplementedError

    def exe_autogen(self, input):
        # ⭐⭐ run in subprocess
        input = input.content
        code_execution_config = {"work_dir": self.autogen_work_dir, "use_docker": self.use_docker}
        agents = self.define_agents()
        user_proxy = None
        assistant = None
        for agent_kwargs in agents:
            agent_cls = agent_kwargs.pop('cls')
            kwargs = {
                'llm_config':self.llm_kwargs,
                'code_execution_config':code_execution_config
            }
            kwargs.update(agent_kwargs)
            agent_handle = agent_cls(**kwargs)
            agent_handle._print_received_message = lambda a,b: self.gpt_academic_print_override(agent_kwargs, a, b)
            for d in agent_handle._reply_func_list:
                if hasattr(d['reply_func'],'__name__') and d['reply_func'].__name__ == 'generate_oai_reply':
                    d['reply_func'] = gpt_academic_generate_oai_reply
            if agent_kwargs['name'] == 'user_proxy':
                agent_handle.get_human_input = lambda a: self.gpt_academic_get_human_input(user_proxy, a)
                user_proxy = agent_handle
            if agent_kwargs['name'] == 'assistant': assistant = agent_handle
        try:
            if user_proxy is None or assistant is None: raise Exception("用户代理或助理代理未定义")
            with ProxyNetworkActivate("AutoGen"):
                user_proxy.initiate_chat(assistant, message=input)
        except Exception as e:
            tb_str = '```\n' + trimmed_format_exc() + '```'
            self.child_conn.send(PipeCom("done", "AutoGen 执行失败: \n\n" + tb_str))

    def subprocess_worker(self, child_conn):
        # ⭐⭐ run in subprocess
        self.child_conn = child_conn
        while True:
            msg = self.child_conn.recv()  # PipeCom
            self.exe_autogen(msg)


class AutoGenGroupChat(AutoGenGeneral):
    def exe_autogen(self, input):
        # ⭐⭐ run in subprocess
        import autogen

        input = input.content
        with ProxyNetworkActivate("AutoGen"):
            code_execution_config = {"work_dir": self.autogen_work_dir, "use_docker": self.use_docker}
            agents = self.define_agents()
            agents_instances = []
            for agent_kwargs in agents:
                agent_cls = agent_kwargs.pop("cls")
                kwargs = {"code_execution_config": code_execution_config}
                kwargs.update(agent_kwargs)
                agent_handle = agent_cls(**kwargs)
                agent_handle._print_received_message = lambda a, b: self.gpt_academic_print_override(agent_kwargs, a, b)
                agents_instances.append(agent_handle)
                if agent_kwargs["name"] == "user_proxy":
                    user_proxy = agent_handle
                    user_proxy.get_human_input = lambda a: self.gpt_academic_get_human_input(user_proxy, a)
            try:
                groupchat = autogen.GroupChat(agents=agents_instances, messages=[], max_round=50)
                manager = autogen.GroupChatManager(groupchat=groupchat, **self.define_group_chat_manager_config())
                manager._print_received_message = lambda a, b: self.gpt_academic_print_override(agent_kwargs, a, b)
                manager.get_human_input = lambda a: self.gpt_academic_get_human_input(manager, a)
                if user_proxy is None:
                    raise Exception("user_proxy is not defined")
                user_proxy.initiate_chat(manager, message=input)
            except Exception:
                tb_str = "```\n" + trimmed_format_exc() + "```"
                self.child_conn.send(PipeCom("done", "AutoGen exe failed: \n\n" + tb_str))

    def define_group_chat_manager_config(self):
        raise NotImplementedError
