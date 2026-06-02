from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


class XMLParsingError(ValueError):
    pass


@dataclass
class ParsedAction:
    action_type: str
    payload: dict


class XMLParser:
    _CODE_FENCE = re.compile(r"```(?:xml)?|```", re.IGNORECASE)

    @classmethod
    def clean_markdown(cls, text: str) -> str:
        return cls._CODE_FENCE.sub("", text).strip()

    @classmethod
    def parse(cls, text: str) -> list[ParsedAction]:
        cleaned = cls.clean_markdown(text)
        soup = BeautifulSoup(cleaned, "html.parser")

        actions: list[ParsedAction] = []

        for file_tag in soup.find_all("file"):
            path = file_tag.get("path")
            action = file_tag.get("action")
            content = file_tag.text.strip("\n")
            if not path or action not in {"create", "update", "upsert"}:
                raise XMLParsingError("Invalid <file> tag")
            actions.append(
                ParsedAction(
                    action_type="file",
                    payload={"path": path, "action": action, "content": content},
                )
            )

        for doc_tag in soup.find_all("doc_update"):
            path = doc_tag.get("path")
            action = doc_tag.get("action", "upsert")
            content = doc_tag.text.strip("\n")
            if not path or action not in {"create", "update", "upsert"}:
                raise XMLParsingError("Invalid <doc_update> tag")
            actions.append(
                ParsedAction(
                    action_type="doc_update",
                    payload={"path": path, "action": action, "content": content},
                )
            )

        for execute_tag in soup.find_all("execute"):
            command = execute_tag.text.strip()
            if not command:
                raise XMLParsingError("Invalid <execute> tag")
            actions.append(ParsedAction(action_type="execute", payload={"command": command}))

        for transition_tag in soup.find_all("transition_to"):
            to_state = transition_tag.text.strip()
            if not to_state:
                raise XMLParsingError("Invalid <transition_to> tag")
            actions.append(
                ParsedAction(action_type="transition_to", payload={"state": to_state})
            )

        if not actions:
            raise XMLParsingError("No valid XML handoff tags found")

        return actions
