


> **Note**
>
> This README was translated by GPT (implemented by the plugin of this project) and may not be 100% reliable. Please carefully check the translation results.
>
> 2023.11.7: When installing dependencies, please select the **specified versions** in the `requirements.txt` file. Installation command: `pip install -r requirements.txt`.


# <div align=center><img src="logo.png" width="40"> GPT Academic</div>

<div align="center">
    
[简体中文](README.md) | **English** | [日本語](docs/README.Japanese.md) | [한국어](docs/README.Korean.md) | [Русский](docs/README.Russian.md) | [Français](docs/README.French.md)

</div>


**If you like this project, please give it a ⭐. If you have invented useful shortcut keys or plugins, please feel free to send Pull Requests!**

To translate this project to arbitrary language with GPT, read and run [`multi_language.py`](multi_language.py) (experimental).

> **Note**
>
> 1.Please note that only plugins (buttons) highlighted in **bold** support reading files, and some plugins are located in the **dropdown menu** in the plugin area. Additionally, we welcome and process any new plugins with the **highest priority** through PRs.
>
> 2.The functionalities of each file in this project are described in detail in the [self-analysis report `self_analysis.md`](https://github.com/binary-husky/gpt_academic/wiki/GPT‐Academic项目自译解报告). As the version iterates, you can also click on the relevant function plugin at any time to call GPT to regenerate the project's self-analysis report. Common questions are in the [`wiki`](https://github.com/binary-husky/gpt_academic/wiki). [Regular installation method](#installation) | [One-click installation script](https://github.com/binary-husky/gpt_academic/releases) | [Configuration instructions](https://github.com/binary-husky/gpt_academic/wiki/项目配置说明).
>
> 3.This project is compatible with and encourages the use of domestic large-scale language models such as ChatGLM. Multiple api-keys can be used together. You can fill in the configuration file with `API_KEY="openai-key1,openai-key2,azure-key3,api2d-key4"` to temporarily switch `API_KEY` during input, enter the temporary `API_KEY`, and then press enter to apply it.




<div align="center">

Feature (⭐ = Recently Added) | Description
--- | ---
⭐[Integrate New Models](https://github.com/binary-husky/gpt_academic/wiki/%E5%A6%82%E4%BD%95%E5%88%87%E6%8D%A2%E6%A8%A1%E5%9E%8B) | Baidu [Qianfan](https://cloud.baidu.com/doc/WENXINWORKSHOP/s/Nlks5zkzu) and Wenxin Yiyan, [Tongyi Qianwen](https://modelscope.cn/models/qwen/Qwen-7B-Chat/summary), Shanghai AI-Lab [Shusheng](https://github.com/InternLM/InternLM), Xunfei [Xinghuo](https://xinghuo.xfyun.cn/), [LLaMa2](https://huggingface.co/meta-llama/Llama-2-7b-chat-hf), Zhifu API, DALLE3
Proofreading, Translation, Code Explanation | One-click proofreading, translation, searching for grammar errors in papers, explaining code
[Custom Shortcuts](https://www.bilibili.com/video/BV14s4y1E7jN) | Support for custom shortcuts
Modular Design | Support for powerful [plugins](https://github.com/binary-husky/gpt_academic/tree/master/crazy_functions), plugins support [hot updates](https://github.com/binary-husky/gpt_academic/wiki/%E5%87%BD%E6%95%B0%E6%8F%92%E4%BB%B6%E6%8C%87%E5%8D%97)
[Program Profiling](https://www.bilibili.com/video/BV1cj411A7VW) | [Plugin] One-click to profile Python/C/C++/Java/Lua/... project trees or [self-profiling](https://www.bilibili.com/video/BV1cj411A7VW)
Read Papers, [Translate](https://www.bilibili.com/video/BV1KT411x7Wn) Papers | [Plugin] One-click to interpret full-text latex/pdf papers and generate abstracts
Full-text Latex [Translation](https://www.bilibili.com/video/BV1nk4y1Y7Js/), [Proofreading](https://www.bilibili.com/video/BV1FT411H7c5/) | [Plugin] One-click translation or proofreading of latex papers
Batch Comment Generation | [Plugin] One-click batch generation of function comments
Markdown [Translation](https://www.bilibili.com/video/BV1yo4y157jV/) | [Plugin] Did you see the [README](https://github.com/binary-husky/gpt_academic/blob/master/docs/README_EN.md) in the top five languages?
Chat Analysis Report Generation | [Plugin] Automatically generates summary reports after running
[PDF Paper Full-text Translation](https://www.bilibili.com/video/BV1KT411x7Wn) | [Plugin] Extract title & abstract of PDF papers + translate full-text (multi-threaded)
[Arxiv Helper](https://www.bilibili.com/video/BV1LM4y1279X) | [Plugin] Enter the arxiv article URL to translate the abstract + download PDF with one click
One-click Proofreading of Latex Papers | [Plugin] Syntax and spelling correction of Latex papers similar to Grammarly + output side-by-side PDF
[Google Scholar Integration Helper](https://www.bilibili.com/video/BV19L411U7ia) | [Plugin] Given any Google Scholar search page URL, let GPT help you [write related works](https://www.bilibili.com/video/BV1GP411U7Az/)
Internet Information Aggregation + GPT | [Plugin] One-click to let GPT retrieve information from the Internet to answer questions and keep the information up to date
⭐Arxiv Paper Fine Translation ([Docker](https://github.com/binary-husky/gpt_academic/pkgs/container/gpt_academic_with_latex)) | [Plugin] One-click [high-quality translation of arxiv papers](https://www.bilibili.com/video/BV1dz4y1v77A/), the best paper translation tool at present
⭐[Real-time Speech Input](https://github.com/binary-husky/gpt_academic/blob/master/docs/use_audio.md) | [Plugin] Asynchronously [listen to audio](https://www.bilibili.com/video/BV1AV4y187Uy/), automatically segment sentences, and automatically find the best time to answer
Formula/Image/Table Display | Can simultaneously display formulas in [TeX form and rendered form](https://user-images.githubusercontent.com/96192199/230598842-1d7fcddd-815d-40ee-af60-baf488a199df.png), support formula and code highlighting
⭐AutoGen Multi-Agent Plugin | [Plugin] Explore the emergence of multi-agent intelligence with Microsoft AutoGen!
Start Dark [Theme](https://github.com/binary-husky/gpt_academic/issues/173) | Add ```/?__theme=dark``` to the end of the browser URL to switch to the dark theme
[More LLM Model Support](https://www.bilibili.com/video/BV1wT411p7yf) | It must be great to be served by GPT3.5, GPT4, [THU ChatGLM2](https://github.com/THUDM/ChatGLM2-6B), and [Fudan MOSS](https://github.com/OpenLMLab/MOSS) at the same time, right?
⭐ChatGLM2 Fine-tuning Model | Support for loading ChatGLM2 fine-tuning models and providing ChatGLM2 fine-tuning assistant plugins
More LLM Model Access, support for [huggingface deployment](https://huggingface.co/spaces/qingxu98/gpt-academic) | Join NewBing interface (New Bing), introduce Tsinghua [JittorLLMs](https://github.com/Jittor/JittorLLMs) to support [LLaMA](https://github.com/facebookresearch/llama) and [Pangu](https://openi.org.cn/pangu/)
⭐[void-terminal](https://github.com/binary-husky/void-terminal) pip package | Use this project's all function plugins directly in Python without GUI (under development)
⭐Void Terminal Plugin | [Plugin] Schedule other plugins of this project directly in natural language
More New Feature Demonstrations (Image Generation, etc.)...... | See the end of this document ........
</div>


- New interface (modify the LAYOUT option in `config.py` to switch between "left-right layout" and "top-bottom layout")
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/d81137c3-affd-4cd1-bb5e-b15610389762" width="700" >
</div>


- All buttons are dynamically generated by reading `functional.py` and can be added with custom functions to free up the clipboard
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/231975334-b4788e91-4887-412f-8b43-2b9c5f41d248.gif" width="700" >
</div>

- Proofreading/Correction
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/231980294-f374bdcb-3309-4560-b424-38ef39f04ebd.gif" width="700" >
</div>



- If the output contains formulas, they will be displayed in both tex format and rendered format for easy copying and reading.
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/230598842-1d7fcddd-815d-40ee-af60-baf488a199df.png" width="700" >
</div>

- Too lazy to look at the project code? Show off the whole project directly in chatgpt's mouth
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/226935232-6b6a73ce-8900-4aee-93f9-733c7e6fef53.png" width="700" >
</div>

- Multiple large language models mixed calling (ChatGLM + OpenAI-GPT3.5 + [API2D](https://api2d.com/)-GPT4)
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/232537274-deca0563-7aa6-4b5d-94a2-b7c453c47794.png" width="700" >
</div>

# Installation
### Installation Method I: Run directly (Windows, Linux or MacOS)

1. Download the project
```sh
git clone --depth=1 https://github.com/binary-husky/gpt_academic.git
cd gpt_academic
```

2. Configure API_KEY

In `config.py`, configure API KEY and other settings, [click here to see special network environment configuration methods](https://github.com/binary-husky/gpt_academic/issues/1). [Wiki page](https://github.com/binary-husky/gpt_academic/wiki/项目配置说明)。

「 The program will first check if a secret configuration file named `config_private.py` exists and use the configurations from that file to override the ones in `config.py` with the same names. If you understand this logic, we strongly recommend that you create a new configuration file named `config_private.py` next to `config.py` and move (copy) the configurations from `config.py` to `config_private.py` (only copy the configuration items you have modified). 」

「 Project configuration can be done via `environment variables`. The format of the environment variables can be found in the `docker-compose.yml` file or our [Wiki page](https://github.com/binary-husky/gpt_academic/wiki/项目配置说明). Configuration priority: `environment variables` > `config_private.py` > `config.py`. 」


3. Install dependencies
```sh
# (Option I: If you are familiar with python, python>=3.9) Note: Use the official pip source or the Aliyun pip source. Temporary method for switching the source: python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
python -m pip install -r requirements.txt

# (Option II: Using Anaconda) The steps are similar (https://www.bilibili.com/video/BV1rc411W7Dr):
conda create -n gptac_venv python=3.11    # Create the anaconda environment
conda activate gptac_venv                 # Activate the anaconda environment
python -m pip install -r requirements.txt # This step is the same as the pip installation process
```


<details><summary>If you need to support THU ChatGLM2, Fudan MOSS, or RWKV Runner as backends, click here to expand</summary>
<p>

【Optional Step】If you need to support THU ChatGLM2 or Fudan MOSS as backends, you need to install additional dependencies (Prerequisites: Familiar with Python + Familiar with Pytorch + Sufficient computer configuration):
```sh
# 【Optional Step I】Support THU ChatGLM2. Note: If you encounter the "Call ChatGLM fail unable to load ChatGLM parameters" error, refer to the following: 1. The default installation above is for torch+cpu version. To use cuda, uninstall torch and reinstall torch+cuda; 2. If the model cannot be loaded due to insufficient local configuration, you can modify the model accuracy in request_llm/bridge_chatglm.py. Change AutoTokenizer.from_pretrained("THUDM/chatglm-6b", trust_remote_code=True) to AutoTokenizer.from_pretrained("THUDM/chatglm-6b-int4", trust_remote_code=True)
python -m pip install -r request_llms/requirements_chatglm.txt

# 【Optional Step II】Support Fudan MOSS
python -m pip install -r request_llms/requirements_moss.txt
git clone --depth=1 https://github.com/OpenLMLab/MOSS.git request_llms/moss  # When executing this line of code, make sure you are in the root directory of the project

# 【Optional Step III】Support RWKV Runner
Refer to wiki: https://github.com/binary-husky/gpt_academic/wiki/%E9%80%82%E9%85%8DRWKV-Runner

# 【Optional Step IV】Make sure that the AVAIL_LLM_MODELS in the config.py configuration file includes the expected models. The currently supported models are as follows (jittorllms series currently only supports the docker solution):
AVAIL_LLM_MODELS = ["gpt-3.5-turbo", "api2d-gpt-3.5-turbo", "gpt-4", "api2d-gpt-4", "chatglm", "moss"] # + ["jittorllms_rwkv", "jittorllms_pangualpha", "jittorllms_llama"]
```

</p>
</details>



4. Run
```sh
python main.py
```

### Installation Method II: Use Docker

0. Deploy all capabilities of the project (this is a large image that includes cuda and latex. Not recommended if you have slow internet speed or small hard drive)
[![fullcapacity](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-all-capacity.yml/badge.svg?branch=master)](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-all-capacity.yml)

``` sh
# Modify docker-compose.yml, keep scheme 0 and delete other schemes. Then run:
docker-compose up
```

1. ChatGPT + Wenxin + Spark online models only (recommended for most people)
[![basic](https://github.com/binary-husky/gpt_academic/actions/workflows/build-without-local-llms.yml/badge.svg?branch=master)](https://github.com/binary-husky/gpt_academic/actions/workflows/build-without-local-llms.yml)
[![basiclatex](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-latex.yml/badge.svg?branch=master)](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-latex.yml)
[![basicaudio](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-audio-assistant.yml/badge.svg?branch=master)](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-audio-assistant.yml)

``` sh
# Modify docker-compose.yml, keep scheme 1 and delete other schemes. Then run:
docker-compose up
```

P.S. If you need the latex plugin functionality, please see the Wiki. Also, you can directly use scheme 4 or scheme 0 to get the Latex functionality.

2. ChatGPT + ChatGLM2 + MOSS + LLAMA2 + Intelligent Questions (requires familiarity with [Nvidia Docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#installing-on-ubuntu-and-debian) runtime)
[![chatglm](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-chatglm.yml/badge.svg?branch=master)](https://github.com/binary-husky/gpt_academic/actions/workflows/build-with-chatglm.yml)

``` sh
# Modify docker-compose.yml, keep scheme 2 and delete other schemes. Then run:
docker-compose up
```


### Installation Method III: Other deployment methods
1. **Windows one-click running script**.
Windows users who are completely unfamiliar with the python environment can download the one-click running script from the [Release](https://github.com/binary-husky/gpt_academic/releases) to install the version without local models.
The script is contributed by [oobabooga](https://github.com/oobabooga/one-click-installers).

2. Use third-party APIs, Azure, Wenxin, Xinghuo, etc., see [Wiki page](https://github.com/binary-husky/gpt_academic/wiki/项目配置说明)

3. Pitfall guide for deploying on cloud servers.
Please visit [Cloud Server Remote Deployment Wiki](https://github.com/binary-husky/gpt_academic/wiki/%E4%BA%91%E6%9C%8D%E5%8A%A1%E5%99%A8%E8%BF%9C%E7%A8%8B%E9%83%A8%E7%BD%B2%E6%8C%87%E5%8D%97)

4. Some new deployment platforms or methods
    - Use Sealos [to deploy with one click](https://github.com/binary-husky/gpt_academic/issues/993).
    - Use WSL2 (Windows Subsystem for Linux). Please refer to [Deployment Wiki-2](https://github.com/binary-husky/gpt_academic/wiki/%E4%BD%BF%E7%94%A8WSL2%EF%BC%88Windows-Subsystem-for-Linux-%E5%AD%90%E7%B3%BB%E7%BB%9F%EF%BC%89%E9%83%A8%E7%BD%B2)
    - How to run under a subpath (such as `http://localhost/subpath`). Please visit [FastAPI Run Instructions](docs/WithFastapi.md)



# Advanced Usage
### I: Customizing new convenient buttons (academic shortcuts)
Open `core_functional.py` with any text editor, add the following entry, and then restart the program. (If the button already exists, both the prefix and suffix can be modified on-the-fly without restarting the program.)
For example:
```
"Super Translation": {
    # Prefix: will be added before your input. For example, used to describe your request, such as translation, code explanation, proofreading, etc.
    "Prefix": "Please translate the following paragraph into Chinese and then explain each proprietary term in the text using a markdown table:\n\n",

    # Suffix: will be added after your input. For example, used to wrap your input in quotation marks along with the prefix.
    "Suffix": "",
},
```
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/226899272-477c2134-ed71-4326-810c-29891fe4a508.png" width="500" >
</div>

### II: Custom function plugins
Write powerful function plugins to perform any task you desire and can't imagine.
The difficulty of writing and debugging plugins in this project is very low. As long as you have a certain knowledge of Python, you can implement your own plugin functionality by following the template we provide.
For more details, please refer to the [Function Plugin Guide](https://github.com/binary-husky/gpt_academic/wiki/%E5%87%BD%E6%95%B0%E6%8F%92%E4%BB%B6%E6%8C%87%E5%8D%97).

# Updates
### I: Dynamics

1. Conversation-saving feature. Call `Save the current conversation` in the function plugin area to save the current conversation as a readable and restorable HTML file. Additionally, call `Load conversation history archive` in the function plugin area (drop-down menu) to restore previous sessions.
Tip: Clicking `Load conversation history archive` without specifying a file allows you to view the cached historical HTML archive.
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/235222390-24a9acc0-680f-49f5-bc81-2f3161f1e049.png" width="500" >
</div>

2. ⭐Latex/Arxiv paper translation feature⭐
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/002a1a75-ace0-4e6a-94e2-ec1406a746f1" height="250" > ===>
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/9fdcc391-f823-464f-9322-f8719677043b" height="250" >
</div>

3. Void Terminal (understanding user intent from natural language input and automatically calling other plugins)

- Step 1: Enter " Please call the plugin to translate the PDF paper, the address is https://openreview.net/pdf?id=rJl0r3R9KX"
- Step 2: Click "Void Terminal"

<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/66f1b044-e9ff-4eed-9126-5d4f3668f1ed" width="500" >
</div>

4. Modular function design, simple interface supporting powerful functionality
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/229288270-093643c1-0018-487a-81e6-1d7809b6e90f.png" height="400" >
<img src="https://user-images.githubusercontent.com/96192199/227504931-19955f78-45cd-4d1c-adac-e71e50957915.png" height="400" >
</div>

5. Translate and interpret other open-source projects
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/226935232-6b6a73ce-8900-4aee-93f9-733c7e6fef53.png" height="250" >
<img src="https://user-images.githubusercontent.com/96192199/226969067-968a27c1-1b9c-486b-8b81-ab2de8d3f88a.png" height="250" >
</div>

6. Added small features that decorate [live2d](https://github.com/fghrsh/live2d_demo) (disabled by default, needs modification in `config.py`)
<div align="center">
<img src="https://user-images.githubusercontent.com/96192199/236432361-67739153-73e8-43fe-8111-b61296edabd9.png" width="500" >
</div>

7. OpenAI image generation
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/bc7ab234-ad90-48a0-8d62-f703d9e74665" width="500" >
</div>

8. OpenAI audio parsing and summarization
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/709ccf95-3aee-498a-934a-e1c22d3d5d5b" width="500" >
</div>

9. Latex full-text proofreading and correction
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/651ccd98-02c9-4464-91e1-77a6b7d1b033" height="200" > ===>
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/476f66d9-7716-4537-b5c1-735372c25adb" height="200">
</div>

10. Language and theme switching
<div align="center">
<img src="https://github.com/binary-husky/gpt_academic/assets/96192199/b6799499-b6fb-4f0c-9c8e-1b441872f4e8" width="500" >
</div>



### II: Versions:
- version 3.70 (todo): Optimize the AutoGen plugin theme and design a series of derivative plugins
- version 3.60: Introduce AutoGen as the cornerstone of the new generation of plugins
- version 3.57: Support GLM3, Spark v3, Wenxin Quote v4, and fix concurrency bugs in local models
- version 3.56: Support dynamically adding basic functional buttons and a new summary PDF page
- version 3.55: Refactor the frontend interface and introduce floating windows and a menu bar
- version 3.54: Add a dynamic code interpreter (Code Interpreter) (to be improved)
- version 3.53: Support dynamically choosing different interface themes, improve stability, and resolve conflicts between multiple users
- version 3.50: Use natural language to call all function plugins of this project (Void Terminal), support plugin classification, improve UI, and design new themes
- version 3.49: Support Baidu Qianfan Platform and Wenxin Quote
- version 3.48: Support Ali Dharma Academy Tongyi Qianwen, Shanghai AI-Lab Shusheng, and Xunfei Spark
- version 3.46: Support fully hands-off real-time voice conversation
- version 3.45: Support customizing ChatGLM2 fine-tuned models
- version 3.44: Officially support Azure, optimize interface usability
- version 3.4: + Arxiv paper translation, latex paper correction functionality
- version 3.3: + Internet information integration functionality
- version 3.2: Function plugins support more parameter interfaces (conversation saving functionality, interpreting any code language + asking any combination of LLMs simultaneously)
- version 3.1: Support querying multiple GPT models simultaneously! Support API2D, support load balancing for multiple API keys
- version 3.0: Support chatglm and other small-scale LLMs
- version 2.6: Refactored plugin structure, improved interactivity, added more plugins
- version 2.5: Self-updating, fix the problem of text being too long and token overflowing when summarizing large code projects
- version 2.4: (1) Add PDF full-text translation functionality; (2) Add functionality to switch the position of the input area; (3) Add vertical layout option; (4) Optimize multi-threaded function plugins.
- version 2.3: Enhance multi-threaded interactivity
- version 2.2: Function plugin hot-reloading support
- version 2.1: Collapsible layout
- version 2.0: Introduce modular function plugins
- version 1.0: Basic functionality

GPT Academic Developer QQ Group: `610599535`

- Known Issues
    - Some browser translation plugins interfere with the frontend operation of this software
    - Official Gradio currently has many compatibility bugs, please make sure to install Gradio using `requirement.txt`

### III: Themes
You can change the theme by modifying the `THEME` option (config.py).
1. `Chuanhu-Small-and-Beautiful` [Website](https://github.com/GaiZhenbiao/ChuanhuChatGPT/)

### IV: Development Branches of This Project

1. `master` branch: Main branch, stable version
2. `frontier` branch: Development branch, test version

***

### V: References and Learning


The code references the designs of many other excellent projects, in no particular order:

[THU ChatGLM2-6B](https://github.com/THUDM/ChatGLM2-6B)


[THU JittorLLMs](https://github.com/Jittor/JittorLLMs)


[ChatPaper](https://github.com/kaixindelele/ChatPaper)


[Edge-GPT](https://github.com/acheong08/EdgeGPT)


[ChuanhuChatGPT](https://github.com/GaiZhenbiao/ChuanhuChatGPT)



# Oobabooga one-click installer:
https://github.com/oobabooga/one-click-installers

# More:
https://github.com/gradio-app/gradio
https://github.com/fghrsh/live2d_demo
