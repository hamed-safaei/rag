from dataclasses import dataclass, field


@dataclass
class ChildChunk:
    """یک زیرعنوان با محتوای آن"""
    id: str           # مثال: "2.1"
    title: str        # عنوان زیربخش
    content: str      # متن کامل زیربخش
    parent_id: str    # شناسه عنوان والد


@dataclass
class ParentChunk:
    """یک عنوان اصلی با تمام زیرعنوان‌هایش"""
    id: str           # مثال: "2"
    title: str        # عنوان اصلی
    content: str      # متن کل عنوان (شامل همه زیرعنوان‌ها)
    children: list[ChildChunk] = field(default_factory=list)
    