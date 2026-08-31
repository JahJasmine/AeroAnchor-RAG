# src/utils/llm_client.py
import os
import httpx
import json
from typing import List, Dict, Any, Optional
from .config import config
from .logger import setup_logger

logger = setup_logger(__name__)

class LLMClient:
    """Unified LLM client - supports DeepSeek and OpenAI (Beiyang relay)"""

    def __init__(self):
        # Read the currently used provider from config
        self.provider = config.get('llm.provider', 'deepseek')

        # Load the config for the corresponding provider
        self._load_provider_config()

        logger.info(f"LLM client initialized, current provider: {self.provider}, model: {self.model}")

    def _load_provider_config(self):
        """Load the config for the current provider"""
        provider_config = config.get(f'llm.{self.provider}', {})

        # Prefer the shared root .env key (set once), fall back to config.yaml.
        env_var = {'deepseek': 'DEEPSEEK_API_KEY', 'openai': 'OPENAI_API_KEY'}.get(self.provider)
        env_key = os.getenv(env_var) if env_var else ''
        self.api_key = (env_key or '').strip() or provider_config.get('api_key', '')
        self.base_url = provider_config.get('base_url', '')
        self.model = provider_config.get('model', '')
        self.temperature = provider_config.get('temperature', 0.3)
        self.max_tokens = provider_config.get('max_tokens', 2000)

        # Validate config
        if not self.api_key or self.api_key.startswith('YOUR_') or self.api_key.startswith('sk-your'):
            logger.warning(f"{self.provider} API key not configured, please check config.yaml")

    def get_provider(self) -> str:
        """Get the currently used provider"""
        return self.provider

    def get_model(self) -> str:
        """Get the currently used model"""
        return self.model

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> str:
        """Unified LLM call interface"""

        if not self.api_key or self.api_key.startswith('YOUR_') or self.api_key.startswith('sk-your'):
            raise ValueError(f"{self.provider} API Key not configured, please check config.yaml")

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }

            if response_format and response_format.get('type') == 'json_object':
                payload['response_format'] = {"type": "json_object"}

            # Fix: use the /v1/chat/completions endpoint
            base = self.base_url.rstrip('/')
            if '/v1' in base:
                url = f"{base}/chat/completions"
            else:
                url = f"{base}/v1/chat/completions"
            logger.debug(f"Request URL: {url}")

            logger.info(f"Calling {self.provider} API: {url}, model: {self.model}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    error_msg = f"API call failed (HTTP {response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # Check whether the response is empty
                response_text = response.text
                if not response_text or response_text.strip() == '':
                    logger.error("API returned an empty response")
                    raise Exception("API returned an empty response")

                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}, response content: {response_text[:200]}")
                    raise Exception(f"API returned malformed data: {response_text[:100]}")

                if 'choices' not in result or not result['choices']:
                    logger.error(f"Abnormal response format: {result}")
                    raise Exception("API response format is abnormal")

                usage = result.get('usage', {})
                logger.info(f"LLM call successful, provider: {self.provider}, token usage: {usage.get('total_tokens', 0)}")

                return result['choices'][0]['message']['content']

        except httpx.TimeoutException:
            logger.error(f"{self.provider} API timed out")
            raise Exception(f"{self.provider} API request timed out")
        except httpx.ConnectError as e:
            logger.error(f"{self.provider} API connection failed: {e}")
            raise Exception(f"Unable to connect to {self.provider} API")
        except Exception as e:
            logger.error(f"{self.provider} API call failed: {str(e)}")
            raise

    async def extract_json(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from an LLM response"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            import re
            # Try to extract a JSON code block
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            matches = re.findall(json_pattern, response_text)
            if matches:
                return json.loads(matches[0])
            # Try to extract brace-delimited content
            brace_pattern = r'\{[\s\S]*\}'
            matches = re.findall(brace_pattern, response_text)
            if matches:
                return json.loads(matches[0])
            raise ValueError(f"Unable to extract JSON from response: {response_text[:200]}")

# Create global instance
llm_client = LLMClient()
