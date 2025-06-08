import re
import os

# Windows路徑檢測
def sanitize_windows_path(input_string: str) -> str:
    input_string = input_string.replace('\t', ' ').replace('\n', ' ')
    # 定义 Windows 路径中的非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    # 用下划线替换非法字符
    sanitized_string = re.sub(illegal_chars, '_', input_string)
    # 删除 Windows 不允许的文件名结尾字符（空格和句号）
    sanitized_string = sanitized_string.rstrip(' .')
    # 检查是否是保留名称
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    if sanitized_string.upper() in reserved_names:
        sanitized_string = f"_{sanitized_string}"  # 添加前缀以规避保留名称
    # 截断到 255 字符，Windows 文件名长度限制（不含路径）
    max_length = 255
    sanitized_string = sanitized_string[:max_length]
    return sanitized_string

def setup_paths(config, title):
    if "{title}" in config['output_path']:
        config['output_path'] = config['output_path'].format(title=title)
    if "{title}" in config['backup_path']:
        config['backup_path'] = config['backup_path'].format(title=title)
    return os.path.abspath(config['output_path']), os.path.abspath(config['backup_path'])
