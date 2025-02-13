import datetime
import re
import os
from loguru import logger
from textwrap import dedent
from toolbox import CatchException, update_ui
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive

# TODO: 解决缩进问题

find_function_end_prompt = '''
Below is a page of code that you need to read. This page may not yet complete, you job is to split this page to separate functions, class functions etc.
- Provide the line number where the first visible function ends.
- Provide the line number where the next visible function begins.
- If there are no other functions in this page, you should simply return the line number of the last line.
- Only focus on functions declared by `def` keyword. Ignore inline functions. Ignore function calls.

------------------ Example ------------------
INPUT:

    ```
    L0000 |import sys
    L0001 |import re
    L0002 |
    L0003 |def trimmed_format_exc():
    L0004 |    import os
    L0005 |    import traceback
    L0006 |    str = traceback.format_exc()
    L0007 |    current_path = os.getcwd()
    L0008 |    replace_path = "."
    L0009 |    return str.replace(current_path, replace_path)
    L0010 |
    L0011 |
    L0012 |def trimmed_format_exc_markdown():
    L0013 |    ...
    L0014 |    ...
    ```

OUTPUT:

    ```
    <first_function_end_at>L0009</first_function_end_at>
    <next_function_begin_from>L0012</next_function_begin_from>
    ```

------------------ End of Example ------------------


------------------ the real INPUT you need to process NOW ------------------
```
{THE_TAGGED_CODE}
```
'''







revise_function_prompt = '''
You need to read the following code, and revise the source code ({FILE_BASENAME}) according to following instructions:
1. You should analyze the purpose of the functions (if there are any).
2. You need to add docstring for the provided functions (if there are any).

Be aware:
1. You must NOT modify the indent of code.
2. You are NOT authorized to change or translate non-comment code, and you are NOT authorized to add empty lines either, toggle qu.
3. Use {LANG} to add comments and docstrings. Do NOT translate Chinese that is already in the code.
4. Besides adding a docstring, use the ⭐ symbol to annotate the most core and important line of code within the function, explaining its role.

------------------ Example ------------------
INPUT:
```
L0000 |
L0001 |def zip_result(folder):
L0002 |    t = gen_time_str()
L0003 |    zip_folder(folder, get_log_folder(), f"result.zip")
L0004 |    return os.path.join(get_log_folder(), f"result.zip")
L0005 |
L0006 |
```

OUTPUT:

<instruction_1_purpose>
This function compresses a given folder, and return the path of the resulting `zip` file.
</instruction_1_purpose>
<instruction_2_revised_code>
```
def zip_result(folder):
    """
    Compresses the specified folder into a zip file and stores it in the log folder.

    Args:
        folder (str): The path to the folder that needs to be compressed.

    Returns:
        str: The path to the created zip file in the log folder.
    """
    t = gen_time_str()
    zip_folder(folder, get_log_folder(), f"result.zip")  # ⭐ Execute the zipping of folder
    return os.path.join(get_log_folder(), f"result.zip")
```
</instruction_2_revised_code>
------------------ End of Example ------------------


------------------ the real INPUT you need to process NOW ({FILE_BASENAME}) ------------------
```
{THE_CODE}
```
{INDENT_REMINDER}
{BRIEF_REMINDER}
{HINT_REMINDER}
'''


revise_function_prompt_chinese = '''
您需要阅读以下代码，并根据以下说明修订源代码({FILE_BASENAME}):
1. 如果源代码中包含函数的话, 你应该分析给定函数实现了什么功能
2. 如果源代码中包含函数的话, 你需要为函数添加docstring, docstring必须使用中文

请注意：
1. 你不得修改代码的缩进
2. 你无权更改或翻译代码中的非注释部分，也不允许添加空行
3. 使用 {LANG} 添加注释和文档字符串。不要翻译代码中已有的中文
4. 除了添加docstring之外, 使用⭐符号给该函数中最核心、最重要的一行代码添加注释，并说明其作用

------------------ 示例 ------------------
INPUT:
```
L0000 |
L0001 |def zip_result(folder):
L0002 |    t = gen_time_str()
L0003 |    zip_folder(folder, get_log_folder(), f"result.zip")
L0004 |    return os.path.join(get_log_folder(), f"result.zip")
L0005 |
L0006 |
```

OUTPUT:

<instruction_1_purpose>
该函数用于压缩指定文件夹，并返回生成的`zip`文件的路径。
</instruction_1_purpose>
<instruction_2_revised_code>
```
def zip_result(folder):
    """
    该函数将指定的文件夹压缩成ZIP文件, 并将其存储在日志文件夹中。

    输入参数:
        folder (str): 需要压缩的文件夹的路径。
    返回值:
        str: 日志文件夹中创建的ZIP文件的路径。
    """
    t = gen_time_str()
    zip_folder(folder, get_log_folder(), f"result.zip")  # ⭐ 执行文件夹的压缩
    return os.path.join(get_log_folder(), f"result.zip")
```
</instruction_2_revised_code>
------------------ End of Example ------------------


------------------ the real INPUT you need to process NOW ({FILE_BASENAME}) ------------------
```
{THE_CODE}
```
{INDENT_REMINDER}
{BRIEF_REMINDER}
{HINT_REMINDER}
'''


class PythonCodeComment():

    def __init__(self, llm_kwargs, plugin_kwargs, language, observe_window_update) -> None:
        self.original_content = ""
        self.full_context = []
        self.full_context_with_line_no = []
        self.current_page_start = 0
        self.page_limit = 100 # 100 lines of code each page
        self.ignore_limit = 20
        self.llm_kwargs = llm_kwargs
        self.plugin_kwargs = plugin_kwargs
        self.language = language
        self.observe_window_update = observe_window_update
        if self.language == "chinese":
            self.core_prompt = revise_function_prompt_chinese
        else:
            self.core_prompt = revise_function_prompt
        self.path = None
        self.file_basename = None
        self.file_brief = ""

    def generate_tagged_code_from_full_context(self):
        for i, code in enumerate(self.full_context):
            number = i
            padded_number = f"{number:04}"
            result = f"L{padded_number}"
            self.full_context_with_line_no.append(f"{result} | {code}")
        return self.full_context_with_line_no

    def read_file(self, path, brief):
        with open(path, 'r', encoding='utf8') as f:
            self.full_context = f.readlines()
        self.original_content = ''.join(self.full_context)
        self.file_basename = os.path.basename(path)
        self.file_brief = brief
        self.full_context_with_line_no = self.generate_tagged_code_from_full_context()
        self.path = path

    def find_next_function_begin(self, tagged_code:list, begin_and_end):
        begin, end = begin_and_end
        THE_TAGGED_CODE = ''.join(tagged_code)
        self.llm_kwargs['temperature'] = 0
        result = predict_no_ui_long_connection(
            inputs=find_function_end_prompt.format(THE_TAGGED_CODE=THE_TAGGED_CODE),
            llm_kwargs=self.llm_kwargs,
            history=[],
            sys_prompt="",
            observe_window=[],
            console_silence=True
        )

        def extract_number(text):
            # 使用正则表达式匹配模式
            match = re.search(r'<next_function_begin_from>L(\d+)</next_function_begin_from>', text)
            if match:
                # 提取匹配的数字部分并转换为整数
                return int(match.group(1))
            return None

        line_no = extract_number(result)
        if line_no is not None:
            return line_no
        else:
            return end

    def _get_next_window(self):
        #
        current_page_start = self.current_page_start

        if self.current_page_start == len(self.full_context) + 1:
            raise StopIteration

        # 如果剩余的行数非常少，一鼓作气处理掉
        if len(self.full_context) - self.current_page_start < self.ignore_limit:
            future_page_start = len(self.full_context) + 1
            self.current_page_start = future_page_start
            return current_page_start, future_page_start


        tagged_code = self.full_context_with_line_no[ self.current_page_start: self.current_page_start + self.page_limit]
        line_no = self.find_next_function_begin(tagged_code, [self.current_page_start, self.current_page_start + self.page_limit])

        if line_no > len(self.full_context) - 5:
            line_no = len(self.full_context) + 1

        future_page_start = line_no
        self.current_page_start = future_page_start

        # ! consider eof
        return current_page_start, future_page_start

    def dedent(self, text):
        """Remove any common leading whitespace from every line in `text`.
        """
        # Look for the longest leading string of spaces and tabs common to
        # all lines.
        margin = None
        _whitespace_only_re = re.compile('^[ \t]+$', re.MULTILINE)
        _leading_whitespace_re = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)
        text = _whitespace_only_re.sub('', text)
        indents = _leading_whitespace_re.findall(text)
        for indent in indents:
            if margin is None:
                margin = indent

            # Current line more deeply indented than previous winner:
            # no change (previous winner is still on top).
            elif indent.startswith(margin):
                pass

            # Current line consistent with and no deeper than previous winner:
            # it's the new winner.
            elif margin.startswith(indent):
                margin = indent

            # Find the largest common whitespace between current line and previous
            # winner.
            else:
                for i, (x, y) in enumerate(zip(margin, indent)):
                    if x != y:
                        margin = margin[:i]
                        break

        # sanity check (testing/debugging only)
        if 0 and margin:
            for line in text.split("\n"):
                assert not line or line.startswith(margin), \
                    "line = %r, margin = %r" % (line, margin)

        if margin:
            text = re.sub(r'(?m)^' + margin, '', text)
            return text, len(margin)
        else:
            return text, 0

    def get_next_batch(self):
        current_page_start, future_page_start = self._get_next_window()
        return ''.join(self.full_context[current_page_start: future_page_start]), current_page_start, future_page_start

    def tag_code(self, fn, hint):
        code = fn
        _, n_indent = self.dedent(code)
        indent_reminder = "" if n_indent == 0 else "(Reminder: as you can see, this piece of code has indent made up with {n_indent} whitespace, please preserve them in the OUTPUT.)"
        brief_reminder = "" if self.file_brief == "" else f"({self.file_basename} abstract: {self.file_brief})"
        hint_reminder = "" if hint is None else f"(Reminder: do not ignore or modify code such as `{hint}`, provide complete code in the OUTPUT.)"
        self.llm_kwargs['temperature'] = 0
        result = predict_no_ui_long_connection(
            inputs=self.core_prompt.format(
                LANG=self.language, 
                FILE_BASENAME=self.file_basename, 
                THE_CODE=code, 
                INDENT_REMINDER=indent_reminder, 
                BRIEF_REMINDER=brief_reminder,
                HINT_REMINDER=hint_reminder
            ),
            llm_kwargs=self.llm_kwargs,
            history=[],
            sys_prompt="",
            observe_window=[],
            console_silence=True
        )

        def get_code_block(reply):
            import re
            pattern = r"```([\s\S]*?)```" # regex pattern to match code blocks
            matches = re.findall(pattern, reply) # find all code blocks in text
            if len(matches) == 1:
                return matches[0].strip('python') #  code block
            return None

        code_block = get_code_block(result)
        if code_block is not None:
            code_block = self.sync_and_patch(original=code, revised=code_block)
            return code_block
        else:
            return code
        
    def get_markdown_block_in_html(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        found_list = soup.find_all("div", class_="markdown-body")
        if found_list:
            res = found_list[0]
            return res.prettify()
        else:
            return None


    def sync_and_patch(self, original, revised):
        """Ensure the number of pre-string empty lines in revised matches those in original."""

        def count_leading_empty_lines(s, reverse=False):
            """Count the number of leading empty lines in a string."""
            lines = s.split('\n')
            if reverse: lines = list(reversed(lines))
            count = 0
            for line in lines:
                if line.strip() == '':
                    count += 1
                else:
                    break
            return count

        original_empty_lines = count_leading_empty_lines(original)
        revised_empty_lines = count_leading_empty_lines(revised)

        if original_empty_lines > revised_empty_lines:
            additional_lines = '\n' * (original_empty_lines - revised_empty_lines)
            revised = additional_lines + revised
        elif original_empty_lines < revised_empty_lines:
            lines = revised.split('\n')
            revised = '\n'.join(lines[revised_empty_lines - original_empty_lines:])

        original_empty_lines = count_leading_empty_lines(original, reverse=True)
        revised_empty_lines = count_leading_empty_lines(revised, reverse=True)

        if original_empty_lines > revised_empty_lines:
            additional_lines = '\n' * (original_empty_lines - revised_empty_lines)
            revised =  revised + additional_lines
        elif original_empty_lines < revised_empty_lines:
            lines = revised.split('\n')
            revised = '\n'.join(lines[:-(revised_empty_lines - original_empty_lines)])

        return revised

    def begin_comment_source_code(self, chatbot=None, history=None):
        # from toolbox import update_ui_latest_msg
        assert self.path is not None
        assert '.py' in self.path   # must be python source code
        # write_target = self.path + '.revised.py'

        write_content = ""
        # with open(self.path + '.revised.py', 'w+', encoding='utf8') as f:
        while True:
            try:
                # yield from update_ui_latest_msg(f"({self.file_basename}) 正在读取下一段代码片段:\n", chatbot=chatbot, history=history, delay=0)
                next_batch, line_no_start, line_no_end = self.get_next_batch()
                self.observe_window_update(f"正在处理{self.file_basename} - {line_no_start}/{len(self.full_context)}\n")
                # yield from update_ui_latest_msg(f"({self.file_basename}) 处理代码片段:\n\n{next_batch}", chatbot=chatbot, history=history, delay=0)
                
                hint = None
                MAX_ATTEMPT = 2
                for attempt in range(MAX_ATTEMPT):
                    result = self.tag_code(next_batch, hint)
                    try:
                        successful, hint = self.verify_successful(next_batch, result)
                    except Exception as e:
                        logger.error('ignored exception:\n' + str(e))
                        break
                    if successful:
                        break
                    if attempt == MAX_ATTEMPT - 1:
                        # cannot deal with this, give up
                        result = next_batch
                        break

                # f.write(result)
                write_content += result
            except StopIteration:
                next_batch, line_no_start, line_no_end = [], -1, -1
                return None, write_content

    def verify_successful(self, original, revised):
        """ Determine whether the revised code contains every line that already exists
        """
        from crazy_functions.ast_fns.comment_remove import remove_python_comments
        original = remove_python_comments(original)
        original_lines = original.split('\n')
        revised_lines = revised.split('\n')

        for l in original_lines:
            l = l.strip()
            if '\'' in l or '\"' in l: continue  # ast sometimes toggle " to '
            found = False
            for lt in revised_lines:
                if l in lt:
                    found = True
                    break
            if not found:
                return False, l
        return True, None