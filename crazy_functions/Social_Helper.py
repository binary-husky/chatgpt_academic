import pickle, os, random
from toolbox import CatchException, update_ui, get_conf, get_log_folder, update_ui_latest_msg
from crazy_functions.crazy_utils import input_clipping
from crazy_functions.crazy_utils import request_gpt_model_in_new_thread_with_ui_alive
from request_llms.bridge_all import predict_no_ui_long_connection
from crazy_functions.json_fns.select_tool import structure_output, select_tool
from pydantic import BaseModel, Field
from loguru import logger
from typing import List


SOCIAL_NETWORK_WORKER_REGISTER = {}

class SocialNetwork():
    def __init__(self):
        self.people = []

class SaveAndLoad():
    def __init__(self, user_name, llm_kwargs, auto_load_checkpoint=True, checkpoint_dir=None) -> None:
        self.user_name = user_name
        self.checkpoint_dir = checkpoint_dir
        if auto_load_checkpoint:
            self.social_network = self.load_from_checkpoint(checkpoint_dir)
        else:
            self.social_network = SocialNetwork()

    def does_checkpoint_exist(self, checkpoint_dir=None):
        import os, glob
        if checkpoint_dir is None: checkpoint_dir = self.checkpoint_dir
        if not os.path.exists(checkpoint_dir): return False
        if len(glob.glob(os.path.join(checkpoint_dir, "social_network.pkl"))) == 0: return False
        return True

    def save_to_checkpoint(self, checkpoint_dir=None):
        if checkpoint_dir is None: checkpoint_dir = self.checkpoint_dir
        with open(os.path.join(checkpoint_dir, 'social_network.pkl'), "wb+") as f:
            pickle.dump(self.social_network, f)
        return

    def load_from_checkpoint(self, checkpoint_dir=None):
        if checkpoint_dir is None: checkpoint_dir = self.checkpoint_dir
        if self.does_checkpoint_exist(checkpoint_dir=checkpoint_dir):
            with open(os.path.join(checkpoint_dir, 'social_network.pkl'), "rb") as f:
                social_network = pickle.load(f)
                return social_network
        else:
            return SocialNetwork()


class Friend(BaseModel):
    friend_name: str = Field(description="name of a friend")
    friend_description: str = Field(description="description of a friend (everything about this friend)")
    friend_relationship: str = Field(description="The relationship with a friend (e.g. friend, family, colleague)")

class FriendList(BaseModel):
    friends_list: List[Friend] = Field(description="The list of friends")


class SocialNetworkWorker(SaveAndLoad):
    def ai_socail_advice(self, prompt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, run_gpt_fn, intention_type):
        pass

    def ai_remove_friend(self, prompt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, run_gpt_fn, intention_type):
        pass

    def ai_list_friends(self, prompt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, run_gpt_fn, intention_type):
        pass

    def ai_add_multi_friends(self, prompt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, run_gpt_fn, intention_type):
        friend, err_msg = structure_output(
            txt=prompt,
            prompt="根据提示, 解析多个联系人的身份信息\n\n",
            err_msg=f"不能理解该联系人",
            run_gpt_fn=run_gpt_fn,
            pydantic_cls=FriendList
        )
        if friend.friends_list:
            for f in friend.friends_list: 
                self.add_friend(f)
            msg = f"成功添加{len(friend.friends_list)}个联系人: {str(friend.friends_list)}"
            yield from update_ui_latest_msg(lastmsg=msg, chatbot=chatbot, history=history, delay=0)


    def run(self, txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):
        prompt = txt
        run_gpt_fn = lambda inputs, sys_prompt: predict_no_ui_long_connection(inputs=inputs, llm_kwargs=llm_kwargs, history=[], sys_prompt=sys_prompt, observe_window=[])
        self.tools_to_select = {
            "SocialAdvice":{
                "explain_to_llm": "如果用户希望获取社交指导，调用SocialAdvice生成一些社交建议",
                "callback": self.ai_socail_advice,
            },
            "AddFriends":{
                "explain_to_llm": "如果用户给出了联系人，调用AddMultiFriends把联系人添加到数据库",
                "callback": self.ai_add_multi_friends,
            },
            "RemoveFriend":{
                "explain_to_llm": "如果用户希望移除某个联系人，调用RemoveFriend",
                "callback": self.ai_remove_friend,
            },
            "ListFriends":{
                "explain_to_llm": "如果用户列举联系人，调用ListFriends",
                "callback": self.ai_list_friends,
            }
        }

        try:
            Explanation = '\n'.join([f'{k}: {v["explain_to_llm"]}' for k, v in self.tools_to_select.items()])
            class UserSociaIntention(BaseModel):
                intention_type: str = Field(
                    description=
                        f"The type of user intention. You must choose from {self.tools_to_select.keys()}.\n\n" 
                        f"Explanation:\n{Explanation}", 
                    default="SocialAdvice"
                )
            pydantic_cls_instance, err_msg = select_tool(
                prompt=txt,
                run_gpt_fn=run_gpt_fn,
                pydantic_cls=UserSociaIntention
            )
        except Exception as e:
            yield from update_ui_latest_msg(
                lastmsg=f"无法理解用户意图 {err_msg}", 
                chatbot=chatbot, 
                history=history, 
                delay=0
            )
            return

        intention_type = pydantic_cls_instance.intention_type
        intention_callback = self.tools_to_select[pydantic_cls_instance.intention_type]['callback']
        yield from intention_callback(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, run_gpt_fn, intention_type)


    def add_friend(self, friend):
        # check whether the friend is already in the social network
        for f in self.social_network.people:
            if f.friend_name == friend.friend_name:
                f.friend_description = friend.friend_description
                f.friend_relationship = friend.friend_relationship
                logger.info(f"Repeated friend, update info: {friend}")
                return
        logger.info(f"Add a new friend: {friend}")
        self.social_network.people.append(friend)
        return


@CatchException
def I人助手(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request):

    # 1. we retrieve worker from global context
    user_name = chatbot.get_user()
    checkpoint_dir=get_log_folder(user_name, plugin_name='experimental_rag')
    if user_name in SOCIAL_NETWORK_WORKER_REGISTER:
        social_network_worker = SOCIAL_NETWORK_WORKER_REGISTER[user_name]
    else:
        social_network_worker = SOCIAL_NETWORK_WORKER_REGISTER[user_name] = SocialNetworkWorker(
            user_name, 
            llm_kwargs, 
            checkpoint_dir=checkpoint_dir, 
            auto_load_checkpoint=True
        )

    # 2. save
    yield from social_network_worker.run(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, user_request)
    social_network_worker.save_to_checkpoint(checkpoint_dir)
    yield from update_ui(chatbot=chatbot, history=history) # 刷新界面

