"""
https://github.com/langchain-ai/langchain/blob/master/docs/extras/modules/model_io/output_parsers/pydantic.ipynb

Example 1.

# Define your desired data structure.
class Joke(BaseModel):
    setup: str = Field(description="question to set up a joke")
    punchline: str = Field(description="answer to resolve the joke")

    # You can add custom validation logic easily with Pydantic.
    @validator("setup")
    def question_ends_with_question_mark(cls, field):
        if field[-1] != "?":
            raise ValueError("Badly formed question!")
        return field


Example 2.

# Here's another example, but with a compound typed field.
class Actor(BaseModel):
    name: str = Field(description="name of an actor")
    film_names: List[str] = Field(description="list of names of films they starred in")
"""

import json, re
from loguru import logger as logging

PYDANTIC_FORMAT_INSTRUCTIONS = """The output should be formatted as a JSON instance that conforms to the JSON schema below.

As an example, for the schema {{"properties": {{"foo": {{"title": "Foo", "description": "a list of strings", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["foo"]}}
the object {{"foo": ["bar", "baz"]}} is a well-formatted instance of the schema. The object {{"properties": {{"foo": ["bar", "baz"]}}}} is not well-formatted.

Here is the output schema:
```
{schema}
```"""


PYDANTIC_FORMAT_INSTRUCTIONS_SIMPLE = """The output should be formatted as a JSON instance that conforms to the JSON schema below.
```
{schema}
```"""

class JsonStringError(Exception): ...

class GptJsonIO():

    def __init__(self, schema, example_instruction=True):
        self.pydantic_object = schema
        self.example_instruction = example_instruction
        self.format_instructions = self.generate_format_instructions()

    def generate_format_instructions(self):
        schema = self.pydantic_object.schema()

        # Remove extraneous fields.
        reduced_schema = schema
        if "title" in reduced_schema:
            del reduced_schema["title"]
        if "type" in reduced_schema:
            del reduced_schema["type"]
        # Ensure json in context is well-formed with double quotes.
        schema_str = json.dumps(reduced_schema)
        if self.example_instruction:
            return PYDANTIC_FORMAT_INSTRUCTIONS.format(schema=schema_str)
        else:
            return PYDANTIC_FORMAT_INSTRUCTIONS_SIMPLE.format(schema=schema_str)

    def generate_output(self, text):
        # Greedy search for 1st json candidate.
        match = re.search(
            r"\{.*\}", text.strip(), re.MULTILINE | re.IGNORECASE | re.DOTALL
        )
        json_str = ""
        if match: json_str = match.group()
        json_object = json.loads(json_str, strict=False)
        final_object = self.pydantic_object.parse_obj(json_object)
        return final_object

    def generate_repair_prompt(self, broken_json, error):
        prompt = "Fix a broken json string.\n\n" + \
                 "(1) The broken json string need to fix is: \n\n" + \
                 "```" + "\n" + \
                 broken_json + "\n" + \
                 "```" + "\n\n" + \
                 "(2) The error message is: \n\n" + \
                 error + "\n\n" + \
                "Now, fix this json string. \n\n"
        return prompt

    def generate_output_auto_repair(self, response, gpt_gen_fn):
        """
        response: string containing canidate json
        gpt_gen_fn: gpt_gen_fn(inputs, sys_prompt)
        """
        try:
            result = self.generate_output(response)
        except Exception as e:
            try:
                logging.info(f'Repairing json：{response}')
                repair_prompt = self.generate_repair_prompt(broken_json = response, error=repr(e))
                result = self.generate_output(gpt_gen_fn(repair_prompt, self.format_instructions))
                logging.info('Repair json success.')
            except Exception as e:
                # 没辙了，放弃治疗
                logging.info('Repair json fail.')
                raise JsonStringError('Cannot repair json.', str(e))
        return result

