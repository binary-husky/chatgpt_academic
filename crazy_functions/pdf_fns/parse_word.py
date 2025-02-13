from crazy_functions.crazy_utils import read_and_clean_pdf_text, get_files_from_everything
import os
import re
def extract_text_from_files(txt, chatbot, history):
    """
    查找pdf/md/word并获取文本内容并返回状态以及文本

    输入参数 Args:
        chatbot: chatbot inputs and outputs （用户界面对话窗口句柄，用于数据流可视化）
        history (list): List of chat history （历史，对话历史列表）

    输出 Returns:
        文件是否存在(bool)
        final_result(list):文本内容
        page_one(list):第一页内容/摘要
        file_manifest(list):文件路径
        exception(string):需要用户手动处理的信息,如没出错则保持为空
    """

    final_result = []
    page_one = []
    file_manifest = []
    exception = ""

    if txt == "":
        final_result.append(txt)
        return False, final_result, page_one, file_manifest, exception   #如输入区内容不是文件则直接返回输入区内容

    #查找输入区内容中的文件
    file_pdf,pdf_manifest,folder_pdf = get_files_from_everything(txt, '.pdf')
    file_md,md_manifest,folder_md = get_files_from_everything(txt, '.md')
    file_word,word_manifest,folder_word = get_files_from_everything(txt, '.docx')
    file_doc,doc_manifest,folder_doc = get_files_from_everything(txt, '.doc')

    if file_doc:
        exception = "word"
        return False, final_result, page_one, file_manifest, exception

    file_num = len(pdf_manifest) + len(md_manifest) + len(word_manifest)
    if file_num == 0:
        final_result.append(txt)
        return False, final_result, page_one, file_manifest, exception   #如输入区内容不是文件则直接返回输入区内容

    if file_pdf:
        try:    # 尝试导入依赖，如果缺少依赖，则给出安装建议
            import fitz
        except:
            exception = "pdf"
            return False, final_result, page_one, file_manifest, exception
        for index, fp in enumerate(pdf_manifest):
            file_content, pdf_one = read_and_clean_pdf_text(fp) # （尝试）按照章节切割PDF
            file_content = file_content.encode('utf-8', 'ignore').decode()   # avoid reading non-utf8 chars
            pdf_one = str(pdf_one).encode('utf-8', 'ignore').decode()  # avoid reading non-utf8 chars
            final_result.append(file_content)
            page_one.append(pdf_one)
            file_manifest.append(os.path.relpath(fp, folder_pdf))

    if file_md:
        for index, fp in enumerate(md_manifest):
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                file_content = f.read()
            file_content = file_content.encode('utf-8', 'ignore').decode()
            headers = re.findall(r'^#\s(.*)$', file_content, re.MULTILINE)  #接下来提取md中的一级/二级标题作为摘要
            if len(headers) > 0:
                page_one.append("\n".join(headers)) #合并所有的标题,以换行符分割
            else:
                page_one.append("")
            final_result.append(file_content)
            file_manifest.append(os.path.relpath(fp, folder_md))

    if file_word:
        try:    # 尝试导入依赖，如果缺少依赖，则给出安装建议
            from docx import Document
        except:
            exception = "word_pip"
            return False, final_result, page_one, file_manifest, exception
        for index, fp in enumerate(word_manifest):
            doc = Document(fp)
            file_content = '\n'.join([p.text for p in doc.paragraphs])
            file_content = file_content.encode('utf-8', 'ignore').decode()
            page_one.append(file_content[:200])
            final_result.append(file_content)
            file_manifest.append(os.path.relpath(fp, folder_word))

    return True, final_result, page_one, file_manifest, exception