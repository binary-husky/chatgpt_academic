from crazy_functions.plugin_template.plugin_class_template import GptAcademicPluginTemplate, ArgProperty
from .PDF_Translate import 批量翻译PDF文档


class PDF_Tran(GptAcademicPluginTemplate):
    def __init__(self):
        """
        请注意`execute`会执行在不同的线程中，因此您在定义和使用类变量时，应当慎之又慎！
        """
        pass

    def define_arg_selection_menu(self):
        """
        定义插件的二级选项菜单
        """
        gui_definition = {
            "main_input":
                ArgProperty(title="PDF文件路径", description="未指定路径，请上传文件后，再点击该插件", default_value="", type="string").model_dump_json(), # 主输入，自动从输入框同步
            "additional_prompt":
                ArgProperty(title="额外提示词", description="例如：对专有名词、翻译语气等方面的要求", default_value="", type="string").model_dump_json(), # 高级参数输入区，自动同步
            "pdf_parse_method":
                ArgProperty(title="PDF解析方法", options=["DOC2X", "GROBID", "Classic"], description="无", default_value="GROBID", type="dropdown").model_dump_json(),
        }
        return gui_definition

    def execute(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
        """
        执行插件
        """
        main_input = plugin_kwargs["main_input"]
        additional_prompt = plugin_kwargs["additional_prompt"]
        pdf_parse_method = plugin_kwargs["pdf_parse_method"]
        yield from 批量翻译PDF文档(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request)