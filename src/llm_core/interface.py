
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import openai
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel

from src.config import settings
from src.entities.profile import CognitiveProfile
from src.exceptions import LLMError
from src.logger import logger


class LLMResponse(BaseModel):
    """Standardized LLM response"""
    content: str
    model_used: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_response(self, messages: List[Dict[str, str]], 
                              **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = openai.AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY
        )
        self.model = "gpt-4-turbo-preview"
        self.max_tokens = 4000
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, messages: List[Dict[str, str]], 
                              **kwargs) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', 0.7),
                top_p=kwargs.get('top_p', 0.9)
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model_used=self.model,
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMError(f"OpenAI generation failed: {e}")
    
    def get_max_tokens(self) -> int:
        return self.max_tokens


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.ANTHROPIC_API_KEY
        )
        self.model = "claude-3-sonnet-20240229"
        self.max_tokens = 4000
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_response(self, messages: List[Dict[str, str]], 
                              **kwargs) -> LLMResponse:
        try:
            # Convert messages format for Anthropic
            system_message = ""
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', 0.7),
                system=system_message,
                messages=user_messages
            )
            
            return LLMResponse(
                content=response.content[0].text,
                model_used=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                metadata={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise LLMError(f"Anthropic generation failed: {e}")
    
    def get_max_tokens(self) -> int:
        return self.max_tokens


class LLMInterface:
    """Main LLM interface that manages multiple providers"""
    
    def __init__(self):
        self.providers = {}
        
        # Initialize available providers
        if settings.OPENAI_API_KEY:
            self.providers['openai'] = OpenAIProvider()
        
        if settings.ANTHROPIC_API_KEY:
            self.providers['anthropic'] = AnthropicProvider()
        
        # Default provider
        self.default_provider = list(self.providers.keys())[0] if self.providers else None
        
        if not self.providers:
            logger.warning("No LLM providers configured")
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              provider: Optional[str] = None,
                              **kwargs) -> LLMResponse:
        """Generate response using specified or default provider"""
        
        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise LLMError(f"Provider {provider_name} not available")
        
        provider_instance = self.providers[provider_name]
        
        try:
            return await provider_instance.generate_response(messages, **kwargs)
        except Exception as e:
            # Fallback to another provider if available
            if len(self.providers) > 1:
                fallback_providers = [p for p in self.providers.keys() if p != provider_name]
                for fallback in fallback_providers:
                    try:
                        logger.warning(f"Falling back to {fallback} provider")
                        return await self.providers[fallback].generate_response(messages, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback provider {fallback} also failed: {fallback_error}")
            
            raise LLMError(f"All LLM providers failed: {e}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        health_status = {}
        
        for name, provider in self.providers.items():
            try:
                test_messages = [{"role": "user", "content": "Hello"}]
                await provider.generate_response(test_messages, max_tokens=10)
                health_status[name] = True
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                health_status[name] = False
        
        return health_status


# Global LLM interface instance
llm_interface = LLMInterface()