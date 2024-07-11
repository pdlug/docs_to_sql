import instructor

from pydantic import BaseModel
from openai import OpenAI
from typing import Type, TypeVar

from docs_to_sql.settings import settings


openai_client = OpenAI(api_key=settings.openai_api_key)
client = instructor.from_openai(openai_client)


T = TypeVar("T", bound=BaseModel)


def extract(model: Type[T], system_prompt: str, content: str) -> T:
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    )
