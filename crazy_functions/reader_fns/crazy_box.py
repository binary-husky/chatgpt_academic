# encoding: utf-8
# @Time   : 2023/6/14
# @Author : Spike
# @Descr   :
import copy
import os
import json
import re

from common.func_box import Shell, get_fold_panel,  replace_expected_text, replace_special_chars
from common.func_box import valid_img_extensions, vain_open_extensions
from common.func_box import html_tag_color, html_view_blank
from common.func_box import split_domain_url, extract_link_pf
from common.toolbox import update_ui, update_ui_lastest_msg, get_conf, trimmed_format_exc
from common.db.repository import prompt_repository
from common.knowledge_base import kb_doc_api
from crazy_functions import crazy_utils
from crazy_functions.pdf_fns.breakdown_txt import breakdown_text_to_satisfy_token_limit
from request_llms import bridge_all
from moviepy.editor import AudioFileClip
from common.path_handler import init_path
from crazy_functions import reader_fns
from common.logger_handler import logger


class Utils:

    def __init__(self):
        self.find_keys_type = 'type'
        self.find_picture_source = ['caption', 'imgID', 'sourceKey']
        self.find_document_source = ['wpsDocumentLink', 'wpsDocumentName', 'wpsDocumentType']
        self.find_document_tags = ['WPSDocument']
        self.find_picture_tags = ['picture', 'processon']
        self.picture_format = valid_img_extensions
        self.comments = []

    def find_all_text_keys(self, dictionary, parent_type=None, text_values=None, filter_type=''):
        """
        Args:
            dictionary: 字典或列表
            parent_type: 匹配的type，作为新列表的key，用于分类
            text_values: 存储列表
            filter_type: 当前层级find_keys_type==filter_type时，不继续往下嵌套
        Returns:
            text_values和排序后的context_
        """
        # 初始化 text_values 为空列表，用于存储找到的所有text值
        if text_values is None:
            text_values = []
        # 如果输入的dictionary不是字典类型，返回已收集到的text值
        if not isinstance(dictionary, dict):
            return text_values
        # 获取当前层级的 type 值
        current_type = dictionary.get(self.find_keys_type, parent_type)
        # 如果字典中包含 'text' 或 'caption' 键，将对应的值添加到 text_values 列表中
        if 'comments' in dictionary:
            temp = dictionary.get('comments', [])
            for t in temp:
                if type(t) is dict:
                    self.comments.append(t.get('key'))
        if 'text' in dictionary:
            content_value = dictionary.get('text', None)
            text_values.append({current_type: content_value})
        if 'caption' in dictionary:
            temp = {}
            for key in self.find_picture_source:
                temp[key] = dictionary.get(key, None)
            text_values.append({current_type: temp})
        if 'wpsDocumentId' in dictionary:
            temp = {}
            for key in self.find_document_source:
                temp[key] = dictionary.get(key, None)
            text_values.append({current_type: temp})
        # 如果当前类型不等于 filter_type，则继续遍历子级属性
        if current_type != filter_type:
            for key, value in dictionary.items():
                if isinstance(value, dict):
                    self.find_all_text_keys(value, current_type, text_values, filter_type)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self.find_all_text_keys(item, current_type, text_values, filter_type)
        return text_values

    def statistical_results(self, text_values, img_proce=False):
        """
        Args: 提取爬虫内嵌图片、文件等等信息
            text_values: dict
            img_proce: 图片标识
        Returns: （元数据， 组合数据， 图片dict， 文件dict）
        """
        context_ = []
        pic_dict = {}
        file_dict = {}
        for i in text_values:
            for key, value in i.items():
                if key in self.find_picture_tags:
                    if img_proce:
                        mark = f'{key}"""\n{value["sourceKey"]}\n"""\n'
                        if value["caption"]: mark += f'\n{key}:{value["caption"]}\n\n'
                        context_.append(mark)
                        pic_dict[value['sourceKey']] = value['imgID']
                    else:
                        if value["caption"]: context_.append(f'{key}描述: {value["caption"]}\n')
                        pic_dict[value['sourceKey']] = value['imgID']
                elif key in self.find_document_tags:
                    mark = f'{value["wpsDocumentName"]}: {value["wpsDocumentLink"]}'
                    file_dict.update({value["wpsDocumentName"]: value["wpsDocumentLink"]})
                    context_.append(mark)
                else:
                    context_.append(value)
        context_ = '\n'.join(context_)
        return text_values, context_, pic_dict, file_dict

    def write_markdown(self, data, hosts, file_name):
        """
        Args: 将data写入md文件
            data: 数据
            hosts: 用户标识
            file_name: 另取文件名
        Returns: 写入的文件地址
        """
        user_path = os.path.join(init_path.private_files_path, hosts, 'markdown')
        os.makedirs(user_path, exist_ok=True)
        md_file = os.path.join(user_path, f"{file_name}.md")
        with open(file=md_file, mode='w', encoding='utf-8') as f:
            f.write(data)
        return md_file

    def markdown_to_flow_chart(self, data, hosts, file_name):
        """
        Args: 调用markmap-cli
            data: 要写入md的数据
            hosts: 用户标识
            file_name: 要写入的文件名
        Returns: [md, 流程图] 文件
        """
        user_path = os.path.join(init_path.private_files_path, hosts, 'mark_map')
        os.makedirs(user_path, exist_ok=True)
        md_file = self.write_markdown(data, hosts, file_name)
        html_file = os.path.join(user_path, f"{file_name}.html")
        Shell(f'npx markmap-cli --no-open "{md_file}" -o "{html_file}"').start()
        return md_file, html_file

    def global_search_for_files(self, file_path, matching: list):
        file_list = []
        if os.path.isfile(file_path):
            file_list.append(file_path)
        for root, dirs, files in os.walk(file_path):
            for file in files:
                for math in matching:
                    if str(math).lower() in str(file).lower():
                        file_list.append(os.path.join(root, file))
        return file_list


# <---------------------------------------乱七八糟的方法，有点用，很好用----------------------------------------->
def find_index_inlist(data_list: list, search_terms: list) -> int:
    """ 在data_list找到符合search_terms字符串，找到后直接返回下标
    Args:
        data_list: list数据，最多往里面找两层
        search_terms: list数据，符合一个就返回数据
    Returns: 对应的下标
    """
    for i, sublist in enumerate(data_list):
        if any(term in str(sublist) for term in search_terms):
            return i
        for j, item in enumerate(sublist):
            if any(term in str(item) for term in search_terms):
                return i
    return 0  # 如果没有找到匹配的元素，则返回初始坐标


def file_reader_content(file_path, save_path, plugin_kwargs):
    reader_statsu = ''
    file_content = ''

    if file_path.endswith('pdf'):
        content = reader_fns.PDFHandler(file_path, save_path).get_markdown()
        file_content = "".join(content)
    elif file_path.endswith('docx') or file_path.endswith('doc'):
        file_content = reader_fns.DocxHandler(file_path, save_path).get_markdown()
    elif file_path.endswith('xmind'):
        file_content = reader_fns.XmindHandle(file_path, save_path).get_markdown()
    elif file_path.endswith('mp4'):
        file_content = reader_fns.AudioHandler(file_path).video_converters()
    elif file_path.endswith('xlsx') or file_path.endswith('xls'):
        sheet, = json_args_return(plugin_kwargs, keys=['读取指定Sheet'], default='测试要点')
        # 创建文件对象
        ex_handle = reader_fns.XlsxHandler(file_path, save_path, sheet=sheet)
        if sheet in ex_handle.workbook.sheetnames:
            ex_handle.split_merged_cells(save_work=False)  # 避免更改到原文件
            xlsx_dict = ex_handle.read_as_dict()
            file_content = xlsx_dict.get(sheet)
        else:
            active_sheet = ex_handle.workbook.active.title
            ex_handle.sheet = active_sheet
            ex_handle.split_merged_cells(save_work=False)
            xlsx_dict = ex_handle.read_as_dict()
            file_content = xlsx_dict.get(active_sheet)
            reader_statsu += f'\n\n无法在`{os.path.basename(file_path)}`找到`{sheet}`工作表，' \
                             f'将读取上次预览的活动工作表`{active_sheet}`，' \
                             f'若你的用例工作表是其他名称, 请及时暂停插件运行，并在自定义插件配置中更改' \
                             f'{html_tag_color("读取指定Sheet")}。'
        plugin_kwargs['写入指定模版'] = file_path
        plugin_kwargs['写入指定Sheet'] = ex_handle.sheet
    elif file_path.split('.')[-1] not in vain_open_extensions:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            reader_statsu += f'An error occurred while reading the file: {e}'
    return file_content, reader_statsu


def file_extraction_intype(file_mapping, chatbot, history, llm_kwargs, plugin_kwargs):
    # 文件读取
    file_limit = {}
    file_format = get_fold_panel()
    old_say = chatbot[-1][1] + '\n\n'
    for file_path in file_mapping:
        chatbot[-1][1] = old_say + file_format(
            title=f'正在解析本地文件:【{file_path.replace(init_path.base_path, ".")}】')
        yield from update_ui(chatbot, history)
        save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'])
        content, status = file_reader_content(file_path, save_path, plugin_kwargs)
        if isinstance(content, str):
            file_limit[file_path] = content.replace(init_path.base_path, 'file=.')
        else:
            file_limit[file_path] = content
        mapping_data = "\n\n--\n\n".join([f"{file_limit[fp]}" for fp in file_limit])
        chatbot[-1][1] = old_say + file_format(title=f'文件解析完成', content=mapping_data, status='Done')
        yield from update_ui(chatbot, history, msg=status)
    return file_limit


def json_args_return(kwargs: dict, keys: list, default=None) -> list:
    """
    Args: 提取插件的调优参数，如果有，则返回取到的值，如果无，则返回False
        kwargs: 一般是plugin_kwargs
        keys: 需要取得key
        default: 找不到时总得返回什么东西
    Returns: 有key返value，无key返False
    """
    temp = [default for i in range(len(keys))]
    for i in range(len(keys)):
        try:
            temp[i] = kwargs[keys[i]]
        except Exception:
            try:
                temp[i] = json.loads(kwargs['advanced_arg'])[keys[i]]
            except Exception as f:
                try:
                    temp[i] = kwargs['parameters_def'][keys[i]]
                except Exception as f:
                    temp[i] = default
    return temp


def long_name_processing(file_name):
    """
    Args:
        file_name: 文件名取材，如果是list，则取下标0，转换为str， 如果是str则取最多20个字符
    Returns: 返回处理过的文件名
    """
    if type(file_name) is list:
        file_name = file_name[0]
    if len(file_name) > 20:
        for i in file_name.splitlines():
            i = re.sub(r"\s+", " ", i)
            if i:
                file_name = replace_special_chars(i[:20])  # 限制文件名最长20个字符
                break
    if file_name.find('.') != -1:
        file_name = "".join(file_name.split('.')[:-1])
    return file_name


# <---------------------------------------插件用了都说好方法----------------------------------------->
def split_list_token_limit(data, get_num, max_num=500):
    header_index = find_index_inlist(data_list=data, search_terms=['操作步骤', '前置条件', '预期结果'])
    header_data = data[header_index]
    max_num -= len(str(header_data))
    temp_list = []
    split_data = []
    for index in data[header_index + 1:]:
        if get_num(str(temp_list)) > max_num:
            temp_list.insert(0, header_data)
            split_data.append(json.dumps(temp_list, ensure_ascii=False))
            temp_list = []
        else:
            temp_list.append(index)
    return split_data


def split_content_limit(inputs: str, llm_kwargs, chatbot, history) -> list:
    """
    Args:
        inputs: 需要提取拆分的提问信息
        llm_kwargs: 调优参数
        chatbot: 对话组件
        history: 历史记录
    Returns: [拆分1， 拆分2]
    """
    model = llm_kwargs['llm_model']
    if model.find('&') != -1:  # 判断是否多模型，如果多模型，那么使用tokens最少的进行拆分
        models = str(model).split('&')
        _tokens = []
        _num_func = {}
        for _model in models:
            num_s = bridge_all.model_info[_model]['max_token']
            _tokens.append(num_s)
            _num_func[num_s] = _model
        all_tokens = min(_tokens)
        get_token_num = bridge_all.model_info[_num_func[all_tokens]]['token_cnt']
    else:
        all_tokens = bridge_all.model_info[model]['max_token']
        get_token_num = bridge_all.model_info[model]['token_cnt']
    max_token = all_tokens / 2 - all_tokens / 4  # 考虑到对话+回答会超过tokens,所以/2
    segments = []
    gpt_latest_msg = chatbot[-1][1]
    if type(inputs) is list:
        if get_token_num(str(inputs)) > max_token:
            bro_say = gpt_latest_msg + f'\n\n提交数据预计会超出`{all_tokens}' \
                                       f'token`限制, 将按照模型最大可接收token拆分为多线程运行\n\n---\n\n'
            yield from update_ui_lastest_msg(bro_say, chatbot, history)
            segments.extend(split_list_token_limit(data=inputs, get_num=get_token_num, max_num=max_token))
        else:
            segments.append(json.dumps(inputs, ensure_ascii=False))
    else:
        inputs = inputs.split('\n---\n')
        for input_ in inputs:
            if get_token_num(input_) > max_token:
                bro_say = gpt_latest_msg + f'\n\n{html_tag_color(input_[0][:20])} 对话数据预计会超出`{all_tokens}' \
                                           f'token`限制, 将按照模型最大可接收token拆分为多线程运行'
                yield from update_ui_lastest_msg(bro_say, chatbot, history)
                segments.extend(
                    breakdown_text_to_satisfy_token_limit(input_, max_token, llm_kwargs['llm_model']))
            else:
                segments.append(input_)
    yield from update_ui(chatbot, history)
    return segments


def input_output_processing(gpt_response_collection, llm_kwargs, plugin_kwargs, chatbot, history,
                            kwargs_prompt: str = False, knowledge_base: bool = False):
    """
    Args:
        gpt_response_collection:  多线程GPT的返回结果or文件读取处理后的结果
        plugin_kwargs: 对话使用的插件参数
        chatbot: 对话组件
        history: 历史对话
        llm_kwargs:  调优参数
        kwargs_prompt: Prompt名称, 如果为False，则不添加提示词
        knowledge_base: 是否启用知识库
    Returns: 下次使用？
        inputs_array， inputs_show_user_array
    """
    inputs_array = []
    inputs_show_user_array = []
    prompt_cls, = json_args_return(plugin_kwargs, ['提示词分类'])
    ipaddr = llm_kwargs['ipaddr']
    if kwargs_prompt:
        prompt = prompt_repository.query_prompt(kwargs_prompt, prompt_cls, ipaddr, quote_num=True)
        if prompt:
            prompt = prompt.value
        else:
            raise ValueError('指定的提示词不存在')
    else:
        prompt = '{{{v}}}'
    for inputs, you_say in zip(gpt_response_collection[1::2], gpt_response_collection[0::2]):
        content_limit = yield from split_content_limit(inputs, llm_kwargs, chatbot, history)
        try:
            plugin_kwargs['上阶段文件'] = you_say
            plugin_kwargs[you_say] = {}
            plugin_kwargs[you_say]['原测试用例数据'] = [json.loads(limit)[1:] for limit in content_limit]
            plugin_kwargs[you_say]['原测试用例表头'] = json.loads(content_limit[0])[0]
        except Exception as f:
            print(f'读取原测试用例报错 {f}')
        for limit in content_limit:
            # 拼接内容与提示词
            plugin_prompt = replace_expected_text(prompt, content=limit, expect='{{{v}}}')
            inputs_array.append(plugin_prompt)
            inputs_show_user_array.append(you_say)
    yield from update_ui(chatbot, history)
    return inputs_array, inputs_show_user_array


def submit_no_use_ui_task(txt_proc, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, *args):
    inputs_show_user = None  # 不重复展示
    gpt_say = yield from crazy_utils.request_gpt_model_in_new_thread_with_ui_alive(
        inputs=txt_proc, inputs_show_user=inputs_show_user,
        llm_kwargs=llm_kwargs, chatbot=chatbot, history=history,
        sys_prompt="", refresh_interval=0.1
    )
    gpt_response_collection = [txt_proc, gpt_say]
    history.extend(gpt_response_collection)


def submit_multithreaded_tasks(inputs_array, inputs_show_user_array, llm_kwargs, chatbot, history, plugin_kwargs):
    """
    Args: 提交多线程任务
        inputs_array: 需要提交给gpt的任务列表
        inputs_show_user_array: 显示在user页面上信息
        llm_kwargs: 调优参数
        chatbot: 对话组件
        history: 历史对话
        plugin_kwargs: 插件调优参数
    Returns:  将对话结果返回[输入, 输出]
    """
    apply_history, = json_args_return(plugin_kwargs, ['上下文关联'], True)
    if apply_history:
        history_array = [[history] for _ in range(len(inputs_array))]
    else:
        history_array = [[] for _ in range(len(inputs_array))]
    # 是否要多线程处理
    if len(inputs_array) == 1:
        inputs_show_user = None  # 不重复展示
        gpt_say = yield from crazy_utils.request_gpt_model_in_new_thread_with_ui_alive(
            inputs=inputs_array[0], inputs_show_user=inputs_show_user,
            llm_kwargs=llm_kwargs, chatbot=chatbot, history=history_array[0],
            sys_prompt="", refresh_interval=0.1
        )
        gpt_response_collection = [inputs_show_user_array[0], gpt_say]
        history.extend(gpt_response_collection)
    else:
        gpt_response_collection = yield from crazy_utils.request_gpt_model_multi_threads_with_very_awesome_ui_and_high_efficiency(
            inputs_array=inputs_array,
            inputs_show_user_array=inputs_show_user_array,
            llm_kwargs=llm_kwargs,
            chatbot=chatbot,
            history_array=history_array,
            sys_prompt_array=["" for _ in range(len(inputs_array))],
            # max_workers=5,  # OpenAI所允许的最大并行过载
        )
    if apply_history:
        history.extend(gpt_response_collection)
    return gpt_response_collection


def func_拆分与提问(file_limit, llm_kwargs, plugin_kwargs, chatbot, history, plugin_prompt, knowledge_base):
    many_llm = json_args_return(plugin_kwargs, ['多模型并行'], )
    if many_llm[0]:
        llm_kwargs['llm_model'] = "&".join([i for i in many_llm[0].split('&') if i])
    split_content_limit = yield from input_output_processing(file_limit, llm_kwargs, plugin_kwargs,
                                                             chatbot, history, kwargs_prompt=plugin_prompt,
                                                             knowledge_base=knowledge_base)
    inputs_array, inputs_show_user_array = split_content_limit
    gpt_response_collection = yield from submit_multithreaded_tasks(inputs_array, inputs_show_user_array,
                                                                    llm_kwargs, chatbot, history,
                                                                    plugin_kwargs)
    return gpt_response_collection


# <---------------------------------------写入文件方法----------------------------------------->
def file_classification_to_dict(gpt_response_collection):
    """
    接收gpt多线程的返回数据，将输入相同的作为key, gpt返回以列表形式添加到对应的key中，主要是为了区分不用文件的输入
    Args:
        gpt_response_collection: 多线程GPT的返回耶
    Returns: {'文件': [结果1， 结果2...], '文件2': [结果1， 结果2...]}
    """
    file_classification = {}
    for inputs, you_say in zip(gpt_response_collection[1::2], gpt_response_collection[0::2]):
        file_classification[you_say] = []
    for inputs, you_say in zip(gpt_response_collection[1::2], gpt_response_collection[0::2]):
        file_classification[you_say].append(inputs)
    return file_classification


def batch_recognition_images_to_md(img_list, ipaddr):
    """
    Args: 将图片批量识别然后写入md文件
        img_list: 图片地址list
        ipaddr: 用户所属标识
    Returns: [文件list]
    """
    temp_list = []
    save_path = os.path.join(init_path.private_files_path, ipaddr, 'ocr_to_md')
    for img in img_list:
        if os.path.exists(img):
            img_content, img_result, _ = reader_fns.ImgHandler(img, save_path).get_paddle_ocr()
            temp_file = os.path.join(save_path,
                                     img_content.splitlines()[0][:20] + '.md')
            with open(temp_file, mode='w', encoding='utf-8') as f:
                f.write(f"{html_view_blank(temp_file)}\n\n" + img_content)
            temp_list.append(temp_list)
        else:
            print(img, '文件路径不存在')
    return temp_list


def name_de_add_sort(response, index=0):
    if type(index) is not int:
        return response  # 如果不是数字下标，那么不排序
    try:
        unique_tuples = set(tuple(lst) for lst in response)
        de_result = [list(tpl) for tpl in unique_tuples]
        d = {}
        for i, v in enumerate(de_result):
            if len(v) >= index:
                if v[index] not in d:
                    d[v[index]] = i
            else:
                d[v[len(v)]] = i
        de_result.sort(key=lambda x: d[x[index]])
        return de_result
    except:
        from common.toolbox import trimmed_format_exc
        tb_str = '```\n' + trimmed_format_exc() + '```'
        print(tb_str)
        return response


def parsing_json_in_text(txt_data: list, old_case, filter_list: list = 'None----', tags='插件补充的用例', sort_index=0):
    response = []
    desc = '\n\n---\n\n'.join(txt_data)
    for index in range(len(old_case)):
        # 获取所有Json
        supplementary_data = reader_fns.MdProcessor(txt_data[index]).json_to_list()
        # 兼容一下哈
        if len(txt_data) != len(old_case): index = -1
        # 过滤掉产出带的表头数据
        filtered_supplementary_data = [data for data in supplementary_data
                                       if filter_list[:5] != data[:5] or filter_list[-5:] != data[-5:]]
        # 检查 filtered_supplementary_data 是否为空
        if not filtered_supplementary_data:
            max_length = 0  # 或其他合适的默认值
        else:
            max_length = max(len(lst) for lst in filtered_supplementary_data)
        supplement_temp_data = [lst + [''] * (max_length - len(lst)) for lst in filtered_supplementary_data]
        for new_case in supplement_temp_data:
            if new_case not in old_case[index] and new_case + [tags] not in old_case[index]:
                old_case[index].append(new_case + [tags])
        response.extend(old_case[index])
    # 按照名称排列重组
    response = name_de_add_sort(response, sort_index)
    return response, desc


def result_extract_to_test_cases(gpt_response_collection, llm_kwargs, plugin_kwargs, chatbot, history):
    """
    Args:
        gpt_response_collection: [输入文件标题， 输出]
        llm_kwargs: 调优参数
        plugin_kwargs: 插件调优参数
        chatbot: 对话组件
        history: 对话历史
        file_key: 存入历史文件
    Returns: None
    """
    template_file, sheet, sort_index = json_args_return(plugin_kwargs,
                                                        ['写入指定模版', '写入指定Sheet', '用例下标排序'])
    file_classification = file_classification_to_dict(gpt_response_collection)
    chat_file_list = ''
    you_say = '准备将测试用例写入Excel中...'
    chatbot.append([you_say, chat_file_list])
    yield from update_ui(chatbot, history)
    files_limit = {}
    for file_name in file_classification:
        # 处理md数据
        test_case = reader_fns.MdProcessor(file_classification[file_name]).tabs_to_list()
        sort_test_case = name_de_add_sort(test_case, sort_index)
        # 正式准备写入文件
        save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'], 'test_case')
        xlsx_handler = reader_fns.XlsxHandler(template_file, output_dir=save_path, sheet=sheet)
        xlsx_handler.split_merged_cells()  # 先把合并的单元格拆分，避免写入失败
        file_path = xlsx_handler.list_write_to_excel(sort_test_case, save_as_name=long_name_processing(file_name))
        chat_file_list += f'{file_name}生成结果如下:\t {html_view_blank(__href=file_path, to_tabs=True)}\n\n'
        chatbot[-1] = [you_say, chat_file_list]
        yield from update_ui(chatbot, history)
        files_limit.update({file_path: file_name})
    return files_limit


def result_supplementary_to_test_case(gpt_response_collection, llm_kwargs, plugin_kwargs, chatbot, history):
    template_file, sheet, sort_index = json_args_return(plugin_kwargs,
                                                        ['写入指定模版', '写入指定Sheet', '用例下标排序'])
    if not sheet:
        sheet, = json_args_return(plugin_kwargs, ['读取指定Sheet'])
    file_classification = file_classification_to_dict(gpt_response_collection)
    chat_file_list = ''
    you_say = '准备将测试用例写入Excel中...'
    chatbot.append([you_say, chat_file_list])
    yield from update_ui(chatbot, history)
    files_limit = {}
    for file_name in file_classification:
        old_file = plugin_kwargs['上阶段文件']
        old_case = plugin_kwargs[old_file].get('原测试用例数据', [])
        header = plugin_kwargs[old_file].get('原测试用例表头', [])
        test_case, desc = parsing_json_in_text(file_classification[file_name], old_case, filter_list=header,
                                               sort_index=sort_index)
        save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'], 'test_case')
        # 写入excel
        xlsx_handler = reader_fns.XlsxHandler(template_file, output_dir=save_path, sheet=sheet)
        file_path = xlsx_handler.list_write_to_excel(test_case, save_as_name=long_name_processing(file_name))
        # 写入 markdown
        md_path = os.path.join(save_path, f"{long_name_processing(file_name)}.md")
        reader_fns.MdHandler(md_path).save_markdown(desc)
        chat_file_list += f'{file_name}生成结果如下:\t {html_view_blank(__href=file_path, to_tabs=True)}\n\n' \
                          f'{file_name}补充思路如下：\t{html_view_blank(__href=md_path, to_tabs=True)}\n\n---\n\n'
        chatbot[-1] = [you_say, chat_file_list]
        yield from update_ui(chatbot, history)
        files_limit.update({file_path: file_name})
    return files_limit


def result_converter_to_flow_chart(gpt_response_collection, llm_kwargs, plugin_kwargs, chatbot, history):
    """
    Args: 将输出结果写入md，并转换为流程图
        gpt_response_collection: [输入、输出]
        llm_kwargs: 调优参数
        chatbot: 对话组件
        history: 历史对话
    Returns:
        None
    """
    file_classification = file_classification_to_dict(gpt_response_collection)
    file_limit = {}
    chat_file_list = ''
    you_say = '请将Markdown结果转换为流程图~'
    chatbot.append([you_say, chat_file_list])
    for file_name in file_classification:
        inputs_count = ''
        for value in file_classification[file_name]:
            inputs_count += str(value).replace('```', '')  # 去除头部和尾部的代码块, 避免流程图堆在一块
        save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'])
        md_file = os.path.join(save_path, f"{long_name_processing(file_name)}.md")
        html_file = reader_fns.MdHandler(md_path=md_file, output_dir=save_path).save_mark_map()
        chat_file_list += "View: " + html_view_blank(md_file, to_tabs=True) + \
                          '\n\n--- \n\n View: ' + html_view_blank(html_file)
        chatbot.append([you_say, chat_file_list])
        yield from update_ui(chatbot=chatbot, history=history, msg='成功写入文件！')
        file_limit.update({md_file: file_name})
    # f'tips: 双击空白处可以放大～\n\n' f'{html_iframe_code(html_file=html)}'  无用，不允许内嵌网页了
    return file_limit


def result_written_to_markdown(gpt_response_collection, llm_kwargs, plugin_kwargs, chatbot, history, stage=''):
    """
    Args: 将输出结果写入md
        gpt_response_collection: [输入、输出]
        llm_kwargs: 调优参数
        chatbot: 对话组件
        history: 历史对话
    Returns:
        None
    """
    file_classification = file_classification_to_dict(gpt_response_collection)
    file_limit = []
    chat_file_list = ''
    you_say = '请将Markdown结果写入文件中...'
    chatbot.append([you_say, chat_file_list])
    for file_name in file_classification:
        inputs_all = ''
        for value in file_classification[file_name]:
            inputs_all += value
        md = Utils().write_markdown(data=inputs_all, hosts=llm_kwargs['ipaddr'],
                                    file_name=long_name_processing(file_name) + stage)
        chat_file_list = f'markdown已写入文件，下次使用插件可以直接提交markdown文件啦 {html_view_blank(md, to_tabs=True)}'
        chatbot[-1] = [you_say, chat_file_list]
        yield from update_ui(chatbot=chatbot, history=history, msg='成功写入文件！')
        file_limit.append(md)
    return file_limit


def check_url_domain_cloud(link_limit):
    wps_links = split_domain_url(link_limit, domain_name=[get_conf('WPS_BASE_HOST'), 'wps'])
    qq_link = split_domain_url(link_limit, domain_name=[get_conf('QQ_BASE_HOST')])
    feishu_link = split_domain_url(link_limit, domain_name=[get_conf('FEISHU_BASE_HOST')])
    project_link = split_domain_url(link_limit, domain_name=[get_conf('PROJECT_BASE_HOST')])
    return wps_links, qq_link, feishu_link, project_link


def detach_cloud_links(link_limit, llm_kwargs, valid_types):
    fp_mapping = {}
    save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'])
    wps_links, qq_link, feishu_link, project_link = check_url_domain_cloud(link_limit)
    wps_status, qq_status, feishu_status = '', '', ''
    try:
        # wps云文档下载
        wps_status, wps_mapping = reader_fns.get_kdocs_from_limit(wps_links, save_path, llm_kwargs.get('wps_cookies'))
        fp_mapping.update(wps_mapping)
    except Exception as e:
        error = trimmed_format_exc()
        wps_status += f'# 下载WPS文档出错了 \n ERROR: {error} \n'

    try:
        # qq云文档下载
        qq_status, qq_mapping = reader_fns.get_qqdocs_from_limit(qq_link, save_path, llm_kwargs.get('qq_cookies'))
        fp_mapping.update(qq_mapping)
    except Exception as e:
        error = trimmed_format_exc()
        wps_status += f'# 下载QQ文档出错了 \n ERROR: {error}'

    try:
        # 飞书云文档下载
        feishu_status, feishu_mapping = reader_fns.get_feishu_from_limit(feishu_link, save_path,
                                                                         llm_kwargs.get('feishu_header'))
        fp_mapping.update(feishu_mapping)
    except Exception as e:
        error = trimmed_format_exc()
        wps_status += f'# 下载飞书文档出错了 \n ERROR: {error}'

    try:
        # 飞书项目转换
        feishu_status, feishu_mapping = reader_fns.get_project_from_limit(project_link, save_path,
                                                                          llm_kwargs.get('project_config'))
        fp_mapping.update(feishu_mapping)
    except Exception as e:
        error = trimmed_format_exc()
        wps_status += f'# 解析飞书项目出错了 \n ERROR: {error}'

    download_status = ''
    if wps_status or qq_status or feishu_status:
        download_status = "\n".join([wps_status, qq_status, feishu_status]).strip('\n')
    # 筛选文件
    for fp in fp_mapping:
        if fp.split('.')[-1] not in valid_types and valid_types != ['*']:
            download_status += '\n\n' + f'过滤掉了`{fp_mapping[fp]}`，因为不是插件能够接收处理的文件类型`{valid_types}`'
            fp_mapping.pop(fp)  # 过滤不能处理的文件

    return fp_mapping, {'status': download_status}


def content_img_vision_analyze(content: str, chatbot, history, llm_kwargs, plugin_kwargs):
    ocr_switch, = json_args_return(plugin_kwargs, ['开启OCR'])
    cor_cache = llm_kwargs.get('ocr_cache', False)
    img_mapping = extract_link_pf(content, valid_img_extensions)
    gpt_old_say = chatbot[-1][1]
    vision_format = get_fold_panel()
    # 如果开启了OCR，并且文中存在图片链接，处理图片
    if ocr_switch and img_mapping:
        vision_loading_statsu = {os.path.basename(i): "Loading..." for i in img_mapping}
        chatbot[-1][1] = gpt_old_say + vision_format(f'检测到识图开关为`{ocr_switch}`，正在识别图片中的文字...',
                                                     vision_loading_statsu)
        yield from update_ui(chatbot=chatbot, history=history)
        # 识别图片中的文字
        save_path = os.path.join(init_path.private_files_path, llm_kwargs['ipaddr'])
        if isinstance(ocr_switch, dict):  # 如果是字典，那么就是自定义OCR参数
            ocr_switch_copy = copy.deepcopy(llm_kwargs)
            ocr_switch_copy.update(ocr_switch)
        vision_submission = reader_fns.submit_threads_img_handle(img_mapping, save_path, cor_cache, ocr_switch_copy)
        filed_sum = 0
        for t in vision_submission:
            base_name = os.path.basename(t)
            try:
                img_content, img_path, status = vision_submission[t].result()

                vision_loading_statsu.update({base_name: img_content})
                chatbot[-1][1] = gpt_old_say + vision_format(f'检测到识图开关为`{ocr_switch}`，正在识别图片中的文字...',
                                                             vision_loading_statsu)
                yield from update_ui(chatbot=chatbot, history=history)
                if not status or status == '本次识别结果读取数据库缓存':  # 出现异常，不替换文本
                    content = content.replace(img_mapping[t], f'[{img_mapping[t]}]\n{base_name}图片识别结果：\n{img_content}')
                else:
                    filed_sum += 1
                    logger.warning(f'{img_mapping[t]} 识别失败，跳过，error: {status}')
            except Exception as e:
                filed_sum += 1
                status = f'`{t}` `{trimmed_format_exc()}` 识别失败，过滤这个图片\n\n'
                vision_loading_statsu.update({base_name: status})  # 错误展示完整路径
                chatbot[-1][1] = gpt_old_say + vision_format(f'啊哦，有文件失败了哦', vision_loading_statsu)
                yield from update_ui(chatbot=chatbot, history=history)

        chatbot[-1][1] = gpt_old_say + vision_format(f'图片识别完成, 共{len(vision_submission)}张图片，识别失败`{filed_sum}`', vision_loading_statsu, 'Done')
        yield from update_ui(chatbot=chatbot, history=history, msg='Done')
    return content.replace(init_path.base_path, 'file=.')  # 增加保障，防止路径泄露


def content_clear_links(user_input, clear_fp_map, clear_link_map):
    """清除文本中已处理的链接"""
    for link in clear_link_map:
        user_input = user_input.replace(link, '')
    for pf in clear_fp_map:
        user_input = user_input.replace(clear_fp_map[pf], '')
    return user_input


def input_retrieval_file(user_input, llm_kwargs, valid_types):
    # 网络链接
    fp_mapping, download_status = detach_cloud_links(user_input, llm_kwargs, valid_types)
    # 本地文件
    fp_mapping.update(extract_link_pf(user_input, valid_types))
    return fp_mapping, download_status


def user_input_embedding_content(user_input, chatbot, history, llm_kwargs, plugin_kwargs, valid_types):
    embedding_content = []  # 对话内容
    yield from update_ui(chatbot=chatbot, history=history, msg='🕵🏻‍超级侦探，正在办案～')
    if plugin_kwargs.get('embedding_content'):
        embedding_content = plugin_kwargs['embedding_content']
        plugin_kwargs['embedding_content'] = ''  # 用了即刻丢弃
    else:
        chatbot.append([user_input, ''])
        download_format = get_fold_panel()
        chatbot[-1][1] = download_format(title='检测提交是否存在需要解析的文件或链接...', content='')
        yield from update_ui(chatbot=chatbot, history=history, msg='Reader loading...')
        fp_mapping, download_status = input_retrieval_file(user_input, llm_kwargs, valid_types)
        download_status.update(fp_mapping)
        if fp_mapping:
            chatbot[-1][1] = download_format(title='链接解析完成', content=download_status, status='Done')
        content_mapping = yield from file_extraction_intype(fp_mapping, chatbot, history, llm_kwargs, plugin_kwargs)
        for content_fp in content_mapping:  # 一个文件一个对话
            file_content = content_mapping[content_fp]
            # 将解析的数据提交到正文
            input_handle = user_input.replace(fp_mapping[content_fp], str(file_content))
            # 将其他文件链接清除
            user_clear = content_clear_links(input_handle, fp_mapping, content_mapping)
            # 识别图片链接内容
            complete_input = yield from content_img_vision_analyze(user_clear, chatbot, history,
                                                                   llm_kwargs, plugin_kwargs)
            embedding_content.extend([os.path.basename(content_fp), complete_input])
        if not content_mapping:
            if len(user_input) > 100:  # 没有探测到任何文件，并且提交大于50个字符，那么运行往下走
                chatbot[-1][1] = download_format(title='没有检测到任何文件', content=download_status, status='Done')
                yield from update_ui(chatbot=chatbot, history=history, msg='没有探测到文件')
                # 识别图片链接内容
                complete_input = yield from content_img_vision_analyze(user_input, chatbot, history,
                                                                       llm_kwargs, plugin_kwargs)
                embedding_content.extend([long_name_processing(user_input), complete_input])
            else:
                devs_document = get_conf('devs_document')
                status = '\n\n没有探测到任何文件，并且提交字符少于50，无法完成后续任务' \
                         f'请在输入框中输入需要解析的云文档链接或本地文件地址，如果有多个文档则用换行或空格隔开，然后再点击对应的插件\n\n' \
                         f'插件支持解析文档类型`{valid_types}`' \
                         f"有问题？请联系`@spike` or 查看开发文档{devs_document}"
                if chatbot[-1][1] is None:
                    chatbot[-1][1] = status
                chatbot[-1][1] += status
                yield from update_ui(chatbot=chatbot, history=history, msg='没有探测到数据')
                return []
        kb_upload, = json_args_return(plugin_kwargs, ['自动录入知识库'])
        files_list = [i for i in content_mapping if os.path.exists(i)]
        if kb_upload and files_list:
            kb_doc_api.upload_docs_simple(files=files_list, knowledge_base_name=kb_upload)
    return embedding_content


# <---------------------------------------一些Tips----------------------------------------->
previously_on_plugins = f'如果是本地文件，请点击【🔗】先上传，多个文件请上传压缩包，' \
                        f'{html_tag_color("如果是网络文件或金山文档链接，请粘贴到输入框")}, 然后再次点击该插件' \
                        f'多个文件{html_tag_color("请使用换行或空格区分")}'

if __name__ == '__main__':
    test = [1, 2, 3, 4, [12], 33, 1]
