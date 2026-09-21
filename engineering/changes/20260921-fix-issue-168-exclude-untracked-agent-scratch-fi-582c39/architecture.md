# Bounded design

Keep the repair at changed_files/util so routing, verification, receipts and grants share one interpretation. Recognize exactly top-level .qwen/tmp/ with a directory boundary; preserve literal Git pathname identity and do not resolve symlinks to classify disposal. Following independent review, Git NUL inventories use binary output, filesystem-byte decoding, and Git's actual forward-slash directory delimiters. A literal POSIX backslash is filename data, never a directory separator. Fingerprinting re-encodes filenames and symlink targets through filesystem encoding, and JSON serialization uses lossless escapes for otherwise unencodable surrogate code points.

Establish tracked ownership from a successful NUL-separated index lookup and tracked diff provenance. Diff paths protect staged deletions absent from the index. Apply this override before existing noise checks; only genuinely untracked paths receive scratch/cache exclusions. No persistent tracking cache. Do not put the new prefix into an unconditional filter.

If tracking inspection fails or times out, disable the new scratch exemption and retain candidate bytes. Non-Git trees retain scratch; unborn repositories must not use absent HEAD as proof of untracked ownership. Preserve changed_files(base=...) scope. This bounded repair does not claim to solve every pre-existing Git-subcommand failure.

The four analysis reports under evidence support these decisions. No new dependency, public API/event/schema contract or production data migration is introduced. Canonical governance records remain separate authority; no rule/debt adoption or exception is created.
