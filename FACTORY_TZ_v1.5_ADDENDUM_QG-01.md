# FACTORY_TZ_v1.5_ADDENDUM_QG-01 — проверка гейтов допуска

## Назначение

QG-01 добавляет fail-closed слой допуска поверх существующих проверок. Цель — не дать зелёному локальному отчёту пройти, если обязательная проверка отсутствует, отключена, помечена `skip` без явного правила, привязана к старому артефакту или была выполнена до смены модели, профиля, правил или конфигурации.

Дополнение связано с требованиями F05/F22 для доказательств проверки и негативных контролей, а также с F21/F26 для повторного допуска после смены источника, модели, правил или конфигурации.

## Обязательные правила

1. `skip` не является `pass`. Для обязательного PR/release-гейта `skip` допускается только по явной политике с причиной, областью и отражением в отчёте.
2. В PR/release-режиме должны быть видны базовые проверки: diff, docs-state scope, change-spec, architecture inputs, architecture, governance, workflow artifacts, secret scan, contract structure, SQL safety, source stability, Python quality tools и Python discovery/coverage.
3. Фокусный docs/state-профиль может заменить полный discovery, coverage и factory postgres exit только когда selector явно признал inventory допустимым и назвал все пропущенные проверки.
4. Проверка `factory-postgres-exit` может быть пропущена в repository sandbox только с точной причиной отсутствия nested container/database capability.
5. Отчёт допуска должен содержать отдельный результат `quality-gate`. Общий `status` и `check_status` должны учитывать этот результат.
6. Артефакты публикации и результаты попыток должны оставаться привязанными к source SHA, candidate SHA, profile/spec/model/config identity и attempt number. Подмена любого связанного байта должна блокировать допуск.

## Негативные сценарии

- QG-NEG-01: обязательная проверка отсутствует в отчёте. Ожидание: `quality-gate=fail`.
- QG-NEG-02: обязательная проверка вернула `skip` без allowlist-причины. Ожидание: `quality-gate=fail`.
- QG-NEG-03: coverage отсутствует или отключён в PR/release при наличии Python discovery. Ожидание: блокировка допуска.
- QG-NEG-04: docs/state профиль пытается скрыть runtime/test change. Ожидание: selector переводит проверку в full PR suite.
- QG-NEG-05: артефакт или sidecar относится к другому candidate/source/profile/spec/attempt. Ожидание: отказ с кодом integrity/binding.
- QG-NEG-06: подтверждение было получено до смены модели, правил, профиля или конфигурации. Ожидание: требуется новая квалификация.

## Критерии приёмки

- Верификатор создаёт `quality-gate` после `source-stability`.
- `status` и `check_status` не могут быть `pass`, если `quality-gate` вернул `fail`.
- Есть unit-тесты на отсутствие обязательной проверки, неразрешённый `skip`, разрешённый docs/state skip и разрешённый repository sandbox skip.
- QG-01 описан в репозитории как отдельное Markdown-дополнение к ТЗ.
