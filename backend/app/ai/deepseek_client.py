import json
from json import JSONDecodeError
from typing import Any

import aiohttp
from pydantic import BaseModel, ValidationError

from app.config import Settings


class DeepSeekError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        if settings.deepseek_api_key is None:
            raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
        self.api_key = settings.deepseek_api_key.get_secret_value()
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        payload = await self._request(system_prompt, user_prompt, response_json=True)
        content = _extract_content(payload)
        try:
            return schema.model_validate_json(_strip_json_fence(content))
        except (ValidationError, JSONDecodeError) as exc:
            retry_prompt = (
                f"{user_prompt}\n\nПредыдущий ответ не прошел JSON schema validation: "
                f"{exc.errors(include_url=False)}. Верни только валидный JSON."
            )
            payload = await self._request(system_prompt, retry_prompt, response_json=True)
            content = _extract_content(payload)
            return schema.model_validate_json(_strip_json_fence(content))

    async def _request(
        self, system_prompt: str, user_prompt: str, *, response_json: bool
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if response_json:
            body["response_format"] = {"type": "json_object"}

        timeout = aiohttp.ClientTimeout(total=60)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=body,
                ) as response:
                    if response.status in {401, 403}:
                        raise DeepSeekError("DeepSeek authentication failed")
                    if response.status == 429:
                        raise DeepSeekError("DeepSeek rate limit")
                    if response.status >= 500:
                        raise DeepSeekError("DeepSeek API unavailable")
                    if response.status >= 400:
                        raise DeepSeekError("DeepSeek API request failed")
                    return await response.json()
        except TimeoutError as exc:
            raise DeepSeekError("DeepSeek timeout") from exc
        except aiohttp.ClientError as exc:
            raise DeepSeekError("DeepSeek API unavailable") from exc


def _extract_content(payload: dict[str, Any]) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekError("DeepSeek returned invalid response") from exc


def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    json.loads(text)
    return text
