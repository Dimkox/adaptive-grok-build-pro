# SEO Landing showcase

Статическая русская витрина repository-local Codex skill `$seo-landing`.

## Локальный просмотр

Из корня репозитория:

```bash
python3 -m http.server 4173 --directory side-projects/seo-landing-showcase
```

Откройте `http://127.0.0.1:4173/`.

## Воспроизводимый browser contract

Runner не требует npm-пакетов и использует Node.js 24 и локальный Chrome. Из
корня репозитория, пока showcase-сервер работает на порту `8765`:

```bash
node side-projects/seo-landing-showcase/browser-contract.mjs \
  --url http://127.0.0.1:8765/ \
  --output engineering/changes/20260901-codex-seo-landing-side-project-23b06c/evidence/showcase \
  --chrome /usr/bin/google-chrome
```

Runner запускает изолированный headless Chrome, проверяет overflow на ширинах
320/768/1280/1920, reduced-motion и первый keyboard focus, затем записывает
`browser-contract.json` и четыре PNG в указанный каталог. Вместо запуска Chrome
можно передать уже работающий endpoint через `--cdp-url http://127.0.0.1:9222`.

## Границы

- Нет JavaScript, внешних шрифтов, изображений, аналитики и сетевых runtime-зависимостей.
- `browser-contract.mjs` — локальный test runner, он не загружается страницей.
- CTA показывает локальный prompt и ничего не отправляет.
- Страница содержит `noindex, nofollow` и не содержит canonical или `og:url`, потому что production origin не задан.
- Включение индексации требует отдельного изменения с реальным каноническим URL и повторной проверкой абсолютных ссылок.

Проверки и фактические результаты хранятся в change package, а не заявляются внутри витрины.
