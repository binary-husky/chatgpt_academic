from toolbox import CatchException, update_ui, update_ui_latest_msg
from crazy_functions.multi_stage.multi_stage_utils import GptAcademicGameBaseState
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.game_fns.game_utils import get_code_block, is_same_thing
import random


class MiniGame_ASCII_Art(GptAcademicGameBaseState):
    def step(self, prompt, chatbot, history):
        if self.step_cnt == 0:
            chatbot.append(["我画你猜（动物）", "请稍等..."])
        else:
            if prompt.strip() == 'exit':
                self.delete_game = True
                yield from update_ui_latest_msg(lastmsg=f"谜底是{self.obj}，游戏结束。", chatbot=chatbot, history=history, delay=0.)
                return
            chatbot.append([prompt, ""])
        yield from update_ui(chatbot=chatbot, history=history)

        if self.step_cnt == 0:
            self.lock_plugin(chatbot)
            self.cur_task = 'draw'

        if self.cur_task == 'draw':
            avail_obj = ["狗","猫","鸟","鱼","老鼠","蛇"]
            self.obj = random.choice(avail_obj)
            inputs = "I want to play a game called Guess the ASCII art. You can draw the ASCII art and I will try to guess it. " + \
                f"This time you draw a {self.obj}. Note that you must not indicate what you have draw in the text, and you should only produce the ASCII art wrapped by ```. "
            raw_res = predict_no_ui_long_connection(inputs=inputs, llm_kwargs=self.llm_kwargs, history=[], sys_prompt="")
            self.cur_task = 'identify user guess'
            res = get_code_block(raw_res)
            history += ['', f'the answer is {self.obj}', inputs, res]
            yield from update_ui_latest_msg(lastmsg=res, chatbot=chatbot, history=history, delay=0.)

        elif self.cur_task == 'identify user guess':
            if is_same_thing(self.obj, prompt, self.llm_kwargs):
                self.delete_game = True
                yield from update_ui_latest_msg(lastmsg="你猜对了！", chatbot=chatbot, history=history, delay=0.)
            else:
                self.cur_task = 'identify user guess'
                yield from update_ui_latest_msg(lastmsg="猜错了，再试试，输入“exit”获取答案。", chatbot=chatbot, history=history, delay=0.)