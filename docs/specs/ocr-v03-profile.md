# AECCTX OCR v0.3 profile

Status: Normative bounded profile for ACX-29

## Closed runtime and licensing

The only runtime is Tesseract `5.3.4` in the reviewed Linux OCI boundary. The
only language-data packages are Ubuntu Noble `tesseract-ocr-eng`,
`tesseract-ocr-spa` and `tesseract-ocr-por`, each version `1:4.1.0-2`. The
engine and trained-data distributions are Apache-2.0; Pillow remains HPND.
No caller may select an executable, library, tessdata directory, model path,
configuration file or arbitrary Tesseract variable.

## Closed request profiles

`ocr_profile` MUST be one of:

| profile | language | PSM | layout contract |
| --- | --- | --- | --- |
| `eng-auto-v1` | `eng` | 3 | automatic blocks, lines and words |
| `eng-column-v1` | `eng` | 4 | one column, blocks, lines and words |
| `eng-block-v1` | `eng` | 6 | one uniform block, lines and words |
| `spa-block-v1` | `spa` | 6 | one uniform block, lines and words |
| `por-block-v1` | `por` | 6 | one uniform block, lines and words |
| `eng-table-v1` | `eng` | 6 | bounded inferred table grid |

`orientation_degrees` MUST be one of `0`, `90`, `180` or `270`, interpreted as
the clockwise correction applied before OCR. `dpi` is an integer in
`[70,1200]`; `minimum_confidence` is finite in `[0,100]`. Unknown keys fail
closed. Language combinations, scripts outside Latin, caller-selected PSM and
all unlisted profiles are unsupported.

## `aecctx.ocr.layout.v1`

The provider emits exactly one event validated by
`schemas/v0.2/ocr-layout.schema.json`. It binds the source SHA-256, original
pixel dimensions, correction, profile, language, PSM, and ordered blocks,
lines and words. TSV page/block/paragraph/line/word identifiers are retained.
Bounding boxes are integer source-pixel rectangles after the exact inverse
orthogonal transform. Provider order is known only when the complete retained
TSV hierarchy is monotonic; otherwise `reading_order` is `unknown` and no
order is invented.

Every word/line/block is inferred evidence. Request, response, runtime, input
artifact and input-region hashes remain attached through the provider
attestation and inference envelope. Native PDF text and OCR remain independent;
conflict produces an explicit conflicted assertion and diagnostic.

## Bounded table inference

Only `eng-table-v1` attempts table inference. A single table is emitted when
there are at least two lines, every line contains the same two-to-eight words,
and corresponding word horizontal centres differ by no more than 12 pixels.
Rows and cells reference retained word indices; topology is `known` only for
that closed condition. Otherwise the event contains a table result with
`topology.state = unknown` and reason `AECCTX_OCR_TABLE_TOPOLOGY_NOT_ESTABLISHED`.
No cell spans, merged cells, borders, semantic headers or spreadsheet meaning
are claimed.

## Safety, determinism and claim ceiling

Inputs remain subject to the existing OCI limits and a 100,000,000-pixel
ceiling. Network is disabled. Corrupt rasters, hash drift, invalid TSV,
out-of-bounds geometry, excessive records and configurations outside this
profile fail closed. Blank and low-confidence input succeeds with explicit
no-text evidence. Live Linux arm64 and amd64 results must be replay-equivalent
for every public request profile.

The claim `pdf-image.ocr-layout` may be public `partial` only for the exact
matrix above. OCR is never source identity, authoritative geometry, hidden
geometry, measurement, validation completeness or consumer semantics. Vision,
arbitrary scripts/languages, handwriting and table semantics remain unsupported.

