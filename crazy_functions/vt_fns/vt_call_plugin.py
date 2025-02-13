from pydantic import BaseModel, Field
from typing import List
from toolbox import update_ui_latest_msg, disable_auto_promotion
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.json_fns.pydantic_io import GptJsonIO, JsonStringError
import copy, json, pickle, os, sys, time


def read_avail_plugin_enum():
    from crazy_functional import get_crazy_functions
    plugin_arr = get_crazy_functions()
    # remove plugins with out explanation
    plugin_arr = {k:v for k, v in plugin_arr.items() if ('Info' in v) and ('Function' in v)}
    plugin_arr_info = {"F_{:04d}".format(i):v["Info"] for i, v in enumerate(plugin_arr.values(), start=1)}
    plugin_arr_dict = {"F_{:04d}".format(i):v for i, v in enumerate(plugin_arr.values(), start=1)}
    plugin_arr_dict_parse = {"F_{:04d}".format(i):v for i, v in enumerate(plugin_arr.values(), start=1)}
    plugin_arr_dict_parse.update({f"F_{i}":v for i, v in enumerate(plugin_arr.values(), start=1)})
    prompt = json.dumps(plugin_arr_info, ensure_ascii=False, indent=2)
    prompt = "\n\nThe definition of PluginEnum:\nPluginEnum=" + prompt
    return prompt, plugin_arr_dict, plugin_arr_dict_parse

def wrap_code(txt):
    txt = txt.replace('```','')
    return f"\n```\n{txt}\n```\n"

def have_any_recent_upload_files(chatbot):
    _5min = 5 * 60
    if not chatbot: return False    # chatbot is None
    most_recent_uploaded = chatbot._cookies.get("most_recent_uploaded", None)
    if not most_recent_uploaded: return False   # most_recent_uploaded is None
    if time.time() - most_recent_uploaded["time"] < _5min: return True # most_recent_uploaded is new
    else: return False  # most_recent_uploaded is too old

def get_recent_file_prompt_support(chatbot):
    most_recent_uploaded = chatbot._cookies.get("most_recent_uploaded", None)
    path = most_recent_uploaded['path']
    prompt =   "\nAdditional Information:\n"
    prompt =   "In case that this plugin requires a path or a file as argument,"
    prompt += f"it is important for you to know that the user has recently uploaded a file, located at: `{path}`"
    prompt += f"Only use it when necessary, otherwise, you can ignore this file."
    return prompt

def get_inputs_show_user(inputs, plugin_arr_enum_prompt):
    # remove plugin_arr_enum_prompt from inputs string
    inputs_show_user = inputs.replace(plugin_arr_enum_prompt, "")
    inputs_show_user += plugin_arr_enum_prompt[:200] + '...'
    inputs_show_user += '\n...\n'
    inputs_show_user += '...\n'
    inputs_show_user += '...}'
    return inputs_show_user

def execute_plugin(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention):
    plugin_arr_enum_prompt, plugin_arr_dict, plugin_arr_dict_parse = read_avail_plugin_enum()
    class Plugin(BaseModel):
        plugin_selection: str = Field(description="The most related plugin from one of the PluginEnum.", default="F_0000")
        reason_of_selection: str = Field(description="The reason why you should select this plugin.", default="This plugin satisfy user requirement most")
    # ⭐ ⭐ ⭐ 选择插件
    yield from update_ui_latest_msg(lastmsg=f"正在执行任务: {txt}\n\n查找可用插件中...", chatbot=chatbot, history=history, delay=0)
    gpt_json_io = GptJsonIO(Plugin)
    gpt_json_io.format_instructions = "The format of your output should be a json that can be parsed by json.loads.\n"
    gpt_json_io.format_instructions += """Output example: {"plugin_selection":"F_1234", "reason_of_selection":"F_1234 plugin satisfy user requirement most"}\n"""
    gpt_json_io.format_instructions += "The plugins you are authorized to use are listed below:\n"
    gpt_json_io.format_instructions += plugin_arr_enum_prompt
    inputs = "Choose the correct plugin according to user requirements, the user requirement is: \n\n" + \
             ">> " + txt.rstrip('\n').replace('\n','\n>> ') + '\n\n' + gpt_json_io.format_instructions

    run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(
        inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
    try:
        gpt_reply = run_gpt_fn(inputs, "")
        plugin_sel = gpt_json_io.generate_output_auto_repair(gpt_reply, run_gpt_fn)
    except JsonStringError:
        msg = f"抱歉, {llm_kwargs['llm_model']}无法理解您的需求。"
        msg += "请求的Prompt为：\n" + wrap_code(get_inputs_show_user(inputs, plugin_arr_enum_prompt))
        msg += "语言模型回复为：\n" + wrap_code(gpt_reply)
        msg += "\n但您可以尝试再试一次\n"
        yield from update_ui_latest_msg(lastmsg=msg, chatbot=chatbot, history=history, delay=2)
        return
    if plugin_sel.plugin_selection not in plugin_arr_dict_parse:
        msg = f"抱歉, 找不到合适插件执行该任务, 或者{llm_kwargs['llm_model']}无法理解您的需求。"
        msg += f"语言模型{llm_kwargs['llm_model']}选择了不存在的插件：\n" + wrap_code(gpt_reply)
        msg += "\n但您可以尝试再试一次\n"
        yield from update_ui_latest_msg(lastmsg=msg, chatbot=chatbot, history=history, delay=2)
        return

    # ⭐ ⭐ ⭐ 确认插件参数
    if not have_any_recent_upload_files(chatbot):
        appendix_info = ""
    else:
        appendix_info = get_recent_file_prompt_support(chatbot)

    plugin = plugin_arr_dict_parse[plugin_sel.plugin_selection]
    yield from update_ui_latest_msg(lastmsg=f"正在执行任务: {txt}\n\n提取插件参数...", chatbot=chatbot, history=history, delay=0)
    class PluginExplicit(BaseModel):
        plugin_selection: str = plugin_sel.plugin_selection
        plugin_arg: str = Field(description="The argument of the plugin.", default="")
    gpt_json_io = GptJsonIO(PluginExplicit)
    gpt_json_io.format_instructions += "The information about this plugin is:" + plugin["Info"]
    inputs = f"A plugin named {plugin_sel.plugin_selection} is selected, " + \
             "you should extract plugin_arg from the user requirement, the user requirement is: \n\n" + \
             ">> " + (txt + appendix_info).rstrip('\n').replace('\n','\n>> ') + '\n\n' + \
             gpt_json_io.format_instructions
    run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(
        inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
    plugin_sel = gpt_json_io.generate_output_auto_repair(run_gpt_fn(inputs, ""), run_gpt_fn)


    # ⭐ ⭐ ⭐ 执行插件
    fn = plugin['Function']
    fn_name = fn.__name__
    msg = f'{llm_kwargs["llm_model"]}为您选择了插件: `{fn_name}`\n\n插件说明：{plugin["Info"]}\n\n插件参数：{plugin_sel.plugin_arg}\n\n假如偏离了您的要求，按停止键终止。'
    yield from update_ui_latest_msg(lastmsg=msg, chatbot=chatbot, history=history, delay=2)
    yield from fn(plugin_sel.plugin_arg, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, -1)
    return