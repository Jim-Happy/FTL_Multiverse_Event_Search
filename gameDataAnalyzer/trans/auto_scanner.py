import os
import re
import xml.etree.ElementTree as ET

# 👇 请把这里改成你存放 XML 文件的实际路径
DATA_DIR = r"C:\gmae\data\data" 

def build_global_dict():
    global_dict = {}

    print("开始全局扫描 XML 文件...")
    
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith(".xml"):
            continue

        filepath = os.path.join(DATA_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 清理 XML 声明，并包裹一个伪根节点（防止 FTL 文件格式不规范报错）
            content = re.sub(r'<\?xml.*?\?>', '', content, flags=re.IGNORECASE)
            xml_string = f"<dummy_root>\n{content}\n</dummy_root>"
            
            root = ET.fromstring(xml_string)
            
            # 策略 1: 提取所有 <text name="ID">中文内容</text>
            for text_node in root.findall('.//text'):
                node_id = text_node.get('name')
                if node_id and text_node.text:
                    global_dict[node_id.strip()] = text_node.text.strip()
                    
            # 策略 2: 提取所有带有 name 属性，且内部有 <title> 标签的蓝图
            # 这将一网打尽所有武器、无人机、船员、系统、以及 GIFTLIST 这种随机池
            for blueprint in root.findall('.//*[@name]'):
                node_id = blueprint.get('name')
                title_node = blueprint.find('title')
                if node_id and title_node is not None and title_node.text:
                    global_dict[node_id.strip()] = title_node.text.strip()
                    
            # 策略 3: 提取成就 <achievement name="ID"><name>中文</name>
            for ach in root.findall('.//achievement'):
                node_id = ach.get('name')
                name_node = ach.find('name')
                if node_id and name_node is not None and name_node.text:
                    global_dict[node_id.strip()] = name_node.text.strip()

        except Exception as e:
            print(f"解析 {filename} 时出错 (已跳过): {e}")

    # 兜底补充：把一些写死在代码里、XML里不一定有的基础游戏词汇直接塞进去
    base_resources = {
        "scrap": "废料", "fuel": "燃料", "missiles": "导弹", "drones": "无人机部件",
        "item": "物品/插件", "drone": "无人机", "weapon": "武器",
        "LOW": "少量", "MED": "中等", "HIGH": "大量", "RANDOM": "随机"
    }
    global_dict.update(base_resources)

    # 写入到你的翻译字典文件中
    out_file = "translation_dict.py"
    print(f"\n扫描完成！共提取了 {len(global_dict)} 条翻译记录。")
    print(f"正在生成 {out_file} ...")
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# 自动生成的 FTL 全局超级翻译字典\n\n")
        f.write("GLOBAL_DICT = {\n")
        for k, v in global_dict.items():
            # 过滤掉内容里的换行符和双引号，防止破坏 Python 语法
            clean_v = v.replace('\n', ' ').replace('"', '\\"')
            f.write(f'    "{k}": "{clean_v}",\n')
        f.write("}\n\n")
        
        # 改造 translate 函数，现在无视 category，直接从全局字典查
        f.write("def translate(category, raw_key):\n")
        f.write("    return GLOBAL_DICT.get(raw_key, raw_key)\n")

    print("大功告成！你可以直接启动主程序了。")

if __name__ == "__main__":
    build_global_dict()