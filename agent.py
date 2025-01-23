from nearai.agents.environment import Environment

import json
import requests
import nilql
import uuid

from typing import Union, Dict, List


AGENT_NAME = "nildb-agent"
PROMPT = """
You are a helpful assistant that can upload data into a privacy preserving database called nildb. Your data generation will be inspired by user messages and you will then prepare the data as a JSON output. 

Rules for the content:
1. Never generate or allow special characters
2. Never generate control characters
3. Never generate newlines, instead concatenate with a semicolon
4. The content must serialize to JSON text format and be ASCII iso-8859 latin-1 at all times
5. If the input does not ask you to interact with storage or mention nildb then you must output the uppercase string SKIP. Example:
SKIP
6. Output the final content as a JSON object with one field: content
7. Format the output JSON object as follows. Example:
{"content":"Call me Ishmael"}
8. You must not leave any other commentary, your response must be only the full, valid, and parsable JSON with no additions. Example:
{"content":"Call me Ishmael"}
9. Your response must be complete. If you cannot complete your request in one operation, then you must wait.
"""

JSON_TYPE = Dict[str, Union[str, int, float, bool, None, List, Dict]]


class NilDBAPI:
    def __init__(self, env: Environment, config: str):
        CONFIG = json.loads(config)
        self.nodes = CONFIG["hosts"]
        self.secret_key = nilql.SecretKey.generate(
            {"nodes": [{}] * len(CONFIG["hosts"])}, {"store": True}
        )
        self.env = env

    def data_upload(self, schema_id: str, payload: JSON_TYPE) -> bool:
        """Create/upload records in the specified node and schema."""
        try:
            print(json.dumps(payload))
            payload["text"] = {
                "$allot": nilql.encrypt(self.secret_key, payload["text"])
            }
            payloads = nilql.allot(payload)
            for idx, shard in enumerate(payloads):
                node = self.nodes[idx]
                headers = {
                    "Authorization": f'Bearer {node["bearer"]}',
                    "Content-Type": "application/json",
                }

                body = {"schema": schema_id, "data": [shard]}

                response = requests.post(
                    f"https://{node['url']}/api/v1/data/create",
                    headers=headers,
                    json=body,
                )

                self.env.add_message("assistant", f"-          uploaded to host {idx}")
                # self.env.add_message('assistant', f"- [{idx}]: {json.dumps(response.json())}")
                assert response.status_code == 200 and not response.json().get(
                    "errors", []
                ), ("upload failed: " + response.content)
            return True
        except Exception as e:
            print(f"Error creating records in node {idx}: {str(e)}")
            return False


def generate_nildb_content(
    messages: list[dict[str, str]], env: Environment, retries=3
) -> dict | None:
    res = env.completion(
        [
            {"role": "system", "content": PROMPT},
        ]
        + messages
    )
    try:
        return json.loads(res)
    except json.JSONDecodeError:
        if res == "SKIP":
            return None
        print("Failed to parse JSON from response.")
        print("Response was:", res)
        if retries > 0:
            messages.append(
                {
                    "role": "user",
                    "content": "Please output only the data as specified, with no additional text.",
                }
            )
            return generate_nildb_content(messages, env, retries - 1)
        else:
            print("Exceeded maximum retries for parsing JSON.")
            return None


def task(env: Environment):
    """nildb data uploader"""

    CONFIG = env.env_vars["config"]
    SCHEMA_ID = env.env_vars["schema_id"]
    TEAM = env.env_vars["team"]

    messages = env.list_messages()
    if not messages:
        return

    env.add_message("assistant", f"Generating creative work for [{TEAM}] team...")
    nildb_data = generate_nildb_content(messages, env)
    if nildb_data is None:
        env.add_system_log("Failed to generate content for nildb.")
        env.add_message(
            "assistant",
            "Content generation failed or was skipped. What else can I do for you?",
        )
        env.mark_done()
        return

    env.add_message("assistant", "Encrypting content...")
    nildb = NilDBAPI(env, CONFIG)
    my_id = str(uuid.uuid4())

    env.add_message("assistant", f"Uploading content for schema [{SCHEMA_ID}]...")
    is_ok = nildb.data_upload(
        schema_id=SCHEMA_ID,
        payload={"_id": my_id, "team": TEAM, "text": nildb_data["content"]},
    )
    if is_ok:
        env.add_message("assistant", "COMPLETE! stored content")
    else:
        env.add_message("assistant", "FAILED! error storing content")
    env.mark_done()


task(env)
