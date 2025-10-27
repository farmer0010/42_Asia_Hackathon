import json, jsonschema

def validate_json(js, schema):
    try:
        obj = json.loads(js)
        jsonschema.validate(obj, schema)
        return True, obj
    except Exception as e:
        return False, str(e)

def fix_prompt(bad, schema, err):
    return (
f"You fix JSON. Return ONLY valid JSON matching this schema.\nSchema:\n{json.dumps(schema,ensure_ascii=False)}\n"
f"Broken JSON:\n{bad}\nError:\n{err}\n"
    )

async def guarded_json(llm, base_prompt, schema, retries=2):
    out = await llm.generate(base_prompt, max_tokens=800, temperature=0.0)
    ok, res = validate_json(out, schema)
    for _ in range(retries):
        if ok: return res
        out = await llm.generate(fix_prompt(out, schema, res), max_tokens=800, temperature=0.0)
        ok, res = validate_json(out, schema)
    return res if ok else None  # BE가 후처리
