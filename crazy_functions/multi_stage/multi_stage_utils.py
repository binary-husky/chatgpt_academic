from pydantic import BaseModel, Field
from typing import List
from toolbox import update_ui_latest_msg, disable_auto_promotion
from toolbox import CatchException, update_ui, get_conf, select_api_key, get_log_folder
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.json_fns.pydantic_io import GptJsonIO, JsonStringError
import time
import pickle

def have_any_recent_upload_files(chatbot):
    _5min = 5 * 60
    if not chatbot: return False    # chatbot is None
    most_recent_uploaded = chatbot._cookies.get("most_recent_uploaded", None)
    if not most_recent_uploaded: return False   # most_recent_uploaded is None
    if time.time() - most_recent_uploaded["time"] < _5min: return True # most_recent_uploaded is new
    else: return False  # most_recent_uploaded is too old

class GptAcademicState():
    def __init__(self):
        self.reset()

    def reset(self):
        pass

    def dump_state(self, chatbot):
        chatbot._cookies['plugin_state'] = pickle.dumps(self)

    def set_state(self, chatbot, key, value):
        setattr(self, key, value)
        chatbot._cookies['plugin_state'] = pickle.dumps(self)

    def get_state(chatbot, cls=None):
        state = chatbot._cookies.get('plugin_state', None)
        if state is not None:   state = pickle.loads(state)
        elif cls is not None:   state = cls()
        else:                   state = GptAcademicState()
        state.chatbot = chatbot
        return state


class GptAcademicGameBaseState():
    """
    1. first init: __init__ ->
    """
    def init_game(self, chatbot, lock_plugin):
        self.plugin_name = None
        self.callback_fn = None
        self.delete_game = False
        self.step_cnt = 0

    def lock_plugin(self, chatbot):
        if self.callback_fn is None:
            raise ValueError("callback_fn is None")
        chatbot._cookies['lock_plugin'] = self.callback_fn
        self.dump_state(chatbot)

    def get_plugin_name(self):
        if self.plugin_name is None:
            raise ValueError("plugin_name is None")
        return self.plugin_name

    def dump_state(self, chatbot):
        chatbot._cookies[f'plugin_state/{self.get_plugin_name()}'] = pickle.dumps(self)

    def set_state(self, chatbot, key, value):
        setattr(self, key, value)
        chatbot._cookies[f'plugin_state/{self.get_plugin_name()}'] = pickle.dumps(self)

    @staticmethod
    def sync_state(chatbot, llm_kwargs, cls, plugin_name, callback_fn, lock_plugin=True):
        state = chatbot._cookies.get(f'plugin_state/{plugin_name}', None)
        if state is not None:
            state = pickle.loads(state)
        else:
            state = cls()
            state.init_game(chatbot, lock_plugin)
        state.plugin_name = plugin_name
        state.llm_kwargs = llm_kwargs
        state.chatbot = chatbot
        state.callback_fn = callback_fn
        return state

    def continue_game(self, prompt, chatbot, history):
        # 游戏主体
        yield from self.step(prompt, chatbot, history)
        self.step_cnt += 1
        # 保存状态，收尾
        self.dump_state(chatbot)
        # 如果游戏结束，清理
        if self.delete_game:
            chatbot._cookies['lock_plugin'] = None
            chatbot._cookies[f'plugin_state/{self.get_plugin_name()}'] = None
        yield from update_ui(chatbot=chatbot, history=history)
