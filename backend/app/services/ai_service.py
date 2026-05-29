"""
AI Teacher & AI Assistant — HSK1-2 教学引擎

Architecture:
- AI Teacher: structured HSK1-2 prompt with strict vocabulary control + teaching flow
- AI Assistant: RAG-augmented FAQ answering within HSK level constraints
- Future: TTS integration, voice recognition, SSE streaming
"""

import json
from typing import Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.user import Message, MessageRole


# =============================================================================
# HSK1-2 词汇白名单 — 用于输出约束
# =============================================================================

HSK1_VOCAB = {
    "pronouns": ["我", "你", "他", "她", "它", "我们", "你们", "他们", "她们"],
    "greetings": ["你好", "再见", "谢谢", "不客气", "对不起", "没关系", "请"],
    "numbers": ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                "百", "千", "个", "岁", "块", "元", "点", "分"],
    "family": ["爸爸", "妈妈", "哥哥", "姐姐", "弟弟", "妹妹", "儿子", "女儿", "家"],
    "daily": ["吃", "喝", "去", "来", "看", "听", "说", "读", "写", "买", "卖",
              "做", "学", "叫", "住", "有", "是", "在", "会", "能"],
    "time": ["今天", "明天", "昨天", "早上", "中午", "晚上", "现在", "年", "月",
             "星期", "号", "日"],
    "places": ["学校", "医院", "商店", "公司", "家", "图书馆", "公园"],
    "food": ["苹果", "米饭", "面包", "牛奶", "水", "茶", "咖啡", "鸡蛋", "肉", "菜"],
    "colors": ["红", "白", "黑", "蓝", "绿", "黄", "大", "小"],
    "questions": ["什么", "谁", "哪里", "什么时候", "为什么", "怎么", "多少", "几"],
    "grammar": ["的", "了", "吗", "呢", "吧", "不", "很", "也", "都", "和",
                "在", "有", "是", "要", "想", "会", "能", "可以", "应该"],
    "measure_words": ["个", "本", "杯", "张", "只", "条", "块", "件"],
    "adjectives": ["好", "坏", "多", "少", "大", "小", "高", "矮", "长", "短",
                   "快", "慢", "热", "冷", "高兴", "漂亮", "好吃"],
}

HSK2_EXTRA = {
    "verbs": ["告诉", "帮助", "欢迎", "打算", "觉得", "希望", "开始", "结束",
              "准备", "参加", "比赛", "表现", "表示", "检查", "需要"],
    "time": ["已经", "正在", "经常", "有时候", "从来不", "刚", "就", "才",
             "以前", "以后", "一边"],
    "places": ["办公室", "教室", "宿舍", "银行", "邮局", "机场", "火车站",
               "地铁", "公共汽车"],
    "grammar": ["把", "被", "比", "从", "对", "跟", "让", "给", "为", "因为",
                "所以", "但是", "虽然", "如果", "而且", "或者", "一边...一边..."],
    "daily2": ["运动", "跑步", "游泳", "唱歌", "跳舞", "旅行", "照相", "上网",
               "看电视", "打电话", "洗衣服", "做饭"],
    "adjectives2": ["聪明", "努力", "认真", "着急", "累", "忙", "舒服", "难过",
                    "开心", "特别", "非常", "太", "真"],
}

# 助教常见问题知识库（可扩展为 RAG 向量检索）
FAQ_KNOWLEDGE_BASE = [
    # HSK 考试类
    {"q": "HSK是什么", "a": "HSK是汉语水平考试，测试中文能力。HSK1级需要会150个词，HSK2级需要会300个词。"},
    {"q": "HSK1级要学多久", "a": "HSK1级大约需要30-40小时的学习。每天学习1小时，一个月可以学完。"},
    {"q": "HSK2级比HSK1级难多少", "a": "HSK2级比HSK1级多150个词。HSK1是基础，HSK2开始有更复杂的句子。"},
    {"q": "HSK有口语考试吗", "a": "HSK有口语考试（HSKK），分为初级、中级和高级。HSK1-2对应HSKK初级。"},

    # 学习方法类
    {"q": "怎么记住汉字", "a": "建议每天写5-10个新汉字。用笔画顺序写，看部首的意思。"},
    {"q": "中文声调很难", "a": "声调需要多听多练。建议：1)听录音跟读 2)用手势帮助记声调 3)每天练习10分钟。"},
    {"q": "怎么练习听力", "a": "1)听简单的对话 2)先看字幕再不看 3)每天听15分钟。我们的AI老师可以帮你练习。"},
    {"q": "拼音和汉字先学什么", "a": "建议先学拼音（1-2周），再学汉字。拼音帮助发音，汉字帮助读写。"},

    # 语法类
    {"q": "什么是量词", "a": "量词是中文里用在数字后面的词。例如：一个人、两本书、三杯水。"},
    {"q": "了是什么意思", "a": "\"了\"可以表示事情已经完成。例如：我吃了（已经吃完）。也可以表示变化：我饿了（以前不饿）。"},
    {"q": "把字句怎么用", "a": "\"把\"把宾语放在动词前面。例如：我把书放在桌子上（书→桌子上）。HSK2级学习这个语法。"},
    {"q": "在、正在、着有什么区别", "a": "都表示在做事情。\"在\"和\"正在\"一样：我在吃饭=我正在吃饭。\"着\"强调状态：门开着。"},
    {"q": "会和能有什么区别", "a": "\"会\"表示学会了：我会游泳。\"能\"表示可能或有能力：我今天能去。"},

    # 文化类
    {"q": "中国人怎么打招呼", "a": "最常用：你好！早上好！下午好！吃饭了吗？（是问候，不是真问吃饭）"},
    {"q": "中国有什么节日", "a": "最重要的节日：春节（新年，1-2月）、中秋节（9-10月，吃月饼）、端午节（5-6月，吃粽子）。"},
    {"q": "中国菜有什么特点", "a": "中国菜有很多种：辣（四川）、甜（上海）、清淡（广东）。八大菜系各有特色。"},
    {"q": "在中国怎么付钱", "a": "中国人常用手机付钱：微信支付和支付宝。现金也可以用。"},
]

# =============================================================================
# PROMPTS
# =============================================================================

TEACHER_SYSTEM_PROMPT_TEMPLATE = """你是一位专业的HSK{level}级中文教师。你的名字是"齐老师"。

## 核心教学原则
1. 只使用HSK{level}级词汇表中的词语。如果学生用了超纲词，委婉提醒并简化
2. 每次回复控制在3-5句中文 + 1-2句英文翻译（对HSK1级初学者，每句都要翻译）
3. 每次只教1个核心句型 + 不超过5个生词
4. 每完成一个小节，必须向学生提1个简单问题，确认他们理解了
5. 纠正错误时要先肯定再纠正，用"很好，但是应该说..."

## 教学流程（必须按顺序）
每节课按以下5步进行：
1. 【引出句型】展示当天的核心句型，用学生能理解的例子
2. 【生词展示】教3-5个与句型相关的生词，每个词给出汉字+拼音+英文
3. 【对话示例】用句型编一个简单对话（2-3轮）
4. 【提问练习】基于对话内容提问，让学生回答
5. 【检查纠错】对学生的回答给出反馈，纠正语法/用词错误

## 输出格式
- HSK1: 每句中文后面加括号写英文翻译。例："你好，我叫齐老师。(Hello, I'm Teacher Qi.)"
- HSK2: 重要句子加英文注释。生词给出拼音。

## 角色性格
耐心、鼓励、幽默。学生说错时不要批评，而是说"很好！有一点小建议..."。
"""

ASSISTANT_SYSTEM_PROMPT = """你是一位HSK1-2级中文学习助教，名叫"小齐"。

## 职责
1. 回答中文学习相关的问题（语法、词汇、文化、考试）
2. 只使用HSK1-2级学生能理解的简单中文和英文
3. 如果问题超纲，礼貌地说："这个问题很棒！等你学到更高等级就能明白了。"

## 回答规则
1. 先给出简短答案（2-3句中文 + 英文翻译）
2. 如果学生要求，再给出详细解释
3. 不要主动教学新内容，只回答问题
4. 鼓励学生用中文提问

## 知识来源
你的知识来自HSK1-2级标准教学内容。如果某个问题不在课程范围内，如实告知。
"""


class AIService:
    """AI 教学服务 — 教师模式与助教模式"""

    def __init__(self):
        self.client = None
        self.model = settings.zhipuai_model
        self._faq_index = self._build_faq_index()

    def _get_client(self) -> AsyncOpenAI:
        """延迟初始化 OpenAI 客户端，避免无 API key 时构造失败"""
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=settings.zhipuai_api_key,
                base_url=settings.zhipuai_api_base,
            )
        return self.client

    def _build_faq_index(self) -> dict[str, str]:
        """构建 FAQ 索引（后续可升级为 pgvector 向量检索）"""
        return {entry["q"]: entry["a"] for entry in FAQ_KNOWLEDGE_BASE}

    def _lookup_faq(self, query: str) -> Optional[str]:
        """简单 FAQ 检索 — 子串匹配 + 字符重叠降级（占位实现）"""
        for question, answer in self._faq_index.items():
            if question in query or query in question:
                return answer
        # 中文模糊降级：字符重叠超过 50% 即匹配
        for question, answer in self._faq_index.items():
            overlap = sum(1 for c in question if c in query)
            if overlap >= len(question) * 0.5:
                return answer
        return None

    def _build_messages(
        self,
        history: list[Message],
        hsk_level: float,
        mode: str = "teacher",
    ) -> list[dict]:
        """构建消息列表"""
        if mode == "teacher":
            system_prompt = TEACHER_SYSTEM_PROMPT_TEMPLATE.format(level=int(hsk_level))
        else:
            system_prompt = ASSISTANT_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role.value, "content": msg.content})
        return messages

    async def chat(
        self,
        history: list[Message],
        hsk_level: float = 1.0,
        mode: str = "teacher",
    ) -> str:
        """
        与 AI 教师/助教对话。

        Args:
            history: 消息历史
            hsk_level: HSK 等级 (1-6)
            mode: "teacher" 或 "assistant"

        Returns:
            AI 回复文本
        """
        # 助教模式：优先查 FAQ
        if mode == "assistant" and history:
            last_msg = history[-1].content if history else ""
            faq_answer = self._lookup_faq(last_msg)
            if faq_answer:
                return faq_answer

        messages = self._build_messages(history, hsk_level, mode)
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7 if mode == "teacher" else 0.5,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(
        self,
        history: list[Message],
        hsk_level: float = 1.0,
        mode: str = "teacher",
    ):
        """
        流式对话（SSE），用于打字机效果。

        Yields:
            文本片段，逐块返回给前端 SSE。
        """
        messages = self._build_messages(history, hsk_level, mode)
        client = self._get_client()
        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7 if mode == "teacher" else 0.5,
            max_tokens=1024,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
