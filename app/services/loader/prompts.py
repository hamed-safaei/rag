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
-عنوان ها معمولا الگو های مشابه را دنبال میکنند
نمونه رایج الگو ها :
1._______
2._______
یا 
الف )
ب )
و ...
به این الگو ها برای شناسایی توجه کن


child:
- زیرعنوان یک parent
- معمولاً عنوان یک زیربخش است.
منطق تشخیص Child
پس از اینکه یک عنوان به‌عنوان child شناسایی شد، الگوی شماره‌گذاری یا نشانه‌گذاری آن به‌عنوان مرجع همان سطح در نظر گرفته می‌شود و انتظار می‌رود childهای بعدی از همان الگو به‌صورت ترتیبی پیروی کنند.

مثال‌ها:

اگر الف) به‌عنوان child شناسایی شد، انتظار می‌رود ب)، سپس پ) و ... نیز childهای هم‌سطح باشند.
اگر 1.1 به‌عنوان child شناسایی شد، انتظار می‌رود 1.2، 1.3 و ... childهای هم‌سطح باشند.

نکته مهم: ممکن است داخل یک child، زیربخش‌هایی با الگوهای دیگری (مانند الف), ب) یا 1.1.1, 1.1.2) وجود داشته باشد. این موارد یک سطح پایین‌تر از child هستند و نباید به‌عنوان child برچسب‌گذاری شوند. فقط عناوین هم‌سطح با اولین child شناسایی‌شده باید برچسب child دریافت کنند.

body:
- متن معمولی
- توضیح
- ادامه یک پاراگراف

نکات:
- خروجی فقط باید مطابق Schema باشد و دقیقاً به تعداد و index بلاک‌های جدید باشد.
"""

prompt = ChatPromptTemplate.from_template(STRUCTURE_PROMPT)


def build_blocks_prompt(blocks: list[dict]) -> str:
    lines = []

    for block in blocks:
        lines.append(
            f"[{block['index']}] "
            f"text={block['text']}"
        )

    return "\n".join(lines)


def build_context_prompt(context_blocks: list[dict], final_labels: dict[int, str]) -> str:
    if not context_blocks:
        return "(بدون بلاک زمینه‌ای - این اولین بخش سند است)"

    lines = []
    for block in context_blocks:
        label = final_labels.get(block["index"], "body")
        lines.append(
            f"[{block['index']}] "
            f"label={label} "
            f"text={block['text']}"
        )
    return "\n".join(lines)


def build_hint(blocks_by_index: dict[int, dict], labels: dict[int, str]) -> str:
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