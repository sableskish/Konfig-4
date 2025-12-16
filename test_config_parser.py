#!/usr/bin/env python3
import unittest
import tempfile
import os
import json
from config_parser import ConfigParser

class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.parser = ConfigParser()
    
    def test_remove_comments(self):
        text = """key1 = value1 || комментарий
key2 = value2 (* многострочный
комментарий *) key3 = value3"""
        
        result = self.parser.remove_comments(text)
        expected = "key1 = value1 \nkey2 = value2  key3 = value3"
        self.assertEqual(result.strip(), expected.strip())
    
    def test_parse_number(self):
        self.assertEqual(self.parser.parse_number("123"), 123)
        self.assertEqual(self.parser.parse_number("3.14"), 3.14)
        self.assertEqual(self.parser.parse_number("0.5"), 0.5)
    
    def test_parse_string(self):
        self.assertEqual(self.parser.parse_string("[[test]]"), "test")
        self.assertEqual(self.parser.parse_string("[[Hello World]]"), "Hello World")
    
    def test_parse_array(self):
        result = self.parser.parse_array("{ 1. 2. 3. }")
        self.assertEqual(result, [1, 2, 3])
        
        result = self.parser.parse_array("{ [[a]]. [[b]]. [[c]]. }")
        self.assertEqual(result, ["a", "b", "c"])
        
        result = self.parser.parse_array("{ { 1. 2. }. { 3. 4. }. }")
        self.assertEqual(result, [[1, 2], [3, 4]])
    
    def test_parse_value(self):
        self.assertEqual(self.parser.parse_value("123"), 123)
        self.assertEqual(self.parser.parse_value("3.14"), 3.14)
        self.assertEqual(self.parser.parse_value("[[test]]"), "test")
        
        self.assertEqual(self.parser.parse_value("{ 1. 2. 3. }"), [1, 2, 3])
    
    def test_parse_assignment(self):
        self.parser.parse_assignment("pi := 3.14")
        self.assertEqual(self.parser.constants["pi"], 3.14)
        
        self.parser.parse_assignment("name := [[John]]")
        self.assertEqual(self.parser.constants["name"], "John")
    
    def test_constant_evaluation(self):
        self.parser.parse_assignment("max_connections := 100")
        
        value = self.parser.parse_value("!(max_connections)")
        self.assertEqual(value, 100)
    
    def test_parse_key_value(self):
        key, value = self.parser.parse_key_value("port = 8080")
        self.assertEqual(key, "port")
        self.assertEqual(value, 8080)
        
        key, value = self.parser.parse_key_value("name = [[Server]]")
        self.assertEqual(key, "name")
        self.assertEqual(value, "Server")
    
    def test_full_parse(self):
        text = """
        || Конфигурация сервера
        name := [[Test Server]]
        
        server = {
            host = [[localhost]]
            port = 8080
            name = !(name)
            max_connections = 100
            protocols = { [[http]]. [[https]]. }
            ports = { 80. 443. 8080. }
        }
        
        (*
        Настройки базы данных
        *)
        database = {
            host = [[db.local]]
            port = 5432
            pool_size = 10
        }
        """
        
        result = self.parser.parse(text)
        
        self.assertIn("server", result)
        self.assertIn("database", result)
        self.assertEqual(result["server"]["name"], "Test Server")
        self.assertEqual(result["server"]["port"], 8080)
        self.assertEqual(result["database"]["port"], 5432)
    
    def test_error_handling(self):
        with self.assertRaises(SyntaxError):
            self.parser.remove_comments("key = value (* незакрытый")
        
        with self.assertRaises(SyntaxError):
            self.parser.parse_key_value("123 = value")
        
        with self.assertRaises(NameError):
            self.parser.parse_value("!(undefined)")
        
        with self.assertRaises(SyntaxError):
            self.parser.parse("key value")
    
    def test_nested_structures(self):
        text = """
        config = {
            level1 = {
                level2 = {
                    value = [[deep]]
                    numbers = { 1. 2. 3. }
                }
            }
            array_of_arrays = { { 1. 2. }. { 3. 4. }. }
        }
        """
        
        result = self.parser.parse(text)
        self.assertEqual(result["config"]["level1"]["level2"]["value"], "deep")
        self.assertEqual(result["config"]["array_of_arrays"], [[1, 2], [3, 4]])

class TestCommandLine(unittest.TestCase):
    def test_cli_workflow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as input_file:
            input_file.write("""
            app_name := [[My Application]]
            version = 1.0
            name = !(app_name)
            features = { [[auth]]. [[logging]]. [[api]]. }
            """)
            input_path = input_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            import subprocess
            result = subprocess.run(
                ['python', 'config_parser.py', '-i', input_path, '-o', output_path],
                capture_output=True,
                text=True
            )
            
            self.assertEqual(result.returncode, 0)
            
            with open(output_path, 'r') as f:
                output_data = json.load(f)
            
            self.assertEqual(output_data['version'], 1.0)
            self.assertEqual(output_data['name'], "My Application")
            self.assertEqual(output_data['features'], ["auth", "logging", "api"])
            
        finally:
            os.unlink(input_path)
            os.unlink(output_path)

if __name__ == "__main__":
    unittest.main()