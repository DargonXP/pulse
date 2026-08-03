"""AI layer for UpWise.

Wraps Anthropic's API for two demonstrable, judge-facing features:
  1. recommend_tools_for_business  -> onboarding tool/action recommendations
  2. generate_campaign_copy        -> campaign title/text generation

Both fall back to deterministic, rule-based logic when ANTHROPIC_API_KEY is
not configured or the API call fails, so the demo never breaks live on stage.
"""

import json
import logging

from app.config import get_settings

logger = logging.getLogger("upwise.ai")
settings = get_settings()

_client = None
_client_initialized = False


def _get_client():
    global _client, _client_initialized
    if _client_initialized:
        return _client
    _client_initialized = True
    if not settings.anthropic_api_key:
        _client = None
        return None
    try:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except Exception:  # pragma: no cover - defensive, e.g. missing package
        logger.exception("Failed to initialize Anthropic client")
        _client = None
    return _client


def _call_claude_json(system_prompt: str, user_prompt: str) -> dict | None:
    client = _get_client()
    if client is None:
        return None
    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(raw_text[start : end + 1])
    except Exception:
        logger.exception("Anthropic call failed, falling back to rules")
        return None


# ---------------------------------------------------------------------------
# Rule-based knowledge base (mirrors the case's worked examples)
# ---------------------------------------------------------------------------

BUSINESS_TYPE_LABELS = {
    "coffee_shop": "кофейня",
    "clothing_store": "магазин одежды",
    "beauty_salon": "салон красоты",
    "service_point": "сервисная точка",
    "other": "малый бизнес",
}

GOAL_LABELS = {
    "new_customers": "привлечение новых клиентов",
    "retention": "удержание и повторные визиты",
    "revenue": "рост среднего чека и выручки",
}

FALLBACK_TOOL_RULES: dict[str, list[dict]] = {
    "coffee_shop": [
        {"tool_type": "marketing", "title": "Акция «2+1» на напитки", "priority": "high",
         "reason": "Для кофеен комбо-акции лучше всего повышают частоту визитов в течение дня."},
        {"tool_type": "retention", "title": "Программа лояльности с баллами", "priority": "high",
         "reason": "Постоянные гости кофеен чувствительны к накопительным бонусам за визит."},
        {"tool_type": "automation", "title": "Уведомления о скидках", "priority": "medium",
         "reason": "Автоматические напоминания возвращают клиентов в часы затишья."},
    ],
    "clothing_store": [
        {"tool_type": "marketing", "title": "Сезонная скидка на коллекцию", "priority": "high",
         "reason": "Магазинам одежды нужна регулярная ротация акций под сезон и остатки."},
        {"tool_type": "retention", "title": "VIP-доступ для постоянных клиентов", "priority": "medium",
         "reason": "Ранний доступ к новым поступлениям удерживает лояльных покупателей."},
        {"tool_type": "analytics", "title": "Аналитика повторных покупок", "priority": "medium",
         "reason": "Помогает понять, какие категории товаров приводят клиентов обратно."},
    ],
    "beauty_salon": [
        {"tool_type": "retention", "title": "Скидка на повторное посещение", "priority": "high",
         "reason": "Для салонов ключевая метрика — интервал между визитами; скидка сокращает его."},
        {"tool_type": "sales", "title": "CRM для истории клиентов", "priority": "high",
         "reason": "Мастеру важно помнить историю услуг и предпочтения клиента."},
        {"tool_type": "automation", "title": "Напоминание о записи", "priority": "medium",
         "reason": "Снижает количество пропущенных визитов и простоев в расписании."},
    ],
    "service_point": [
        {"tool_type": "retention", "title": "Бонусная карта постоянного клиента", "priority": "high",
         "reason": "Сервисные точки выигрывают от простых накопительных программ."},
        {"tool_type": "marketing", "title": "Реферальная акция «Приведи друга»", "priority": "medium",
         "reason": "Сарафанное радио остаётся главным каналом привлечения для локального сервиса."},
        {"tool_type": "analytics", "title": "Простая аналитика продаж", "priority": "medium",
         "reason": "Базовые метрики помогают увидеть, какие услуги приносят больше выручки."},
    ],
    "other": [
        {"tool_type": "marketing", "title": "Стартовая акция для новых клиентов", "priority": "high",
         "reason": "Универсальный инструмент привлечения для любого типа малого бизнеса."},
        {"tool_type": "retention", "title": "Программа лояльности", "priority": "medium",
         "reason": "Простой способ повысить повторные покупки без сложных настроек."},
        {"tool_type": "analytics", "title": "Базовая аналитика клиентов", "priority": "low",
         "reason": "Помогает принимать решения на основе данных, а не интуиции."},
    ],
}

FALLBACK_CAMPAIGN_TEMPLATES: dict[str, dict[str, dict]] = {
    "coffee_shop": {
        "combo": {"title": "Акция «2+1» на напитки", "text": "Купи 2 напитка — третий получи в подарок! Только сегодня и завтра. Расскажи друзьям ☕"},
        "discount": {"title": "Скидка {discount}% для постоянных гостей", "text": "Специально для вас — скидка {discount}% на любой напиток при следующем визите в течение недели."},
        "bonus": {"title": "Бонус за визит", "text": "Каждый 5-й напиток — бесплатно! Копите баллы лояльности при каждом заказе."},
        "coupon": {"title": "Купон на {discount}% на выпечку", "text": "Покажите этот купон и получите скидку {discount}% на любую выпечку к кофе."},
    },
    "clothing_store": {
        "discount": {"title": "Скидка {discount}% на новую коллекцию", "text": "Только 3 дня: скидка {discount}% на новое поступление. Успейте обновить гардероб!"},
        "bonus": {"title": "Бонусные баллы за покупку", "text": "Получайте баллы за каждую покупку и обменивайте их на скидки в следующий визит."},
        "coupon": {"title": "Купон на {discount}% на второй товар", "text": "При покупке одной вещи — скидка {discount}% на вторую. Купон действует 7 дней."},
        "combo": {"title": "Комплект со скидкой", "text": "Собери образ и получи скидку {discount}% при покупке от 2 вещей."},
    },
    "beauty_salon": {
        "discount": {"title": "Скидка {discount}% на повторный визит", "text": "Запишитесь повторно в течение 30 дней и получите скидку {discount}% на любую услугу."},
        "bonus": {"title": "Бонус за рекомендацию", "text": "Приведите подругу — обе получите бонус на следующую процедуру."},
        "coupon": {"title": "Купон новому клиенту", "text": "Ваш первый визит со скидкой {discount}%! Покажите этот купон администратору."},
        "combo": {"title": "Комплекс услуг со скидкой", "text": "При заказе комплекса из 2 услуг — скидка {discount}% на вторую."},
    },
    "service_point": {
        "discount": {"title": "Скидка {discount}% постоянным клиентам", "text": "Специальное предложение для наших постоянных клиентов — скидка {discount}% в этом месяце."},
        "bonus": {"title": "Бонусная карта", "text": "Каждое 6-е обращение — бесплатно. Копите визиты в бонусной карте."},
        "coupon": {"title": "Купон на {discount}% скидку", "text": "Предъявите купон и получите скидку {discount}% на услугу."},
        "combo": {"title": "Комбо-предложение", "text": "Закажите две услуги вместе и получите скидку {discount}% на комплект."},
    },
    "other": {
        "discount": {"title": "Скидка {discount}% для клиентов", "text": "Успейте воспользоваться скидкой {discount}% в ограниченный период."},
        "bonus": {"title": "Бонус за покупку", "text": "Получайте бонусы за каждую покупку и обменивайте на скидки."},
        "coupon": {"title": "Купон на скидку {discount}%", "text": "Предъявите купон на кассе и получите скидку {discount}%."},
        "combo": {"title": "Специальное комбо-предложение", "text": "Ограниченное предложение с выгодой до {discount}%."},
    },
}


def recommend_tools_for_business(business_type: str, size: str, goal: str, available_tools: list[dict]) -> list[dict]:
    """Return a list of {tool_name, tool_type, title, description, reason, priority, source}.

    `available_tools` is a list of {"id", "name", "tool_type", "description"} from the DB,
    used so recommendations can be matched back to real Tool rows.
    """
    label = BUSINESS_TYPE_LABELS.get(business_type, business_type)
    goal_label = GOAL_LABELS.get(goal, goal)

    tools_json = json.dumps(available_tools, ensure_ascii=False)
    system_prompt = (
        "Ты — AI-модуль платформы UpWise, помогающей малому офлайн-бизнесу в Казахстане "
        "(кофейни, магазины, салоны) расти без маркетинговой команды. "
        "Отвечай СТРОГО в формате JSON без markdown-обёртки: "
        '{"recommendations": [{"tool_id": <int or null>, "title": "...", "description": "...", '
        '"reason": "...", "priority": "high|medium|low"}]}. Верни от 2 до 4 рекомендаций.'
    )
    user_prompt = (
        f"Тип бизнеса: {label}. Размер: {size}. Цель: {goal_label}.\n"
        f"Доступные инструменты платформы (выбирай tool_id из этого списка, если подходит): {tools_json}\n"
        "Порекомендуй наиболее подходящие инструменты и коротко объясни, почему именно эти."
    )
    result = _call_claude_json(system_prompt, user_prompt)
    if result and isinstance(result.get("recommendations"), list) and result["recommendations"]:
        recs = []
        for item in result["recommendations"][:4]:
            recs.append({
                "tool_id": item.get("tool_id"),
                "title": str(item.get("title", ""))[:255],
                "description": str(item.get("description", "")),
                "reason": str(item.get("reason", "")),
                "priority": item.get("priority") if item.get("priority") in ("high", "medium", "low") else "medium",
                "source": "ai",
            })
        return recs

    # Fallback: deterministic rules matching the case's worked examples
    rules = FALLBACK_TOOL_RULES.get(business_type, FALLBACK_TOOL_RULES["other"])
    matched_by_type: dict[str, dict] = {}
    for t in available_tools:
        matched_by_type.setdefault(t["tool_type"], t)
    recs = []
    for rule in rules:
        tool = matched_by_type.get(rule["tool_type"])
        recs.append({
            "tool_id": tool["id"] if tool else None,
            "title": rule["title"],
            "description": tool["description"] if tool else rule["title"],
            "reason": rule["reason"],
            "priority": rule["priority"],
            "source": "rules",
        })
    return recs


def generate_campaign_copy(
    business_type: str,
    campaign_type: str,
    discount_value: float,
    channel: str,
    goal: str,
    business_name: str = "",
    custom_prompt: str | None = None,
) -> dict:
    """Return {title, text, predicted_roi, generated_by_ai}."""
    label = BUSINESS_TYPE_LABELS.get(business_type, business_type)
    goal_label = GOAL_LABELS.get(goal, goal)

    system_prompt = (
        "Ты — AI-копирайтер платформы UpWise для малого офлайн-бизнеса в Казахстане. "
        "Пиши короткие, тёплые, продающие тексты акций на русском языке, готовые к рассылке. "
        "Отвечай СТРОГО в формате JSON без markdown-обёртки: "
        '{"title": "...", "text": "...", "predicted_roi": <число от 1.0 до 6.0>}.'
    )
    user_prompt = (
        f"Бизнес: {business_name or label} ({label}). Цель: {goal_label}.\n"
        f"Тип акции: {campaign_type}. Скидка/бонус: {discount_value}%. Канал рассылки: {channel}.\n"
    )
    if custom_prompt:
        user_prompt += f"Дополнительное пожелание владельца бизнеса: {custom_prompt}\n"
    user_prompt += "Придумай короткий заголовок акции и текст сообщения (2-3 предложения, с эмодзи уместно)."

    result = _call_claude_json(system_prompt, user_prompt)
    if result and result.get("title") and result.get("text"):
        try:
            roi = float(result.get("predicted_roi", 2.5))
        except (TypeError, ValueError):
            roi = 2.5
        return {
            "title": str(result["title"])[:255],
            "text": str(result["text"]),
            "predicted_roi": round(max(1.0, min(roi, 6.0)), 2),
            "generated_by_ai": True,
        }

    templates = FALLBACK_CAMPAIGN_TEMPLATES.get(business_type, FALLBACK_CAMPAIGN_TEMPLATES["other"])
    template = templates.get(campaign_type, templates["discount"])
    title = template["title"].format(discount=int(discount_value))
    text = template["text"].format(discount=int(discount_value))
    base_roi = {"discount": 2.2, "bonus": 2.6, "coupon": 2.0, "combo": 3.1}.get(campaign_type, 2.0)
    return {
        "title": title,
        "text": text,
        "predicted_roi": base_roi,
        "generated_by_ai": False,
    }
