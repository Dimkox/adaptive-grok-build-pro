# Recovery

Source delivery may be superseded by a corrective PR. Once022 is applied, recover via a later forward migration restoring prior behavior if needed; never edit/delete applied resources or ledger rows. Failed transactional migration retains the recorded prefix and permits retry after releasing contention. Package/DB readiness requires equal migration versions, so coordinate rollout/drain and verify readiness; no production operation is authorized by this source package.
