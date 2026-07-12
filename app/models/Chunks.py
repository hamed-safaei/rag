from dataclasses import dataclass, field


@dataclass
class ChildChunk:
    """یک زیرعنوان با محتوای آن"""
    id: str          
    title: str      
    content: str      
    parent_id: str    


@dataclass
class ParentChunk:
    """یک عنوان اصلی با تمام زیرعنوان‌هایش"""
    id: str          
    title: str       
    content: str    
    children: list[ChildChunk] = field(default_factory=list)
    