def is_full_width_char(ch):
    """判断给定的单个字符是否是全角字符"""
    if '\u4e00' <= ch <= '\u9fff':
        return True  # 中文字符
    if '\uff01' <= ch <= '\uff5e':
        return True  # 全角符号
    if '\u3000' <= ch <= '\u303f':
        return True  # CJK标点符号
    return False

def scrolling_visual_effect(text, scroller_max_len):
    text = text.\
            replace('\n', '').replace('`', '.').replace(' ', '.').replace('<br/>', '.....').replace('$', '.')
    place_take_cnt = 0
    pointer = len(text) - 1

    if len(text) < scroller_max_len:
        return text

    while place_take_cnt < scroller_max_len and pointer > 0:
        if is_full_width_char(text[pointer]): place_take_cnt += 2
        else: place_take_cnt += 1
        pointer -= 1

    return text[pointer:]