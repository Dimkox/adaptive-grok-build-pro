from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .repo import RepoProfile, detect_repo
from .util import git_default_base, load_json, now_utc, tree_fingerprint, unique_ordered


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    'incident': ('incident', 'outage', 'авар', 'прод упал', 'production down', 'срочно почин', 'hotfix'),
    'bugfix': ('bug', 'fix', 'repair', 'ошиб', 'баг', 'сломал', 'не работает', 'исправ', 'regression', 'exception', 'fatal'),
    'review': ('review', 'ревью', 'проверь код', 'аудит кода', 'code review', 'pull request', ' pr '),
    'release': ('release', 'релиз', 'deploy', 'деплой', 'publish', 'выкат', 'rollback', 'canary'),
    'test': ('test', 'тест', 'coverage', 'покрытие', 'phpunit', 'cypress', 'playwright'),
    'refactor': ('refactor', 'рефактор', 'legacy', 'легаси', 'модерниз', 'переписать', 'передел'),
    'architecture': ('architecture', 'архитект', 'design system', 'новая подсистема', 'microservice', 'микросервис'),
    'research': ('research', 'исслед', 'разберись', 'проанализируй', 'сравни', 'spike'),
    'feature': ('feature', 'фича', 'добав', 'реализ', 'сделай', 'создай', 'build', 'implement', 'develop'),
    'docs': ('documentation', 'документац', 'readme', 'инструкц', 'описание'),
}

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    'bitrix': ('bitrix', 'битрикс', 'd7', 'инфоблок', 'iblock', 'highload', 'hl-блок', 'битрикс24', 'crm bitrix'),
    'php': ('php', 'composer', 'symfony', 'laravel', 'phpunit', 'phpstan'),
    'frontend': ('frontend', 'фронтенд', 'ui', 'интерфейс', 'javascript', 'typescript', 'react', 'vue', 'cypress', 'css'),
    'api': ('api', 'rest', 'graphql', 'endpoint', 'эндпоинт', 'openapi', 'webhook'),
    'event': ('event-driven', 'event', 'событи', 'asyncapi', 'kafka', 'rabbitmq', 'queue', 'очеред'),
    'data': ('sql', 'database', 'база данных', 'миграц', 'clickhouse', 'elasticsearch', 'opensearch', 'postgres', 'mysql', 'индекс'),
    'integration': ('integration', 'интеграц', '1c', '1с', 'sap', 'erp', 'wms', 'bitrix24 rest', 'external system', 'внешн'),
    'ai': ('rag', 'llm', ' ai ', 'искусственный интеллект', 'генеративн', 'нейросет', 'prompt injection', 'embedding', 'vector store', 'ai agent'),
    'infra': ('terraform', 'kubernetes', 'docker', 'ci/cd', 'github actions', 'инфраструктур', 'devops'),
    'security': ('security', 'безопасност', 'auth', 'oauth', 'permission', 'права', 'роль', 'pii', 'персональн', 'secret', 'prompt injection', 'tenant isolation', 'изоляц'),
}

HIGH_RISK = (
    'production', 'прод', 'deploy', 'деплой', 'delete', 'удалить данные', 'drop table', 'truncate',
    'auth', 'oauth', 'permission', 'права доступа', 'billing', 'платеж', 'payment', 'pii', 'персональн',
    'secret', 'credential', 'пароль', 'irreversible', 'необрат', 'sap write', '1c write', '1с запись',
    'prompt injection', 'tenant isolation', 'изоляция арендат',
)
MEDIUM_RISK = (
    'migration', 'миграц', 'api', 'event', 'событи', 'integration', 'интеграц', 'database', 'sql',
    'legacy', 'рефактор', 'module install', 'установка модуля', 'cache', 'кеш', 'agent', 'агент битрикс',
)

FOLLOW_UP_RE = re.compile(
    r'^\s*(да|нет|ок|окей|делай|продолжай|согласен|согласна|go|continue|yes|no|вариант\s+[abcабв123]|[abcабв123])\s*[.!]?\s*$',
    re.IGNORECASE,
)
CLOSED_ROUTE_STATUSES = frozenset({'ready', 'released', 'completed', 'cancelled', 'archived'})
FEATURE_LIKE_INTENTS = frozenset({'feature', 'architecture', 'refactor', 'research'})
DEFAULT_ANALYSIS_CAP = 10

DEFAULT_ROUTING: dict[str, Any] = {
    'schema_version': 1,
    'max_parallel_analysis': DEFAULT_ANALYSIS_CAP,
    'write_roles': [
        'ai_implementer',
        'bitrix_implementer',
        'data_implementer',
        'frontend_implementer',
        'general_implementer',
        'integration_implementer',
        'php_implementer',
    ],
    'analysis_floors': {
        'always': ['repo_explorer'],
        'feature_like': ['task_analyst'],
        'standard': ['architect', 'docs_researcher'],
    },
    'analysis_domain_agents': {
        'bitrix': ['bitrix_architect'],
        'api': ['integration_architect'],
        'event': ['integration_architect'],
        'integration': ['integration_architect'],
        'data': ['data_architect'],
        'ai': ['ai_architect'],
    },
    'review_floors': {
        'delivery': ['code_reviewer', 'test_reviewer'],
        'docs': ['code_reviewer'],
        'review_intent': ['code_reviewer', 'test_reviewer'],
        'release': ['release_reviewer'],
    },
    'review_domain_agents': {
        'bitrix': ['bitrix_reviewer'],
        'data': ['data_reviewer'],
        'security': ['security_reviewer'],
        'ai': ['security_reviewer'],
        'integration': ['security_reviewer'],
    },
    'review_risk_agents': {
        'high': ['security_reviewer', 'release_reviewer'],
    },
}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def _analysis_cap(config: dict[str, Any]) -> int:
    raw = config.get('max_parallel_analysis', DEFAULT_ANALYSIS_CAP)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        return DEFAULT_ANALYSIS_CAP
    return raw


def load_routing_config(root: Path) -> dict[str, Any]:
    data = load_json(root / '.grok-stack/config/routing.json', None)
    merged = copy.deepcopy(DEFAULT_ROUTING)
    if not isinstance(data, dict):
        return merged
    cap = data.get('max_parallel_analysis')
    if isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1:
        merged['max_parallel_analysis'] = cap
    roles = _string_list(data.get('write_roles'))
    if roles:
        merged['write_roles'] = roles
    for key in (
        'analysis_floors',
        'analysis_domain_agents',
        'review_floors',
        'review_domain_agents',
        'review_risk_agents',
    ):
        value = data.get(key)
        if not isinstance(value, dict):
            continue
        base = merged.setdefault(key, {})
        if not isinstance(base, dict):
            merged[key] = value
            continue
        for sub, items in value.items():
            if isinstance(items, list):
                base[str(sub)] = _string_list(items)
    return merged


@dataclass
class Route:
    schema_version: int
    route_id: str
    created_at: str
    session_id: str
    task: str
    intent: str
    domains: list[str]
    task_domains: list[str]
    risk: str
    complexity: str
    repo: dict[str, object]
    base_commit: str | None
    base_fingerprint: str
    primary_skill: str
    workflow_skills: list[str]
    analysis_agents: list[str]
    write_agent: str | None
    review_agents: list[str]
    allowed_agents: list[str]
    quality_profiles: list[str]
    required_evidence: list[str]
    human_gates: list[str]
    delivery_expected: bool
    status: str = 'routed'
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _score(text: str, mapping: dict[str, tuple[str, ...]]) -> dict[str, int]:
    lowered = f' {text.lower()} '
    scores: dict[str, int] = {}
    for label, keywords in mapping.items():
        score = sum(2 if ' ' in word.strip() else 1 for word in keywords if word in lowered)
        if score:
            scores[label] = score
    return scores


def _best_intent(text: str) -> str:
    scores = _score(text, INTENT_KEYWORDS)
    if not scores:
        return 'feature'

    # Defect, release, review and architectural intent must not be masked by
    # secondary words such as "add a regression test". Generic implementation
    # verbs are deliberately lower priority than the concrete work type.
    for intent in ('incident', 'bugfix', 'review', 'release', 'refactor', 'architecture', 'research', 'docs'):
        if scores.get(intent):
            return intent

    lowered = text.lower().strip()
    test_primary = (
        re.search(
            r'^(?:добав(?:ь|ить)|напиш(?:и|ите)|созда(?:й|йте)|сдела(?:й|йте))\s+'
            r'(?:(?:регрессионн|интеграционн|юнит|unit|e2e|phpunit|cypress|playwright)\w*\s+)*'
            r'(?:тест|tests?|coverage)',
            lowered,
        )
        or re.search(r'^(?:покрой|покрыть)\b.*\b(?:тест|coverage)', lowered)
    )
    if scores.get('test') and (test_primary or not scores.get('feature')):
        return 'test'
    if scores.get('feature'):
        return 'feature'
    if scores.get('test'):
        return 'test'
    return next(iter(scores))


def _task_domains(text: str) -> list[str]:
    scores = _score(text, DOMAIN_KEYWORDS)
    return [label for label, score in sorted(scores.items(), key=lambda item: (-item[1], item[0])) if score > 0]


def _domains(text: str, repo: RepoProfile) -> tuple[list[str], list[str]]:
    task_domains = _task_domains(text)
    combined = unique_ordered([*task_domains, *repo.domains]) or ['generic']
    return combined, task_domains


def _has_term(text: str, term: str) -> bool:
    """Match risk/domain terms as words, not as substrings of larger words.

    `'прод' in 'продукт'` is True and was classifying ordinary product work as production.
    """
    haystack = f' {text.lower()} '
    needle = term.lower().strip()
    if not needle:
        return False
    if ' ' in needle:
        return needle in haystack
    return re.search(r'(?<![\w])' + re.escape(needle) + r'(?![\w])', haystack, re.UNICODE) is not None


def _risk(text: str, intent: str, domains: list[str]) -> tuple[str, list[str]]:
    rationale: list[str] = []
    high = [word for word in HIGH_RISK if _has_term(text, word)]
    medium = [word for word in MEDIUM_RISK if _has_term(text, word)]
    if high or intent in {'incident', 'release'} or 'security' in domains:
        rationale.append('high-risk signal: ' + ', '.join(high[:5]) if high else f'high-risk intent/domain: {intent}')
        return 'high', rationale
    if medium or intent in {'architecture', 'refactor'} or any(d in domains for d in ('integration', 'data', 'api', 'event', 'ai')):
        rationale.append('medium-risk integration, contract, data, AI, or modernization work')
        return 'medium', rationale
    rationale.append('bounded change without high-risk signals')
    return 'low', rationale


def _complexity(intent: str, risk: str, domains: list[str], text: str) -> str:
    if risk == 'high' or intent in {'architecture', 'incident', 'release'} or len(domains) >= 4:
        return 'high-risk'
    if risk == 'low' and intent in {'bugfix', 'docs', 'test'} and len(text) < 300 and len(domains) <= 2:
        return 'micro'
    return 'standard'


def should_reuse_active_route(prompt: str) -> bool:
    return bool(FOLLOW_UP_RE.match(prompt or ''))


def can_reuse_active_route(prompt: str, existing: dict | None, session_id: str | None) -> bool:
    if not existing or not should_reuse_active_route(prompt):
        return False
    if existing.get('session_id') != session_id:
        return False
    if existing.get('status') in CLOSED_ROUTE_STATUSES:
        return False
    return True


def is_development_prompt(prompt: str, repo: RepoProfile) -> bool:
    if should_reuse_active_route(prompt):
        return False
    scores = _score(prompt, INTENT_KEYWORDS)
    if scores:
        return True
    lowered = prompt.lower()
    technical = any(word in lowered for words in DOMAIN_KEYWORDS.values() for word in words)
    return technical and len(prompt.strip()) > 12


def build_route(root: Path, prompt: str, session_id: str = 'manual') -> Route:
    repo = detect_repo(root)
    intent = _best_intent(prompt)
    domains, task_domains = _domains(prompt, repo)
    risk, rationale = _risk(prompt, intent, domains)
    complexity = _complexity(intent, risk, domains, prompt)

    cfg = load_routing_config(root)
    floors = cfg.get('analysis_floors') if isinstance(cfg.get('analysis_floors'), dict) else {}
    analysis: list[str] = list(_string_list(floors.get('always')))
    feature_like = intent in FEATURE_LIKE_INTENTS
    if feature_like:
        analysis.extend(_string_list(floors.get('feature_like')))
    if complexity != 'micro':
        analysis.extend(_string_list(floors.get('standard')))
    elif feature_like:
        analysis.append('architect')
    domain_agents = cfg.get('analysis_domain_agents') if isinstance(cfg.get('analysis_domain_agents'), dict) else {}
    for domain in domains:
        analysis.extend(_string_list(domain_agents.get(domain)))
    cap = _analysis_cap(cfg)
    analysis = unique_ordered(analysis)[:cap]

    no_write_intents = {'review', 'research', 'release'}
    write_agent: str | None = None
    if intent not in no_write_intents:
        explicit = set(task_domains)
        # Explicit task focus wins over repository background. This matters in
        # polyglot and Bitrix repositories where not every change is a D7 change.
        if 'ai' in explicit:
            write_agent = 'ai_implementer'
        elif 'frontend' in explicit and 'bitrix' not in explicit:
            write_agent = 'frontend_implementer'
        elif 'data' in explicit and 'integration' not in explicit:
            write_agent = 'data_implementer'
        elif any(d in explicit for d in ('integration', 'api', 'event')) and 'bitrix' not in explicit:
            write_agent = 'integration_implementer'
        elif 'bitrix' in explicit or 'bitrix' in repo.domains:
            write_agent = 'bitrix_implementer'
        elif 'php' in explicit or 'php' in repo.domains:
            write_agent = 'php_implementer'
        elif 'frontend' in domains:
            write_agent = 'frontend_implementer'
        else:
            write_agent = 'general_implementer'

    review_floors = cfg.get('review_floors') if isinstance(cfg.get('review_floors'), dict) else {}
    review_domain = cfg.get('review_domain_agents') if isinstance(cfg.get('review_domain_agents'), dict) else {}
    review_risk = cfg.get('review_risk_agents') if isinstance(cfg.get('review_risk_agents'), dict) else {}
    review: list[str] = []
    if write_agent:
        review.extend(_string_list(review_floors.get('docs' if intent == 'docs' else 'delivery')))
    elif intent == 'review':
        review.extend(_string_list(review_floors.get('review_intent')))
    if 'bitrix' in domains:
        review.extend(_string_list(review_domain.get('bitrix')))
    if risk == 'high':
        review.extend(_string_list(review_risk.get('high')))
    elif any(d in domains for d in ('security', 'ai', 'integration')):
        for key in ('security', 'ai', 'integration'):
            if key in domains:
                review.extend(_string_list(review_domain.get(key)))
    if 'data' in domains:
        review.extend(_string_list(review_domain.get('data')))
    if intent == 'release' or risk == 'high':
        review.extend(_string_list(review_floors.get('release')))

    workflow_skills = ['adaptive-delivery']
    intent_skill = {
        'bugfix': 'bugfix-workflow',
        'incident': 'incident-response',
        'feature': 'feature-workflow',
        'architecture': 'feature-workflow',
        'refactor': 'legacy-modernization',
        'release': 'release-readiness',
        'review': 'verification-evidence',
        'test': 'verification-evidence',
        'research': 'task-triage',
        'docs': 'task-triage',
    }.get(intent, 'feature-workflow')
    workflow_skills.append(intent_skill)
    for domain, skill in [
        ('bitrix', 'bitrix-development'),
        ('api', 'api-event-change'),
        ('event', 'api-event-change'),
        ('data', 'data-change'),
        ('integration', 'enterprise-integration'),
        ('frontend', 'frontend-change'),
        ('ai', 'ai-rag-change'),
        ('security', 'security-sensitive-change'),
    ]:
        if domain in domains:
            workflow_skills.append(skill)

    profiles = ['base']
    for domain, profile in [
        ('php', 'php'), ('bitrix', 'bitrix'), ('frontend', 'frontend'),
        ('api', 'contracts'), ('event', 'contracts'), ('data', 'data'),
        ('integration', 'integration'), ('ai', 'ai'), ('infra', 'infra'),
    ]:
        if domain in domains:
            profiles.append(profile)

    evidence: list[str] = []
    if write_agent or intent in {'review', 'release', 'test'}:
        evidence.append('verification')
    if 'code_reviewer' in review:
        evidence.append('code_review')
    if 'test_reviewer' in review:
        evidence.append('test_review')
    if 'bitrix_reviewer' in review:
        evidence.append('bitrix_review')
    if 'security_reviewer' in review:
        evidence.append('security_review')
    if 'data_reviewer' in review:
        evidence.append('data_review')
    if 'release_reviewer' in review:
        evidence.append('release_review')

    human_gates: list[str] = []
    if complexity == 'high-risk' or intent == 'architecture':
        human_gates.append('scope_and_design_approval')
    if any(d in domains for d in ('integration', 'data')) and risk == 'high':
        human_gates.append('migration_or_external_write_approval')
    if intent == 'release' or any(_has_term(prompt, word) for word in ('production', 'прод', 'deploy', 'деплой')):
        human_gates.append('production_action_approval')

    delivery_expected = intent != 'research'
    route_seed = f'{session_id}|{prompt}|{tree_fingerprint(root)}'
    route_id = hashlib.sha256(route_seed.encode()).hexdigest()[:12]
    allowed = unique_ordered([*analysis, *(review or []), *([write_agent] if write_agent else [])])

    rationale.extend([
        f'intent={intent}',
        f'domains={",".join(domains)}',
        f'repository={repo.kind}',
        f'write-owner={write_agent or "none"}',
        f'analysis-wave={len(analysis)}/{cap}',
    ])

    return Route(
        schema_version=1,
        route_id=route_id,
        created_at=now_utc(),
        session_id=session_id,
        task=prompt.strip(),
        intent=intent,
        domains=domains,
        task_domains=task_domains,
        risk=risk,
        complexity=complexity,
        repo=repo.to_dict(),
        base_commit=git_default_base(root),
        base_fingerprint=tree_fingerprint(root),
        primary_skill='adaptive-delivery',
        workflow_skills=unique_ordered(workflow_skills),
        analysis_agents=unique_ordered(analysis),
        write_agent=write_agent,
        review_agents=unique_ordered(review),
        allowed_agents=allowed,
        quality_profiles=unique_ordered(profiles),
        required_evidence=unique_ordered(evidence),
        human_gates=human_gates,
        delivery_expected=delivery_expected,
        rationale=rationale,
    )


def route_context(route: Route | dict[str, object]) -> str:
    data = route.to_dict() if isinstance(route, Route) else route
    analysis = ', '.join(data.get('analysis_agents', [])) or 'none'
    reviews = ', '.join(data.get('review_agents', [])) or 'none'
    skills = ', '.join(f'${name}' for name in data.get('workflow_skills', []))
    gates = ', '.join(data.get('human_gates', [])) or 'none'
    return (
        'ADAPTIVE GROK ROUTE\n'
        f"Route ID: {data.get('route_id')}\n"
        f"Intent: {data.get('intent')} | Risk: {data.get('risk')} | Complexity: {data.get('complexity')}\n"
        f"Domains: {', '.join(data.get('domains', []))} (task focus: {', '.join(data.get('task_domains', [])) or 'repository default'})\n"
        f"Required skills: {skills}\n"
        f"Parallel read-only analysis agents: {analysis}\n"
        f"Single write owner: {data.get('write_agent') or 'none'}\n"
        f"Parallel review agents after implementation: {reviews}\n"
        f"Quality profiles: {', '.join(data.get('quality_profiles', []))}\n"
        f"Human gates: {gates}\n"
        'Use /adaptive-delivery. Do not spawn agents outside the route. '
        'Run every listed read-only analysis agent in parallel (cap is a ceiling, not a quota). '
        'Keep exactly one write owner.'
    )
