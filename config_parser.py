import re
import sys
import json
import argparse
from typing import Dict, List, Any, Union, Optional
from pathlib import Path

class ConfigParser:
    def __init__(self):
        self.constants: Dict[str, Any] = {}
        self.output_data = {}
        
    def remove_comments(self, text: str) -> str:
        while True:
            start = text.find("(*")
            if start == -1:
                break
            end = text.find("*)", start + 2)
            if end == -1:
                raise SyntaxError("Незакрытый многострочный комментарий")
            text = text[:start] + text[end + 2:]
        
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            comment_pos = line.find("||")
            if comment_pos != -1:
                line = line[:comment_pos]
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def parse_number(self, value: str) -> Union[int, float]:
        if '.' in value:
            return float(value)
        return int(value)
    
    def parse_string(self, value: str) -> str:
        if value.startswith("[[") and value.endswith("]]"):
            return value[2:-2]
        return value
    
    def parse_array(self, value: str) -> List[Any]:
        value = value.strip()
        if not value.startswith("{") or not value.endswith("}"):
            raise SyntaxError(f"Некорректный формат массива: {value}")
        
        content = value[1:-1].strip()
        if not content:
            return []
        
        items = []
        current_item = ""
        brace_count = 0
        bracket_count = 0
        
        for char in content + ".":
            if char == "." and brace_count == 0 and bracket_count == 0:
                if current_item.strip():
                    items.append(current_item.strip())
                current_item = ""
            else:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                current_item += char
        
        parsed_items = []
        for item in items:
            parsed_items.append(self.parse_value(item.strip()))
        
        return parsed_items
    
    def parse_value(self, value: str) -> Any:
        value = value.strip()
        
        const_match = re.match(r'^!\(([a-zA-Z][a-zA-Z0-9]*)\)$', value)
        if const_match:
            const_name = const_match.group(1)
            if const_name not in self.constants:
                raise NameError(f"Неопределенная константа: {const_name}")
            return self.constants[const_name]
        
        if re.match(r'^\d*\.\d+$', value) or re.match(r'^\d+$', value):
            return self.parse_number(value)
        
        if value.startswith("[[") and value.endswith("]]"):
            return self.parse_string(value)
        
        if value.startswith("{") and value.endswith("}"):
            return self.parse_array(value)
        
        if re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', value):
            return value
        
        return value
    
    def parse_assignment(self, line: str) -> None:
        match = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)\s*:=\s*(.+)$', line)
        if not match:
            raise SyntaxError(f"Некорректное объявление константы: {line}")
        
        name = match.group(1)
        value_str = match.group(2).strip()
        
        value = self.parse_value(value_str)
        
        self.constants[name] = value
    
    def parse_key_value(self, line: str) -> tuple:
        parts = line.split('=', 1)
        if len(parts) != 2:
            raise SyntaxError(f"Некорректная пара ключ=значение: {line}")
        
        key = parts[0].strip()
        value_str = parts[1].strip()
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', key):
            raise SyntaxError(f"Некорректное имя ключа: {key}")
        
        value = self.parse_value(value_str)
        
        return key, value
    
    def parse(self, text: str) -> Dict[str, Any]:
        text = self.remove_comments(text)
        
        lines = text.split('\n')
        result = {}
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                if ":=" in line:
                    self.parse_assignment(line)
                elif "=" in line:
                    key, value = self.parse_key_value(line)
                    result[key] = value
                else:
                    if line:
                        raise SyntaxError(f"Некорректный синтаксис в строке {line_num}: {line}")
            except Exception as e:
                raise SyntaxError(f"Ошибка в строке {line_num}: {e}")
        
        return result

def main():
    parser = argparse.ArgumentParser(
        description='Конвертер учебного конфигурационного языка в JSON'
    )
    parser.add_argument('-i', '--input', required=True, help='Путь к входному файлу')
    parser.add_argument('-o', '--output', required=True, help='Путь к выходному файлу JSON')
    
    args = parser.parse_args()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            input_text = f.read()
        
        config_parser = ConfigParser()
        result = config_parser.parse(input_text)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Конфигурация успешно преобразована в {args.output}")
        
    except FileNotFoundError:
        print(f"Ошибка: файл {args.input} не найден", file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print(f"Синтаксическая ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()