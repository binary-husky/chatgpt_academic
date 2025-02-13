import os
from loguru import logger
from toolbox import CatchException, update_ui, gen_time_str, promote_file_to_downloadzone
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from crazy_functions.crazy_utils import input_clipping

def inspect_dependency(chatbot, history):
    # 尝试导入依赖，如果缺少依赖，则给出安装建议
    try:
        import manim
        return True
    except:
        chatbot.append(["导入依赖失败", "使用该模块需要额外依赖，安装方法:```pip install manim manimgl```"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面
        return False

def eval_manim(code):
    import subprocess, sys, os, shutil

    with open('gpt_log/MyAnimation.py', 'w', encoding='utf8') as f:
        f.write(code)

    def get_class_name(class_string):
        import re
        # Use regex to extract the class name
        class_name = re.search(r'class (\w+)\(', class_string).group(1)
        return class_name

    class_name = get_class_name(code)

    try:
        time_str = gen_time_str()
        subprocess.check_output([sys.executable, '-c', f"from gpt_log.MyAnimation import {class_name}; {class_name}().render()"])
        shutil.move(f'media/videos/1080p60/{class_name}.mp4', f'gpt_log/{class_name}-{time_str}.mp4')
        return f'gpt_log/{time_str}.mp4'
    except subprocess.CalledProcessError as e:
        output = e.output.decode()
        logger.error(f"Command returned non-zero exit status {e.returncode}: {output}.")
        return f"Evaluating python script failed: {e.output}."
    except:
        logger.error('generating mp4 failed')
        return "Generating mp4 failed."


def get_code_block(reply):
    import re
    pattern = r"```([\s\S]*?)```" # regex pattern to match code blocks
    matches = re.findall(pattern, reply) # find all code blocks in text
    if len(matches) != 1:
        raise RuntimeError("GPT is not generating proper code.")
    return matches[0].strip('python') #  code block

@CatchException
def 动画生成(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
    """
    txt             输入栏用户输入的文本，例如需要翻译的一段话，再例如一个包含了待处理文件的路径
    llm_kwargs      gpt模型参数，如温度和top_p等，一般原样传递下去就行
    plugin_kwargs   插件模型的参数，暂时没有用武之地
    chatbot         聊天显示框的句柄，用于显示给用户
    history         聊天历史，前情提要
    system_prompt   给gpt的静默提醒
    user_request    当前用户的请求信息（IP地址等）
    """
    # 清空历史，以免输入溢出
    history = []

    # 基本信息：功能、贡献者
    chatbot.append([
        "函数插件功能？",
        "生成数学动画, 此插件处于开发阶段, 建议暂时不要使用, 作者: binary-husky, 插件初始化中 ..."
    ])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    # 尝试导入依赖, 如果缺少依赖, 则给出安装建议
    dep_ok = yield from inspect_dependency(chatbot=chatbot, history=history) # 刷新界面
    if not dep_ok: return

    # 输入
    i_say = f'Generate a animation to show: ' + txt
    demo = ["Here is some examples of manim", examples_of_manim()]
    _, demo = input_clipping(inputs="", history=demo, max_token_limit=2560)
    # 开始
    gpt_say = yield from request_gpt_model_in_new_thread_with_ui_alive(
        inputs=i_say, inputs_show_user=i_say,
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=demo,
        sys_prompt=
        r"Write a animation script with 3blue1brown's manim. "+
        r"Please begin with `from manim import *`. " +
        r"Answer me with a code block wrapped by ```."
    )
    chatbot.append(["开始生成动画", "..."])
    history.extend([i_say, gpt_say])
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新

    # 将代码转为动画
    code = get_code_block(gpt_say)
    res = eval_manim(code)

    chatbot.append(("生成的视频文件路径", res))
    if os.path.exists(res):
        promote_file_to_downloadzone(res, chatbot=chatbot)
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面 # 界面更新

# 在这里放一些网上搜集的demo，辅助gpt生成代码
def examples_of_manim():
    return r"""


```

class MovingGroupToDestination(Scene):
    def construct(self):
        group = VGroup(Dot(LEFT), Dot(ORIGIN), Dot(RIGHT, color=RED), Dot(2 * RIGHT)).scale(1.4)
        dest = Dot([4, 3, 0], color=YELLOW)
        self.add(group, dest)
        self.play(group.animate.shift(dest.get_center() - group[2].get_center()))
        self.wait(0.5)

```


```

class LatexWithMovingFramebox(Scene):
    def construct(self):
        text=MathTex(
            "\\frac{d}{dx}f(x)g(x)=","f(x)\\frac{d}{dx}g(x)","+",
            "g(x)\\frac{d}{dx}f(x)"
        )
        self.play(Write(text))
        framebox1 = SurroundingRectangle(text[1], buff = .1)
        framebox2 = SurroundingRectangle(text[3], buff = .1)
        self.play(
            Create(framebox1),
        )
        self.wait()
        self.play(
            ReplacementTransform(framebox1,framebox2),
        )
        self.wait()

```



```

class PointWithTrace(Scene):
    def construct(self):
        path = VMobject()
        dot = Dot()
        path.set_points_as_corners([dot.get_center(), dot.get_center()])
        def update_path(path):
            previous_path = path.copy()
            previous_path.add_points_as_corners([dot.get_center()])
            path.become(previous_path)
        path.add_updater(update_path)
        self.add(path, dot)
        self.play(Rotating(dot, radians=PI, about_point=RIGHT, run_time=2))
        self.wait()
        self.play(dot.animate.shift(UP))
        self.play(dot.animate.shift(LEFT))
        self.wait()

```

```

# do not use get_graph, this function is deprecated

class ExampleFunctionGraph(Scene):
    def construct(self):
        cos_func = FunctionGraph(
            lambda t: np.cos(t) + 0.5 * np.cos(7 * t) + (1 / 7) * np.cos(14 * t),
            color=RED,
        )

        sin_func_1 = FunctionGraph(
            lambda t: np.sin(t) + 0.5 * np.sin(7 * t) + (1 / 7) * np.sin(14 * t),
            color=BLUE,
        )

        sin_func_2 = FunctionGraph(
            lambda t: np.sin(t) + 0.5 * np.sin(7 * t) + (1 / 7) * np.sin(14 * t),
            x_range=[-4, 4],
            color=GREEN,
        ).move_to([0, 1, 0])

        self.add(cos_func, sin_func_1, sin_func_2)

```
"""