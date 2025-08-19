from typing import Dict, Any, Optional, List
from string import Template
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

class PromptTemplate:
    """프롬프트 템플릿 클래스"""
    
    def __init__(self, template: str, variables: List[str] = None):
        self.template = template
        self.variables = variables or []
        self._template_obj = Template(template)
    
    def format(self, **kwargs) -> str:
        """변수를 치환하여 프롬프트 생성"""
        missing_vars = set(self.variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"필수 변수가 누락되었습니다: {missing_vars}")
        
        return self._template_obj.safe_substitute(**kwargs)
    
    def validate(self, **kwargs) -> bool:
        """변수 유효성 검증"""
        return all(var in kwargs for var in self.variables)


class PromptManager:
    """프롬프트 관리자"""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self.chat_templates: Dict[str, ChatPromptTemplate] = {}
    
    def register_template(self, name: str, template: str, variables: List[str] = None):
        """일반 프롬프트 템플릿 등록"""
        self.templates[name] = PromptTemplate(template, variables)
    
    def register_chat_template(self, name: str, system: str, human: str = None):
        messages = [("system", system)]
        if human:
            messages.append(("human", human))
        
        self.chat_templates[name] = ChatPromptTemplate.from_messages(messages)
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """템플릿 가져오기"""
        return self.templates.get(name)
    
    def get_chat_template(self, name: str) -> Optional[ChatPromptTemplate]:
        """ChatPromptTemplate 가져오기"""
        return self.chat_templates.get(name)
    
    def format(self, name: str, **kwargs) -> str:
        """템플릿 포맷팅"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"템플릿을 찾을 수 없습니다: {name}")
        
        return template.format(**kwargs)
    
    @staticmethod
    def create_system_prompt(content: str) -> SystemMessage:
        """시스템 메시지 생성"""
        return SystemMessage(content=content)
    
    @staticmethod
    def create_human_prompt(content: str) -> HumanMessage:
        """사용자 메시지 생성"""
        return HumanMessage(content=content)