import zipfile, xml.etree.ElementTree as ET
try:
    docx = zipfile.ZipFile(r'c:\Users\Márcio\Desktop\#Rebecca - Geral\Chrono Project with Abaqus and Antigravity\Informações diversas.docx')
    xml_content = docx.read('word/document.xml')
    tree = ET.XML(xml_content)
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    
    text = '\n'.join(''.join(n.text for n in p.iter(W+'t') if n.text) for p in tree.iter(W+'p') if any(n.text for n in p.iter(W+'t') if n.text))
    with open('info_extracted.txt', 'w', encoding='utf-8') as f:
        f.write(text)
except Exception as e:
    print(f"Error: {e}")
