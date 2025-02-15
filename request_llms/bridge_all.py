
"""
    该文件中主要包含2个函数，是所有LLM的通用接口，它们会继续向下调用更底层的LLM模型，处理多模型并行等细节

    不具备多线程能力的函数：正常对话时使用，具备完备的交互功能，不可多线程
    1. predict(...)

    具备多线程调用能力的函数：在函数插件中被调用，灵活而简洁
    2. predict_no_ui_long_connection(...)
"""
import tiktoken, copy, re
from loguru import logger
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from toolbox import get_conf, trimmed_format_exc, apply_gpt_academic_string_mask, read_one_api_model_name

from .bridge_chatgpt import predict_no_ui_long_connection as chatgpt_noui
from .bridge_chatgpt import predict as chatgpt_ui

from .bridge_chatgpt_vision import predict_no_ui_long_connection as chatgpt_vision_noui
from .bridge_chatgpt_vision import predict as chatgpt_vision_ui

from .bridge_chatglm import predict_no_ui_long_connection as chatglm_noui
from .bridge_chatglm import predict as chatglm_ui

from .bridge_chatglm3 import predict_no_ui_long_connection as chatglm3_noui
from .bridge_chatglm3 import predict as chatglm3_ui

from .bridge_chatglm4 import predict_no_ui_long_connection as chatglm4_noui
from .bridge_chatglm4 import predict as chatglm4_ui

from .bridge_qianfan import predict_no_ui_long_connection as qianfan_noui
from .bridge_qianfan import predict as qianfan_ui

from .bridge_google_gemini import predict as genai_ui
from .bridge_google_gemini import predict_no_ui_long_connection  as genai_noui

from .bridge_zhipu import predict_no_ui_long_connection as zhipu_noui
from .bridge_zhipu import predict as zhipu_ui

from .bridge_taichu import predict_no_ui_long_connection as taichu_noui
from .bridge_taichu import predict as taichu_ui

from .bridge_cohere import predict as cohere_ui
from .bridge_cohere import predict_no_ui_long_connection as cohere_noui

from .oai_std_model_template import get_predict_function

colors = ['#FF00FF', '#00FFFF', '#FF0000', '#990099', '#009999', '#990044']

class LazyloadTiktoken(object):
    def __init__(self, model):
        self.model = model

    @staticmethod
    @lru_cache(maxsize=128)
    def get_encoder(model):
        logger.info('正在加载tokenizer，如果是第一次运行，可能需要一点时间下载参数')
        tmp = tiktoken.encoding_for_model(model)
        logger.info('加载tokenizer完毕')
        return tmp

    def encode(self, *args, **kwargs):
        encoder = self.get_encoder(self.model)
        return encoder.encode(*args, **kwargs)

    def decode(self, *args, **kwargs):
        encoder = self.get_encoder(self.model)
        return encoder.decode(*args, **kwargs)

# Endpoint 重定向
API_URL_REDIRECT, AZURE_ENDPOINT, AZURE_ENGINE = get_conf("API_URL_REDIRECT", "AZURE_ENDPOINT", "AZURE_ENGINE")
openai_endpoint = "https://api.openai.com/v1/chat/completions"
api2d_endpoint = "https://openai.api2d.net/v1/chat/completions"
newbing_endpoint = "wss://sydney.bing.com/sydney/ChatHub"
gemini_endpoint = "https://generativelanguage.googleapis.com/v1beta/models"
claude_endpoint = "https://api.anthropic.com/v1/messages"
cohere_endpoint = "https://api.cohere.ai/v1/chat"
ollama_endpoint = "http://localhost:11434/api/chat"
yimodel_endpoint = "https://api.lingyiwanwu.com/v1/chat/completions"
deepseekapi_endpoint = "https://api.deepseek.com/v1/chat/completions"
grok_model_endpoint = "https://api.x.ai/v1/chat/completions"
siliconflow_endpoint = "https://api.siliconflow.cn/v1/chat/completions"

if not AZURE_ENDPOINT.endswith('/'): AZURE_ENDPOINT += '/'
azure_endpoint = AZURE_ENDPOINT + f'openai/deployments/{AZURE_ENGINE}/chat/completions?api-version=2023-05-15'
# 兼容旧版的配置
try:
    API_URL = get_conf("API_URL")
    if API_URL != "https://api.openai.com/v1/chat/completions":
        openai_endpoint = API_URL
        logger.warning("警告！API_URL配置选项将被弃用，请更换为API_URL_REDIRECT配置")
except:
    pass
# 新版配置
if openai_endpoint in API_URL_REDIRECT: openai_endpoint = API_URL_REDIRECT[openai_endpoint]
if api2d_endpoint in API_URL_REDIRECT: api2d_endpoint = API_URL_REDIRECT[api2d_endpoint]
if newbing_endpoint in API_URL_REDIRECT: newbing_endpoint = API_URL_REDIRECT[newbing_endpoint]
if gemini_endpoint in API_URL_REDIRECT: gemini_endpoint = API_URL_REDIRECT[gemini_endpoint]
if claude_endpoint in API_URL_REDIRECT: claude_endpoint = API_URL_REDIRECT[claude_endpoint]
if cohere_endpoint in API_URL_REDIRECT: cohere_endpoint = API_URL_REDIRECT[cohere_endpoint]
if ollama_endpoint in API_URL_REDIRECT: ollama_endpoint = API_URL_REDIRECT[ollama_endpoint]
if yimodel_endpoint in API_URL_REDIRECT: yimodel_endpoint = API_URL_REDIRECT[yimodel_endpoint]
if deepseekapi_endpoint in API_URL_REDIRECT: deepseekapi_endpoint = API_URL_REDIRECT[deepseekapi_endpoint]
if grok_model_endpoint in API_URL_REDIRECT: grok_model_endpoint = API_URL_REDIRECT[grok_model_endpoint]
if siliconflow_endpoint in API_URL_REDIRECT: siliconflow_endpoint = API_URL_REDIRECT[siliconflow_endpoint]


# 获取tokenizer
tokenizer_gpt35 = LazyloadTiktoken("gpt-3.5-turbo")
tokenizer_gpt4 = LazyloadTiktoken("gpt-4")
get_token_num_gpt35 = lambda txt: len(tokenizer_gpt35.encode(txt, disallowed_special=()))
get_token_num_gpt4 = lambda txt: len(tokenizer_gpt4.encode(txt, disallowed_special=()))


# 开始初始化模型
AVAIL_LLM_MODELS, LLM_MODEL = get_conf("AVAIL_LLM_MODELS", "LLM_MODEL")
AVAIL_LLM_MODELS = AVAIL_LLM_MODELS + [LLM_MODEL]
# -=-=-=-=-=-=- 以下这部分是最早加入的最稳定的模型 -=-=-=-=-=-=-
model_info = {
    # openai
    "gpt-3.5-turbo": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 16385,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "taichu": {
        "fn_with_ui": taichu_ui,
        "fn_without_ui": taichu_noui,
        "endpoint": openai_endpoint,
        "max_token": 4096,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-3.5-turbo-16k": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 16385,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-3.5-turbo-0613": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 4096,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-3.5-turbo-16k-0613": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 16385,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-3.5-turbo-1106": { #16k
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 16385,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-3.5-turbo-0125": { #16k
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 16385,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "gpt-4": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 8192,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-32k": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 32768,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4o": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "has_multimodal_capacity": True,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4o-mini": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "has_multimodal_capacity": True,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "chatgpt-4o-latest": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "has_multimodal_capacity": True,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4o-2024-05-13": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "has_multimodal_capacity": True,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-turbo-preview": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-1106-preview": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-0125-preview": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "o1-preview": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
        "openai_disable_system_prompt": True,
        "openai_disable_stream": True,
        "openai_force_temperature_one": True,
    },

    "o1-mini": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
        "openai_disable_system_prompt": True,
        "openai_disable_stream": True,
        "openai_force_temperature_one": True,
    },

    "o1-2024-12-17": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 200000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
        "openai_disable_system_prompt": True,
        "openai_disable_stream": True,
        "openai_force_temperature_one": True,
    },

    "o1": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 200000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
        "openai_disable_system_prompt": True,
        "openai_disable_stream": True,
        "openai_force_temperature_one": True,
    },

    "gpt-4-turbo": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "has_multimodal_capacity": True,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-turbo-2024-04-09": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "has_multimodal_capacity": True,
        "endpoint": openai_endpoint,
        "max_token": 128000,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-3.5-random": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": openai_endpoint,
        "max_token": 4096,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    "gpt-4-vision-preview": {
        "fn_with_ui": chatgpt_vision_ui,
        "fn_without_ui": chatgpt_vision_noui,
        "endpoint": openai_endpoint,
        "max_token": 4096,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },


    # azure openai
    "azure-gpt-3.5":{
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": azure_endpoint,
        "max_token": 4096,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    "azure-gpt-4":{
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": azure_endpoint,
        "max_token": 8192,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    # 智谱AI
    "glm-4": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-4-0520": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-4-air": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-4-airx": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-4-flash": {
         "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,       
    },
    "glm-4v": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 1000,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-3-turbo": {
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 4,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "glm-4-plus":{
        "fn_with_ui": zhipu_ui,
        "fn_without_ui": zhipu_noui,
        "endpoint": None,
        "max_token": 10124 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    # api_2d (此后不需要在此处添加api2d的接口了，因为下面的代码会自动添加)
    "api2d-gpt-4": {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "endpoint": api2d_endpoint,
        "max_token": 8192,
        "tokenizer": tokenizer_gpt4,
        "token_cnt": get_token_num_gpt4,
    },

    # ChatGLM本地模型
    # 将 chatglm 直接对齐到 chatglm2
    "chatglm": {
        "fn_with_ui": chatglm_ui,
        "fn_without_ui": chatglm_noui,
        "endpoint": None,
        "max_token": 1024,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "chatglm2": {
        "fn_with_ui": chatglm_ui,
        "fn_without_ui": chatglm_noui,
        "endpoint": None,
        "max_token": 1024,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "chatglm3": {
        "fn_with_ui": chatglm3_ui,
        "fn_without_ui": chatglm3_noui,
        "endpoint": None,
        "max_token": 8192,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "chatglm4": {
        "fn_with_ui": chatglm4_ui,
        "fn_without_ui": chatglm4_noui,
        "endpoint": None,
        "max_token": 8192,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "qianfan": {
        "fn_with_ui": qianfan_ui,
        "fn_without_ui": qianfan_noui,
        "endpoint": None,
        "max_token": 2000,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    # Gemini
    # Note: now gemini-pro is an alias of gemini-1.0-pro.
    # Warning: gemini-pro-vision has been deprecated.
    # Support for gemini-pro-vision has been removed.
    "gemini-pro": {
        "fn_with_ui": genai_ui,
        "fn_without_ui": genai_noui,
        "endpoint": gemini_endpoint,
        "has_multimodal_capacity": False,
        "max_token": 1024 * 32,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "gemini-1.0-pro": {
        "fn_with_ui": genai_ui,
        "fn_without_ui": genai_noui,
        "endpoint": gemini_endpoint,
        "has_multimodal_capacity": False,
        "max_token": 1024 * 32,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "gemini-1.5-pro": {
        "fn_with_ui": genai_ui,
        "fn_without_ui": genai_noui,
        "endpoint": gemini_endpoint,
        "has_multimodal_capacity": True,
        "max_token": 1024 * 204800,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "gemini-1.5-flash": {
        "fn_with_ui": genai_ui,
        "fn_without_ui": genai_noui,
        "endpoint": gemini_endpoint,
        "has_multimodal_capacity": True,
        "max_token": 1024 * 204800,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

    # cohere
    "cohere-command-r-plus": {
        "fn_with_ui": cohere_ui,
        "fn_without_ui": cohere_noui,
        "can_multi_thread": True,
        "endpoint": cohere_endpoint,
        "max_token": 1024 * 4,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },

}
# -=-=-=-=-=-=- 月之暗面 -=-=-=-=-=-=-
from request_llms.bridge_moonshot import predict as moonshot_ui
from request_llms.bridge_moonshot import predict_no_ui_long_connection as moonshot_no_ui
model_info.update({
    "moonshot-v1-8k": {
        "fn_with_ui": moonshot_ui,
        "fn_without_ui": moonshot_no_ui,
        "can_multi_thread": True,
        "endpoint": None,
        "max_token": 1024 * 8,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "moonshot-v1-32k": {
        "fn_with_ui": moonshot_ui,
        "fn_without_ui": moonshot_no_ui,
        "can_multi_thread": True,
        "endpoint": None,
        "max_token": 1024 * 32,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    },
    "moonshot-v1-128k": {
        "fn_with_ui": moonshot_ui,
        "fn_without_ui": moonshot_no_ui,
        "can_multi_thread": True,
        "endpoint": None,
        "max_token": 1024 * 128,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    }
})
# -=-=-=-=-=-=- api2d 对齐支持 -=-=-=-=-=-=-
for model in AVAIL_LLM_MODELS:
    if model.startswith('api2d-') and (model.replace('api2d-','') in model_info.keys()):
        mi = copy.deepcopy(model_info[model.replace('api2d-','')])
        mi.update({"endpoint": api2d_endpoint})
        model_info.update({model: mi})

# -=-=-=-=-=-=- azure 对齐支持 -=-=-=-=-=-=-
for model in AVAIL_LLM_MODELS:
    if model.startswith('azure-') and (model.replace('azure-','') in model_info.keys()):
        mi = copy.deepcopy(model_info[model.replace('azure-','')])
        mi.update({"endpoint": azure_endpoint})
        model_info.update({model: mi})

# -=-=-=-=-=-=- 以下部分是新加入的模型，可能附带额外依赖 -=-=-=-=-=-=-
# claude家族
claude_models = ["claude-instant-1.2","claude-2.0","claude-2.1","claude-3-haiku-20240307","claude-3-sonnet-20240229","claude-3-opus-20240229","claude-3-5-sonnet-20240620"]
if any(item in claude_models for item in AVAIL_LLM_MODELS):
    from .bridge_claude import predict_no_ui_long_connection as claude_noui
    from .bridge_claude import predict as claude_ui
    model_info.update({
        "claude-instant-1.2": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 100000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-2.0": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 100000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-2.1": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 200000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-3-haiku-20240307": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 200000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-3-sonnet-20240229": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 200000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-3-opus-20240229": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 200000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
    model_info.update({
        "claude-3-5-sonnet-20240620": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": claude_endpoint,
            "max_token": 200000,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })    
if "jittorllms_rwkv" in AVAIL_LLM_MODELS:
    from .bridge_jittorllms_rwkv import predict_no_ui_long_connection as rwkv_noui
    from .bridge_jittorllms_rwkv import predict as rwkv_ui
    model_info.update({
        "jittorllms_rwkv": {
            "fn_with_ui": rwkv_ui,
            "fn_without_ui": rwkv_noui,
            "endpoint": None,
            "max_token": 1024,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
if "jittorllms_llama" in AVAIL_LLM_MODELS:
    from .bridge_jittorllms_llama import predict_no_ui_long_connection as llama_noui
    from .bridge_jittorllms_llama import predict as llama_ui
    model_info.update({
        "jittorllms_llama": {
            "fn_with_ui": llama_ui,
            "fn_without_ui": llama_noui,
            "endpoint": None,
            "max_token": 1024,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
if "jittorllms_pangualpha" in AVAIL_LLM_MODELS:
    from .bridge_jittorllms_pangualpha import predict_no_ui_long_connection as pangualpha_noui
    from .bridge_jittorllms_pangualpha import predict as pangualpha_ui
    model_info.update({
        "jittorllms_pangualpha": {
            "fn_with_ui": pangualpha_ui,
            "fn_without_ui": pangualpha_noui,
            "endpoint": None,
            "max_token": 1024,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
if "moss" in AVAIL_LLM_MODELS:
    from .bridge_moss import predict_no_ui_long_connection as moss_noui
    from .bridge_moss import predict as moss_ui
    model_info.update({
        "moss": {
            "fn_with_ui": moss_ui,
            "fn_without_ui": moss_noui,
            "endpoint": None,
            "max_token": 1024,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
if "stack-claude" in AVAIL_LLM_MODELS:
    from .bridge_stackclaude import predict_no_ui_long_connection as claude_noui
    from .bridge_stackclaude import predict as claude_ui
    model_info.update({
        "stack-claude": {
            "fn_with_ui": claude_ui,
            "fn_without_ui": claude_noui,
            "endpoint": None,
            "max_token": 8192,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        }
    })
if "newbing" in AVAIL_LLM_MODELS:   # same with newbing-free
    try:
        from .bridge_newbingfree import predict_no_ui_long_connection as newbingfree_noui
        from .bridge_newbingfree import predict as newbingfree_ui
        model_info.update({
            "newbing": {
                "fn_with_ui": newbingfree_ui,
                "fn_without_ui": newbingfree_noui,
                "endpoint": newbing_endpoint,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
if "chatglmft" in AVAIL_LLM_MODELS:   # same with newbing-free
    try:
        from .bridge_chatglmft import predict_no_ui_long_connection as chatglmft_noui
        from .bridge_chatglmft import predict as chatglmft_ui
        model_info.update({
            "chatglmft": {
                "fn_with_ui": chatglmft_ui,
                "fn_without_ui": chatglmft_noui,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 上海AI-LAB书生大模型 -=-=-=-=-=-=-
if "internlm" in AVAIL_LLM_MODELS:
    try:
        from .bridge_internlm import predict_no_ui_long_connection as internlm_noui
        from .bridge_internlm import predict as internlm_ui
        model_info.update({
            "internlm": {
                "fn_with_ui": internlm_ui,
                "fn_without_ui": internlm_noui,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
if "chatglm_onnx" in AVAIL_LLM_MODELS:
    try:
        from .bridge_chatglmonnx import predict_no_ui_long_connection as chatglm_onnx_noui
        from .bridge_chatglmonnx import predict as chatglm_onnx_ui
        model_info.update({
            "chatglm_onnx": {
                "fn_with_ui": chatglm_onnx_ui,
                "fn_without_ui": chatglm_onnx_noui,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 通义-本地模型 -=-=-=-=-=-=-
if "qwen-local" in AVAIL_LLM_MODELS:
    try:
        from .bridge_qwen_local import predict_no_ui_long_connection as qwen_local_noui
        from .bridge_qwen_local import predict as qwen_local_ui
        model_info.update({
            "qwen-local": {
                "fn_with_ui": qwen_local_ui,
                "fn_without_ui": qwen_local_noui,
                "can_multi_thread": False,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 通义-在线模型 -=-=-=-=-=-=-
qwen_models = ["qwen-max-latest", "qwen-max-2025-01-25","qwen-max","qwen-turbo","qwen-plus"]
if any(item in qwen_models for item in AVAIL_LLM_MODELS):
    try:
        from .bridge_qwen import predict_no_ui_long_connection as qwen_noui
        from .bridge_qwen import predict as qwen_ui
        model_info.update({
            "qwen-turbo": {
                "fn_with_ui": qwen_ui,
                "fn_without_ui": qwen_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 100000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "qwen-plus": {
                "fn_with_ui": qwen_ui,
                "fn_without_ui": qwen_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 129024,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "qwen-max": {
                "fn_with_ui": qwen_ui,
                "fn_without_ui": qwen_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 30720,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "qwen-max-latest": {
                "fn_with_ui": qwen_ui,
                "fn_without_ui": qwen_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 30720,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "qwen-max-2025-01-25": {
                "fn_with_ui": qwen_ui,
                "fn_without_ui": qwen_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 30720,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 零一万物模型 -=-=-=-=-=-=-
yi_models = ["yi-34b-chat-0205","yi-34b-chat-200k","yi-large","yi-medium","yi-spark","yi-large-turbo","yi-large-preview"]
if any(item in yi_models for item in AVAIL_LLM_MODELS):
    try:
        yimodel_4k_noui, yimodel_4k_ui = get_predict_function(
            api_key_conf_name="YIMODEL_API_KEY", max_output_token=600, disable_proxy=False
            )
        yimodel_16k_noui, yimodel_16k_ui = get_predict_function(
            api_key_conf_name="YIMODEL_API_KEY", max_output_token=4000, disable_proxy=False
            )
        yimodel_200k_noui, yimodel_200k_ui = get_predict_function(
            api_key_conf_name="YIMODEL_API_KEY", max_output_token=4096, disable_proxy=False
            )
        model_info.update({
            "yi-34b-chat-0205": {
                "fn_with_ui": yimodel_4k_ui,
                "fn_without_ui": yimodel_4k_noui,
                "can_multi_thread": False,  # 目前来说，默认情况下并发量极低，因此禁用
                "endpoint": yimodel_endpoint,
                "max_token": 4000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-34b-chat-200k": {
                "fn_with_ui": yimodel_200k_ui,
                "fn_without_ui": yimodel_200k_noui,
                "can_multi_thread": False,  # 目前来说，默认情况下并发量极低，因此禁用
                "endpoint": yimodel_endpoint,
                "max_token": 200000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-large": {
                "fn_with_ui": yimodel_16k_ui,
                "fn_without_ui": yimodel_16k_noui,
                "can_multi_thread": False,  # 目前来说，默认情况下并发量极低，因此禁用
                "endpoint": yimodel_endpoint,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-medium": {
                "fn_with_ui": yimodel_16k_ui,
                "fn_without_ui": yimodel_16k_noui,
                "can_multi_thread": True,  # 这个并发量稍微大一点
                "endpoint": yimodel_endpoint,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-spark": {
                "fn_with_ui": yimodel_16k_ui,
                "fn_without_ui": yimodel_16k_noui,
                "can_multi_thread": True,  # 这个并发量稍微大一点
                "endpoint": yimodel_endpoint,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-large-turbo": {
                "fn_with_ui": yimodel_16k_ui,
                "fn_without_ui": yimodel_16k_noui,
                "can_multi_thread": False,  # 目前来说，默认情况下并发量极低，因此禁用
                "endpoint": yimodel_endpoint,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "yi-large-preview": {
                "fn_with_ui": yimodel_16k_ui,
                "fn_without_ui": yimodel_16k_noui,
                "can_multi_thread": False,  # 目前来说，默认情况下并发量极低，因此禁用
                "endpoint": yimodel_endpoint,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
        })
    except:
        logger.error(trimmed_format_exc())


# -=-=-=-=-=-=- Grok model from x.ai -=-=-=-=-=-=-
grok_models = ["grok-beta"]
if any(item in grok_models for item in AVAIL_LLM_MODELS):
    try:
        grok_beta_128k_noui, grok_beta_128k_ui = get_predict_function(
            api_key_conf_name="GROK_API_KEY", max_output_token=8192, disable_proxy=False
            )
        
        model_info.update({
            "grok-beta": {
                "fn_with_ui": grok_beta_128k_ui,
                "fn_without_ui": grok_beta_128k_noui,
                "can_multi_thread": True,  
                "endpoint": grok_model_endpoint,
                "max_token": 128000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            
        })
    except:
        logger.error(trimmed_format_exc())

# -=-=-=-=-=-=- 讯飞星火认知大模型 -=-=-=-=-=-=-
if "spark" in AVAIL_LLM_MODELS:
    try:
        from .bridge_spark import predict_no_ui_long_connection as spark_noui
        from .bridge_spark import predict as spark_ui
        model_info.update({
            "spark": {
                "fn_with_ui": spark_ui,
                "fn_without_ui": spark_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
if "sparkv2" in AVAIL_LLM_MODELS:   # 讯飞星火认知大模型
    try:
        from .bridge_spark import predict_no_ui_long_connection as spark_noui
        from .bridge_spark import predict as spark_ui
        model_info.update({
            "sparkv2": {
                "fn_with_ui": spark_ui,
                "fn_without_ui": spark_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
if any(x in AVAIL_LLM_MODELS for x in ("sparkv3", "sparkv3.5", "sparkv4")):   # 讯飞星火认知大模型
    try:
        from .bridge_spark import predict_no_ui_long_connection as spark_noui
        from .bridge_spark import predict as spark_ui
        model_info.update({
            "sparkv3": {
                "fn_with_ui": spark_ui,
                "fn_without_ui": spark_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "sparkv3.5": {
                "fn_with_ui": spark_ui,
                "fn_without_ui": spark_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "sparkv4":{
                "fn_with_ui": spark_ui,
                "fn_without_ui": spark_noui,
                "can_multi_thread": True,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
if "llama2" in AVAIL_LLM_MODELS:   # llama2
    try:
        from .bridge_llama2 import predict_no_ui_long_connection as llama2_noui
        from .bridge_llama2 import predict as llama2_ui
        model_info.update({
            "llama2": {
                "fn_with_ui": llama2_ui,
                "fn_without_ui": llama2_noui,
                "endpoint": None,
                "max_token": 4096,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 智谱 -=-=-=-=-=-=-
if "zhipuai" in AVAIL_LLM_MODELS:   # zhipuai 是glm-4的别名，向后兼容配置
    try:
        model_info.update({
            "zhipuai": {
                "fn_with_ui": zhipu_ui,
                "fn_without_ui": zhipu_noui,
                "endpoint": None,
                "max_token": 10124 * 8,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 幻方-深度求索本地大模型 -=-=-=-=-=-=-
if "deepseekcoder" in AVAIL_LLM_MODELS:   # deepseekcoder
    try:
        from .bridge_deepseekcoder import predict_no_ui_long_connection as deepseekcoder_noui
        from .bridge_deepseekcoder import predict as deepseekcoder_ui
        model_info.update({
            "deepseekcoder": {
                "fn_with_ui": deepseekcoder_ui,
                "fn_without_ui": deepseekcoder_noui,
                "endpoint": None,
                "max_token": 2048,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            }
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- 幻方-深度求索大模型在线API -=-=-=-=-=-=-
if "deepseek-chat" in AVAIL_LLM_MODELS or "deepseek-coder" in AVAIL_LLM_MODELS or "deepseek-reasoner" in AVAIL_LLM_MODELS:
    try:
        deepseekapi_noui, deepseekapi_ui = get_predict_function(
            api_key_conf_name="DEEPSEEK_API_KEY", max_output_token=4096, disable_proxy=False
        )
        model_info.update({
            "deepseek-chat":{
                "fn_with_ui": deepseekapi_ui,
                "fn_without_ui": deepseekapi_noui,
                "endpoint": deepseekapi_endpoint,
                "can_multi_thread": True,
                "max_token": 64000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "deepseek-coder":{
                "fn_with_ui": deepseekapi_ui,
                "fn_without_ui": deepseekapi_noui,
                "endpoint": deepseekapi_endpoint,
                "can_multi_thread": True,
                "max_token": 16000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
            },
            "deepseek-reasoner":{
                "fn_with_ui": deepseekapi_ui,
                "fn_without_ui": deepseekapi_noui,
                "endpoint": deepseekapi_endpoint,
                "can_multi_thread": True,
                "max_token": 64000,
                "tokenizer": tokenizer_gpt35,
                "token_cnt": get_token_num_gpt35,
                "enable_reasoning": True
            },
        })
    except:
        logger.error(trimmed_format_exc())
# -=-=-=-=-=-=- one-api 对齐支持 -=-=-=-=-=-=-
for model in [m for m in AVAIL_LLM_MODELS if m.startswith("one-api-")]:
    # 为了更灵活地接入one-api多模型管理界面，设计了此接口，例子：AVAIL_LLM_MODELS = ["one-api-mixtral-8x7b(max_token=6666)"]
    # 其中
    #   "one-api-"          是前缀（必要）
    #   "mixtral-8x7b"      是模型名（必要）
    #   "(max_token=6666)"  是配置（非必要）
    try:
        origin_model_name, max_token_tmp = read_one_api_model_name(model)
        # 如果是已知模型，则尝试获取其信息
        original_model_info = model_info.get(origin_model_name.replace("one-api-", "", 1), None)
    except:
        logger.error(f"one-api模型 {model} 的 max_token 配置不是整数，请检查配置文件。")
        continue
    this_model_info = {
        "fn_with_ui": chatgpt_ui,
        "fn_without_ui": chatgpt_noui,
        "can_multi_thread": True,
        "endpoint": openai_endpoint,
        "max_token": max_token_tmp,
        "tokenizer": tokenizer_gpt35,
        "token_cnt": get_token_num_gpt35,
    }

    # 同步已知模型的其他信息
    attribute = "has_multimodal_capacity"
    if original_model_info is not None and original_model_info.get(attribute, None) is not None: this_model_info.update({attribute: original_model_info.get(attribute, None)})
    # attribute = "attribute2"
    # if original_model_info is not None and original_model_info.get(attribute, None) is not None: this_model_info.update({attribute: original_model_info.get(attribute, None)})
    # attribute = "attribute3"
    # if original_model_info is not None and original_model_info.get(attribute, None) is not None: this_model_info.update({attribute: original_model_info.get(attribute, None)})
    model_info.update({model: this_model_info})

# -=-=-=-=-=-=- vllm 对齐支持 -=-=-=-=-=-=-
for model in [m for m in AVAIL_LLM_MODELS if m.startswith("vllm-")]:
    # 为了更灵活地接入vllm多模型管理界面，设计了此接口，例子：AVAIL_LLM_MODELS = ["vllm-/home/hmp/llm/cache/Qwen1___5-32B-Chat(max_token=6666)"]
    # 其中
    #   "vllm-"             是前缀（必要）
    #   "mixtral-8x7b"      是模型名（必要）
    #   "(max_token=6666)"  是配置（非必要）
    try:
        _, max_token_tmp = read_one_api_model_name(model)
    except:
        logger.error(f"vllm模型 {model} 的 max_token 配置不是整数，请检查配置文件。")
        continue
    model_info.update({
        model: {
            "fn_with_ui": chatgpt_ui,
            "fn_without_ui": chatgpt_noui,
            "can_multi_thread": True,
            "endpoint": openai_endpoint,
            "max_token": max_token_tmp,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })
# -=-=-=-=-=-=- ollama 对齐支持 -=-=-=-=-=-=-
for model in [m for m in AVAIL_LLM_MODELS if m.startswith("ollama-")]:
    from .bridge_ollama import predict_no_ui_long_connection as ollama_noui
    from .bridge_ollama import predict as ollama_ui
    break
for model in [m for m in AVAIL_LLM_MODELS if m.startswith("ollama-")]:
    # 为了更灵活地接入ollama多模型管理界面，设计了此接口，例子：AVAIL_LLM_MODELS = ["ollama-phi3(max_token=6666)"]
    # 其中
    #   "ollama-"           是前缀（必要）
    #   "phi3"            是模型名（必要）
    #   "(max_token=6666)"  是配置（非必要）
    try:
        _, max_token_tmp = read_one_api_model_name(model)
    except:
        logger.error(f"ollama模型 {model} 的 max_token 配置不是整数，请检查配置文件。")
        continue
    model_info.update({
        model: {
            "fn_with_ui": ollama_ui,
            "fn_without_ui": ollama_noui,
            "endpoint": ollama_endpoint,
            "max_token": max_token_tmp,
            "tokenizer": tokenizer_gpt35,
            "token_cnt": get_token_num_gpt35,
        },
    })

# -=-=-=-=-=-=- azure模型对齐支持 -=-=-=-=-=-=-
AZURE_CFG_ARRAY = get_conf("AZURE_CFG_ARRAY") # <-- 用于定义和切换多个azure模型 -->
if len(AZURE_CFG_ARRAY) > 0:
    for azure_model_name, azure_cfg_dict in AZURE_CFG_ARRAY.items():
        # 可能会覆盖之前的配置，但这是意料之中的
        if not azure_model_name.startswith('azure'):
            raise ValueError("AZURE_CFG_ARRAY中配置的模型必须以azure开头")
        endpoint_ = azure_cfg_dict["AZURE_ENDPOINT"] + \
            f'openai/deployments/{azure_cfg_dict["AZURE_ENGINE"]}/chat/completions?api-version=2023-05-15'
        model_info.update({
            azure_model_name: {
                "fn_with_ui": chatgpt_ui,
                "fn_without_ui": chatgpt_noui,
                "endpoint": endpoint_,
                "azure_api_key": azure_cfg_dict["AZURE_API_KEY"],
                "max_token": azure_cfg_dict["AZURE_MODEL_MAX_TOKEN"],
                "tokenizer": tokenizer_gpt35,   # tokenizer只用于粗估token数量
                "token_cnt": get_token_num_gpt35,
            }
        })
        if azure_model_name not in AVAIL_LLM_MODELS:
            AVAIL_LLM_MODELS += [azure_model_name]

# -=-=-=-=-=-=- Openrouter模型对齐支持 -=-=-=-=-=-=-
# 为了更灵活地接入Openrouter路由，设计了此接口
for model in [m for m in AVAIL_LLM_MODELS if m.startswith("openrouter-")]:
    from request_llms.bridge_openrouter import predict_no_ui_long_connection as openrouter_noui
    from request_llms.bridge_openrouter import predict as openrouter_ui
    model_info.update({
        model: {
            "fn_with_ui": openrouter_ui,
            "fn_without_ui": openrouter_noui,
            # 以下参数参考gpt-4o-mini的配置, 请根据实际情况修改
            "endpoint": openai_endpoint,
            "has_multimodal_capacity": True,
            "max_token": 128000,
            "tokenizer": tokenizer_gpt4,
            "token_cnt": get_token_num_gpt4,
        },
    })


# -=-=-=-=-=-=- 硅基智能SiliconFlow在线API -=-=-=-=-=-=-
siliconflow_models = [
    "deepseek-ai/DeepSeek-R1","deepseek-ai/DeepSeek-V3",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B","deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B","deepseek-ai/DeepSeek-R1-Distill-Qwen-14B","deepseek-ai/DeepSeek-R1-Distill-Qwen-7B","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
    "Pro/deepseek-ai/DeepSeek-R1-Distill-Llama-8B","Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B","Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
    "meta-llama/Llama-3.3-70B-Instruct",
    "deepseek-ai/DeepSeek-V2.5",
    "Qwen/Qwen2.5-72B-Instruct-128K","Qwen/Qwen2.5-72B-Instruct","Qwen/Qwen2.5-32B-Instruct","Qwen/Qwen2.5-14B-Instruct","Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct","Qwen/Qwen2.5-Coder-7B-Instruct",
    "Qwen/QwQ-32B-Preview",
    "TeleAI/TeleChat2",
    "01-ai/Yi-1.5-34B-Chat-16K","01-ai/Yi-1.5-9B-Chat-16K","01-ai/Yi-1.5-6B-Chat",
    "THUDM/glm-4-9b-chat",
    "Vendor-A/Qwen/Qwen2.5-72B-Instruct",
    "google/gemma-2-27b-it","google/gemma-2-9b-it","Pro/google/gemma-2-9b-it",
    "Pro/Qwen/Qwen2.5-7B-Instruct","Pro/Qwen/Qwen2-7B-Instruct","Pro/Qwen/Qwen2-1.5B-Instruct",
    "THUDM/glm-4-9b-chat","Pro/THUDM/chatglm3-6b","Pro/THUDM/glm-4-9b-chat",
	"meta-llama/Meta-Llama-3.1-405B-Instruct","meta-llama/Meta-Llama-3.1-70B-Instruct","meta-llama/Meta-Llama-3.1-8B-Instruct"
]
if any(item in siliconflow_models for item in AVAIL_LLM_MODELS):
    try:
        siliconflow_noui, siliconflow_ui = get_predict_function(
            api_key_conf_name="SILICONFLOW_API_KEY",
            max_output_token=4096,
            disable_proxy=False,
        )
        model_info.update(
            {
                "deepseek-ai/DeepSeek-R1": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "deepseek-ai/DeepSeek-V3": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "eepseek-ai/DeepSeek-R1-Distill-Qwen-32B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "deepseek-ai/DeepSeek-R1-Distill-Llama-8B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "Pro/deepseek-ai/DeepSeek-R1-Distill-Llama-8B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                    "enable_reasoning": True,
                },
                "meta-llama/Llama-3.3-70B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "deepseek-ai/DeepSeek-V2.5": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-72B-Instruct-128K": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-72B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-32B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-14B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-7B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-Coder-32B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/Qwen2.5-Coder-7B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Qwen/QwQ-32B-Preview": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "TeleAI/TeleChat2": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "01-ai/Yi-1.5-34B-Chat-16K": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "01-ai/Yi-1.5-9B-Chat-16K": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "01-ai/Yi-1.5-6B-Chat": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "THUDM/glm-4-9b-chat": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Vendor-A/Qwen/Qwen2.5-72B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "internlm/internlm2_5-7b-chat": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "internlm/internlm2_5-20b-chat": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "meta-llama/Meta-Llama-3.1-405B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "meta-llama/Meta-Llama-3.1-70B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "meta-llama/Meta-Llama-3.1-8B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "google/gemma-2-27b-it": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "google/gemma-2-9b-it": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/Qwen/Qwen2.5-7B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/Qwen/Qwen2-7B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/Qwen/Qwen2-1.5B-Instruct": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/THUDM/chatglm3-6b": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/THUDM/glm-4-9b-chat": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
                "Pro/google/gemma-2-9b-it": {
                    "fn_with_ui": siliconflow_ui,
                    "fn_without_ui": siliconflow_noui,
                    "endpoint": siliconflow_endpoint,
                    "can_multi_thread": True,
                    "max_token": 8000,
                    "tokenizer": tokenizer_gpt35,
                    "token_cnt": get_token_num_gpt35,
                },
            }
        )

    except:
        logger.error(trimmed_format_exc())



# -=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=-=-=
# -=-=-=-=-=-=-=-=-=- ☝️ 以上是模型路由 -=-=-=-=-=-=-=-=-=
# -=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=-=-=

# -=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=-=-=
# -=-=-=-=-=-=-= 👇 以下是多模型路由切换函数 -=-=-=-=-=-=-=
# -=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=--=-=-=-=-=-=-=-=


def LLM_CATCH_EXCEPTION(f):
    """
    装饰器函数，将错误显示出来
    """
    def decorated(inputs:str, llm_kwargs:dict, history:list, sys_prompt:str, observe_window:list, console_slience:bool):
        try:
            return f(inputs, llm_kwargs, history, sys_prompt, observe_window, console_slience)
        except Exception as e:
            tb_str = '\n```\n' + trimmed_format_exc() + '\n```\n'
            observe_window[0] = tb_str
            return tb_str
    return decorated


def predict_no_ui_long_connection(inputs:str, llm_kwargs:dict, history:list, sys_prompt:str, observe_window:list=[], console_slience:bool=False):
    """
    发送至LLM，等待回复，一次性完成，不显示中间过程。但内部（尽可能地）用stream的方法避免中途网线被掐。
    inputs：
        是本次问询的输入
    sys_prompt:
        系统静默prompt
    llm_kwargs：
        LLM的内部调优参数
    history：
        是之前的对话列表
    observe_window = None：
        用于负责跨越线程传递已经输出的部分，大部分时候仅仅为了fancy的视觉效果，留空即可。observe_window[0]：观测窗。observe_window[1]：看门狗
    """
    import threading, time, copy

    inputs = apply_gpt_academic_string_mask(inputs, mode="show_llm")
    model = llm_kwargs['llm_model']
    n_model = 1
    if '&' not in model:
        # 如果只询问“一个”大语言模型（多数情况）：
        method = model_info[model]["fn_without_ui"]
        return method(inputs, llm_kwargs, history, sys_prompt, observe_window, console_slience)
    else:
        # 如果同时询问“多个”大语言模型，这个稍微啰嗦一点，但思路相同，您不必读这个else分支
        executor = ThreadPoolExecutor(max_workers=4)
        models = model.split('&')
        n_model = len(models)

        window_len = len(observe_window)
        assert window_len==3
        window_mutex = [["", time.time(), ""] for _ in range(n_model)] + [True]

        futures = []
        for i in range(n_model):
            model = models[i]
            method = model_info[model]["fn_without_ui"]
            llm_kwargs_feedin = copy.deepcopy(llm_kwargs)
            llm_kwargs_feedin['llm_model'] = model
            future = executor.submit(LLM_CATCH_EXCEPTION(method), inputs, llm_kwargs_feedin, history, sys_prompt, window_mutex[i], console_slience)
            futures.append(future)

        def mutex_manager(window_mutex, observe_window):
            while True:
                time.sleep(0.25)
                if not window_mutex[-1]: break
                # 看门狗（watchdog）
                for i in range(n_model):
                    window_mutex[i][1] = observe_window[1]
                # 观察窗（window）
                chat_string = []
                for i in range(n_model):
                    color = colors[i%len(colors)]
                    chat_string.append( f"【{str(models[i])} 说】: <font color=\"{color}\"> {window_mutex[i][0]} </font>" )
                res = '<br/><br/>\n\n---\n\n'.join(chat_string)
                # # # # # # # # # # #
                observe_window[0] = res

        t_model = threading.Thread(target=mutex_manager, args=(window_mutex, observe_window), daemon=True)
        t_model.start()

        return_string_collect = []
        while True:
            worker_done = [h.done() for h in futures]
            if all(worker_done):
                executor.shutdown()
                break
            time.sleep(1)

        for i, future in enumerate(futures):  # wait and get
            color = colors[i%len(colors)]
            return_string_collect.append( f"【{str(models[i])} 说】: <font color=\"{color}\"> {future.result()} </font>" )

        window_mutex[-1] = False # stop mutex thread
        res = '<br/><br/>\n\n---\n\n'.join(return_string_collect)
        return res

# 根据基础功能区 ModelOverride 参数调整模型类型，用于 `predict` 中
import importlib
import core_functional
def execute_model_override(llm_kwargs, additional_fn, method):
    functional = core_functional.get_core_functions()
    if (additional_fn in functional) and 'ModelOverride' in functional[additional_fn]:
        # 热更新Prompt & ModelOverride
        importlib.reload(core_functional)
        functional = core_functional.get_core_functions()
        model_override = functional[additional_fn]['ModelOverride']
        if model_override not in model_info:
            raise ValueError(f"模型覆盖参数 '{model_override}' 指向一个暂不支持的模型，请检查配置文件。")
        method = model_info[model_override]["fn_with_ui"]
        llm_kwargs['llm_model'] = model_override
        return llm_kwargs, additional_fn, method
    # 默认返回原参数
    return llm_kwargs, additional_fn, method

def predict(inputs:str, llm_kwargs:dict, plugin_kwargs:dict, chatbot,
            history:list=[], system_prompt:str='', stream:bool=True, additional_fn:str=None):
    """
    发送至LLM，流式获取输出。
    用于基础的对话功能。

    完整参数列表：
        predict(
            inputs:str,                     # 是本次问询的输入
            llm_kwargs:dict,                # 是LLM的内部调优参数
            plugin_kwargs:dict,             # 是插件的内部参数
            chatbot:ChatBotWithCookies,     # 原样传递，负责向用户前端展示对话，兼顾前端状态的功能
            history:list=[],                # 是之前的对话列表
            system_prompt:str='',           # 系统静默prompt
            stream:bool=True,               # 是否流式输出（已弃用）
            additional_fn:str=None          # 基础功能区按钮的附加功能
        ):
    """

    inputs = apply_gpt_academic_string_mask(inputs, mode="show_llm")

    if llm_kwargs['llm_model'] not in model_info:
        from toolbox import update_ui
        chatbot.append([inputs, f"很抱歉，模型 '{llm_kwargs['llm_model']}' 暂不支持<br/>(1) 检查config中的AVAIL_LLM_MODELS选项<br/>(2) 检查request_llms/bridge_all.py中的模型路由"])
        yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

    method = model_info[llm_kwargs['llm_model']]["fn_with_ui"]  # 如果这里报错，检查config中的AVAIL_LLM_MODELS选项

    if additional_fn: # 根据基础功能区 ModelOverride 参数调整模型类型
        llm_kwargs, additional_fn, method = execute_model_override(llm_kwargs, additional_fn, method)

    # 更新一下llm_kwargs的参数，否则会出现参数不匹配的问题
    yield from method(inputs, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, stream, additional_fn)
