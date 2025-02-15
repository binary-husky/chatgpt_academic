"""
    以下所有配置也都支持利用环境变量覆写，环境变量配置格式见docker-compose.yml。
    读取优先级：环境变量 > config_private.py > config.py
    --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
    All the following configurations also support using environment variables to override,
    and the environment variable configuration format can be seen in docker-compose.yml.
    Configuration reading priority: environment variable > config_private.py > config.py
"""

# [step 1-1]>> ( 接入GPT等模型 ) API_KEY = "sk-123456789xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx123456789"。极少数情况下，还需要填写组织（格式如org-123456789abcdefghijklmno的），请向下翻，找 API_ORG 设置项
API_KEY = "在此处填写APIKEY"    # 可同时填写多个API-KEY，用英文逗号分割，例如API_KEY = "sk-openaikey1,sk-openaikey2,fkxxxx-api2dkey3,azure-apikey4"

# [step 1-2]>> ( 接入通义 qwen-max ) 接入通义千问在线大模型，api-key获取地址 https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY = "" # 阿里灵积云API_KEY

# [step 1-3]>> ( 接入 deepseek-reasoner, 即 deepseek-r1 ) 深度求索(DeepSeek) API KEY，默认请求地址为"https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = ""

# [step 1-4]>> ( 接入 硅基智能API ) 硅基智能(Siliconflow) API KEY，默认请求地址为"https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_API_KEY = ""

# [step 2]>> 改为True应用代理。如果使用本地或无地域限制的大模型时，此处不修改；如果直接在海外服务器部署，此处不修改
USE_PROXY = False
if USE_PROXY:
    """
    代理网络的地址，打开你的代理软件查看代理协议(socks5h / http)、地址(localhost)和端口(11284)
    填写格式是 [协议]://  [地址] :[端口]，填写之前不要忘记把USE_PROXY改成True，如果直接在海外服务器部署，此处不修改
            <配置教程&视频教程> https://github.com/binary-husky/gpt_academic/issues/1>
    [协议] 常见协议无非socks5h/http; 例如 v2**y 和 ss* 的默认本地协议是socks5h; 而cl**h 的默认本地协议是http
    [地址] 填localhost或者127.0.0.1（localhost意思是代理软件安装在本机上）
    [端口] 在代理软件的设置里找。虽然不同的代理软件界面不一样，但端口号都应该在最显眼的位置上
    """
    proxies = {
        #          [协议]://  [地址]  :[端口]
        "http": "socks5h://localhost:11284",  # 再例如  "http":  "http://127.0.0.1:7890",
        "https": "socks5h://localhost:11284",  # 再例如  "https": "http://127.0.0.1:7890",
    }
else:
    proxies = None

# [step 3]>> 模型选择是 (注意: LLM_MODEL是默认选中的模型, 它*必须*被包含在AVAIL_LLM_MODELS列表中 )
LLM_MODEL = "gpt-3.5-turbo-16k" # 可选 ↓↓↓
AVAIL_LLM_MODELS = ["qwen-max", "o1-mini", "o1-mini-2024-09-12", "o1", "o1-2024-12-17", "o1-preview", "o1-preview-2024-09-12",
                    "gpt-4-1106-preview", "gpt-4-turbo-preview", "gpt-4-vision-preview",
                    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4-turbo-2024-04-09",
                    "gpt-3.5-turbo-1106", "gpt-3.5-turbo-16k", "gpt-3.5-turbo", "azure-gpt-3.5",
                    "gpt-4", "gpt-4-32k", "azure-gpt-4", "glm-4", "glm-4v", "glm-3-turbo",
                    "gemini-1.5-pro", "chatglm3", "chatglm4",
                    "deepseek-chat", "deepseek-coder", "deepseek-reasoner",
                    "deepseek-ai/DeepSeek-R1","deepseek-ai/DeepSeek-V3",
                    "Qwen/Qwen2.5-32B-Instruct","Qwen/Qwen2.5-14B-Instruct","Qwen/Qwen2.5-7B-Instruct"
                    ]

EMBEDDING_MODEL = "text-embedding-3-small"

# --- --- --- ---
# P.S. 其他可用的模型还包括
# AVAIL_LLM_MODELS = [
#   "glm-4-0520", "glm-4-air", "glm-4-airx", "glm-4-flash",
#   "qianfan", "deepseekcoder",
#   "spark", "sparkv2", "sparkv3", "sparkv3.5", "sparkv4",
#   "qwen-turbo", "qwen-plus", "qwen-local",
#   "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k",
#   "gpt-3.5-turbo-0613", "gpt-3.5-turbo-16k-0613", "gpt-3.5-turbo-0125", "gpt-4o-2024-05-13"
#   "claude-3-haiku-20240307","claude-3-sonnet-20240229","claude-3-opus-20240229", "claude-2.1", "claude-instant-1.2",
#   "moss", "llama2", "chatglm_onnx", "internlm", "jittorllms_pangualpha", "jittorllms_llama",
#   "deepseek-chat" ,"deepseek-coder",
#   "gemini-1.5-flash",
#   "yi-34b-chat-0205","yi-34b-chat-200k","yi-large","yi-medium","yi-spark","yi-large-turbo","yi-large-preview",
#   "grok-beta",
# ]
# --- --- --- ---
# 此外，您还可以在接入one-api/vllm/ollama/Openroute时，
# 使用"one-api-*","vllm-*","ollama-*","openrouter-*"前缀直接使用非标准方式接入的模型，例如
# AVAIL_LLM_MODELS = ["one-api-claude-3-sonnet-20240229(max_token=100000)", "ollama-phi3(max_token=4096)","openrouter-openai/gpt-4o-mini","openrouter-openai/chatgpt-4o-latest"]
# --- --- --- ---
# 硅基智能(Siliconflow) API 可以通过 https://cloud.siliconflow.cn/models 或 https://docs.siliconflow.cn/api-reference/chat-completions/chat-completions 获取模型名称，并放置在AVAIL_LLM_MODELS列表中。
# AVAIL_LLM_MODELS = [
#                       "deepseek-ai/DeepSeek-R1","deepseek-ai/DeepSeek-V3",
#                       "Qwen/Qwen2.5-32B-Instruct","Qwen/Qwen2.5-14B-Instruct","Qwen/Qwen2.5-7B-Instruct"
# ]
# --- --- --- ---

# --------------- 以下配置可以优化体验 ---------------

# 重新URL重新定向，实现更换API_URL的作用（高危设置! 常规情况下不要修改! 通过修改此设置，您将把您的API-KEY和对话隐私完全暴露给您设定的中间人！）
# 格式: API_URL_REDIRECT = {"https://api.openai.com/v1/chat/completions": "在这里填写重定向的api.openai.com的URL"}
# 举例: API_URL_REDIRECT = {"https://api.openai.com/v1/chat/completions": "https://reverse-proxy-url/v1/chat/completions", "http://localhost:11434/api/chat": "在这里填写您ollama的URL"}
API_URL_REDIRECT = {}


# 多线程函数插件中，默认允许多少路线程同时访问OpenAI。Free trial users的限制是每分钟3次，Pay-as-you-go users的限制是每分钟3500次
# 一言以蔽之：免费（5刀）用户填3，OpenAI绑了信用卡的用户可以填 16 或者更高。提高限制请查询：https://platform.openai.com/docs/guides/rate-limits/overview
DEFAULT_WORKER_NUM = 8


# 色彩主题, 可选 ["Default", "Chuanhu-Small-and-Beautiful", "High-Contrast"]
# 更多主题, 请查阅Gradio主题商店: https://huggingface.co/spaces/gradio/theme-gallery 可选 ["Gstaff/Xkcd", "NoCrypt/Miku", ...]
THEME = "Default"
AVAIL_THEMES = ["Default", "Chuanhu-Small-and-Beautiful", "High-Contrast", "Gstaff/Xkcd", "NoCrypt/Miku"]

FONT = "Theme-Default-Font"
AVAIL_FONTS = [
    "默认值(Theme-Default-Font)", 
    "宋体(SimSun)",  
    "黑体(SimHei)",  
    "楷体(KaiTi)",  
    "仿宋(FangSong)",  
    "华文细黑(STHeiti Light)",
    "华文楷体(STKaiti)",  
    "华文仿宋(STFangsong)",  
    "华文宋体(STSong)",  
    "华文中宋(STZhongsong)",  
    "华文新魏(STXinwei)",  
    "华文隶书(STLiti)", 
    # 备注：以下字体需要网络支持，您可以自定义任意您喜欢的字体，如下所示，需要满足的格式为 "字体昵称(字体英文真名@字体css下载链接)" 
    "思源宋体(Source Han Serif CN VF@https://chinese-fonts-cdn.deno.dev/packages/syst/dist/SourceHanSerifCN/result.css)",
    "月星楷(Moon Stars Kai HW@https://chinese-fonts-cdn.deno.dev/packages/moon-stars-kai/dist/MoonStarsKaiHW-Regular/result.css)",
    "珠圆体(MaokenZhuyuanTi@https://chinese-fonts-cdn.deno.dev/packages/mkzyt/dist/猫啃珠圆体/result.css)",
    "平方萌萌哒(PING FANG MENG MNEG DA@https://chinese-fonts-cdn.deno.dev/packages/pfmmd/dist/平方萌萌哒/result.css)",
    "Helvetica",
    "ui-sans-serif",
    "sans-serif",
    "system-ui"
]


# 默认的系统提示词（system prompt）
INIT_SYS_PROMPT = "Serve me as a writing and programming assistant."


# 对话窗的高度 （仅在LAYOUT="TOP-DOWN"时生效）
CHATBOT_HEIGHT = 1115


# 代码高亮
CODE_HIGHLIGHT = True


# 窗口布局
LAYOUT = "LEFT-RIGHT"   # "LEFT-RIGHT"（左右布局） # "TOP-DOWN"（上下布局）


# 暗色模式 / 亮色模式
DARK_MODE = True


# 发送请求到OpenAI后，等待多久判定为超时
TIMEOUT_SECONDS = 30


# 网页的端口, -1代表随机端口
WEB_PORT = -1


# 是否自动打开浏览器页面
AUTO_OPEN_BROWSER = True


# 如果OpenAI不响应（网络卡顿、代理失败、KEY失效），重试的次数限制
MAX_RETRY = 2


# 插件分类默认选项
DEFAULT_FN_GROUPS = ['对话', '编程', '学术', '智能体']


# 定义界面上“询问多个GPT模型”插件应该使用哪些模型，请从AVAIL_LLM_MODELS中选择，并在不同模型之间用`&`间隔，例如"gpt-3.5-turbo&chatglm3&azure-gpt-4"
MULTI_QUERY_LLM_MODELS = "gpt-3.5-turbo&chatglm3"


# 选择本地模型变体（只有当AVAIL_LLM_MODELS包含了对应本地模型时，才会起作用）
# 如果你选择Qwen系列的模型，那么请在下面的QWEN_MODEL_SELECTION中指定具体的模型
# 也可以是具体的模型路径
QWEN_LOCAL_MODEL_SELECTION = "Qwen/Qwen-1_8B-Chat-Int8"


# 百度千帆（LLM_MODEL="qianfan"）
BAIDU_CLOUD_API_KEY = ''
BAIDU_CLOUD_SECRET_KEY = ''
BAIDU_CLOUD_QIANFAN_MODEL = 'ERNIE-Bot'    # 可选 "ERNIE-Bot-4"(文心大模型4.0), "ERNIE-Bot"(文心一言), "ERNIE-Bot-turbo", "BLOOMZ-7B", "Llama-2-70B-Chat", "Llama-2-13B-Chat", "Llama-2-7B-Chat", "ERNIE-Speed-128K", "ERNIE-Speed-8K", "ERNIE-Lite-8K"


# 如果使用ChatGLM3或ChatGLM4本地模型，请把 LLM_MODEL="chatglm3" 或LLM_MODEL="chatglm4"，并在此处指定模型路径
CHATGLM_LOCAL_MODEL_PATH = "THUDM/glm-4-9b-chat" # 例如"/home/hmp/ChatGLM3-6B/"

# 如果使用ChatGLM2微调模型，请把 LLM_MODEL="chatglmft"，并在此处指定模型路径
CHATGLM_PTUNING_CHECKPOINT = "" # 例如"/home/hmp/ChatGLM2-6B/ptuning/output/6b-pt-128-1e-2/checkpoint-100"


# 本地LLM模型如ChatGLM的执行方式 CPU/GPU
LOCAL_MODEL_DEVICE = "cpu" # 可选 "cuda"
LOCAL_MODEL_QUANT = "FP16" # 默认 "FP16" "INT4" 启用量化INT4版本 "INT8" 启用量化INT8版本


# 设置gradio的并行线程数（不需要修改）
CONCURRENT_COUNT = 100


# 是否在提交时自动清空输入框
AUTO_CLEAR_TXT = False


# 加一个live2d装饰
ADD_WAIFU = False


# 设置用户名和密码（不需要修改）（相关功能不稳定，与gradio版本和网络都相关，如果本地使用不建议加这个）
# [("username", "password"), ("username2", "password2"), ...]
AUTHENTICATION = []


# 如果需要在二级路径下运行（常规情况下，不要修改!!）
# （举例 CUSTOM_PATH = "/gpt_academic"，可以让软件运行在 http://ip:port/gpt_academic/ 下。）
CUSTOM_PATH = "/"


# HTTPS 秘钥和证书（不需要修改）
SSL_KEYFILE = ""
SSL_CERTFILE = ""


# 极少数情况下，openai的官方KEY需要伴随组织编码（格式如org-xxxxxxxxxxxxxxxxxxxxxxxx）使用
API_ORG = ""


# 如果需要使用Slack Claude，使用教程详情见 request_llms/README.md
SLACK_CLAUDE_BOT_ID = ''
SLACK_CLAUDE_USER_TOKEN = ''


# 如果需要使用AZURE（方法一：单个azure模型部署）详情请见额外文档 docs\use_azure.md
AZURE_ENDPOINT = "https://你亲手写的api名称.openai.azure.com/"
AZURE_API_KEY = "填入azure openai api的密钥"    # 建议直接在API_KEY处填写，该选项即将被弃用
AZURE_ENGINE = "填入你亲手写的部署名"            # 读 docs\use_azure.md


# 如果需要使用AZURE（方法二：多个azure模型部署+动态切换）详情请见额外文档 docs\use_azure.md
AZURE_CFG_ARRAY = {}


# 阿里云实时语音识别 配置难度较高
# 参考 https://github.com/binary-husky/gpt_academic/blob/master/docs/use_audio.md
ENABLE_AUDIO = False
ALIYUN_TOKEN=""     # 例如 f37f30e0f9934c34a992f6f64f7eba4f
ALIYUN_APPKEY=""    # 例如 RoPlZrM88DnAFkZK
ALIYUN_ACCESSKEY="" # （无需填写）
ALIYUN_SECRET=""    # （无需填写）


# GPT-SOVITS 文本转语音服务的运行地址（将语言模型的生成文本朗读出来）
TTS_TYPE = "EDGE_TTS" # EDGE_TTS / LOCAL_SOVITS_API / DISABLE
GPT_SOVITS_URL = ""
EDGE_TTS_VOICE = "zh-CN-XiaoxiaoNeural"


# 接入讯飞星火大模型 https://console.xfyun.cn/services/iat
XFYUN_APPID = "00000000"
XFYUN_API_SECRET = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
XFYUN_API_KEY = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


# 接入智谱大模型
ZHIPUAI_API_KEY = ""
ZHIPUAI_MODEL = "" # 此选项已废弃，不再需要填写


# Claude API KEY
ANTHROPIC_API_KEY = ""


# 月之暗面 API KEY
MOONSHOT_API_KEY = ""


# 零一万物(Yi Model) API KEY
YIMODEL_API_KEY = ""


# 紫东太初大模型 https://ai-maas.wair.ac.cn
TAICHU_API_KEY = ""

# Grok API KEY
GROK_API_KEY = ""

# Mathpix 拥有执行PDF的OCR功能，但是需要注册账号
MATHPIX_APPID = ""
MATHPIX_APPKEY = ""


# DOC2X的PDF解析服务，注册账号并获取API KEY: https://doc2x.noedgeai.com/login
DOC2X_API_KEY = ""


# 自定义API KEY格式
CUSTOM_API_KEY_PATTERN = ""


# Google Gemini API-Key
GEMINI_API_KEY = ''


# HUGGINGFACE的TOKEN，下载LLAMA时起作用 https://huggingface.co/docs/hub/security-tokens
HUGGINGFACE_ACCESS_TOKEN = "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"


# GROBID服务器地址（填写多个可以均衡负载），用于高质量地读取PDF文档
# 获取方法：复制以下空间https://huggingface.co/spaces/qingxu98/grobid，设为public，然后GROBID_URL = "https://(你的hf用户名如qingxu98)-(你的填写的空间名如grobid).hf.space"
GROBID_URLS = [
    "https://qingxu98-grobid.hf.space","https://qingxu98-grobid2.hf.space","https://qingxu98-grobid3.hf.space",
    "https://qingxu98-grobid4.hf.space","https://qingxu98-grobid5.hf.space", "https://qingxu98-grobid6.hf.space",
    "https://qingxu98-grobid7.hf.space", "https://qingxu98-grobid8.hf.space",
]


# Searxng互联网检索服务（这是一个huggingface空间，请前往huggingface复制该空间，然后把自己新的空间地址填在这里）
SEARXNG_URLS = [ f"https://kaletianlre-beardvs{i}dd.hf.space/" for i in range(1,5) ]


# 是否允许通过自然语言描述修改本页的配置，该功能具有一定的危险性，默认关闭
ALLOW_RESET_CONFIG = False


# 在使用AutoGen插件时，是否使用Docker容器运行代码
AUTOGEN_USE_DOCKER = False


# 临时的上传文件夹位置，请尽量不要修改
PATH_PRIVATE_UPLOAD = "private_upload"


# 日志文件夹的位置，请尽量不要修改
PATH_LOGGING = "gpt_log"


# 存储翻译好的arxiv论文的路径，请尽量不要修改
ARXIV_CACHE_DIR = "gpt_log/arxiv_cache"


# 除了连接OpenAI之外，还有哪些场合允许使用代理，请尽量不要修改
WHEN_TO_USE_PROXY = ["Connect_OpenAI", "Download_LLM", "Download_Gradio_Theme", "Connect_Grobid",
                     "Warmup_Modules", "Nougat_Download", "AutoGen", "Connect_OpenAI_Embedding"]


# 启用插件热加载
PLUGIN_HOT_RELOAD = False


# 自定义按钮的最大数量限制
NUM_CUSTOM_BASIC_BTN = 4


# 媒体智能体的服务地址（这是一个huggingface空间，请前往huggingface复制该空间，然后把自己新的空间地址填在这里）
DAAS_SERVER_URLS = [ f"https://niuziniu-biligpt{i}.hf.space/stream" for i in range(1,5) ]


# 在互联网搜索组件中，负责将搜索结果整理成干净的Markdown
JINA_API_KEY = ""

"""
--------------- 配置关联关系说明 ---------------

在线大模型配置关联关系示意图
│
├── "gpt-3.5-turbo" 等openai模型
│   ├── API_KEY
│   ├── CUSTOM_API_KEY_PATTERN（不常用）
│   ├── API_ORG（不常用）
│   └── API_URL_REDIRECT（不常用）
│
├── "azure-gpt-3.5" 等azure模型（单个azure模型，不需要动态切换）
│   ├── API_KEY
│   ├── AZURE_ENDPOINT
│   ├── AZURE_API_KEY
│   ├── AZURE_ENGINE
│   └── API_URL_REDIRECT
│
├── "azure-gpt-3.5" 等azure模型（多个azure模型，需要动态切换，高优先级）
│   └── AZURE_CFG_ARRAY
│
├── "spark" 星火认知大模型 spark & sparkv2
│   ├── XFYUN_APPID
│   ├── XFYUN_API_SECRET
│   └── XFYUN_API_KEY
│
├── "claude-3-opus-20240229" 等claude模型
│   └── ANTHROPIC_API_KEY
│
├── "stack-claude"
│   ├── SLACK_CLAUDE_BOT_ID
│   └── SLACK_CLAUDE_USER_TOKEN
│
├── "qianfan" 百度千帆大模型库
│   ├── BAIDU_CLOUD_QIANFAN_MODEL
│   ├── BAIDU_CLOUD_API_KEY
│   └── BAIDU_CLOUD_SECRET_KEY
│
├── "glm-4", "glm-3-turbo", "zhipuai" 智谱AI大模型
│   └── ZHIPUAI_API_KEY
│
├── "yi-34b-chat-0205", "yi-34b-chat-200k" 等零一万物(Yi Model)大模型
│   └── YIMODEL_API_KEY
│
├── "qwen-turbo" 等通义千问大模型
│   └──  DASHSCOPE_API_KEY
│
├── "Gemini"
│   └──  GEMINI_API_KEY
│
└── "one-api-...(max_token=...)" 用一种更方便的方式接入one-api多模型管理界面
    ├── AVAIL_LLM_MODELS
    ├── API_KEY
    └── API_URL_REDIRECT


本地大模型示意图
│
├── "chatglm4"
├── "chatglm3"
├── "chatglm"
├── "chatglm_onnx"
├── "chatglmft"
├── "internlm"
├── "moss"
├── "jittorllms_pangualpha"
├── "jittorllms_llama"
├── "deepseekcoder"
├── "qwen-local"
├──  RWKV的支持见Wiki
└── "llama2"


用户图形界面布局依赖关系示意图
│
├── CHATBOT_HEIGHT 对话窗的高度
├── CODE_HIGHLIGHT 代码高亮
├── LAYOUT 窗口布局
├── DARK_MODE 暗色模式 / 亮色模式
├── DEFAULT_FN_GROUPS 插件分类默认选项
├── THEME 色彩主题
├── AUTO_CLEAR_TXT 是否在提交时自动清空输入框
├── ADD_WAIFU 加一个live2d装饰
└── ALLOW_RESET_CONFIG 是否允许通过自然语言描述修改本页的配置，该功能具有一定的危险性


插件在线服务配置依赖关系示意图
│
├── 互联网检索
│   └── SEARXNG_URLS
│
├── 语音功能
│   ├── ENABLE_AUDIO
│   ├── ALIYUN_TOKEN
│   ├── ALIYUN_APPKEY
│   ├── ALIYUN_ACCESSKEY
│   └── ALIYUN_SECRET
│
└── PDF文档精准解析
    ├── GROBID_URLS
    ├── MATHPIX_APPID
    └── MATHPIX_APPKEY


"""
