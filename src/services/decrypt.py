from Crypto.Cipher import AES
import os
import sys
import logging

log = logging.getLogger(__name__)

def set_logger(new_log):
    current_module = sys.modules[__name__]  # 取得 `c` 模組的引用
    setattr(current_module, "log", new_log)

def process_iv(iv=None):
    try:
        if iv is None or iv == "":
            iv = bytes(16)  # 默認 16 個 0 字節
        elif isinstance(iv, (bytes, bytearray)):
            pass  # 已经是 bytes，直接返回
        elif isinstance(iv, str):
            iv = bytes.fromhex(iv.removeprefix("0x"))  # 移除 "0x" 并转换
            if len(iv) != 16:
                raise ValueError("IV must be 16 bytes long")
        else:
            raise TypeError("IV must be None, bytes, or a hex string")
    except ValueError as e:
        raise ValueError(f"Invalid IV format: {e}") from e
    return iv

def ts_with_key_file(ts_path, decrypted_path, key, iv=None):
    """
    解密單個 .ts 文件，並檢查解密後的文件格式（前 8 字節）。
    """
    os.makedirs(os.path.dirname(decrypted_path), exist_ok=True)
    if os.path.exists(decrypted_path):
        decrypted_size = os.path.getsize(decrypted_path)
        encrypted_size = os.path.getsize(ts_path)
        if decrypted_size == encrypted_size:
            log.warning(f"目標文件已存在: {decrypted_path}")
            return True
    
    try:
        # 默認初始化向量為 16 個零字節
        iv = process_iv(iv)
        
        # 確保源文件和目標文件不同
        if ts_path == decrypted_path:
            raise ValueError("源文件和目標文件路徑不能相同")
        
        # 打開加密的 .ts 文件和解密後的目標文件
        with open(ts_path, 'rb') as infile:
            encrypted_data = infile.read()
        
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(encrypted_data)
        
        # 去除可能的填充
        if len(decrypted_data) > 0:
            padding_length = decrypted_data[-1]
            if 0 < padding_length <= 16 and decrypted_data[-padding_length:] == bytes([padding_length]) * padding_length:
                decrypted_data = decrypted_data[:-padding_length]
        #print(decrypted_data[:16].hex())
        # 寫入解密後的文件
        with open(decrypted_path, 'wb') as outfile:
            outfile.write(decrypted_data)
        
        # 檢查解密後文件大小是否與原始文件大小一致
        decrypted_size = os.path.getsize(decrypted_path)
        encrypted_size = os.path.getsize(ts_path)
        
        if decrypted_size != encrypted_size:
            #log.warning(f"解密後的文件大小 ({decrypted_size} bytes) 與原始文件大小 ({encrypted_size} bytes) 不一致，文件已保存到: {decrypted_path}")
            return False
        
        # 檢查解密後文件的前 8 字節
        with open(decrypted_path, 'rb') as outfile:
            header = outfile.read(8)
        
        #expected_header = b'\x47\x40\x00\x10'
        #if header[:4] != expected_header:
        #    log.warning("解密後文件的前 8 字節不匹配")
        #    return False
        
        log.debug(f"解密完成且檢查通過，文件已保存到: {decrypted_path}")
        return True
    except Exception as e:
        log.error(f"解密失敗: {e}")
        return False


if __name__ == '__main__':
    # 使用範例
    source_folder = r"M:\自製資料\開發中\m3u8下載器\downloads\VALIS 6th ONE-MAN LIVE「喝采Curtain Call」 -  Z-aN\backup\VALIS 6th ONE-MAN LIVE「喝采Curtain Call」 -  Z-aN\fragments"
    decrypted_folder = r"M:\自製資料\開發中\m3u8下載器\downloads\VALIS 6th ONE-MAN LIVE「喝采Curtain Call」 -  Z-aN\backup\VALIS 6th ONE-MAN LIVE「喝采Curtain Call」 -  Z-aN\decrypt"
    ts_file_path = 'index_8_683900.ts'         # 加密的 .ts 文件路徑
    key_file_path = 'server.key'             # 密鑰文件路徑
    #iv_hex = '0x3DEFA6D2DC885ED5223B4D4B7C50A72F'  # 可選，初始化向量（如未指定，默認為 0 填充）
    # 如果提供 IV，將其轉換為字節
    #iv = bytes.fromhex(iv_hex.replace('0x', '')) if iv_hex else None
    with open(os.path.join(source_folder, key_file_path), 'rb') as key_file:
        key = key_file.read()
    #print(f"IV: {iv.hex()} (len={len(iv)})" if iv else "IV: None")
    print(f"Key: {key.hex()} (len={len(key)})")
    # 執行解密
    ts_with_key_file(os.path.join(source_folder, ts_file_path), os.path.join(decrypted_folder, ts_file_path), key)
    #command = f"openssl aes-128-cbc -d -in {os.path.join(source_folder, ts_file_path)} -out {os.path.join(decrypted_folder)} -K 6806902080b0fc7c17e13611347802ee -iv 3defa6d2dc885ed5223b4d4b7c50a72f -nosalt"
    #print(command)
    #openssl aes-128-cbc -d -in "M:\自製資料\開發中\m3u8下載器\downloads\SINKA LIVE SERIES EP.Ⅵ V.W.P 3rd ONE-MAN LIVE 「現象Ⅲ-神椿市探訪中-」 -  Z-aN\視聴ページ\fragments\index_6_11083.ts" -out "M:\自製資料\開發中\m3u8下載器\downloads\SINKA LIVE SERIES EP.Ⅵ V.W.P 3rd ONE-MAN LIVE 「現象Ⅲ-神椿市探訪中-」 -  Z-aN\視聴ページ\decrypt\index_6_11083.ts" -K 6806902080b0fc7c17e13611347802ee -iv 0 -nosalt