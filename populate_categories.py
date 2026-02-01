import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, AsyncClient
from loguru import logger
from slugify import slugify

# --- Настройка Supabase ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")
supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)

HIERARCHY = {
    "Программирование и Разработка": [
        "Python", "JavaScript", "TypeScript", "PHP", "Go", "Java", "C#", "C++", "Ruby", "Rust", "Swift", "Kotlin", "Bash/Shell",
        "Node.js", "Django", "Flask", "FastAPI", "Laravel", "Spring", "ASP.NET", "Ruby on Rails", "Express.js", "NestJS", ".NET",
        "React", "Vue.js", "Angular", "Svelte", "jQuery", "Next.js", "Nuxt.js", "Web Components", "Android", "iOS",
        "React Native", "Flutter", "Swift/Objective-C (Mobile)", "Kotlin/Java (Mobile)", "Electron", "WPF", "Qt",
        "Swift/Objective-C (Desktop)", "Kotlin/Java (Desktop)", "Unity", "Unreal Engine", "Godot", "Game Development",
        "Embedded Systems", "IoT", "C/C++ (Low-Level)", "Assembler", "1С-Битрикс/Bitrix Framework"
    ],
    "Инфраструктура и DevOps": [
        "AWS", "Google Cloud (GCP)", "Microsoft Azure", "Yandex.Cloud", "DigitalOcean", "Heroku", "Docker", "Kubernetes",
        "OpenShift", "Podman", "Helm", "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "Travis CI", "Argo CD",
        "Ansible", "Terraform", "Puppet", "Chef", "SaltStack", "Prometheus", "Grafana",
        "ELK Stack (Elasticsearch, Logstash, Kibana)", "Sentry", "Datadog", "VMware", "VirtualBox", "KVM", "Xen",
        "Linux", "Windows Server", "macOS", "Unix", "Сетевое администрирование", "Протоколы", "Firewall"
    ],
    "Базы Данных": [
        "PostgreSQL", "MySQL", "MariaDB", "SQL Server", "Oracle", "SQLite", "MongoDB", "Redis", "Cassandra", "Neo4j",
        "Couchbase", "Elasticsearch (DB)", "Data Warehousing", "Data Lake", "Snowflake", "BigQuery", "GraphQL (DB)",
        "REST API Design"
    ],
    "Искусственный Интеллект и Машинное Обучение": [
        "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "Data Science", "MLOps", "Нейронные сети", "Computer Vision",
        "NLP (Обработка Естественного Языка)", "LLMs (Large Language Models)", "Diffusion Models", "GANs", "Алгоритмы ML",
        "Этика ИИ", "Теория ML"
    ],
    "Безопасность (Cybersecurity)": [
        "OWASP", "XSS", "SQL Injection", "CSRF", "Пентестинг", "IDS/IPS", "VPN", "OAuth", "OpenID Connect", "JWT", "SSO",
        "Криптография", "Шифрование", "Хеширование", "TLS/SSL", "Threat Modeling", "Security Best Practices"
    ],
    "Дизайн и UX/UI": [
        "UX Дизайн", "UI Дизайн", "Figma", "Sketch", "Adobe XD", "Прототипирование", "Веб-дизайн", "Адаптивный дизайн",
        "CSS Frameworks (Tailwind CSS, Bootstrap)", "Webflow", "Графический Дизайн", "Типографика", "Иконография", "Брендинг"
    ],
    "Менеджмент и Бизнес в IT": [
        "Agile", "Scrum", "Kanban", "Waterfall", "Jira", "Trello", "Product Management", "Стратегия продукта", "MVP",
        "Бизнес-анализ", "Аналитика", "Метрики", "KPI", "Карьера в IT", "Собеседования", "Резюме", "Развитие карьеры",
        "Soft Skills", "Стартапы", "Инвестиции", "Бизнес-модели"
    ],
    "Общие IT-Темы": [
        "Новости IT", "Тренды в IT", "Технические Блоги", "Статьи (IT)", "Обзоры (IT)", "Конференции/Мероприятия (IT)",
        "Образование/Курсы (IT)", "Open Source", "Книги/Ресурсы (IT)", "Другое (IT)"
    ]
}

def generate_slug(text):
    """
    Генерирует slug из текста.
    """
    return slugify(text, replacements=[['+', '-plus-'], ['/', '-or-'], ['(', ''], [')', '']])

async def populate_categories():
    """
    Заполняет таблицу categories данными из иерархии.
    """
    logger.info("Populating categories table...")

    # Сначала вставляем родительские категории
    parent_categories_to_insert = []
    for parent_name in HIERARCHY.keys():
        parent_categories_to_insert.append({
            "name": parent_name,
            "slug": generate_slug(parent_name),
            "parent_category": None
        })
    
    logger.info(f"Inserting {len(parent_categories_to_insert)} parent categories...")
    response = supabase.table("categories").upsert(parent_categories_to_insert, on_conflict="name").execute()
    if response.data:
        logger.success(f"Successfully inserted/updated {len(response.data)} parent categories.")
    else:
        logger.error(f"Failed to insert parent categories. Response: {response}")

    # Затем вставляем дочерние категории
    child_categories_to_insert = []
    for parent_name, children in HIERARCHY.items():
        for child_name in children:
            child_categories_to_insert.append({
                "name": child_name,
                "slug": generate_slug(child_name),
                "parent_category": parent_name
            })

    logger.info(f"Inserting {len(child_categories_to_insert)} child categories...")
    response = supabase.table("categories").upsert(child_categories_to_insert, on_conflict="name").execute()
    if response.data:
        logger.success(f"Successfully inserted/updated {len(response.data)} child categories.")
    else:
        logger.error(f"Failed to insert child categories. Response: {response}")


async def main():
    await populate_categories()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception("Произошла глобальная ошибка в работе программы:")
