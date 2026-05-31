import os
import re
import xml.etree.ElementTree as ET

# 请修改为你的游戏解包出来的 data 文件夹路径
DATA_DIR = r"C:\gmae\data\data" 

def clean_xml(filepath):
    """读取并清理 XML，去除头部的声明以防解析报错"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        content = re.sub(r'<\?xml.*?\?>', '', content, flags=re.IGNORECASE)
        return f"<dummy_root>\n{content}\n</dummy_root>"
    except Exception as e:
        print(f"读取文件失败: {filepath} - {e}")
        return "<dummy_root></dummy_root>"

def build_translation_dicts():
    dict_systems = {}
    dict_crew = {}
    dict_weapons = {}
    
    # 第一遍遍历：尝试从 text*.xml 提取所有的本地化文本池
    localization_pool = {}
    print("正在构建本地化文本池...")
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("text") and filename.endswith(".xml"):
            filepath = os.path.join(DATA_DIR, filename)
            root = ET.fromstring(clean_xml(filepath))
            # 查找 <text name="ID">中文内容</text>
            for text_elem in root.findall(".//text"):
                name_id = text_elem.get("name")
                if name_id and text_elem.text:
                    localization_pool[name_id.strip()] = text_elem.text.strip()

    # 第二遍遍历：从 blueprints*.xml 提取实体并关联翻译
    print("正在提取蓝图数据...")
    for filename in os.listdir(DATA_DIR):
        if "blueprints" in filename.lower() and filename.endswith(".xml"):
            filepath = os.path.join(DATA_DIR, filename)
            root = ET.fromstring(clean_xml(filepath))
            
            # 1. 提取系统
            for sys in root.findall(".//systemBlueprint"):
                sys_id = sys.get("name")
                title_elem = sys.find("title")
                if sys_id and title_elem is not None:
                    title_text = title_elem.get("id") or title_elem.text # 有些汉化写在属性里，有些在文本里
                    if title_text:
                        # 如果文本是个 ID，去池子里查；否则直接用
                        zh_text = localization_pool.get(title_text, title_text)
                        dict_systems[sys_id] = zh_text
                        
            # 2. 提取船员
            for crew in root.findall(".//crewBlueprint"):
                crew_id = crew.get("name")
                title_elem = crew.find("title")
                if crew_id and title_elem is not None:
                    title_text = title_elem.get("id") or title_elem.text
                    if title_text:
                        zh_text = localization_pool.get(title_text, title_text)
                        dict_crew[crew_id] = zh_text
                        
            # 3. 提取武器和无人机 (统一放到武器字典里，或者你可以再分)
            for item in root.findall(".//weaponBlueprint") + root.findall(".//droneBlueprint") + root.findall(".//augmentBlueprint"):
                item_id = item.get("name")
                title_elem = item.find("title")
                if item_id and title_elem is not None:
                    title_text = title_elem.get("id") or title_elem.text
                    if title_text:
                        zh_text = localization_pool.get(title_text, title_text)
                        dict_weapons[item_id] = zh_text

    # 对于奖励标签，由于它是硬编码的逻辑，我们手动提供一部分常见的基础映射
    dict_rewards = {
        "scrap_only": "废料",
        "standard": "标准物资(废料/燃料/弹药/无人机部件)",
        "fuel_only": "燃料",
        "missiles_only": "导弹/弹药",
        "droneparts_only": "无人机部件",
        "weapon": "随机武器",
        "drone": "随机无人机",
        "augment": "随机系统升级",
        "LOW": "少量",
        "MED": "中等",
        "HIGH": "大量",
        "RANDOM": "随机数量"
    }

    # 将结果写入 Python 文件
    print("正在生成 translation_dict.py ...")
    with open("translation_dict.py", "w", encoding="utf-8") as f:
        f.write("# 自动生成的 FTL 翻译字典\n\n")
        f.write(f"DICT_SYSTEMS = {repr(dict_systems)}\n\n")
        f.write(f"DICT_CREW = {repr(dict_crew)}\n\n")
        f.write(f"DICT_WEAPONS = {repr(dict_weapons)}\n\n")
        f.write(f"DICT_REWARDS = {repr(dict_rewards)}\n\n")
        f.write("""
def translate(category, raw_key):
    dicts = {
        'systems': DICT_SYSTEMS,
        'crew': DICT_CREW,
        'weapons': DICT_WEAPONS,
        'rewards': DICT_REWARDS
    }
    target_dict = dicts.get(category, {})
    return target_dict.get(raw_key, raw_key)
""")
    print("完成！")

if __name__ == "__main__":
    build_translation_dicts()