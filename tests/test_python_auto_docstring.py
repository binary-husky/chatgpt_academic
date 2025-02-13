import init_test

from toolbox import CatchException, update_ui
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from request_llms.bridge_all import predict_no_ui_long_connection
import datetime
import re
from textwrap import dedent
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
You need to read the following code, and revise the code according to following instructions:
1. You should analyze the purpose of the functions (if there are any).
2. You need to add docstring for the provided functions (if there are any).

Be aware:
1. You must NOT modify the indent of code.
2. You are NOT authorized to change or translate non-comment code, and you are NOT authorized to add empty lines either.
3. Use English to add comments and docstrings. Do NOT translate Chinese that is already in the code.

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


------------------ the real INPUT you need to process NOW ------------------
```
{THE_CODE}
```
{INDENT_REMINDER}
'''


class ContextWindowManager():

    def __init__(self, llm_kwargs) -> None:
        self.full_context = []
        self.full_context_with_line_no = []
        self.current_page_start = 0
        self.page_limit = 100 # 100 lines of code each page
        self.ignore_limit = 20
        self.llm_kwargs = llm_kwargs

    def generate_tagged_code_from_full_context(self):
        for i, code in enumerate(self.full_context):
            number = i
            padded_number = f"{number:04}"
            result = f"L{padded_number}"
            self.full_context_with_line_no.append(f"{result} | {code}")
        return self.full_context_with_line_no

    def read_file(self, path):
        with open(path, 'r', encoding='utf8') as f:
            self.full_context = f.readlines()
        self.full_context_with_line_no = self.generate_tagged_code_from_full_context()


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
            raise RuntimeError
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

    def get_next_batch(self):
        current_page_start, future_page_start = self._get_next_window()
        return self.full_context[current_page_start: future_page_start], current_page_start, future_page_start

    def tag_code(self, fn):
        code = ''.join(fn)
        _, n_indent = self.dedent(code)
        indent_reminder = "" if n_indent == 0 else "(Reminder: as you can see, this piece of code has indent made up with {n_indent} whitespace, please preserve them in the OUTPUT.)"
        self.llm_kwargs['temperature'] = 0
        result = predict_no_ui_long_connection(
            inputs=revise_function_prompt.format(THE_CODE=code, INDENT_REMINDER=indent_reminder),
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


from toolbox import get_plugin_default_kwargs
llm_kwargs = get_plugin_default_kwargs()["llm_kwargs"]
cwm = ContextWindowManager(llm_kwargs)
cwm.read_file(path="./test.py")
output_buf = ""
with open('temp.py', 'w+', encoding='utf8') as f:
    while True:
        try:
            next_batch, line_no_start, line_no_end = cwm.get_next_batch()
            result = cwm.tag_code(next_batch)
            f.write(result)
            output_buf += result
        except StopIteration:
            next_batch, line_no_start, line_no_end = [], -1, -1
            break
        print('-------------------------------------------')
        print(''.join(next_batch))
        print('-------------------------------------------')


print(cwm)















