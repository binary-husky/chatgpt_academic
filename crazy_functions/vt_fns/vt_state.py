import pickle

class VoidTerminalState():
    def __init__(self):
        self.reset_state()

    def reset_state(self):
        self.has_provided_explanation = False

    def lock_plugin(self, chatbot):
        chatbot._cookies['lock_plugin'] = 'crazy_functions.虚空终端->虚空终端'
        chatbot._cookies['plugin_state'] = pickle.dumps(self)

    def unlock_plugin(self, chatbot):
        self.reset_state()
        chatbot._cookies['lock_plugin'] = None
        chatbot._cookies['plugin_state'] = pickle.dumps(self)

    def set_state(self, chatbot, key, value):
        setattr(self, key, value)
        chatbot._cookies['plugin_state'] = pickle.dumps(self)

    def get_state(chatbot):
        state = chatbot._cookies.get('plugin_state', None)
        if state is not None:   state = pickle.loads(state)
        else:                   state = VoidTerminalState()
        state.chatbot = chatbot
        return state