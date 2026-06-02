import unittest

from backend.services.xml_parser import XMLParser, XMLParsingError


class XMLParserTests(unittest.TestCase):
    def test_parses_tags_inside_markdown_fence(self):
        raw = """```xml
<file path="src/main.py" action="update">print('ok')</file>
<transition_to>QA_TESTING</transition_to>
```"""

        actions = XMLParser.parse(raw)

        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].action_type, "file")
        self.assertEqual(actions[1].payload["state"], "QA_TESTING")

    def test_raises_on_missing_valid_tags(self):
        with self.assertRaises(XMLParsingError):
            XMLParser.parse("hello world")


if __name__ == "__main__":
    unittest.main()
