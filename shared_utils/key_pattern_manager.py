import re
import os
from functools import wraps, lru_cache
from shared_utils.advanced_markdown_format import format_io
from shared_utils.config_loader import get_conf as get_conf


pj = os.path.join
default_user_name = 'default_user'

# match openai keys
openai_regex = re.compile(
    r"sk-[a-zA-Z0-9_-]{48}$|" +
    r"sk-[a-zA-Z0-9_-]{92}$|" +
    r"sk-proj-[a-zA-Z0-9_-]{48}$|"+
    r"sk-proj-[a-zA-Z0-9_-]{124}$|"+
    r"sk-proj-[a-zA-Z0-9_-]{156}$|"+ #新版apikey位数不匹配故修改此正则表达式
    r"sess-[a-zA-Z0-9]{40}$"
)
def is_openai_api_key(key):
    CUSTOM_API_KEY_PATTERN = get_conf('CUSTOM_API_KEY_PATTERN')
    if len(CUSTOM_API_KEY_PATTERN) != 0:
        API_MATCH_ORIGINAL = re.match(CUSTOM_API_KEY_PATTERN, key)
    else:
        API_MATCH_ORIGINAL = openai_regex.match(key)
    return bool(API_MATCH_ORIGINAL)


def is_azure_api_key(key):
    API_MATCH_AZURE = re.match(r"[a-zA-Z0-9]{32}$", key)
    return bool(API_MATCH_AZURE)


def is_api2d_key(key):
    API_MATCH_API2D = re.match(r"fk[a-zA-Z0-9]{6}-[a-zA-Z0-9]{32}$", key)
    return bool(API_MATCH_API2D)

def is_openroute_api_key(key):
    API_MATCH_OPENROUTE = re.match(r"sk-or-v1-[a-zA-Z0-9]{64}$", key)
    return bool(API_MATCH_OPENROUTE)

def is_cohere_api_key(key):
    API_MATCH_AZURE = re.match(r"[a-zA-Z0-9]{40}$", key)
    return bool(API_MATCH_AZURE)


def is_any_api_key(key):
    # key 一般只包含字母、数字、下划线、逗号、中划线
    if not re.match(r"^[a-zA-Z0-9_\-,]+$", key):
        # 如果配置了 CUSTOM_API_KEY_PATTERN，再检查以下以免误杀
        if CUSTOM_API_KEY_PATTERN := get_conf('CUSTOM_API_KEY_PATTERN'):
            return bool(re.match(CUSTOM_API_KEY_PATTERN, key))
        return False

    if ',' in key:
        keys = key.split(',')
        for k in keys:
            if is_any_api_key(k): return True
        return False
    else:
        return is_openai_api_key(key) or is_api2d_key(key) or is_azure_api_key(key) or is_cohere_api_key(key)


def what_keys(keys):
    avail_key_list = {'OpenAI Key': 0, "Azure Key": 0, "API2D Key": 0}
    key_list = keys.split(',')

    for k in key_list:
        if is_openai_api_key(k):
            avail_key_list['OpenAI Key'] += 1

    for k in key_list:
        if is_api2d_key(k):
            avail_key_list['API2D Key'] += 1

    for k in key_list:
        if is_azure_api_key(k):
            avail_key_list['Azure Key'] += 1

    return f"检测到： OpenAI Key {avail_key_list['OpenAI Key']} 个, Azure Key {avail_key_list['Azure Key']} 个, API2D Key {avail_key_list['API2D Key']} 个"


def select_api_key(keys, llm_model):
    import random
    avail_key_list = []
    key_list = keys.split(',')

    if llm_model.startswith('gpt-') or llm_model.startswith('chatgpt-') or \
       llm_model.startswith('one-api-') or llm_model == 'o1' or llm_model.startswith('o1-'):
        for k in key_list:
            if is_openai_api_key(k): avail_key_list.append(k)

    if llm_model.startswith('api2d-'):
        for k in key_list:
            if is_api2d_key(k): avail_key_list.append(k)

    if llm_model.startswith('azure-'):
        for k in key_list:
            if is_azure_api_key(k): avail_key_list.append(k)

    if llm_model.startswith('cohere-'):
        for k in key_list:
            if is_cohere_api_key(k): avail_key_list.append(k)
    
    if llm_model.startswith('openrouter-'):
        for k in key_list:
            if is_openroute_api_key(k): avail_key_list.append(k)

    if len(avail_key_list) == 0:
        raise RuntimeError(f"您提供的api-key不满足要求，不包含任何可用于{llm_model}的api-key。您可能选择了错误的模型或请求源（左上角更换模型菜单中可切换openai,azure,claude,cohere等请求源）。")

    api_key = random.choice(avail_key_list) # 随机负载均衡
    return api_key


def select_api_key_for_embed_models(keys, llm_model):
    import random
    avail_key_list = []
    key_list = keys.split(',')

    if llm_model.startswith('text-embedding-'):
        for k in key_list:
            if is_openai_api_key(k): avail_key_list.append(k)

    if len(avail_key_list) == 0:
        raise RuntimeError(f"您提供的api-key不满足要求，不包含任何可用于{llm_model}的api-key。您可能选择了错误的模型或请求源。")

    api_key = random.choice(avail_key_list) # 随机负载均衡
    return api_key
