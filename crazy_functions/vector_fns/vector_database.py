# From project chatglm-langchain

import os
import os
import uuid
import tqdm
import shutil
import threading
import numpy as np
from toolbox import Singleton
from loguru import logger
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document
from typing import List, Tuple
from crazy_functions.vector_fns.general_file_loader import load_file

embedding_model_dict = {
    "ernie-tiny": "nghuyong/ernie-3.0-nano-zh",
    "ernie-base": "nghuyong/ernie-3.0-base-zh",
    "text2vec-base": "shibing624/text2vec-base-chinese",
    "text2vec": "GanymedeNil/text2vec-large-chinese",
}

# Embedding model name
EMBEDDING_MODEL = "text2vec"

# Embedding running device
EMBEDDING_DEVICE = "cpu"

# 基于上下文的prompt模版，请务必保留"{question}"和"{context}"
PROMPT_TEMPLATE = """已知信息：
{context}

根据上述已知信息，简洁和专业的来回答用户的问题。如果无法从中得到答案，请说 “根据已知信息无法回答该问题” 或 “没有提供足够的相关信息”，不允许在答案中添加编造成分，答案请使用中文。 问题是：{question}"""

# 文本分句长度
SENTENCE_SIZE = 100

# 匹配后单段上下文长度
CHUNK_SIZE = 250

# LLM input history length
LLM_HISTORY_LEN = 3

# return top-k text chunk from vector store
VECTOR_SEARCH_TOP_K = 5

# 知识检索内容相关度 Score, 数值范围约为0-1100，如果为0，则不生效，经测试设置为小于500时，匹配结果更精准
VECTOR_SEARCH_SCORE_THRESHOLD = 0

NLTK_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nltk_data")

FLAG_USER_NAME = uuid.uuid4().hex

# 是否开启跨域，默认为False，如果需要开启，请设置为True
# is open cross domain
OPEN_CROSS_DOMAIN = False

def similarity_search_with_score_by_vector(
        self, embedding: List[float], k: int = 4
) -> List[Tuple[Document, float]]:

    def separate_list(ls: List[int]) -> List[List[int]]:
        lists = []
        ls1 = [ls[0]]
        for i in range(1, len(ls)):
            if ls[i - 1] + 1 == ls[i]:
                ls1.append(ls[i])
            else:
                lists.append(ls1)
                ls1 = [ls[i]]
        lists.append(ls1)
        return lists

    scores, indices = self.index.search(np.array([embedding], dtype=np.float32), k)
    docs = []
    id_set = set()
    store_len = len(self.index_to_docstore_id)
    for j, i in enumerate(indices[0]):
        if i == -1 or 0 < self.score_threshold < scores[0][j]:
            # This happens when not enough docs are returned.
            continue
        _id = self.index_to_docstore_id[i]
        doc = self.docstore.search(_id)
        if not self.chunk_content:
            if not isinstance(doc, Document):
                raise ValueError(f"Could not find document for id {_id}, got {doc}")
            doc.metadata["score"] = int(scores[0][j])
            docs.append(doc)
            continue
        id_set.add(i)
        docs_len = len(doc.page_content)
        for k in range(1, max(i, store_len - i)):
            break_flag = False
            for l in [i + k, i - k]:
                if 0 <= l < len(self.index_to_docstore_id):
                    _id0 = self.index_to_docstore_id[l]
                    doc0 = self.docstore.search(_id0)
                    if docs_len + len(doc0.page_content) > self.chunk_size:
                        break_flag = True
                        break
                    elif doc0.metadata["source"] == doc.metadata["source"]:
                        docs_len += len(doc0.page_content)
                        id_set.add(l)
            if break_flag:
                break
    if not self.chunk_content:
        return docs
    if len(id_set) == 0 and self.score_threshold > 0:
        return []
    id_list = sorted(list(id_set))
    id_lists = separate_list(id_list)
    for id_seq in id_lists:
        for id in id_seq:
            if id == id_seq[0]:
                _id = self.index_to_docstore_id[id]
                doc = self.docstore.search(_id)
            else:
                _id0 = self.index_to_docstore_id[id]
                doc0 = self.docstore.search(_id0)
                doc.page_content += " " + doc0.page_content
        if not isinstance(doc, Document):
            raise ValueError(f"Could not find document for id {_id}, got {doc}")
        doc_score = min([scores[0][id] for id in [indices[0].tolist().index(i) for i in id_seq if i in indices[0]]])
        doc.metadata["score"] = int(doc_score)
        docs.append(doc)
    return docs


class LocalDocQA:
    llm: object = None
    embeddings: object = None
    top_k: int = VECTOR_SEARCH_TOP_K
    chunk_size: int = CHUNK_SIZE
    chunk_content: bool = True
    score_threshold: int = VECTOR_SEARCH_SCORE_THRESHOLD

    def init_cfg(self,
                 top_k=VECTOR_SEARCH_TOP_K,
                 ):

        self.llm = None
        self.top_k = top_k

    def init_knowledge_vector_store(self,
                                    filepath,
                                    vs_path: str or os.PathLike = None,
                                    sentence_size=SENTENCE_SIZE,
                                    text2vec=None):
        loaded_files = []
        failed_files = []
        if isinstance(filepath, str):
            if not os.path.exists(filepath):
                logger.error("路径不存在")
                return None
            elif os.path.isfile(filepath):
                file = os.path.split(filepath)[-1]
                try:
                    docs = load_file(filepath, SENTENCE_SIZE)
                    logger.info(f"{file} 已成功加载")
                    loaded_files.append(filepath)
                except Exception as e:
                    logger.error(e)
                    logger.error(f"{file} 未能成功加载")
                    return None
            elif os.path.isdir(filepath):
                docs = []
                for file in tqdm(os.listdir(filepath), desc="加载文件"):
                    fullfilepath = os.path.join(filepath, file)
                    try:
                        docs += load_file(fullfilepath, SENTENCE_SIZE)
                        loaded_files.append(fullfilepath)
                    except Exception as e:
                        logger.error(e)
                        failed_files.append(file)

                if len(failed_files) > 0:
                    logger.error("以下文件未能成功加载：")
                    for file in failed_files:
                        logger.error(f"{file}\n")

        else:
            docs = []
            for file in filepath:
                docs += load_file(file, SENTENCE_SIZE)
                logger.info(f"{file} 已成功加载")
                loaded_files.append(file)

        if len(docs) > 0:
            logger.info("文件加载完毕，正在生成向量库")
            if vs_path and os.path.isdir(vs_path):
                try:
                    self.vector_store = FAISS.load_local(vs_path, text2vec)
                    self.vector_store.add_documents(docs)
                except:
                    self.vector_store = FAISS.from_documents(docs, text2vec)
            else:
                self.vector_store = FAISS.from_documents(docs, text2vec)  # docs 为Document列表

            self.vector_store.save_local(vs_path)
            return vs_path, loaded_files
        else:
            raise RuntimeError("文件加载失败，请检查文件格式是否正确")

    def get_loaded_file(self, vs_path):
        ds = self.vector_store.docstore
        return set([ds._dict[k].metadata['source'].split(vs_path)[-1] for k in ds._dict])


    # query      查询内容
    # vs_path    知识库路径
    # chunk_content   是否启用上下文关联
    # score_threshold    搜索匹配score阈值
    # vector_search_top_k   搜索知识库内容条数，默认搜索5条结果
    # chunk_sizes    匹配单段内容的连接上下文长度
    def get_knowledge_based_content_test(self, query, vs_path, chunk_content,
                                        score_threshold=VECTOR_SEARCH_SCORE_THRESHOLD,
                                        vector_search_top_k=VECTOR_SEARCH_TOP_K, chunk_size=CHUNK_SIZE,
                                        text2vec=None):
        self.vector_store = FAISS.load_local(vs_path, text2vec)
        self.vector_store.chunk_content = chunk_content
        self.vector_store.score_threshold = score_threshold
        self.vector_store.chunk_size = chunk_size

        embedding = self.vector_store.embedding_function.embed_query(query)
        related_docs_with_score = similarity_search_with_score_by_vector(self.vector_store, embedding, k=vector_search_top_k)

        if not related_docs_with_score:
            response = {"query": query,
                        "source_documents": []}
            return response, ""
        # prompt = f"{query}. You should answer this question using information from following documents: \n\n"
        prompt = f"{query}. 你必须利用以下文档中包含的信息回答这个问题: \n\n---\n\n"
        prompt += "\n\n".join([f"({k}): " + doc.page_content for k, doc in enumerate(related_docs_with_score)])
        prompt += "\n\n---\n\n"
        prompt = prompt.encode('utf-8', 'ignore').decode()   # avoid reading non-utf8 chars
        # logger.info(prompt)
        response = {"query": query, "source_documents": related_docs_with_score}
        return response, prompt




def construct_vector_store(vs_id, vs_path, files, sentence_size, history, one_content, one_content_segmentation, text2vec):
    for file in files:
        assert os.path.exists(file), "输入文件不存在：" + file
    import nltk
    if NLTK_DATA_PATH not in nltk.data.path: nltk.data.path = [NLTK_DATA_PATH] + nltk.data.path
    local_doc_qa = LocalDocQA()
    local_doc_qa.init_cfg()
    filelist = []
    if not os.path.exists(os.path.join(vs_path, vs_id)):
        os.makedirs(os.path.join(vs_path, vs_id))
    for file in files:
        file_name = file.name if not isinstance(file, str) else file
        filename = os.path.split(file_name)[-1]
        shutil.copyfile(file_name, os.path.join(vs_path, vs_id, filename))
        filelist.append(os.path.join(vs_path, vs_id, filename))
    vs_path, loaded_files = local_doc_qa.init_knowledge_vector_store(filelist, os.path.join(vs_path, vs_id), sentence_size, text2vec)

    if len(loaded_files):
        file_status = f"已添加 {'、'.join([os.path.split(i)[-1] for i in loaded_files if i])} 内容至知识库，并已加载知识库，请开始提问"
    else:
        pass
        # file_status = "文件未成功加载，请重新上传文件"
    # logger.info(file_status)
    return local_doc_qa, vs_path

@Singleton
class knowledge_archive_interface():
    def __init__(self) -> None:
        self.threadLock = threading.Lock()
        self.current_id = ""
        self.kai_path = None
        self.qa_handle = None
        self.text2vec_large_chinese = None

    def get_chinese_text2vec(self):
        if self.text2vec_large_chinese is None:
            # < -------------------预热文本向量化模组--------------- >
            from toolbox import ProxyNetworkActivate
            logger.info('Checking Text2vec ...')
            from langchain.embeddings.huggingface import HuggingFaceEmbeddings
            with ProxyNetworkActivate('Download_LLM'):    # 临时地激活代理网络
                self.text2vec_large_chinese = HuggingFaceEmbeddings(model_name="GanymedeNil/text2vec-large-chinese")

        return self.text2vec_large_chinese


    def feed_archive(self, file_manifest, vs_path, id="default"):
        self.threadLock.acquire()
        # import uuid
        self.current_id = id
        self.qa_handle, self.kai_path = construct_vector_store(
            vs_id=self.current_id,
            vs_path=vs_path,
            files=file_manifest,
            sentence_size=100,
            history=[],
            one_content="",
            one_content_segmentation="",
            text2vec = self.get_chinese_text2vec(),
        )
        self.threadLock.release()

    def get_current_archive_id(self):
        return self.current_id

    def get_loaded_file(self, vs_path):
        return self.qa_handle.get_loaded_file(vs_path)

    def answer_with_archive_by_id(self, txt, id, vs_path):
        self.threadLock.acquire()
        if not self.current_id == id:
            self.current_id = id
            self.qa_handle, self.kai_path = construct_vector_store(
                vs_id=self.current_id,
                vs_path=vs_path,
                files=[],
                sentence_size=100,
                history=[],
                one_content="",
                one_content_segmentation="",
                text2vec = self.get_chinese_text2vec(),
            )
        VECTOR_SEARCH_SCORE_THRESHOLD = 0
        VECTOR_SEARCH_TOP_K = 4
        CHUNK_SIZE = 512
        resp, prompt = self.qa_handle.get_knowledge_based_content_test(
            query = txt,
            vs_path = self.kai_path,
            score_threshold=VECTOR_SEARCH_SCORE_THRESHOLD,
            vector_search_top_k=VECTOR_SEARCH_TOP_K,
            chunk_content=True,
            chunk_size=CHUNK_SIZE,
            text2vec = self.get_chinese_text2vec(),
        )
        self.threadLock.release()
        return resp, prompt