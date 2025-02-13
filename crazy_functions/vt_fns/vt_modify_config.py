from pydantic import BaseModel, Field
from typing import List
from toolbox import update_ui_latest_msg, get_conf
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.json_fns.pydantic_io import GptJsonIO
import copy, json, pickle, os, sys


def modify_configuration_hot(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention):
    ALLOW_RESET_CONFIG = get_conf('ALLOW_RESET_CONFIG')
    if not ALLOW_RESET_CONFIG:
        yield from update_ui_latest_msg(
            lastmsg=f"当前配置不允许被修改！如需激活本功能，请在config.py中设置ALLOW_RESET_CONFIG=True后重启软件。",
            chatbot=chatbot, history=history, delay=2
        )
        return

    # ⭐ ⭐ ⭐ 读取可配置项目条目
    names = {}
    from enum import Enum
    import config
    for k, v in config.__dict__.items():
        if k.startswith('__'): continue
        names.update({k:k})
        # if len(names) > 20: break   # 限制最多前10个配置项，如果太多了会导致gpt无法理解

    ConfigOptions = Enum('ConfigOptions', names)
    class ModifyConfigurationIntention(BaseModel):
        which_config_to_modify: ConfigOptions = Field(description="the name of the configuration to modify, you must choose from one of the ConfigOptions enum.", default=None)
        new_option_value: str = Field(description="the new value of the option", default=None)

    # ⭐ ⭐ ⭐ 分析用户意图
    yield from update_ui_latest_msg(lastmsg=f"正在执行任务: {txt}\n\n读取新配置中", chatbot=chatbot, history=history, delay=0)
    gpt_json_io = GptJsonIO(ModifyConfigurationIntention)
    inputs = "Analyze how to change configuration according to following user input, answer me with json: \n\n" + \
             ">> " + txt.rstrip('\n').replace('\n','\n>> ') + '\n\n' + \
             gpt_json_io.format_instructions

    run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(
        inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
    user_intention = gpt_json_io.generate_output_auto_repair(run_gpt_fn(inputs, ""), run_gpt_fn)

    explicit_conf = user_intention.which_config_to_modify.value

    ok = (explicit_conf in txt)
    if ok:
        yield from update_ui_latest_msg(
            lastmsg=f"正在执行任务: {txt}\n\n新配置{explicit_conf}={user_intention.new_option_value}",
            chatbot=chatbot, history=history, delay=1
        )
        yield from update_ui_latest_msg(
            lastmsg=f"正在执行任务: {txt}\n\n新配置{explicit_conf}={user_intention.new_option_value}\n\n正在修改配置中",
            chatbot=chatbot, history=history, delay=2
        )

        # ⭐ ⭐ ⭐ 立即应用配置
        from toolbox import set_conf
        set_conf(explicit_conf, user_intention.new_option_value)

        yield from update_ui_latest_msg(
            lastmsg=f"正在执行任务: {txt}\n\n配置修改完成，重新页面即可生效。", chatbot=chatbot, history=history, delay=1
        )
    else:
        yield from update_ui_latest_msg(
            lastmsg=f"失败，如果需要配置{explicit_conf}，您需要明确说明并在指令中提到它。", chatbot=chatbot, history=history, delay=5
        )

def modify_configuration_reboot(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention):
    ALLOW_RESET_CONFIG = get_conf('ALLOW_RESET_CONFIG')
    if not ALLOW_RESET_CONFIG:
        yield from update_ui_latest_msg(
            lastmsg=f"当前配置不允许被修改！如需激活本功能，请在config.py中设置ALLOW_RESET_CONFIG=True后重启软件。",
            chatbot=chatbot, history=history, delay=2
        )
        return

    yield from modify_configuration_hot(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_intention)
    yield from update_ui_latest_msg(
        lastmsg=f"正在执行任务: {txt}\n\n配置修改完成，五秒后即将重启！若出现报错请无视即可。", chatbot=chatbot, history=history, delay=5
    )
    os.execl(sys.executable, sys.executable, *sys.argv)
