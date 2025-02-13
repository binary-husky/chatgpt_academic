prompts_hs = """ 请以“{headstart}”为开头，编写一个小说的第一幕。

- 尽量短，不要包含太多情节，因为你接下来将会与用户互动续写下面的情节，要留出足够的互动空间。
- 出现人物时，给出人物的名字。
- 积极地运用环境描写、人物描写等手法，让读者能够感受到你的故事世界。
- 积极地运用修辞手法，比如比喻、拟人、排比、对偶、夸张等等。
- 字数要求：第一幕的字数少于300字，且少于2个段落。
"""

prompts_interact = """ 小说的前文回顾：
「
{previously_on_story}
」

你是一个作家，根据以上的情节，给出4种不同的后续剧情发展方向，每个发展方向都精明扼要地用一句话说明。稍后，我将在这4个选择中，挑选一种剧情发展。

输出格式例如：
1. 后续剧情发展1
2. 后续剧情发展2
3. 后续剧情发展3
4. 后续剧情发展4
"""


prompts_resume = """小说的前文回顾：
「
{previously_on_story}
」

你是一个作家，我们正在互相讨论，确定后续剧情的发展。
在以下的剧情发展中，
「
{choice}
」
我认为更合理的是：{user_choice}。
请在前文的基础上（不要重复前文），围绕我选定的剧情情节，编写小说的下一幕。

- 禁止杜撰不符合我选择的剧情。
- 尽量短，不要包含太多情节，因为你接下来将会与用户互动续写下面的情节，要留出足够的互动空间。
- 不要重复前文。
- 出现人物时，给出人物的名字。
- 积极地运用环境描写、人物描写等手法，让读者能够感受到你的故事世界。
- 积极地运用修辞手法，比如比喻、拟人、排比、对偶、夸张等等。
- 小说的下一幕字数少于300字，且少于2个段落。
"""


prompts_terminate = """小说的前文回顾：
「
{previously_on_story}
」

你是一个作家，我们正在互相讨论，确定后续剧情的发展。
现在，故事该结束了，我认为最合理的故事结局是：{user_choice}。

请在前文的基础上（不要重复前文），编写小说的最后一幕。

- 不要重复前文。
- 出现人物时，给出人物的名字。
- 积极地运用环境描写、人物描写等手法，让读者能够感受到你的故事世界。
- 积极地运用修辞手法，比如比喻、拟人、排比、对偶、夸张等等。
- 字数要求：最后一幕的字数少于1000字。
"""


from toolbox import CatchException, update_ui, update_ui_latest_msg
from crazy_functions.multi_stage.multi_stage_utils import GptAcademicGameBaseState
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.game_fns.game_utils import get_code_block, is_same_thing
import random


class MiniGame_ResumeStory(GptAcademicGameBaseState):
    story_headstart = [
        '先行者知道，他现在是全宇宙中唯一的一个人了。',
        '深夜，一个年轻人穿过天安门广场向纪念堂走去。在二十二世纪编年史中，计算机把他的代号定为M102。',
        '他知道，这最后一课要提前讲了。又一阵剧痛从肝部袭来，几乎使他晕厥过去。',
        '在距地球五万光年的远方，在银河系的中心，一场延续了两万年的星际战争已接近尾声。那里的太空中渐渐隐现出一个方形区域，仿佛灿烂的群星的背景被剪出一个方口。',
        '伊依一行三人乘坐一艘游艇在南太平洋上做吟诗航行，他们的目的地是南极，如果几天后能顺利到达那里，他们将钻出地壳去看诗云。',
        '很多人生来就会莫名其妙地迷上一样东西，仿佛他的出生就是要和这东西约会似的，正是这样，圆圆迷上了肥皂泡。'
    ]


    def begin_game_step_0(self, prompt, chatbot, history):
        # init game at step 0
        self.headstart = random.choice(self.story_headstart)
        self.story = []
        chatbot.append(["互动写故事", f"这次的故事开头是：{self.headstart}"])
        self.sys_prompt_ = '你是一个想象力丰富的杰出作家。正在与你的朋友互动，一起写故事，因此你每次写的故事段落应少于300字（结局除外）。'


    def generate_story_image(self, story_paragraph):
        try:
            from crazy_functions.Image_Generate import gen_image
            prompt_ = predict_no_ui_long_connection(inputs=story_paragraph, llm_kwargs=self.llm_kwargs, history=[], sys_prompt='你需要根据用户给出的小说段落，进行简短的环境描写。要求：80字以内。')
            image_url, image_path = gen_image(self.llm_kwargs, prompt_, '512x512', model="dall-e-2", quality='standard', style='natural')
            return f'<br/><div align="center"><img src="file={image_path}"></div>'
        except:
            return ''

    def step(self, prompt, chatbot, history):

        """
        首先，处理游戏初始化等特殊情况
        """
        if self.step_cnt == 0:
            self.begin_game_step_0(prompt, chatbot, history)
            self.lock_plugin(chatbot)
            self.cur_task = 'head_start'
        else:
            if prompt.strip() == 'exit' or prompt.strip() == '结束剧情':
                # should we terminate game here?
                self.delete_game = True
                yield from update_ui_latest_msg(lastmsg=f"游戏结束。", chatbot=chatbot, history=history, delay=0.)
                return
            if '剧情收尾' in prompt:
                self.cur_task = 'story_terminate'
            # # well, game resumes
            # chatbot.append([prompt, ""])
        # update ui, don't keep the user waiting
        yield from update_ui(chatbot=chatbot, history=history)


        """
        处理游戏的主体逻辑
        """
        if self.cur_task == 'head_start':
            """
            这是游戏的第一步
            """
            inputs_ = prompts_hs.format(headstart=self.headstart)
            history_ = []
            story_paragraph = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs_, '故事开头', self.llm_kwargs,
                chatbot, history_, self.sys_prompt_
            )
            self.story.append(story_paragraph)
            # # 配图
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>正在生成插图中 ...', chatbot=chatbot, history=history, delay=0.)
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>'+ self.generate_story_image(story_paragraph), chatbot=chatbot, history=history, delay=0.)

            # # 构建后续剧情引导
            previously_on_story = ""
            for s in self.story:
                previously_on_story += s + '\n'
            inputs_ = prompts_interact.format(previously_on_story=previously_on_story)
            history_ = []
            self.next_choices = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs_, '请在以下几种故事走向中，选择一种（当然，您也可以选择给出其他故事走向）：', self.llm_kwargs,
                chatbot,
                history_,
                self.sys_prompt_
            )
            self.cur_task = 'user_choice'


        elif self.cur_task == 'user_choice':
            """
            根据用户的提示，确定故事的下一步
            """
            if '请在以下几种故事走向中，选择一种' in chatbot[-1][0]: chatbot.pop(-1)
            previously_on_story = ""
            for s in self.story:
                previously_on_story += s + '\n'
            inputs_ = prompts_resume.format(previously_on_story=previously_on_story, choice=self.next_choices, user_choice=prompt)
            history_ = []
            story_paragraph = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs_, f'下一段故事（您的选择是：{prompt}）。', self.llm_kwargs,
                chatbot, history_, self.sys_prompt_
            )
            self.story.append(story_paragraph)
            # # 配图
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>正在生成插图中 ...', chatbot=chatbot, history=history, delay=0.)
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>'+ self.generate_story_image(story_paragraph), chatbot=chatbot, history=history, delay=0.)

            # # 构建后续剧情引导
            previously_on_story = ""
            for s in self.story:
                previously_on_story += s + '\n'
            inputs_ = prompts_interact.format(previously_on_story=previously_on_story)
            history_ = []
            self.next_choices = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs_,
                '请在以下几种故事走向中，选择一种。当然，您也可以给出您心中的其他故事走向。另外，如果您希望剧情立即收尾，请输入剧情走向，并以“剧情收尾”四个字提示程序。', self.llm_kwargs,
                chatbot,
                history_,
                self.sys_prompt_
            )
            self.cur_task = 'user_choice'


        elif self.cur_task == 'story_terminate':
            """
            根据用户的提示，确定故事的结局
            """
            previously_on_story = ""
            for s in self.story:
                previously_on_story += s + '\n'
            inputs_ = prompts_terminate.format(previously_on_story=previously_on_story, user_choice=prompt)
            history_ = []
            story_paragraph = yield from request_gpt_model_in_new_thread_with_ui_alive(
                inputs_, f'故事收尾（您的选择是：{prompt}）。', self.llm_kwargs,
                chatbot, history_, self.sys_prompt_
            )
            # # 配图
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>正在生成插图中 ...', chatbot=chatbot, history=history, delay=0.)
            yield from update_ui_latest_msg(lastmsg=story_paragraph + '<br/>'+ self.generate_story_image(story_paragraph), chatbot=chatbot, history=history, delay=0.)

            # terminate game
            self.delete_game = True
            return
