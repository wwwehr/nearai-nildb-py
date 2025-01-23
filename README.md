# nildb on nearai

> [!Tip]
> Set up nearai tools and account by following [these instructions](https://docs.near.ai/agents/quickstart/#pre-requisites)

```shell
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
nearai agent create --name nildb-test --description "nilDB NEAR AI Agent"
```
Copy the metadata file and update the environment configs
```shell
cp metadata.json.example metadata.json

# maybe use jq to parse another config file?
jq -c '.' .nildb.config.json | jq -sRr @json
```
Copy code over to local runner filesystem
```shell
cp -r agent.py metadata.json ~/.nearai/registry/<YOUR NEAR USERNAME>/nildb-test/0.0.1/
```

Run the agent
```
nearai agent interactive ~/.nearai/registry/wwwehr.near/nildb-test/0.0.1 --local
```

... and give it a prompt:
```shell
upload a whimsical poem about citizen band radios to nildb
```

