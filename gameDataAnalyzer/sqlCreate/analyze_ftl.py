import os
import xml.etree.ElementTree as ET
import re
from collections import defaultdict

def analyze_ftl_xmls(directory_path):
    tag_attributes = defaultdict(set)
    tag_children = defaultdict(set)
    
    file_count = 0
    error_count = 0

    print(f"开始分析目录: {directory_path}")
    
    for filename in os.listdir(directory_path):
        if not filename.endswith('.xml'):
            continue
            
        filepath = os.path.join(directory_path, filename)
        file_count += 1
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 核心修复：使用正则剔除原始文件中的 <?xml ... ?> 声明
            content = re.sub(r'<\?xml.*?\?>', '', content, flags=re.IGNORECASE)
            
            # 包装虚拟根节点
            wrapped_content = f"<dummy_root>\n{content}\n</dummy_root>"
            
            root = ET.fromstring(wrapped_content)
            
            for elem in root.iter():
                if elem.tag == 'dummy_root':
                    continue
                
                for attr in elem.attrib:
                    tag_attributes[elem.tag].add(attr)
                    
                for child in elem:
                    tag_children[elem.tag].add(child.tag)
                    
        except ET.ParseError as e:
            print(f"[-] XML 解析错误 {filename}: {e}")
            error_count += 1
        except Exception as e:
            print(f"[-] 其他错误 {filename}: {e}")
            error_count += 1

    report = []
    report.append(f"=== FTL XML Schema 分析报告 ===")
    report.append(f"共扫描 XML 文件数: {file_count}")
    report.append(f"解析失败文件数: {error_count}")
    report.append("-" * 40 + "\n")
    
    all_tags = sorted(tag_attributes.keys() | tag_children.keys())
    
    for tag in all_tags:
        attrs = sorted(list(tag_attributes.get(tag, [])))
        children = sorted(list(tag_children.get(tag, [])))
        
        report.append(f"标签: <{tag}>")
        if attrs:
            report.append(f"  - 包含属性 (Attributes): {', '.join(attrs)}")
        else:
            report.append(f"  - 包含属性 (Attributes): [无]")
            
        if children:
            report.append(f"  - 允许的子标签 (Children): {', '.join(children)}")
        else:
            report.append(f"  - 允许的子标签 (Children): [无子节点]")
        report.append("")
        
    output_filename = "ftl_schema_report.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"\n分析完成！共发现 {len(all_tags)} 种不同的标签。")
    print(f"报告已保存至当前目录下的: {output_filename}")

if __name__ == "__main__":
    # 保持你之前的路径
    XML_DIR = r"D:\My_Program\FTLSearch\gamedata" 
    analyze_ftl_xmls(XML_DIR)