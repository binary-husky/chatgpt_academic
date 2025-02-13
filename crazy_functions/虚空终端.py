"""
Explanation of the Void Terminal Plugin:

Please describe in natural language what you want to do.

1. You can open the plugin's dropdown menu to explore various capabilities of this project, and then describe your needs in natural language, for example:
- "Please call the plugin to translate a PDF paper for me. I just uploaded the paper to the upload area."
- "Please use the plugin to translate a PDF paper, with the address being https://www.nature.com/articles/s41586-019-1724-z.pdf."
- "Generate an image with blooming flowers and lush green grass using the plugin."
- "Translate the README using the plugin. The GitHub URL is https://github.com/facebookresearch/co-tracker."
- "Translate an Arxiv paper for me. The Arxiv ID is 1812.10695. Remember to use the plugin and don't do it manually!"
- "I don't like the current interface color. Modify the configuration and change the theme to THEME="High-Contrast"."
- "Could you please explain the structure of the Transformer network?"

2. If you use keywords like "call the plugin xxx", "modify the configuration xxx", "please", etc., your intention can be recognized more accurately.

3. Your intention can be recognized more accurately when using powerful models like GPT4. This plugin is relatively new, so please feel free to provide feedback on GitHub.

4. Now, if you need to process a file, please upload the file (drag the file to the file upload area) or describe the path to the file.

5. If you don't need to upload a file, you can simply repeat your command again.
"""
explain_msg = """
## 虚空终端插件说明:

1. 请用**自然语言**描述您需要做什么。例如：
    - 「请调用插件，为我翻译PDF论文，论文我刚刚放到上传区了」
    - 「请调用插件翻译PDF论文，地址为https://openreview.net/pdf?id=rJl0r3R9KX」
    - 「把Arxiv论文翻译成中文PDF，arxiv论文的ID是1812.10695，记得用插件！」
    - 「生成一张图片，图中鲜花怒放，绿草如茵，用插件实现」
    - 「用插件翻译README，Github网址是https://github.com/facebookresearch/co-tracker」
    - 「我不喜欢当前的界面颜色，修改配置，把主题THEME更换为THEME="High-Contrast"」
    - 「请调用插件，解析python源代码项目，代码我刚刚打包拖到上传区了」
    - 「请问Transformer网络的结构是怎样的？」

2. 您可以打开插件下拉菜单以了解本项目的各种能力。

3. 如果您使用「调用插件xxx」、「修改配置xxx」、「请问」等关键词，您的意图可以被识别的更准确。

4. 建议使用 GPT3.5 或更强的模型，弱模型可能无法理解您的想法。该插件诞生时间不长，欢迎您前往Github反馈问题。

5. 现在，如果需要处理文件，请您上传文件（将文件拖动到文件上传区），或者描述文件所在的路径。

6. 如果不需要上传文件，现在您只需要再次重复一次您的指令即可。
"""

from pydantic import BaseModel, Field
from typing import List
from toolbox import CatchException, update_ui, is_the_upload_folder
from toolbox import update_ui_latest_msg, disable_auto_promotion
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from crazy_functions.crazy_utils import input_clipping
from crazy_functions.json_fns.pydantic_io import GptJsonIO, JsonStringError
from crazy_functions.vt_fns.vt_state import VoidTerminalState
from crazy_functions.vt_fns.vt_modify_config import modify_configuration_hot
from crazy_functions.vt_fns.vt_modify_config import modify_configuration_reboot
from crazy_functions.vt_fns.vt_call_plugin import execute_plugin

class UserIntention(BaseModel):
    user_prompt: str = Field(description="the content of user input", default="")
    intention_type: str = Field(description="the type of user intention, choose from ['ModifyConfiguration', 'ExecutePlugin', 'Chat']", default="ExecutePlugin")
    user_provide_file: bool = Field(description="whether the user provides a path to a file", default=False)
    user_provide_url: bool = Field(description="whether the user provides a url", default=False)


def chat(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention):
    gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=txt, inputs_show_user=txt,
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=[],
        sys_prompt=system_prompt
    )
    chatbot[-1] = [txt, gpt_say]
    history.extend([txt, gpt_say])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
    pass


explain_intention_to_user = {
    'Chat': "聊天对话",
    'ExecutePlugin': "调用插件",
    'ModifyConfiguration': "修改配置",
}


def analyze_intention_with_simple_rules(txt):
    user_intention = UserIntention()
    user_intention.user_prompt = txt
    is_certain = False

    if '请问' in txt:
        is_certain = True
        user_intention.intention_type = 'Chat'

    if '用插件' in txt:
        is_certain = True
        user_intention.intention_type = 'ExecutePlugin'

    if '修改配置' in txt:
        is_certain = True
        user_intention.intention_type = 'ModifyConfiguration'

    return is_certain, user_intention


@CatchException
def 虚空终端(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    disable_auto_promotion(chatbot=chatbot)
    # 获取当前虚空终端状态
    state = VoidTerminalState.get_state(chatbot)
    appendix_msg = ""

    # 用简单的关键词检测用户意图
    is_certain, _ = analyze_intention_with_simple_rules(txt)
    if is_the_upload_folder(txt):
        state.set_state(chatbot=chatbot, key='has_provided_explanation', value=False)
        appendix_msg = "\n\n**很好，您已经上传了文件**，现在请您描述您的需求。"

    if is_certain or (state.has_provided_explanation):
        # 如果意图明确，跳过提示环节
        state.set_state(chatbot=chatbot, key='has_provided_explanation', value=True)
        state.unlock_plugin(chatbot=chatbot)
        yield from update_ui(chatbot=chatbot, history=history)
        yield from 虚空终端主路由(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request)
        return
    else:
        # 如果意图模糊，提示
        state.set_state(chatbot=chatbot, key='has_provided_explanation', value=True)
        state.lock_plugin(chatbot=chatbot)
        chatbot.append(("虚空终端状态:", explain_msg+appendix_msg))
        yield from update_ui(chatbot=chatbot, history=history)
        return



def 虚空终端主路由(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    history = []
    chatbot.append(("虚空终端状态: ", f"正在执行任务: {txt}"))
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # ⭐ ⭐ ⭐ 分析用户意图
    is_certain, user_intention = analyze_intention_with_simple_rules(txt)
    if not is_certain:
        yield from update_ui_latest_msg(
            lastmsg=f"正在执行任务: {txt}\n\n分析用户意图中", chatbot=chatbot, history=history, delay=0)
        gpt_json_io = GptJsonIO(UserIntention)
        rf_req = "\nchoose from ['ModifyConfiguration', 'ExecutePlugin', 'Chat']"
        inputs = "Analyze the intention of the user according to following user input: \n\n" + \
            ">> " + (txt+rf_req).rstrip('\n').replace('\n','\n>> ') + '\n\n' + gpt_json_io.format_instructions
        run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(
            inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
        analyze_res = run_gpt_fn(inputs, "")
        try:
            user_intention = gpt_json_io.generate_output_auto_repair(analyze_res, run_gpt_fn)
            lastmsg=f"正在执行任务: {txt}\n\n用户意图理解: 意图={explain_intention_to_user[user_intention.intention_type]}",
        except JsonStringError as e:
            yield from update_ui_latest_msg(
                lastmsg=f"正在执行任务: {txt}\n\n用户意图理解: 失败 当前语言模型（{llm_kwargs['llm_model']}）不能理解您的意图", chatbot=chatbot, history=history, delay=0)
            return
    else:
        pass

    yield from update_ui_latest_msg(
        lastmsg=f"正在执行任务: {txt}\n\n用户意图理解: 意图={explain_intention_to_user[user_intention.intention_type]}",
        chatbot=chatbot, history=history, delay=0)

    # 用户意图: 修改本项目的配置
    if user_intention.intention_type == 'ModifyConfiguration':
        yield from modify_configuration_reboot(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention)

    # 用户意图: 调度插件
    if user_intention.intention_type == 'ExecutePlugin':
        yield from execute_plugin(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention)

    # 用户意图: 聊天
    if user_intention.intention_type == 'Chat':
        yield from chat(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention)

    return

