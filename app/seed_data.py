import json
import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Business,
    BusinessTypeOption,
    Campaign,
    CampaignTemplate,
    Category,
    Customer,
    Tool,
    User,
)
from app.scoring import compute_customer_scores
from app.security import hash_password

CATEGORIES = [
    {"name": "Маркетинг", "slug": "marketing", "description": "Привлечение новых клиентов"},
    {"name": "Продажи", "slug": "sales", "description": "Инструменты для управления продажами и клиентской базой"},
    {"name": "Удержание клиентов", "slug": "retention", "description": "Программы лояльности и повторные визиты"},
    {"name": "Аналитика", "slug": "analytics", "description": "Отчёты и метрики бизнеса"},
    {"name": "Автоматизация", "slug": "automation", "description": "Автоматические уведомления и рассылки"},
]

BUSINESS_TYPES = [
    {"key": "coffee_shop", "label": "Кофейня", "icon": "coffee"},
    {"key": "clothing_store", "label": "Магазин одежды", "icon": "shirt"},
    {"key": "beauty_salon", "label": "Салон красоты", "icon": "sparkles"},
    {"key": "service_point", "label": "Сервисная точка", "icon": "wrench"},
    {"key": "other", "label": "Другое", "icon": "store"},
]

TOOLS = [
    {
        "name": "Конструктор акций",
        "description": "Создавайте акции со скидкой, бонусами или купонами за пару минут — текст и QR-код генерируются автоматически.",
        "category_slug": "marketing",
        "tool_type": "marketing",
        "icon": "megaphone",
        "steps": ["Выберите тип акции", "AI сгенерирует текст", "Опубликуйте и получите QR-код"],
        "example_usage": "Кофейня запускает акцию «2+1» на выходные за 2 минуты.",
    },
    {
        "name": "Акция «2+1»",
        "description": "Готовый шаблон комбо-акции для увеличения частоты визитов.",
        "category_slug": "marketing",
        "tool_type": "marketing",
        "icon": "gift",
        "steps": ["Активируйте шаблон", "Укажите товар", "Запустите рассылку"],
        "example_usage": "Купи 2 капучино — третий в подарок.",
    },
    {
        "name": "Управление клиентской базой (CRM)",
        "description": "Единая база клиентов с историей визитов, покупок и AI-оценкой ценности и риска оттока.",
        "category_slug": "sales",
        "tool_type": "sales",
        "icon": "users",
        "steps": ["Импортируйте или добавьте клиентов", "Платформа рассчитает сегменты", "Действуйте по рекомендациям"],
        "example_usage": "Салон видит, какие клиенты не приходили 60+ дней.",
    },
    {
        "name": "Программа лояльности",
        "description": "Накопительные баллы и бонусы за визиты для повышения удержания клиентов.",
        "category_slug": "retention",
        "tool_type": "retention",
        "icon": "star",
        "steps": ["Настройте правило начисления", "Клиент копит баллы", "Баллы обмениваются на скидку"],
        "example_usage": "Каждый 5-й визит в кофейню — бесплатный напиток.",
    },
    {
        "name": "Скидка на повторный визит",
        "description": "Автоматическое предложение скидки клиентам, которые давно не приходили.",
        "category_slug": "retention",
        "tool_type": "retention",
        "icon": "repeat",
        "steps": ["Задайте период неактивности", "Платформа найдёт клиентов из группы риска", "Отправьте персональную скидку"],
        "example_usage": "Салон возвращает клиентов, не приходивших 45 дней, скидкой 15%.",
    },
    {
        "name": "Простая аналитика продаж",
        "description": "Наглядные графики выручки, новых и повторных клиентов, эффективности акций без сложных настроек.",
        "category_slug": "analytics",
        "tool_type": "analytics",
        "icon": "bar-chart",
        "steps": ["Откройте раздел аналитики", "Выберите период", "Смотрите выводы AI"],
        "example_usage": "Владелец магазина видит, какая акция принесла больше выручки.",
    },
    {
        "name": "Уведомления о скидках",
        "description": "Автоматические SMS/уведомления клиентам о новых акциях и персональных предложениях.",
        "category_slug": "automation",
        "tool_type": "automation",
        "icon": "bell",
        "steps": ["Выберите сегмент клиентов", "Настройте расписание", "Уведомления отправляются автоматически"],
        "example_usage": "Кофейня уведомляет постоянных гостей о скидке в дождливый день.",
    },
    {
        "name": "Напоминание о записи",
        "description": "Автоматическое напоминание клиентам о предстоящем визите, снижает число пропусков.",
        "category_slug": "automation",
        "tool_type": "automation",
        "icon": "calendar",
        "steps": ["Подключите расписание", "Клиент получает напоминание за день", "Снижение неявок"],
        "example_usage": "Салон красоты сокращает пропуски записей на 30%.",
    },
    {
        "name": "Реферальная программа",
        "description": "Клиенты приводят друзей и получают бонус — простой канал бесплатного привлечения.",
        "category_slug": "marketing",
        "tool_type": "marketing",
        "icon": "share-2",
        "steps": ["Настройте бонус за друга", "Клиент делится ссылкой/QR", "Оба получают вознаграждение"],
        "example_usage": "Сервисная точка растёт за счёт рекомендаций постоянных клиентов.",
    },
    {
        "name": "Купоны с QR-кодом",
        "description": "Генерация купонов на скидку с QR-кодом для сканирования на кассе — без интеграции с POS.",
        "category_slug": "sales",
        "tool_type": "sales",
        "icon": "qr-code",
        "steps": ["Создайте купон", "Получите QR-код", "Отсканируйте на кассе при визите клиента"],
        "example_usage": "Магазин одежды выдаёт купон новым подписчикам в Instagram.",
    },
]

CAMPAIGN_TEMPLATES = [
    {"business_type": "coffee_shop", "campaign_type": "combo", "title_template": "Акция «2+1» на напитки",
     "text_template": "Купи 2 напитка — третий получи в подарок! Только сегодня и завтра.", "default_discount": 33, "channel": "qr"},
    {"business_type": "coffee_shop", "campaign_type": "bonus", "title_template": "Бонус за визит",
     "text_template": "Каждый 5-й напиток — бесплатно! Копите баллы лояльности при каждом заказе.", "default_discount": 20, "channel": "sms"},
    {"business_type": "clothing_store", "campaign_type": "discount", "title_template": "Скидка {discount}% на новую коллекцию",
     "text_template": "Только 3 дня: скидка {discount}% на новое поступление.", "default_discount": 15, "channel": "social"},
    {"business_type": "beauty_salon", "campaign_type": "discount", "title_template": "Скидка {discount}% на повторный визит",
     "text_template": "Запишитесь повторно в течение 30 дней и получите скидку {discount}%.", "default_discount": 15, "channel": "sms"},
    {"business_type": "service_point", "campaign_type": "bonus", "title_template": "Бонусная карта постоянного клиента",
     "text_template": "Каждое 6-е обращение — бесплатно.", "default_discount": 16, "channel": "email"},
    {"business_type": "other", "campaign_type": "discount", "title_template": "Скидка {discount}% для клиентов",
     "text_template": "Успейте воспользоваться скидкой {discount}% в ограниченный период.", "default_discount": 10, "channel": "sms"},
]

DEMO_CUSTOMERS = [
    # (name, visits_count, total_spent, days_since_first, days_since_last)
    ("Айгерим Сатпаева", 14, 84000, 220, 3),
    ("Дамир Нурланов", 9, 52000, 160, 8),
    ("Алия Жаксыбекова", 22, 145000, 300, 1),
    ("Ерлан Тулегенов", 2, 9000, 20, 18),
    ("Madina K.", 1, 3200, 4, 4),
    ("Санжар Абенов", 6, 31000, 90, 55),
    ("Гульмира Ахметова", 3, 14500, 45, 40),
    ("Нурсултан Оспанов", 17, 98000, 250, 12),
    ("Дина Кайратовна", 1, 2800, 2, 2),
    ("Тимур Бекенов", 4, 21000, 70, 130),
    ("Аружан Серикова", 11, 67000, 200, 6),
    ("Бекзат Алиев", 1, 4100, 6, 6),
]


def _tool_dict(tool: Tool) -> dict:
    return {"id": tool.id, "name": tool.name, "tool_type": tool.tool_type, "description": tool.description}


def seed(db: Session) -> None:
    if db.query(Category).count() > 0:
        return  # already seeded

    slug_to_category: dict[str, Category] = {}
    for cat in CATEGORIES:
        obj = Category(**cat)
        db.add(obj)
        db.flush()
        slug_to_category[obj.slug] = obj

    for bt in BUSINESS_TYPES:
        db.add(BusinessTypeOption(**bt))

    tools_by_type: dict[str, Tool] = {}
    for tool_data in TOOLS:
        category = slug_to_category[tool_data["category_slug"]]
        tool = Tool(
            name=tool_data["name"],
            description=tool_data["description"],
            category_id=category.id,
            tool_type=tool_data["tool_type"],
            icon=tool_data["icon"],
            steps=json.dumps(tool_data["steps"], ensure_ascii=False),
            example_usage=tool_data["example_usage"],
            is_active=True,
        )
        db.add(tool)
        db.flush()
        tools_by_type.setdefault(tool.tool_type, tool)

    for tmpl in CAMPAIGN_TEMPLATES:
        db.add(CampaignTemplate(**tmpl))

    admin = User(
        email="admin@upwise.kz",
        hashed_password=hash_password("admin123"),
        business_name="UpWise Platform",
        is_admin=True,
    )
    db.add(admin)

    demo_user = User(
        email="demo@upwise.kz",
        hashed_password=hash_password("demo1234"),
        business_name='Кофейня "Утро"',
        is_admin=False,
    )
    db.add(demo_user)
    db.flush()

    db.add(Business(
        user_id=demo_user.id,
        business_type="coffee_shop",
        size="small",
        goal="retention",
        avg_check=1800.0,
        city="Алматы",
    ))

    today = date.today()
    for name, visits, spent, since_first, since_last in DEMO_CUSTOMERS:
        first_visit = today - timedelta(days=since_first)
        last_visit = today - timedelta(days=since_last)
        value_score, churn_risk, segment = compute_customer_scores(visits, spent, first_visit, last_visit, today)
        db.add(Customer(
            user_id=demo_user.id,
            name=name,
            phone=None,
            email=None,
            first_visit=first_visit,
            last_visit=last_visit,
            visits_count=visits,
            total_spent=spent,
            value_score=value_score,
            churn_risk_score=churn_risk,
            segment=segment,
        ))

    marketing_tool = tools_by_type.get("marketing")
    retention_tool = tools_by_type.get("retention")
    db.add(Campaign(
        user_id=demo_user.id,
        tool_id=marketing_tool.id if marketing_tool else None,
        title="Акция «2+1» на напитки",
        campaign_type="combo",
        text="Купи 2 напитка — третий получи в подарок! Только на этой неделе.",
        channel="qr",
        segment="all",
        discount_value=33,
        status="active",
        predicted_roi=3.1,
        generated_by_ai=False,
        sent_count=140,
        redeemed_count=52,
        qr_token=uuid.uuid4().hex,
    ))
    db.add(Campaign(
        user_id=demo_user.id,
        tool_id=retention_tool.id if retention_tool else None,
        title="Скидка 15% для тех, кто давно не заходил",
        campaign_type="discount",
        text="Соскучились по вашему любимому капучино? Скидка 15% ждёт вас в течение 7 дней.",
        channel="sms",
        segment="at_risk",
        discount_value=15,
        status="completed",
        predicted_roi=2.4,
        generated_by_ai=False,
        sent_count=38,
        redeemed_count=11,
        qr_token=uuid.uuid4().hex,
    ))

    db.commit()
