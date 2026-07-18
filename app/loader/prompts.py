"""
قالب پرامپت تحلیل ساختار سند و توابع کمکی برای تبدیل بلاک‌ها/hint/context
به متنی که داخل پرامپت قرار می‌گیرد.
"""

from langchain_core.prompts import ChatPromptTemplate


STRUCTURE_PROMPT = """
شما مسئول تحلیل ساختار یک سند هستید.

سند به‌صورت بخش‌بخش (batch) در اختیار شما قرار می‌گیرد.
این بخش فعلی، ادامه‌ی بخش(های) قبلی همان سند است، نه یک سند مستقل.

خلاصه‌ی وضعیت تا پیش از این batch (برای فهم اینکه الان زیر کدام parent/child
هستیم استفاده کن):
{hint}

بلاک‌های زمینه‌ای (Context Blocks):
این بلاک‌ها قبلاً توسط شما در دور(های) قبل لیبل‌گذاری شده‌اند و لیبلشان قطعی
و نهایی است. آنها را فقط برای فهم ساختار و پیوستگی متن بخوان.
مطلقاً برای این بلاک‌ها در خروجی چیزی تولید نکن و لیبلشان را تغییر نده.

{context_blocks}

بلاک‌های جدید (New Blocks):
فقط و فقط برای این بلاک‌ها باید دقیقاً یکی از سه برچسب زیر را تعیین کنی.
برای تمام index های این بخش، و فقط همین index ها، خروجی بده.

{new_blocks}

تعریف برچسب‌ها:

parent:
- عنوان اصلی
- شروع یک بخش یا فصل
- معمولاً کوتاه‌تر از متن عادی است.
- ممکن است شماره‌گذاری داشته باشد.
- مراحل parent نیستند

child:
- زیرعنوان یک parent
- معمولاً عنوان یک زیربخش است.
الگو ها :
1.1 1.2 1.3 ...
الف) ب) و ..
نکته بسیار مهم : تا یک سطح CHILD شناسایی کن و داخل یک CHILD دیگر CHILD نخواهیم داشت

body:
- متن معمولی
- توضیح
- ادامه یک پاراگراف

نکات:
-به سایز فونت هیچ توجه ای نکن و براساس محتوا تصمیم گیری بکن
- خروجی فقط باید مطابق Schema باشد و دقیقاً به تعداد و index بلاک‌های جدید باشد.
"""

prompt = ChatPromptTemplate.from_template(STRUCTURE_PROMPT)


def build_blocks_prompt(blocks: list[dict]) -> str:
    """بلاک‌های 'جدید' را به متنی قابل استفاده در پرامپت تبدیل می‌کند."""
    lines = []

    for block in blocks:
        lines.append(
            f"[{block['index']}] "
            f"font_size={block['font_size']} "
            f"text={block['text']}"
        )

    return "\n".join(lines)


def build_context_prompt(context_blocks: list[dict], final_labels: dict[int, str]) -> str:
    """بلاک‌های 'زمینه‌ای' را همراه با لیبل قطعی‌شان به متن پرامپت تبدیل می‌کند."""
    if not context_blocks:
        return "(بدون بلاک زمینه‌ای - این اولین بخش سند است)"

    lines = []
    for block in context_blocks:
        label = final_labels.get(block["index"], "body")
        lines.append(
            f"[{block['index']}] "
            f"font_size={block['font_size']} "
            f"label={label} "
            f"text={block['text']}"
        )
    return "\n".join(lines)


def build_hint(blocks_by_index: dict[int, dict], labels: dict[int, str]) -> str:
    """
    آخرین parent/child قطعی‌شده تا این لحظه را (حتی اگر خارج از پنجره‌ی
    overlap فعلی باشد) به‌عنوان خلاصه‌ی وضعیت برمی‌گرداند.
    """
    last_parent_text = None
    last_child_text = None

    for idx in sorted(labels.keys()):
        level = labels[idx]
        text = blocks_by_index[idx]["text"]

        if level == "parent":
            last_parent_text = text
            last_child_text = None
        elif level == "child":
            last_child_text = text

    if last_parent_text is None and last_child_text is None:
        return "این اولین بخش سند است؛ تا اینجا هیچ parent یا child‌ای شناسایی نشده."

    lines = []
    if last_parent_text:
        lines.append(f"- آخرین Parent قطعی‌شده: {last_parent_text}")
    if last_child_text:
        lines.append(f"- آخرین Child قطعی‌شده (زیرِ همان Parent): {last_child_text}")

    return "\n".join(lines)