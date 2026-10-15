"""LLM service for managing LLM calls with retries and fallback mechanisms."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import (
    Environment,
    settings,
)
from src.system.logs import logger


# Monkey-patch ChatOpenAI.get_num_tokens_from_messages to support non-OpenAI models (e.g. Gemini)
_orig_get_num_tokens_from_messages = ChatOpenAI.get_num_tokens_from_messages


def _safe_get_num_tokens_from_messages(self, messages: List[BaseMessage]) -> int:
    try:
        return _orig_get_num_tokens_from_messages(self, messages)
    except Exception:
        total_chars = sum(len(str(getattr(m, "content", ""))) for m in messages)
        return max(1, total_chars // 4)


ChatOpenAI.get_num_tokens_from_messages = _safe_get_num_tokens_from_messages

# Monkey-patch to preserve Gemini extra_content (thought_signature) in function call parts
import langchain_openai.chat_models.base as _lc_base

import langchain_core.messages.tool as _lc_tool
import langchain_core.messages.ai as _lc_ai
import langchain_core.output_parsers.openai_tools as _lc_openai_tools

_orig_tool_call = _lc_tool.tool_call


def _safe_tool_call(*, name: str, args: Dict[str, Any], id: Optional[str] = None, **kwargs) -> _lc_tool.ToolCall:
    tc = _orig_tool_call(name=name, args=args, id=id)
    for k, v in kwargs.items():
        tc[k] = v
    return tc


_lc_tool.tool_call = _safe_tool_call
_lc_ai.create_tool_call = _safe_tool_call
_lc_openai_tools.create_tool_call = _safe_tool_call

_orig_convert_dict_to_message = _lc_base._convert_dict_to_message


def _patched_convert_dict_to_message(_dict):
    msg = _orig_convert_dict_to_message(_dict)
    if _dict.get("role") == "assistant" and _dict.get("tool_calls"):
        raw_tcs = _dict["tool_calls"]
        msg.additional_kwargs["raw_tool_calls"] = raw_tcs
        for tc, raw_tc in zip(getattr(msg, "tool_calls", []), raw_tcs):
            if isinstance(raw_tc, dict) and "extra_content" in raw_tc:
                tc["extra_content"] = raw_tc["extra_content"]
    return msg


_lc_base._convert_dict_to_message = _patched_convert_dict_to_message

_orig_lc_tool_call_to_openai = _lc_base._lc_tool_call_to_openai_tool_call


def _patched_lc_tool_call_to_openai(tool_call):
    d = _orig_lc_tool_call_to_openai(tool_call)
    if isinstance(tool_call, dict) and "extra_content" in tool_call:
        d["extra_content"] = tool_call["extra_content"]
    return d


_lc_base._lc_tool_call_to_openai_tool_call = _patched_lc_tool_call_to_openai


def _build_gemini_models() -> List[Dict[str, Any]]:
    candidate_names = [
        settings.DEFAULT_LLM_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
    ]
    seen = set()
    models = []
    for name in candidate_names:
        if name and name not in seen:
            seen.add(name)
            models.append(
                {
                    "name": name,
                    "llm": ChatOpenAI(
                        model=name,
                        api_key=settings.LLM_API_KEY,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                        max_tokens=settings.MAX_TOKENS,
                    ),
                }
            )
    return models


class LLMRegistry:
    """Registry of available LLM models with pre-initialized instances.

    This class maintains a list of LLM configurations and provides
    methods to retrieve them by name with optional argument overrides.
    """

    # Build only the configured provider's clients. Constructing OpenAI clients
    # eagerly breaks Gemini-only deployments when OPENAI_API_KEY is absent.
    LLMS: List[Dict[str, Any]] = (
        _build_gemini_models()
        if settings.LLM_PROVIDER == "gemini"
        else [
        {
            "name": "gpt-5-mini",
            "llm": ChatOpenAI(
                model="gpt-5-mini",
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5",
            "llm": ChatOpenAI(
                model="gpt-5",
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5-nano",
            "llm": ChatOpenAI(
                model="gpt-5-nano",
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                reasoning={"effort": "minimal"},
            ),
        },
        {
            "name": "gpt-4o",
            "llm": ChatOpenAI(
                model="gpt-4o",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.95 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
                presence_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
                frequency_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
            ),
        },
        {
            "name": "gpt-4o-mini",
            "llm": ChatOpenAI(
                model="gpt-4o-mini",
                temperature=settings.DEFAULT_LLM_TEMPERATURE,
                api_key=settings.LLM_API_KEY,
                max_tokens=settings.MAX_TOKENS,
                top_p=0.9 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
            ),
        },
        ]
    )

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        """Get an LLM by name with optional argument overrides.

        Args:
            model_name: Name of the model to retrieve
            **kwargs: Optional arguments to override default model configuration

        Returns:
            BaseChatModel instance

        Raises:
            ValueError: If model_name is not found in LLMS
        """
        # Find the model in the registry
        model_entry = None
        for entry in cls.LLMS:
            if entry["name"] == model_name:
                model_entry = entry
                break

        if not model_entry:
            available_models = [entry["name"] for entry in cls.LLMS]
            raise ValueError(
                f"model '{model_name}' not found in registry. available models: {', '.join(available_models)}"
            )

        # If user provides kwargs, create a new instance with those args
        if kwargs:
            logger.debug("creating_llm_with_custom_args", model_name=model_name, custom_args=list(kwargs.keys()))
            if settings.LLM_PROVIDER == "gemini":
                return ChatOpenAI(
                    model=model_name,
                    api_key=settings.LLM_API_KEY,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    max_tokens=settings.MAX_TOKENS,
                    **kwargs,
                )
            return ChatOpenAI(model=model_name, api_key=settings.LLM_API_KEY, **kwargs)

        # Return the default instance
        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """Get all registered LLM names in order.

        Returns:
            List of LLM names
        """
        return [entry["name"] for entry in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        """Get model entry at specific index.

        Args:
            index: Index of the model in LLMS list

        Returns:
            Model entry dict
        """
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]  # Wrap around to first model


class LLMService:
    """Service for managing LLM calls with retries and circular fallback.

    This service handles all LLM interactions with automatic retry logic,
    rate limit handling, and circular fallback through all available models.
    """

    def __init__(self):
        """Initialize the LLM service."""
        self._llm: Optional[BaseChatModel] = None
        self._current_model_index: int = 0
        self._tools: Optional[List[BaseTool]] = None

        # Find index of default model in registry
        all_names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "llm_service_initialized",
                default_model=settings.DEFAULT_LLM_MODEL,
                model_index=self._current_model_index,
                total_models=len(all_names),
                environment=settings.ENVIRONMENT.value,
            )
        except (ValueError, Exception) as e:
            # Default model not found, use first model
            self._current_model_index = 0
            self._llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "default_model_not_found_using_first",
                requested=settings.DEFAULT_LLM_MODEL,
                using=all_names[0] if all_names else "none",
                error=str(e),
            )

    def _get_next_model_index(self) -> int:
        """Get the next model index in circular fashion.

        Returns:
            Next model index (wraps around to 0 if at end)
        """
        total_models = len(LLMRegistry.LLMS)
        next_index = (self._current_model_index + 1) % total_models
        return next_index

    def _switch_to_next_model(self) -> bool:
        """Switch to the next model in the registry (circular).

        Returns:
            True if successfully switched, False otherwise
        """
        try:
            next_index = self._get_next_model_index()
            next_model_entry = LLMRegistry.get_model_at_index(next_index)

            logger.warning(
                "switching_to_next_model",
                from_index=self._current_model_index,
                to_index=next_index,
                to_model=next_model_entry["name"],
            )

            self._current_model_index = next_index
            self._llm = next_model_entry["llm"]
            if self._tools:
                self._llm = self._llm.bind_tools(self._tools)

            logger.info("model_switched", new_model=next_model_entry["name"], new_index=next_index)
            return True
        except Exception as e:
            logger.error("model_switch_failed", error=str(e))
            return False

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError, InternalServerError, APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _call_llm_with_retry(self, messages: List[BaseMessage]) -> BaseMessage:
        """Call the LLM with automatic retry logic.

        Args:
            messages: List of messages to send to the LLM

        Returns:
            BaseMessage response from the LLM

        Raises:
            OpenAIError: If all retries fail
        """
        if not self._llm:
            raise RuntimeError("llm not initialized")

        try:
            response = await self._llm.ainvoke(messages)
            logger.debug("llm_call_successful", message_count=len(messages))
            return response
        except (RateLimitError, APITimeoutError, APIError) as e:
            logger.warning(
                "llm_call_failed_retrying",
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            raise
        except OpenAIError as e:
            logger.error(
                "llm_call_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def call(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
        **model_kwargs,
    ) -> BaseMessage:
        """Call the LLM with the specified messages and circular fallback.

        Args:
            messages: List of messages to send to the LLM
            model_name: Optional specific model to use. If None, uses current model.
            **model_kwargs: Optional kwargs to override default model configuration

        Returns:
            BaseMessage response from the LLM

        Raises:
            RuntimeError: If all models fail after retries
        """
        # If user specifies a model, get it from registry
        if model_name:
            try:
                self._llm = LLMRegistry.get(model_name, **model_kwargs)
                # Update index to match the requested model
                all_names = LLMRegistry.get_all_names()
                try:
                    self._current_model_index = all_names.index(model_name)
                except ValueError:
                    pass  # Keep current index if model name not in list
                logger.info("using_requested_model", model_name=model_name, has_custom_kwargs=bool(model_kwargs))
            except ValueError as e:
                logger.error("requested_model_not_found", model_name=model_name, error=str(e))
                raise

        # Track which models we've tried to prevent infinite loops
        total_models = len(LLMRegistry.LLMS)
        models_tried = 0
        starting_index = self._current_model_index
        last_error = None

        while models_tried < total_models:
            try:
                response = await self._call_llm_with_retry(messages)
                return response
            except Exception as e:
                last_error = e
                models_tried += 1

                current_model_name = LLMRegistry.LLMS[self._current_model_index]["name"]
                logger.error(
                    "llm_call_failed_after_retries",
                    model=current_model_name,
                    models_tried=models_tried,
                    total_models=total_models,
                    error=str(e),
                )

                # If we've tried all models, give up
                if models_tried >= total_models:
                    logger.error(
                        "all_models_failed",
                        models_tried=models_tried,
                        starting_model=LLMRegistry.LLMS[starting_index]["name"],
                    )
                    break

                # Switch to next model in circular fashion
                if not self._switch_to_next_model():
                    logger.error("failed_to_switch_to_next_model")
                    break

                # Continue loop to try next model

        # All models failed
        raise RuntimeError(
            f"failed to get response from llm after trying {models_tried} models. last error: {str(last_error)}"
        )

    def get_llm(self) -> Optional[BaseChatModel]:
        """Get the current LLM instance.

        Returns:
            Current BaseChatModel instance or None if not initialized
        """
        return self._llm

    def bind_tools(self, tools: List) -> "LLMService":
        """Bind tools to the current LLM.

        Args:
            tools: List of tools to bind

        Returns:
            Self for method chaining
        """
        if self._llm:
            self._llm = self._llm.bind_tools(tools)
            logger.debug("tools_bound_to_llm", tool_count=len(tools))
        return self


# Create global LLM service instance
llm_service = LLMService()
