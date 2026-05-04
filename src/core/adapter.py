from typing import Any, List, Optional, Dict, Iterator, Union
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, HumanMessageChunk, SystemMessageChunk, ToolMessageChunk, AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr
from openai import OpenAI
import re
import json
import ast

class LlamaServerAdapter(BaseChatModel):
    """
    The core LLM adapter for Agentic Core.
    Preserves reasoning_content and supports Tool Calling, Images, and Streaming.
    """
    api_key: str = "no-key"
    base_url: str = "http://localhost:8080/v1"
    model: str = "gemma-4"
    temperature: float = 0.7
    streaming: bool = False
    tools: List[Any] = []

    _client: OpenAI = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize client after Pydantic fields are populated
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)


    def _format_tools_for_prompt(self) -> str:
        """Formats the registered tools into a prompt-friendly string."""
        if not self.tools:
            return ""
        
        tool_descriptions = []
        for tool in self.tools:
            # Handle both function-based tools and class-based tools
            name = getattr(tool, "name", getattr(tool, "__name__", "unknown"))
            desc = getattr(tool, "description", "No description provided.")
            # If it's a function, we might need to extract the docstring
            if not hasattr(tool, "description") and hasattr(tool, "__doc__"):
                desc = tool.__doc__ or "No description provided."
            
            tool_descriptions.append(f"- {name}: {desc}")
        
        return "\n## AVAILABLE TOOLS:\n" + "\n".join(tool_descriptions) + \
               "\n\nTo call a tool, use:"

    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        if not content:
            return []
        
        sanitized_content = content.replace('<|"|>', '"')
        pattern = r"<\|tool_call>call:(\w+)\{(.*?)\}<tool_call\|>"
        matches = re.finditer(pattern, sanitized_content, re.DOTALL)
        tool_calls = []
        
        for match in matches:
            tool_name = match.group(1)
            args_str = match.group(2).strip()
            
            try:
                fixed_args_str = re.sub(r'(\w+)\s*:', r'"\1":', args_str)
                data = json.loads(f"{{{fixed_args_str}}}")
                args = data if isinstance(data, dict) else {"raw": args_str}
                is_valid = True
            except json.JSONDecodeError:
                try:
                    data = ast.literal_eval(f"{{{args_str}}}")
                    args = data if isinstance(data, dict) else {"raw": args_str}
                    is_valid = True
                except Exception as e:
                    args = f"{{{args_str}}}"
                    is_valid = False
                    error = str(e)

            tool_call = {
                "name": tool_name,
                "args": args,
                "id": f"call_{id(match)}",
            }
            
            if not is_valid:
                tool_call["type"] = "invalid_tool_call"
                tool_call["error"] = error
            else:
                tool_call["type"] = "tool_call"

            tool_calls.append(tool_call)
        return tool_calls

    def _generate(
        self, 
        messages: List[BaseMessage], 
        stop: Optional[List[str]] = None, 
        run_manager: Optional[Any] = None, 
        **kwargs
    ) -> ChatResult:
        openai_msgs = []
        tool_prompt = self._format_tools_for_prompt()
        for m in messages:
            if isinstance(m, HumanMessage):
                content = m.content if isinstance(m.content, list) else [{"type": "text", "text": m.content}]
                openai_msgs.append({"role": "user", "content": content})
            elif isinstance(m, SystemMessage):
                # Inject tool definitions into the system prompt
                if isinstance(m.content, list):
                    # Append tool prompt as a new text block if it's a list
                    content = m.content + ([{"type": "text", "text": tool_prompt}] if tool_prompt else [])
                else:
                    content = m.content + tool_prompt if tool_prompt else m.content
                openai_msgs.append({"role": "system", "content": content})
            elif isinstance(m, AIMessage):
                msg_dict = {"role": "assistant", "content": m.content}
                if m.tool_calls:
                    openai_tool_calls = []
                    for tc in m.tool_calls:
                        openai_tool_calls.append({
                            "id": tc.get("id"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name"),
                                "arguments": json.dumps(tc.get("args")) if isinstance(tc.get("args"), dict) else tc.get("args")
                            }
                        })
                    msg_dict["tool_calls"] = openai_tool_calls
                if "reasoning" in m.additional_kwargs:
                    msg_dict["reasoning_content"] = m.additional_kwargs["reasoning"]
                openai_msgs.append(msg_dict)
            elif isinstance(m, ToolMessage):
                openai_msgs.append({"role": "tool", "content": m.content, "tool_call_id": m.tool_call_id})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=openai_msgs,
            stop=stop,
            temperature=self.temperature,
            **kwargs
        )

        choice = response.choices[0].message
        content = choice.content or ""
        
        reasoning = getattr(choice, 'reasoning_content', None)
        if not reasoning and hasattr(choice, 'model_extra'):
            reasoning = choice.model_extra.get('reasoning_content')

        parsed_calls = self._parse_tool_calls(content)
        tool_calls = [tc for tc in parsed_calls if tc["type"] == "tool_call"]
        invalid_tool_calls = [tc for tc in parsed_calls if tc["type"] == "invalid_tool_call"]
        clean_content = re.sub(r"<\|tool_call>.*?<tool_call\|>", "", content, flags=re.DOTALL).strip()

        ai_msg = AIMessage(
            content=clean_content,
            additional_kwargs={"reasoning": reasoning},
            tool_calls=[{k: v for k, v in tc.items() if k != "type"} for tc in tool_calls],
            invalid_tool_calls=invalid_tool_calls
        )
        
        if choice.tool_calls:
            ai_msg.tool_calls.extend([tc.model_dump() for tc in choice.tool_calls])

        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    def _stream(
        self, 
        messages: List[BaseMessage], 
        stop: Optional[List[str]] = None, 
        run_manager: Optional[Any] = None, 
        **kwargs
    ) -> Iterator[ChatGenerationChunk]:
        openai_msgs = []
        tool_prompt = self._format_tools_for_prompt()
        for m in messages:
            if isinstance(m, HumanMessage):
                content = m.content if isinstance(m.content, list) else [{"type": "text", "text": m.content}]
                openai_msgs.append({"role": "user", "content": content})
            elif isinstance(m, SystemMessage):
                # Inject tool definitions into the system prompt
                if isinstance(m.content, list):
                    # Append tool prompt as a new text block if it's a list
                    content = m.content + ([{"type": "text", "text": tool_prompt}] if tool_prompt else [])
                else:
                    content = m.content + tool_prompt if tool_prompt else m.content
                openai_msgs.append({"role": "system", "content": content})
            elif isinstance(m, AIMessage):
                msg_dict = {"role": "assistant", "content": m.content}
                if m.tool_calls:
                    openai_tool_calls = []
                    for tc in m.tool_calls:
                        openai_tool_calls.append({
                            "id": tc.get("id"),
                            "type": "function",
                            "function": {
                                "name": tc.get("name"),
                                "arguments": json.dumps(tc.get("args")) if isinstance(tc.get("args"), dict) else tc.get("args")
                            }
                        })
                    msg_dict["tool_calls"] = openai_tool_calls
                if "reasoning" in m.additional_kwargs:
                    msg_dict["reasoning_content"] = m.additional_kwargs["reasoning"]
                openai_msgs.append(msg_dict)
            elif isinstance(m, ToolMessage):
                openai_msgs.append({"role": "tool", "content": m.content, "tool_call_id": m.tool_call_id})

        stream = self._client.chat.completions.create(
            model=self.model,
            messages=openai_msgs,
            stop=stop,
            stream=True,
            temperature=self.temperature,
            **kwargs
        )

        buffer = ""
        in_tool_call = False
        current_tool_name = None

        for chunk in stream:
            delta = chunk.choices[0].delta
            
            # 1. Reasoning streaming
            reasoning = getattr(delta, 'reasoning_content', None)
            if reasoning:
                yield ChatGenerationChunk(message=AIMessageChunk(content="", additional_kwargs={"reasoning": reasoning}))

            # 2. Content / Tool Call streaming logic
            content_delta = delta.content or ""
            if content_delta:
                buffer += content_delta
                events = []
                
                if '<|tool_call>' in buffer and not in_tool_call:
                    in_tool_call = True
                    events.append({"type": "status", "value": "incomplete"})
                    # Extract tool name if present in the buffer immediately
                    match = re.search(r"<\|tool_call>call:(\w+){", buffer)
                    if match:
                        current_tool_name = match.group(1)
                        events.append({"type": "name", "value": current_tool_name})

                elif in_tool_call and not current_tool_name:
                    match = re.search(r"<\|tool_call>call:(\w+){", buffer)
                    if match:
                        current_tool_name = match.group(1)
                        events.append({"type": "name", "value": current_tool_name})

                if in_tool_call:
                    if '<tool_call|>' in buffer:
                        # Split the buffer into the actual tool content and whatever follows
                        raw_call, post_call = buffer.split('<tool_call|>', 1)
                        in_tool_call = False
                        
                        try:
                            # Clean the raw_call to get just the JSON object { ... }
                            # We find the first { and last } to avoid issues with the 'call:name' prefix
                            start_idx = raw_call.find('{')
                            end_idx = raw_call.rfind('}')
                            if start_idx == -1 or end_idx == -1:
                                raise ValueError("No JSON object found in tool call")
                            
                            json_str = raw_call[start_idx : end_idx + 1]
                            sanitized_json_str = json_str.replace('<|"|>', '"')
                            # Handle unquoted keys
                            fixed_json_str = re.sub(r'(?<=[{\,])\s*(\w+)\s*:', r'"\1":', sanitized_json_str)
                            try:
                                args = json.loads(fixed_json_str)
                            except json.JSONDecodeError:
                                args = ast.literal_eval(fixed_json_str)
                            
                            yield ChatGenerationChunk(
                                message=AIMessageChunk(
                                    content="",
                                    tool_call_chunks=[{
                                        "index": 0,
                                        "id": f"call_{id(raw_call)}",
                                        "name": current_tool_name,
                                        "args": json.dumps(args),
                                        "type": "tool_call"
                                    }]
                                )
                            )
                        except Exception as e:
                            yield ChatGenerationChunk(
                                message=AIMessageChunk(
                                    content="",
                                    invalid_tool_calls=[{
                                        "id": f"call_{id(raw_call)}",
                                        "name": current_tool_name,
                                        "args": raw_call,
                                        "error": str(e),
                                        "type": "invalid_tool_call"
                                    }]
                                )
                            )
                        buffer = post_call
                    else:
                        # here we are in a toolcall but have not found the end of it yet.
                        events.append({"type": "token", "value": content_delta})
                        # ASSEMBLING: Use additional_kwargs so it doesn't pollute the 
                        # official LangChain 'invalid_tool_calls' history.
                        yield ChatGenerationChunk(
                            message=AIMessageChunk(
                                content="",
                                additional_kwargs={
                                    "assembling_tool": events
                                }
                            )
                        )
                else:
                    # Normal text streaming
                    yield ChatGenerationChunk(message=AIMessageChunk(content=content_delta))
                    buffer = ""
                    current_tool_name = ""

            # 3. Native API tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="", 
                            tool_call_chunks=[{
                                "index": tc.index,
                                "id": tc.id,
                                "name": tc.function.name if tc.function else None,
                                "args": tc.function.arguments if tc.function else None,
                                "type": "invalid_tool_call" 
                            }]
                        )
                    )

    def bind_tools(self, tools: List[Any], **kwargs: Any) -> Runnable:
        return self.copy(update={"tools": tools, **kwargs})

    @property
    def _llm_type(self) -> str:
        return "llama_server_adapter"