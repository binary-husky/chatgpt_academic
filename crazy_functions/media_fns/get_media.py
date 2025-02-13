from toolbox import update_ui, get_conf, promote_file_to_downloadzone, update_ui_latest_msg, generate_file_link
from shared_utils.docker_as_service_api import stream_daas
from shared_utils.docker_as_service_api import DockerServiceApiComModel
import random

def download_video(video_id, only_audio, user_name, chatbot, history):
    from toolbox import get_log_folder
    chatbot.append([None, "Processing..."])
    yield from update_ui(chatbot, history)
    client_command = f'{video_id} --audio-only' if only_audio else video_id
    server_urls = get_conf('DAAS_SERVER_URLS')
    server_url = random.choice(server_urls)
    docker_service_api_com_model = DockerServiceApiComModel(client_command=client_command)
    save_file_dir = get_log_folder(user_name, plugin_name='media_downloader')
    for output_manifest in stream_daas(docker_service_api_com_model, server_url, save_file_dir):
        status_buf = ""
        status_buf += "DaaS message: \n\n"
        status_buf += output_manifest['server_message'].replace('\n', '<br/>')
        status_buf += "\n\n"
        status_buf += "DaaS standard error: \n\n"
        status_buf += output_manifest['server_std_err'].replace('\n', '<br/>')
        status_buf += "\n\n"
        status_buf += "DaaS standard output: \n\n"
        status_buf += output_manifest['server_std_out'].replace('\n', '<br/>')
        status_buf += "\n\n"
        status_buf += "DaaS file attach: \n\n"
        status_buf += str(output_manifest['server_file_attach'])
        yield from update_ui_latest_msg(status_buf, chatbot, history)

    return output_manifest['server_file_attach']


def search_videos(keywords):
    from toolbox import get_log_folder
    client_command = keywords
    server_urls = get_conf('DAAS_SERVER_URLS')
    server_url = random.choice(server_urls)
    server_url = server_url.replace('stream', 'search')
    docker_service_api_com_model = DockerServiceApiComModel(client_command=client_command)
    save_file_dir = get_log_folder("default_user", plugin_name='media_downloader')
    for output_manifest in stream_daas(docker_service_api_com_model, server_url, save_file_dir):
        return output_manifest['server_message']

