import time
import importlib
from toolbox import trimmed_format_exc, gen_time_str, get_log_folder
from toolbox import CatchException, update_ui, gen_time_str, trimmed_format_exc, is_the_upload_folder
from toolbox import promote_file_to_downloadzone, get_log_folder, update_ui_latest_msg
import multiprocessing

def get_class_name(class_string):
    import re
    # Use regex to extract the class name
    class_name = re.search(r'class (\w+)\(', class_string).group(1)
    return class_name

def try_make_module(code, chatbot):
    module_file = 'gpt_fn_' + gen_time_str().replace('-','_')
    fn_path = f'{get_log_folder(plugin_name="gen_plugin_verify")}/{module_file}.py'
    with open(fn_path, 'w', encoding='utf8') as f: f.write(code)
    promote_file_to_downloadzone(fn_path, chatbot=chatbot)
    class_name = get_class_name(code)
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    p = multiprocessing.Process(target=is_function_successfully_generated, args=(fn_path, class_name, return_dict))
    # only has 10 seconds to run
    p.start(); p.join(timeout=10)
    if p.is_alive(): p.terminate(); p.join()
    p.close()
    return return_dict["success"], return_dict['traceback']

# check is_function_successfully_generated
def is_function_successfully_generated(fn_path, class_name, return_dict):
    return_dict['success'] = False
    return_dict['traceback'] = ""
    try:
        # Create a spec for the module
        module_spec = importlib.util.spec_from_file_location('example_module', fn_path)
        # Load the module
        example_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(example_module)
        # Now you can use the module
        some_class = getattr(example_module, class_name)
        # Now you can create an instance of the class
        instance = some_class()
        return_dict['success'] = True
        return
    except:
        return_dict['traceback'] = trimmed_format_exc()
        return

def subprocess_worker(code, file_path, return_dict):
    return_dict['result'] = None
    return_dict['success'] = False
    return_dict['traceback'] = ""
    try:
        module_file = 'gpt_fn_' + gen_time_str().replace('-','_')
        fn_path = f'{get_log_folder(plugin_name="gen_plugin_run")}/{module_file}.py'
        with open(fn_path, 'w', encoding='utf8') as f: f.write(code)
        class_name = get_class_name(code)
        # Create a spec for the module
        module_spec = importlib.util.spec_from_file_location('example_module', fn_path)
        # Load the module
        example_module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(example_module)
        # Now you can use the module
        some_class = getattr(example_module, class_name)
        # Now you can create an instance of the class
        instance = some_class()
        return_dict['result'] = instance.run(file_path)
        return_dict['success'] = True
    except:
        return_dict['traceback'] = trimmed_format_exc()
